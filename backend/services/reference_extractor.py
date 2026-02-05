"""Reference document processing pipeline — extracts metadata and requirements from reference specs."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from openai import OpenAI
from sqlalchemy.orm import Session

from config import settings
from models.db_models import ReferenceDocument, ReferenceRequirement, ReferenceDocStatus
from models.reference_extraction import (
    ReferenceDocMetadataOutput,
    RequirementExtractionOutput,
    SpecBookSplitOutput,
)
from services.preprocessor import add_line_numbers, extract_lines


def process_reference_document(ref_doc_id: int, text: str, db: Session):
    """
    Full pipeline for processing a reference document:
    1. Add line numbers
    2. Detect multi-spec book
    3. Extract metadata (identifier, version, title)
    4. Extract requirements
    5. Save to DB
    """
    ref_doc = db.query(ReferenceDocument).filter(ReferenceDocument.id == ref_doc_id).first()
    if not ref_doc:
        return

    client = OpenAI(api_key=settings.openai_api_key)
    model = settings.openai_model

    try:
        doc = add_line_numbers(text)

        # Step 1: Detect multi-spec book
        split_result = detect_multi_spec(client, model, doc.numbered_text)

        if split_result.is_multi_spec and len(split_result.specs) > 1:
            # Create child documents for each spec
            for spec in split_result.specs:
                child_text = extract_lines(doc, spec.start_line, spec.end_line)
                child = ReferenceDocument(
                    customer_id=ref_doc.customer_id,
                    filename=f"{ref_doc.filename} [{spec.doc_identifier}]",
                    original_text=child_text,
                    total_lines=spec.end_line - spec.start_line + 1,
                    status=ReferenceDocStatus.PROCESSING,
                    doc_identifier=spec.doc_identifier,
                    version=spec.version,
                    title=spec.title,
                    parent_id=ref_doc.id,
                )
                db.add(child)
                db.flush()

                # Process each child recursively
                _process_single_spec(client, model, child, child_text, db)

            # Parent is just a container
            ref_doc.status = ReferenceDocStatus.READY
            db.commit()
            return

        # Single spec — process directly
        _process_single_spec(client, model, ref_doc, text, db)
        db.commit()

    except Exception as e:
        ref_doc.status = ReferenceDocStatus.ERROR
        ref_doc.error_message = str(e)
        db.commit()
        raise


def _process_single_spec(client: OpenAI, model: str, ref_doc: ReferenceDocument, text: str, db: Session):
    """Process a single specification document."""
    doc = add_line_numbers(text)

    # Step 2: Extract metadata (only if not already provided)
    if not ref_doc.doc_identifier or not ref_doc.title:
        metadata = extract_reference_metadata(client, model, doc.numbered_text)
        if not ref_doc.doc_identifier and metadata.doc_identifier:
            ref_doc.doc_identifier = metadata.doc_identifier
        if not ref_doc.version and metadata.version:
            ref_doc.version = metadata.version
        if not ref_doc.title and metadata.title:
            ref_doc.title = metadata.title

    # Step 3: Extract requirements
    req_result = extract_requirements(client, model, doc.numbered_text)

    for req in req_result.requirements:
        try:
            req_text = extract_lines(doc, req.start_line, req.end_line)
        except ValueError:
            req_text = None

        db_req = ReferenceRequirement(
            reference_document_id=ref_doc.id,
            requirement_number=req.requirement_number,
            title=req.title,
            text=req_text,
            start_line=req.start_line,
            end_line=req.end_line,
        )
        db.add(db_req)

    ref_doc.status = ReferenceDocStatus.READY


def detect_multi_spec(client: OpenAI, model: str, numbered_text: str) -> SpecBookSplitOutput:
    """Detect whether a document contains multiple specifications."""
    response = client.beta.chat.completions.parse(
        model=model,
        messages=[
            {
                "role": "system",
                "content": "You analyze reference documents to determine if they contain a single specification or multiple specifications bundled together.",
            },
            {
                "role": "user",
                "content": f"""Analyze this document and determine if it contains ONE specification or MULTIPLE separate specifications bundled into a book.

A multi-spec book typically has:
- A table of contents listing multiple specs
- Clear boundaries between different spec documents
- Each spec has its own identifier (e.g., SPXQC-17, SPXQC-40)

If it's a single spec, set is_multi_spec=false and leave specs empty.
If it's multiple specs, set is_multi_spec=true and identify each spec's boundaries.

Document:
---
{numbered_text[:8000]}
---""",
            },
        ],
        response_format=SpecBookSplitOutput,
        temperature=0.1,
    )
    return response.choices[0].message.parsed


def extract_reference_metadata(client: OpenAI, model: str, numbered_text: str) -> ReferenceDocMetadataOutput:
    """Extract metadata (identifier, version, title) from a reference document."""
    response = client.beta.chat.completions.parse(
        model=model,
        messages=[
            {
                "role": "system",
                "content": "You extract metadata from reference specifications and standards documents.",
            },
            {
                "role": "user",
                "content": f"""Extract the document identifier, version, and title from this reference specification.

Examples:
- doc_identifier: "SPXQC-17", version: null, title: "SOURCE INSPECTION"
- doc_identifier: "AS9100", version: "Rev D", title: "Quality Management Systems"
- doc_identifier: "SPX-00000874", version: "v57.0", title: null

Document (first 3000 chars):
---
{numbered_text[:3000]}
---""",
            },
        ],
        response_format=ReferenceDocMetadataOutput,
        temperature=0.1,
    )
    return response.choices[0].message.parsed


def extract_requirements(client: OpenAI, model: str, numbered_text: str) -> RequirementExtractionOutput:
    """Extract individual requirements from a reference document."""
    response = client.beta.chat.completions.parse(
        model=model,
        messages=[
            {
                "role": "system",
                "content": "You analyze reference specifications to identify individual requirements and their boundaries.",
            },
            {
                "role": "user",
                "content": f"""Identify each discrete requirement in this reference specification.

Each requirement typically has:
- A number (e.g., 4.2.1, REQ-17, paragraph 3.a)
- A title (optional)
- Body text describing the requirement

Return the start and end line numbers for each requirement.
Include all sub-requirements within their parent's range.

Document:
---
{numbered_text}
---""",
            },
        ],
        response_format=RequirementExtractionOutput,
        temperature=0.1,
        max_completion_tokens=16384,
    )
    return response.choices[0].message.parsed
