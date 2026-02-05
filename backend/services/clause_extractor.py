"""LLM-based clause extraction using line references with structured output."""

import sys
import os
from typing import Literal

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from openai import OpenAI
from pydantic import BaseModel, Field
from config import settings
from models.clause import ClauseReference, ExtractionResult, ExtractedClause, ChunkType
from services.preprocessor import NumberedDocument, extract_lines, add_line_numbers

# Max output tokens for gpt-4o
MAX_OUTPUT_TOKENS = 16384

# Approximate tokens per line (conservative estimate for contracts)
TOKENS_PER_LINE = 15

# Context window limits (leaving room for prompt and output)
MAX_CONTEXT_TOKENS = 100000  # gpt-4o has 128K, leave headroom
MAX_LINES_PER_CHUNK = int(MAX_CONTEXT_TOKENS / TOKENS_PER_LINE)


# Pydantic models for structured output (OpenAI needs these defined separately)
class ClauseReferenceOutput(BaseModel):
    """Reference to a clause by line numbers."""
    start_line: int = Field(..., description="First line of the clause (1-indexed, inclusive)")
    end_line: int = Field(..., description="Last line of the clause (1-indexed, inclusive)")
    clause_number: str | None = Field(None, description="Clause number like '1.3' or '7.2.1', or null if none")
    clause_title: str | None = Field(None, description="Title of the clause if present, or null")
    chunk_type: Literal["clause", "administrative", "boilerplate", "header", "signature"] = Field(
        ...,
        description="Type of chunk: clause (numbered requirement), administrative (header info), boilerplate (dividers), header (section titles), signature (signature blocks)"
    )


class ExtractionResultOutput(BaseModel):
    """Result of clause extraction from a document."""
    clauses: list[ClauseReferenceOutput] = Field(..., description="List of all identified clause references")


EXTRACTION_PROMPT = """You are analyzing a contract/purchase order document to identify discrete clauses and sections.

The document has been pre-processed with line numbers in the format [NNN] at the start of each line.

Your task is to identify where clauses BEGIN and END by their line numbers.

CRITICAL RULES:
1. DO NOT reproduce any text from the document
2. ONLY return line number references
3. A clause includes its header/title line AND all body text until the next clause begins
4. Include subsections with their parent (e.g., if 1.1 has paragraphs (a), (b), (c), include them all in 1.1)

CHUNK TYPES:
- "clause" = A numbered contractual obligation or requirement (e.g., "1.1 ORDER OF PRECEDENCE", "2.3 SOURCE INSPECTION")
- "administrative" = Header info, addresses, contacts, dates, line items, PO details at the start
- "boilerplate" = Divider lines (====), decorative headers
- "header" = Section headers like "SECTION 2: QUALITY REQUIREMENTS" (the header line itself, not the clauses within)
- "signature" = Signature blocks, acceptance sections

GUIDELINES:
- Each numbered clause (1.1, 1.2, 2.1, etc.) should be its own entry
- Section headers (SECTION 1: GENERAL PROVISIONS) are separate "header" entries
- The preamble/header (PO details, addresses, line items before Section 1) is "administrative"
- Attachments at the end can be grouped as single entries
- Make sure clause ranges don't overlap"""


def _extract_chunk(
    client: OpenAI,
    model: str,
    numbered_text: str,
    line_offset: int = 0
) -> list[ClauseReference]:
    """
    Extract clauses from a single chunk of text.

    Args:
        client: OpenAI client
        model: Model to use
        numbered_text: Text with line numbers
        line_offset: Offset to add to line numbers (for chunked processing)

    Returns:
        List of ClauseReference objects
    """
    response = client.beta.chat.completions.parse(
        model=model,
        messages=[
            {
                "role": "system",
                "content": "You are an expert at analyzing legal and contractual documents. You identify clause boundaries precisely using line numbers."
            },
            {
                "role": "user",
                "content": f"{EXTRACTION_PROMPT}\n\nDocument:\n---\n{numbered_text}\n---"
            }
        ],
        response_format=ExtractionResultOutput,
        temperature=0.1,
        max_completion_tokens=MAX_OUTPUT_TOKENS,
    )

    parsed = response.choices[0].message.parsed

    if parsed is None:
        raise ValueError("Failed to parse response - got None")

    # Convert to internal models, applying line offset for chunked docs
    clauses = []
    for item in parsed.clauses:
        clause_ref = ClauseReference(
            start_line=item.start_line + line_offset,
            end_line=item.end_line + line_offset,
            clause_number=item.clause_number,
            clause_title=item.clause_title,
            chunk_type=ChunkType(item.chunk_type)
        )
        clauses.append(clause_ref)

    return clauses


def extract_clauses_from_document(
    doc: NumberedDocument,
    model: str | None = None
) -> ExtractionResult:
    """
    Use OpenAI with structured output to identify clause boundaries in a document.

    Automatically chunks large documents that exceed context limits.

    Args:
        doc: Document with line numbers added
        model: Model to use for extraction (defaults to settings.openai_model)

    Returns:
        ExtractionResult with clause references
    """
    client = OpenAI(api_key=settings.openai_api_key)
    model = model or settings.openai_model

    # Check if we need to chunk
    if doc.total_lines <= MAX_LINES_PER_CHUNK:
        # Single chunk - process entire document
        clauses = _extract_chunk(client, model, doc.numbered_text)
        return ExtractionResult(clauses=clauses)

    # Large document - process in chunks with overlap
    print(f"  Document has {doc.total_lines} lines, chunking (max {MAX_LINES_PER_CHUNK} per chunk)...")

    all_clauses = []
    chunk_overlap = 50  # Overlap lines to avoid splitting clauses
    chunk_start = 0

    while chunk_start < doc.total_lines:
        chunk_end = min(chunk_start + MAX_LINES_PER_CHUNK, doc.total_lines)

        # Extract chunk lines and renumber from 1
        chunk_lines = doc.original_lines[chunk_start:chunk_end]
        chunk_doc = add_line_numbers('\n'.join(chunk_lines))

        print(f"  Processing chunk: lines {chunk_start + 1}-{chunk_end} ({len(chunk_lines)} lines)")

        # Extract with offset so line numbers match original document
        chunk_clauses = _extract_chunk(client, model, chunk_doc.numbered_text, line_offset=chunk_start)

        # For overlapping regions, prefer clauses from earlier chunks
        # (they have more context about clause starts)
        if all_clauses and chunk_start > 0:
            # Filter out clauses that start in the overlap region from previous chunk
            overlap_start = chunk_start
            overlap_end = chunk_start + chunk_overlap
            chunk_clauses = [
                c for c in chunk_clauses
                if c.start_line >= overlap_end or c.end_line <= overlap_start
            ]

        all_clauses.extend(chunk_clauses)

        # Move to next chunk (with overlap)
        chunk_start = chunk_end - chunk_overlap
        if chunk_start >= doc.total_lines - chunk_overlap:
            break

    # Sort by start line and deduplicate
    all_clauses.sort(key=lambda c: c.start_line)

    return ExtractionResult(clauses=all_clauses)


def validate_references(
    refs: list[ClauseReference],
    total_lines: int
) -> tuple[list[ClauseReference], list[str]]:
    """
    Validate clause references and return warnings for any issues.

    Args:
        refs: List of clause references from LLM
        total_lines: Total lines in the document

    Returns:
        Tuple of (valid_refs, warnings)
    """
    warnings = []
    valid_refs = []

    for ref in refs:
        issues = []

        if ref.start_line < 1:
            issues.append(f"start_line {ref.start_line} < 1")
        if ref.end_line > total_lines:
            issues.append(f"end_line {ref.end_line} > document length {total_lines}")
        if ref.start_line > ref.end_line:
            issues.append(f"start_line {ref.start_line} > end_line {ref.end_line}")

        if issues:
            warnings.append(f"Clause {ref.clause_number or 'unnamed'} at lines {ref.start_line}-{ref.end_line}: {', '.join(issues)}")
        else:
            valid_refs.append(ref)

    # Check for overlaps
    sorted_refs = sorted(valid_refs, key=lambda r: r.start_line)
    for i in range(len(sorted_refs) - 1):
        current = sorted_refs[i]
        next_ref = sorted_refs[i + 1]
        if current.end_line >= next_ref.start_line:
            warnings.append(
                f"Overlap: {current.clause_number or 'unnamed'} (lines {current.start_line}-{current.end_line}) "
                f"overlaps with {next_ref.clause_number or 'unnamed'} (lines {next_ref.start_line}-{next_ref.end_line})"
            )

    # Check for large gaps (might indicate missed clauses)
    for i in range(len(sorted_refs) - 1):
        gap = sorted_refs[i + 1].start_line - sorted_refs[i].end_line
        if gap > 10:  # More than 10 lines between clauses
            warnings.append(
                f"Gap of {gap} lines between {sorted_refs[i].clause_number or 'unnamed'} "
                f"(ends line {sorted_refs[i].end_line}) and {sorted_refs[i + 1].clause_number or 'unnamed'} "
                f"(starts line {sorted_refs[i + 1].start_line})"
            )

    return valid_refs, warnings


def extract_clause_texts(
    doc: NumberedDocument,
    refs: list[ClauseReference]
) -> list[ExtractedClause]:
    """
    Extract actual text for each clause reference.

    Args:
        doc: The numbered document
        refs: List of validated clause references

    Returns:
        List of ExtractedClause with text filled in
    """
    extracted = []

    for ref in refs:
        text = extract_lines(doc, ref.start_line, ref.end_line)
        extracted.append(ExtractedClause(reference=ref, text=text))

    return extracted


# --- V2: Section-aware extraction ---

def _slice_numbered_text(doc: NumberedDocument, start_line: int, end_line: int) -> str:
    """
    Extract a slice of the numbered text for a section's line range.

    Preserves original line numbers so the LLM output doesn't need offset adjustment.

    Args:
        doc: The numbered document
        start_line: First line (1-indexed, inclusive)
        end_line: Last line (1-indexed, inclusive)

    Returns:
        The numbered text slice with original line numbers preserved
    """
    numbered_lines = doc.numbered_text.split('\n')
    # numbered_lines is 0-indexed, line numbers are 1-indexed
    return '\n'.join(numbered_lines[start_line - 1:end_line])


SECTION_EXTRACTION_PROMPT = """You are analyzing a specific section of a contract/purchase order document to identify discrete clauses.

The text below is from a {section_type} section{title_info}.
{scope_instruction}

The document has been pre-processed with line numbers in the format [NNN] at the start of each line.
The line numbers are from the ORIGINAL document — use them exactly as shown.

Your task is to identify where clauses BEGIN and END by their line numbers.

CRITICAL RULES:
1. DO NOT reproduce any text from the document
2. ONLY return line number references
3. A clause includes its header/title line AND all body text until the next clause begins
4. Include subsections with their parent (e.g., if 1.1 has paragraphs (a), (b), (c), include them all in 1.1)

CHUNK TYPES:
- "clause" = A numbered contractual obligation or requirement (e.g., "1.1 ORDER OF PRECEDENCE", "2.3 SOURCE INSPECTION")
- "administrative" = Header info, addresses, contacts, dates, line items, PO details
- "boilerplate" = Divider lines (====), decorative headers
- "header" = Section headers like "SECTION 2: QUALITY REQUIREMENTS" (the header line itself, not the clauses within)
- "signature" = Signature blocks, acceptance sections

GUIDELINES:
- Each numbered clause (1.1, 1.2, 2.1, etc.) should be its own entry
- Section headers (SECTION 1: GENERAL PROVISIONS) are separate "header" entries
- Make sure clause ranges don't overlap
- Every line in the provided text must belong to some clause entry"""


def extract_clauses_from_section(
    doc: NumberedDocument,
    section_start_line: int,
    section_end_line: int,
    section_type: str,
    section_title: str | None = None,
    model: str | None = None
) -> ExtractionResult:
    """
    V2 Pass 2: Extract clauses from a single document section.

    Uses the section's line range to slice the document, preserving original
    line numbers so no offset adjustment is needed.

    Args:
        doc: The full numbered document
        section_start_line: First line of the section (1-indexed)
        section_end_line: Last line of the section (1-indexed)
        section_type: Type of section (e.g., "terms_and_conditions")
        section_title: Title of the section if available
        model: Model to use (defaults to settings.openai_model)

    Returns:
        ExtractionResult with clause references (using original document line numbers)
    """
    client = OpenAI(api_key=settings.openai_api_key)
    model = model or settings.openai_model

    # Slice the numbered text for this section
    section_text = _slice_numbered_text(doc, section_start_line, section_end_line)

    # Build context-aware prompt
    title_info = f" titled '{section_title}'" if section_title else ""

    if section_type == "terms_and_conditions":
        scope_instruction = "All clauses in this section apply PO-wide (to the entire purchase order)."
    elif section_type == "line_item":
        scope_instruction = "All clauses in this section apply to a specific line item."
    else:
        scope_instruction = ""

    prompt = SECTION_EXTRACTION_PROMPT.format(
        section_type=section_type,
        title_info=title_info,
        scope_instruction=scope_instruction,
    )

    # Use existing _extract_chunk — line numbers are already correct
    clauses = _extract_chunk(client, model, f"{prompt}\n\nSection text:\n---\n{section_text}\n---")

    return ExtractionResult(clauses=clauses)
