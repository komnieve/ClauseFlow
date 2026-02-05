"""V2 Document segmentation service — Pass 1 of the two-pass extraction pipeline.

Identifies major document sections (header, T&C, line items, attachments, etc.)
and extracts line item metadata from the header section.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from openai import OpenAI
from config import settings
from services.preprocessor import NumberedDocument, extract_lines
from models.segmentation import (
    SectionReferenceOutput,
    SegmentationResultOutput,
    LineItemMetadataOutput,
    LineItemExtractionOutput,
    SectionReference,
    SegmentationResult,
    LineItemMetadata,
)

MAX_OUTPUT_TOKENS = 16384


SEGMENTATION_PROMPT = """You are analyzing a contract/purchase order document to identify its major sections.

The document has been pre-processed with line numbers in the format [NNN] at the start of each line.

Your task is to identify the major SECTIONS of this document by their line number boundaries.

SECTION TYPES:
- "header" = The document preamble: PO number, dates, addresses, supplier info, AND the line items table (parts, quantities, prices). This is typically everything before the first named terms section.
- "terms_and_conditions" = Named sections containing contractual clauses/requirements (e.g., "SECTION 1: GENERAL PROVISIONS", "SECTION 2: QUALITY REQUIREMENTS"). Each named section should be its own entry.
- "line_item" = ONLY use this if the document has per-line-item sections with their own dedicated clauses (rare). Do NOT use this for the line items table in the header.
- "signature" = Signature blocks, acceptance/acknowledgment sections
- "attachment" = Attachments, appendices, exhibits, technical data packages
- "other" = Anything that doesn't fit the above categories

CRITICAL RULES:
1. Every line in the document must belong to exactly ONE section — no gaps, no overlaps
2. Sections must cover line 1 through the last line contiguously
3. Each named T&C section (SECTION 1, SECTION 2, etc.) should be its own entry
4. The header section includes everything from the start through the line items table, up to (but not including) the first T&C section
5. Include section headers (like "SECTION 2: QUALITY REQUIREMENTS") as the first line of their section, not as a separate entry
6. Attachments at the end should each be their own section if they are clearly separated

GUIDELINES:
- Look for clear section breaks: "SECTION N:", "PART N:", divider lines (====), etc.
- Number sections in order using order_index starting from 0
- Provide the section_title as it appears in the document
- Provide the section_number if present (e.g., "1", "2", "A")"""


LINE_ITEM_EXTRACTION_PROMPT = """You are analyzing the header/preamble section of a purchase order to extract line item details.

The text below is from the header section of a PO, which contains a table of line items (parts being ordered).

Your task is to extract each line item with its details:
- line_number: The PO line item number (1, 2, 3, etc.)
- part_number: The part number or item number
- description: Description of the item
- quantity: Quantity ordered (include unit if present, e.g., "50 EA", "100 units")
- quality_level: Quality level, inspection level, or quality class if specified
- start_line: The document line number where this line item starts
- end_line: The document line number where this line item ends

If the line items span multiple lines each, include all lines for that item in the start_line/end_line range.
If quality_level is not explicitly stated, leave it null."""


def segment_document(
    doc: NumberedDocument,
    model: str | None = None
) -> SegmentationResult:
    """
    Pass 1: Use LLM to identify major document sections.

    Args:
        doc: Document with line numbers added
        model: Model to use (defaults to settings.openai_model)

    Returns:
        SegmentationResult with section boundaries
    """
    client = OpenAI(api_key=settings.openai_api_key)
    model = model or settings.openai_model

    response = client.beta.chat.completions.parse(
        model=model,
        messages=[
            {
                "role": "system",
                "content": "You are an expert at analyzing legal and contractual documents. You identify document structure precisely using line numbers."
            },
            {
                "role": "user",
                "content": f"{SEGMENTATION_PROMPT}\n\nDocument ({doc.total_lines} total lines):\n---\n{doc.numbered_text}\n---"
            }
        ],
        response_format=SegmentationResultOutput,
        temperature=0.1,
        max_completion_tokens=MAX_OUTPUT_TOKENS,
    )

    parsed = response.choices[0].message.parsed
    if parsed is None:
        raise ValueError("Failed to parse segmentation response — got None")

    # Convert to internal models
    sections = []
    for item in parsed.sections:
        sections.append(SectionReference(
            start_line=item.start_line,
            end_line=item.end_line,
            section_type=item.section_type,
            section_title=item.section_title,
            section_number=item.section_number,
            line_item_number=item.line_item_number,
        ))

    return SegmentationResult(sections=sections)


def validate_segmentation(
    sections: list[SectionReference],
    total_lines: int
) -> tuple[list[SectionReference], list[str]]:
    """
    Validate segmentation results: no gaps, no overlaps, full coverage.

    Fixes minor issues (e.g., off-by-one gaps) automatically.

    Args:
        sections: List of section references from LLM
        total_lines: Total lines in the document

    Returns:
        Tuple of (fixed_sections, warnings)
    """
    if not sections:
        return sections, ["No sections found"]

    warnings = []

    # Sort by start_line
    sections = sorted(sections, key=lambda s: s.start_line)

    # Fix: ensure first section starts at line 1
    if sections[0].start_line != 1:
        gap = sections[0].start_line - 1
        if gap <= 5:
            sections[0] = sections[0].model_copy(update={"start_line": 1})
            warnings.append(f"Fixed: extended first section to start at line 1 (was {sections[0].start_line + gap})")
        else:
            warnings.append(f"First section starts at line {sections[0].start_line}, expected line 1")

    # Fix gaps and overlaps between adjacent sections
    for i in range(len(sections) - 1):
        current = sections[i]
        next_sec = sections[i + 1]

        gap = next_sec.start_line - current.end_line - 1
        if gap > 0 and gap <= 3:
            # Small gap — extend current section to fill it
            sections[i] = current.model_copy(update={"end_line": next_sec.start_line - 1})
            warnings.append(
                f"Fixed: extended section '{current.section_title or current.section_type}' "
                f"end_line from {current.end_line} to {next_sec.start_line - 1} to fill {gap}-line gap"
            )
        elif gap > 3:
            warnings.append(
                f"Gap of {gap} lines between '{current.section_title or current.section_type}' "
                f"(ends line {current.end_line}) and '{next_sec.section_title or next_sec.section_type}' "
                f"(starts line {next_sec.start_line})"
            )

        overlap = current.end_line - next_sec.start_line + 1
        if overlap > 0:
            # Overlap — shrink current section
            sections[i] = current.model_copy(update={"end_line": next_sec.start_line - 1})
            warnings.append(
                f"Fixed: shrunk section '{current.section_title or current.section_type}' "
                f"end_line from {current.end_line} to {next_sec.start_line - 1} to remove {overlap}-line overlap"
            )

    # Fix: ensure last section ends at total_lines
    last = sections[-1]
    if last.end_line != total_lines:
        diff = total_lines - last.end_line
        if abs(diff) <= 5:
            sections[-1] = last.model_copy(update={"end_line": total_lines})
            warnings.append(f"Fixed: extended last section to end at line {total_lines} (was {last.end_line})")
        elif diff > 0:
            warnings.append(f"Last section ends at line {last.end_line}, document has {total_lines} lines")

    # Validate coverage
    covered = set()
    for sec in sections:
        for line in range(sec.start_line, sec.end_line + 1):
            covered.add(line)

    expected = set(range(1, total_lines + 1))
    missing = expected - covered
    if missing:
        warnings.append(f"Lines not covered by any section: {sorted(missing)[:20]}{'...' if len(missing) > 20 else ''}")

    return sections, warnings


def extract_line_items_from_section(
    doc: NumberedDocument,
    section: SectionReference,
    model: str | None = None
) -> list[LineItemMetadata]:
    """
    Extract line item metadata from a header section.

    Args:
        doc: Document with line numbers
        section: The header section to extract from
        model: Model to use (defaults to settings.openai_model)

    Returns:
        List of LineItemMetadata
    """
    client = OpenAI(api_key=settings.openai_api_key)
    model = model or settings.openai_model

    # Get the numbered text for just this section
    section_lines = doc.numbered_text.split('\n')
    # Line numbers in numbered_text are 1-indexed, array is 0-indexed
    section_text = '\n'.join(section_lines[section.start_line - 1:section.end_line])

    response = client.beta.chat.completions.parse(
        model=model,
        messages=[
            {
                "role": "system",
                "content": "You are an expert at reading purchase orders and extracting structured data from line item tables."
            },
            {
                "role": "user",
                "content": f"{LINE_ITEM_EXTRACTION_PROMPT}\n\nHeader section (lines {section.start_line}-{section.end_line}):\n---\n{section_text}\n---"
            }
        ],
        response_format=LineItemExtractionOutput,
        temperature=0.1,
        max_completion_tokens=MAX_OUTPUT_TOKENS,
    )

    parsed = response.choices[0].message.parsed
    if parsed is None:
        raise ValueError("Failed to parse line item extraction response — got None")

    # Convert to internal models
    items = []
    for item in parsed.line_items:
        items.append(LineItemMetadata(
            line_number=item.line_number,
            part_number=item.part_number,
            description=item.description,
            quantity=item.quantity,
            quality_level=item.quality_level,
            start_line=item.start_line,
            end_line=item.end_line,
        ))

    return items
