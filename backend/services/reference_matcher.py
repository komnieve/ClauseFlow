"""Reference matching service — detects spec references in PO clauses and matches against the customer's library."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from openai import OpenAI
from sqlalchemy.orm import Session
from sqlalchemy import func

from config import settings
from models.db_models import (
    Document, Clause, ClauseReferenceLink, ReferenceDocument,
    MatchStatus,
)
from models.reference_extraction import ReferenceDetectionResultOutput
from services.preprocessor import add_line_numbers


REFERENCE_DETECTION_PROMPT = """You are analyzing clauses from a purchase order to identify references to external specifications, standards, or documents.

Look for patterns like:
- Spec identifiers: "SPXQC-17", "AS9100 Rev D", "MIL-STD-1520"
- Document references: "per SPX-00000874 v57.0", "in accordance with SPXQC-40"
- Standard callouts: "AS9102", "ISO 9001:2015"

For each reference found, return:
- The clause's start/end lines
- The spec identifier (normalized, e.g. "SPXQC-17" not "spxqc17")
- The version if specified
- Brief context of how it's referenced

DO NOT flag generic references like "this PO" or "the contract".
Only flag specific external document/spec identifiers.

Clauses:
---
{clauses_text}
---"""


def detect_references_in_clauses(doc: Document, clauses: list[Clause]) -> list[dict]:
    """
    Use LLM to scan clause texts for external spec references.

    Returns list of dicts with clause_start_line, clause_end_line, spec_identifier, version, context.
    """
    if not clauses:
        return []

    client = OpenAI(api_key=settings.openai_api_key)
    model = settings.openai_model

    # Build a text block with all clauses for the LLM
    clause_lines = []
    for c in clauses:
        clause_lines.append(f"[Lines {c.start_line}-{c.end_line}] {c.clause_number or ''} {c.clause_title or ''}")
        clause_lines.append(c.text)
        clause_lines.append("")

    clauses_text = "\n".join(clause_lines)

    # Truncate if too long
    if len(clauses_text) > 50000:
        clauses_text = clauses_text[:50000] + "\n... (truncated)"

    prompt = REFERENCE_DETECTION_PROMPT.format(clauses_text=clauses_text)

    response = client.beta.chat.completions.parse(
        model=model,
        messages=[
            {
                "role": "system",
                "content": "You identify references to external specifications and standards in purchase order clauses.",
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        response_format=ReferenceDetectionResultOutput,
        temperature=0.1,
        max_completion_tokens=8192,
    )

    parsed = response.choices[0].message.parsed
    if not parsed:
        return []

    return [
        {
            "clause_start_line": ref.clause_start_line,
            "clause_end_line": ref.clause_end_line,
            "spec_identifier": ref.spec_identifier,
            "version": ref.version,
            "context": ref.context,
        }
        for ref in parsed.references
    ]


def match_references_to_library(
    detected: list[dict],
    customer_id: int,
    clauses: list[Clause],
    db: Session,
) -> list[ClauseReferenceLink]:
    """
    Match detected references against the customer's reference library.

    Returns ClauseReferenceLink objects (not yet committed).
    """
    links = []

    # Build lookup of clause by line range
    clause_by_lines = {}
    for c in clauses:
        clause_by_lines[(c.start_line, c.end_line)] = c

    # Pre-load customer's reference docs for matching
    customer_ref_docs = (
        db.query(ReferenceDocument)
        .filter(ReferenceDocument.customer_id == customer_id)
        .all()
    )

    # Build a normalized lookup: identifier -> list of ref docs
    ref_doc_lookup = {}
    for rd in customer_ref_docs:
        if rd.doc_identifier:
            key = _normalize_identifier(rd.doc_identifier)
            ref_doc_lookup.setdefault(key, []).append(rd)

    for det in detected:
        clause = clause_by_lines.get((det["clause_start_line"], det["clause_end_line"]))
        if not clause:
            # Try fuzzy match by start_line
            clause = next(
                (c for c in clauses if c.start_line == det["clause_start_line"]),
                None,
            )
        if not clause:
            continue

        norm_id = _normalize_identifier(det["spec_identifier"])
        matching_docs = ref_doc_lookup.get(norm_id, [])

        if not matching_docs:
            # Unresolved
            link = ClauseReferenceLink(
                clause_id=clause.id,
                detected_spec_identifier=det["spec_identifier"],
                detected_version=det.get("version"),
                match_status=MatchStatus.UNRESOLVED,
            )
        else:
            # Check version match
            det_version = det.get("version")
            exact_match = None
            partial_match = None

            for rd in matching_docs:
                if det_version and rd.version:
                    if _normalize_version(rd.version) == _normalize_version(det_version):
                        exact_match = rd
                        break
                    else:
                        partial_match = rd
                elif not det_version:
                    # No version specified — match the first doc
                    exact_match = rd
                    break
                else:
                    partial_match = rd

            if exact_match:
                link = ClauseReferenceLink(
                    clause_id=clause.id,
                    reference_document_id=exact_match.id,
                    detected_spec_identifier=det["spec_identifier"],
                    detected_version=det.get("version"),
                    match_status=MatchStatus.MATCHED,
                )
            elif partial_match:
                link = ClauseReferenceLink(
                    clause_id=clause.id,
                    reference_document_id=partial_match.id,
                    detected_spec_identifier=det["spec_identifier"],
                    detected_version=det.get("version"),
                    match_status=MatchStatus.PARTIAL,
                )
            else:
                link = ClauseReferenceLink(
                    clause_id=clause.id,
                    detected_spec_identifier=det["spec_identifier"],
                    detected_version=det.get("version"),
                    match_status=MatchStatus.UNRESOLVED,
                )

        links.append(link)

    return links


def run_reference_matching(document_id: int, db: Session):
    """
    Orchestrate reference detection and matching for a document.

    1. Load document and clauses
    2. Detect references via LLM
    3. Match against customer's library
    4. Save ClauseReferenceLink records
    """
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document or not document.customer_id:
        return

    clauses = (
        db.query(Clause)
        .filter(Clause.document_id == document_id)
        .order_by(Clause.start_line)
        .all()
    )

    if not clauses:
        return

    # Step 1: Detect references in clauses
    detected = detect_references_in_clauses(document, clauses)

    if not detected:
        return

    # Step 2: Match against customer's library
    links = match_references_to_library(detected, document.customer_id, clauses, db)

    # Step 3: Save links
    for link in links:
        db.add(link)

    db.commit()


def _normalize_identifier(identifier: str) -> str:
    """Normalize a spec identifier for case-insensitive matching."""
    return identifier.strip().upper().replace(" ", "").replace("-", "").replace("_", "")


def _normalize_version(version: str) -> str:
    """Normalize a version string for comparison."""
    return version.strip().lower().replace(" ", "")
