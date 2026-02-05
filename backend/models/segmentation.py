"""Pydantic models for V2 two-pass segmentation and line item extraction."""

from enum import Enum
from typing import Literal
from pydantic import BaseModel, Field


# --- OpenAI Structured Output Models (used with response_format) ---

class SectionReferenceOutput(BaseModel):
    """A section boundary identified by the LLM during segmentation."""
    start_line: int = Field(..., description="First line of the section (1-indexed, inclusive)")
    end_line: int = Field(..., description="Last line of the section (1-indexed, inclusive)")
    section_type: Literal[
        "header", "line_item", "terms_and_conditions", "signature", "attachment", "other"
    ] = Field(..., description="Type of section")
    section_title: str | None = Field(None, description="Title of the section if present, e.g. 'SECTION 2: QUALITY REQUIREMENTS'")
    section_number: str | None = Field(None, description="Section number if present, e.g. '2' or 'A'")
    line_item_number: int | None = Field(None, description="For line_item sections only: which PO line item number this section belongs to")


class SegmentationResultOutput(BaseModel):
    """Result of document segmentation — list of all sections."""
    sections: list[SectionReferenceOutput] = Field(..., description="List of all identified sections, covering every line in the document")


class LineItemMetadataOutput(BaseModel):
    """A single line item extracted from the header/line-items table."""
    line_number: int = Field(..., description="PO line item number (1, 2, 3, etc.)")
    part_number: str | None = Field(None, description="Part number / item number")
    description: str | None = Field(None, description="Description of the line item")
    quantity: str | None = Field(None, description="Quantity ordered (include unit if present)")
    quality_level: str | None = Field(None, description="Quality level or inspection level if specified")
    start_line: int | None = Field(None, description="Document line where this line item starts")
    end_line: int | None = Field(None, description="Document line where this line item ends")


class LineItemExtractionOutput(BaseModel):
    """Result of line item extraction from header section."""
    line_items: list[LineItemMetadataOutput] = Field(..., description="List of all line items found in the section")


# --- Internal Models (used within the application) ---

class SectionReference(BaseModel):
    """Internal representation of a section boundary."""
    start_line: int = Field(..., ge=1)
    end_line: int = Field(..., ge=1)
    section_type: str
    section_title: str | None = None
    section_number: str | None = None
    line_item_number: int | None = None


class SegmentationResult(BaseModel):
    """Internal representation of segmentation results."""
    sections: list[SectionReference] = Field(default_factory=list)


class LineItemMetadata(BaseModel):
    """Internal representation of a line item."""
    line_number: int
    part_number: str | None = None
    description: str | None = None
    quantity: str | None = None
    quality_level: str | None = None
    start_line: int | None = None
    end_line: int | None = None
