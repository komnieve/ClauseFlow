"""Services package."""

from .preprocessor import NumberedDocument, add_line_numbers, extract_lines
from .clause_extractor import (
    extract_clauses_from_document,
    validate_references,
    extract_clause_texts,
)

__all__ = [
    "NumberedDocument",
    "add_line_numbers",
    "extract_lines",
    "extract_clauses_from_document",
    "validate_references",
    "extract_clause_texts",
]
