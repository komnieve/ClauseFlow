"""ERP mock adapter — JSON-backed clause library for verification."""

import json
import os
import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class ERPClause:
    """A clause from the ERP system."""
    clause_code: str
    title: str
    text: str
    revision: Optional[str] = None
    effective_date: Optional[str] = None
    source_document: Optional[str] = None


@dataclass
class VerificationResult:
    """Result of verifying a PO clause against ERP."""
    status: str  # matched, mismatched, not_found, external_pending
    erp_clause: Optional[ERPClause] = None
    mismatch_details: Optional[str] = None


# Default path for the mock ERP library JSON
_DEFAULT_LIBRARY_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "erp_library.json",
)

_library_cache: Optional[dict[str, ERPClause]] = None
_library_path: Optional[str] = None


def _normalize_code(code: str) -> str:
    """Normalize a clause code for comparison.

    Uppercase, collapse whitespace, strip common punctuation noise.
    """
    code = code.upper().strip()
    code = re.sub(r"\s+", " ", code)
    # Normalize common variations: "FAR 52.204-21" == "FAR52.204-21"
    # But keep the space between alpha prefix and number for readability
    return code


def _load_library(path: Optional[str] = None) -> dict[str, ERPClause]:
    """Load the ERP clause library from JSON. Returns {normalized_code: ERPClause}."""
    global _library_cache, _library_path

    path = path or os.environ.get("ERP_LIBRARY_PATH", _DEFAULT_LIBRARY_PATH)

    if _library_cache is not None and _library_path == path:
        return _library_cache

    if not os.path.exists(path):
        print(f"  ERP library not found at {path} — using empty library")
        _library_cache = {}
        _library_path = path
        return _library_cache

    with open(path, "r") as f:
        data = json.load(f)

    library = {}
    for entry in data.get("clauses", []):
        clause = ERPClause(
            clause_code=entry["clause_code"],
            title=entry.get("title", ""),
            text=entry.get("text", ""),
            revision=entry.get("revision"),
            effective_date=entry.get("effective_date"),
            source_document=entry.get("source_document"),
        )
        normalized = _normalize_code(clause.clause_code)
        library[normalized] = clause

    _library_cache = library
    _library_path = path
    print(f"  ERP library loaded: {len(library)} clauses from {path}")
    return library


def reload_library(path: Optional[str] = None):
    """Force reload of the ERP library (e.g., after editing the JSON)."""
    global _library_cache, _library_path
    _library_cache = None
    _library_path = None
    _load_library(path)


def _looks_like_external_reference(clause_text: str, clause_title: Optional[str]) -> bool:
    """Heuristic: does this clause look like an external document reference?"""
    combined = (clause_text or "") + " " + (clause_title or "")
    combined_lower = combined.lower()

    # URL patterns
    if re.search(r"https?://", combined):
        return True

    # "See document X" / "per document X" / "refer to" patterns
    if re.search(r"\b(see|refer\s+to|per|in\s+accordance\s+with)\s+(document|spec|specification|standard)\b", combined_lower):
        # Only if the clause is short (a reference pointer, not a full clause)
        if len(clause_text or "") < 500:
            return True

    return False


def find_clause(code: Optional[str], title: Optional[str] = None) -> Optional[ERPClause]:
    """Find a clause in the ERP library by code or title."""
    library = _load_library()

    if code:
        normalized = _normalize_code(code)
        if normalized in library:
            return library[normalized]

        # Try partial match (e.g., "52.204-21" matches "FAR 52.204-21")
        for lib_code, clause in library.items():
            if normalized in lib_code or lib_code in normalized:
                return clause

    # Title-based fallback (fuzzy)
    if title:
        title_lower = title.lower().strip()
        for clause in library.values():
            if clause.title and title_lower in clause.title.lower():
                return clause

    return None


def verify_clause(
    clause_code: Optional[str],
    clause_title: Optional[str],
    clause_text: str,
    po_revision: Optional[str] = None,
    po_date: Optional[str] = None,
) -> VerificationResult:
    """Verify a single PO clause against the ERP library.

    Matching logic (per review feedback):
    1. If clause looks like an external reference → external_pending
    2. Normalize code, exact lookup
    3. No candidate → not_found
    4. Candidate found → compare revision/date
       - Same code, different revision/date → mismatched
       - Same code, matching or no revision/date → matched
    """
    # Step 1: Check for external reference
    if _looks_like_external_reference(clause_text, clause_title):
        return VerificationResult(status="external_pending")

    # Step 2: Find in ERP
    erp_clause = find_clause(clause_code, clause_title)

    # Step 3: No candidate
    if erp_clause is None:
        return VerificationResult(status="not_found")

    # Step 4: Compare revision/date
    mismatch_parts = []

    if po_revision and erp_clause.revision:
        # Normalize revisions for comparison
        po_rev_norm = po_revision.strip().upper()
        erp_rev_norm = erp_clause.revision.strip().upper()
        if po_rev_norm != erp_rev_norm:
            mismatch_parts.append(
                f"Revision mismatch: PO has '{po_revision}', ERP has '{erp_clause.revision}'"
            )

    if po_date and erp_clause.effective_date:
        po_date_norm = po_date.strip()
        erp_date_norm = erp_clause.effective_date.strip()
        if po_date_norm != erp_date_norm:
            mismatch_parts.append(
                f"Date mismatch: PO has '{po_date}', ERP has '{erp_clause.effective_date}'"
            )

    if mismatch_parts:
        return VerificationResult(
            status="mismatched",
            erp_clause=erp_clause,
            mismatch_details="; ".join(mismatch_parts),
        )

    return VerificationResult(
        status="matched",
        erp_clause=erp_clause,
    )


def list_all_clauses() -> list[ERPClause]:
    """Return all clauses in the ERP library."""
    library = _load_library()
    return list(library.values())
