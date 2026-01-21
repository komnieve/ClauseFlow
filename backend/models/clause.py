"""Data models for clause extraction."""

from enum import Enum
from pydantic import BaseModel, Field


class ChunkType(str, Enum):
    """Type of document chunk."""
    CLAUSE = "clause"
    ADMINISTRATIVE = "administrative"
    BOILERPLATE = "boilerplate"
    HEADER = "header"
    SIGNATURE = "signature"


class ClauseReference(BaseModel):
    """Reference to a clause by line numbers (no text copying)."""
    start_line: int = Field(..., ge=1, description="First line of the clause (1-indexed, inclusive)")
    end_line: int = Field(..., ge=1, description="Last line of the clause (1-indexed, inclusive)")
    clause_number: str | None = Field(None, description="Clause number like '1.3' or '7.2.1'")
    clause_title: str | None = Field(None, description="Title of the clause if present")
    chunk_type: ChunkType = Field(..., description="Type of this chunk")


class ExtractionResult(BaseModel):
    """Result of clause extraction from a document."""
    clauses: list[ClauseReference] = Field(default_factory=list)


class ExtractedClause(BaseModel):
    """A clause with its actual text extracted using line references."""
    reference: ClauseReference
    text: str = Field(..., description="The actual clause text extracted from the document")

    @property
    def start_line(self) -> int:
        return self.reference.start_line

    @property
    def end_line(self) -> int:
        return self.reference.end_line

    @property
    def clause_number(self) -> str | None:
        return self.reference.clause_number

    @property
    def clause_title(self) -> str | None:
        return self.reference.clause_title

    @property
    def chunk_type(self) -> ChunkType:
        return self.reference.chunk_type
