"""Pydantic models for LLM structured output during reference document processing and matching."""

from typing import Literal
from pydantic import BaseModel, Field


# --- Reference Document Extraction ---

class ReferenceDocMetadataOutput(BaseModel):
    """LLM output: metadata extracted from a reference document."""
    doc_identifier: str | None = Field(None, description="Document identifier like 'SPXQC-17' or 'AS9100'")
    version: str | None = Field(None, description="Version like 'v57.0' or 'Rev D'")
    title: str | None = Field(None, description="Full title of the document/specification")


class ExtractedRequirementOutput(BaseModel):
    """LLM output: a single requirement from a reference document."""
    requirement_number: str | None = Field(None, description="Requirement number like '4.2.1' or 'REQ-17'")
    title: str | None = Field(None, description="Title of the requirement")
    start_line: int = Field(..., description="First line of the requirement (1-indexed, inclusive)")
    end_line: int = Field(..., description="Last line of the requirement (1-indexed, inclusive)")


class RequirementExtractionOutput(BaseModel):
    """LLM output: all requirements from a reference document."""
    requirements: list[ExtractedRequirementOutput] = Field(..., description="List of all identified requirements")


class SpecBoundaryOutput(BaseModel):
    """A single spec boundary within a multi-spec book."""
    doc_identifier: str = Field(..., description="Identifier for this spec")
    version: str | None = Field(None, description="Version if present")
    title: str | None = Field(None, description="Title of this spec")
    start_line: int = Field(..., description="First line of this spec (1-indexed)")
    end_line: int = Field(..., description="Last line of this spec (1-indexed)")


class SpecBookSplitOutput(BaseModel):
    """LLM output: whether a document is a single spec or a book of specs."""
    is_multi_spec: bool = Field(..., description="True if this document contains multiple separate specifications")
    specs: list[SpecBoundaryOutput] = Field(default_factory=list, description="If multi-spec, the boundaries of each spec")


# --- Reference Matching (PO Pass 3) ---

class DetectedReferenceOutput(BaseModel):
    """A reference to an external spec detected within a clause."""
    clause_start_line: int = Field(..., description="Start line of the clause containing this reference")
    clause_end_line: int = Field(..., description="End line of the clause containing this reference")
    spec_identifier: str = Field(..., description="Detected spec identifier like 'SPXQC-17' or 'AS9100'")
    version: str | None = Field(None, description="Detected version like 'Rev D' or 'v57.0'")
    context: str | None = Field(None, description="Brief context of how the spec is referenced")


class ReferenceDetectionResultOutput(BaseModel):
    """LLM output: all external references detected in clauses."""
    references: list[DetectedReferenceOutput] = Field(..., description="List of all detected external spec references")
