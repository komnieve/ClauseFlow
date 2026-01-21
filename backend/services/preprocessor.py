"""Document preprocessing: add line numbers for reference-based extraction."""

from dataclasses import dataclass


@dataclass
class NumberedDocument:
    """A document with line numbers added."""
    numbered_text: str  # Text with [NNN] prefixes for LLM
    original_lines: list[str]  # Original lines without numbers (for extraction)
    total_lines: int


def add_line_numbers(text: str) -> NumberedDocument:
    """
    Add line numbers to document text for reference-based extraction.

    Format: [001] Original line text

    Args:
        text: The raw document text

    Returns:
        NumberedDocument with numbered text and original lines preserved
    """
    lines = text.split('\n')
    total_lines = len(lines)

    # Determine padding width based on total lines
    width = len(str(total_lines))

    # Create numbered version for LLM
    numbered_lines = []
    for i, line in enumerate(lines, start=1):
        numbered_lines.append(f"[{i:0{width}d}] {line}")

    return NumberedDocument(
        numbered_text='\n'.join(numbered_lines),
        original_lines=lines,
        total_lines=total_lines
    )


def extract_lines(doc: NumberedDocument, start_line: int, end_line: int) -> str:
    """
    Extract text from original document using line references.

    Args:
        doc: The numbered document
        start_line: First line to extract (1-indexed, inclusive)
        end_line: Last line to extract (1-indexed, inclusive)

    Returns:
        The extracted text as a single string
    """
    # Convert to 0-indexed
    start_idx = start_line - 1
    end_idx = end_line  # slice end is exclusive, so this gives us inclusive end_line

    if start_idx < 0 or end_idx > doc.total_lines or start_idx >= end_idx:
        raise ValueError(f"Invalid line range: {start_line}-{end_line} (document has {doc.total_lines} lines)")

    return '\n'.join(doc.original_lines[start_idx:end_idx])
