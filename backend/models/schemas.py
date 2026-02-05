"""Pydantic schemas for API request/response."""

from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional
from models.db_models import (
    DocumentStatus, ReviewStatus, ClauseScope, ChunkType,
    SectionType, ScopeType, ReferenceDocStatus, MatchStatus
)


# --- Customer Schemas (V3) ---

class CustomerCreate(BaseModel):
    """Schema for creating a customer."""
    name: str


class CustomerResponse(BaseModel):
    """Schema for customer response."""
    id: int
    name: str
    created_at: datetime
    reference_doc_count: int = 0
    document_count: int = 0

    class Config:
        from_attributes = True


# --- Reference Document Schemas (V3) ---

class ReferenceRequirementResponse(BaseModel):
    """Schema for reference requirement response."""
    id: int
    reference_document_id: int
    requirement_number: Optional[str] = None
    title: Optional[str] = None
    text: Optional[str] = None
    start_line: Optional[int] = None
    end_line: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ReferenceDocumentResponse(BaseModel):
    """Schema for reference document response."""
    id: int
    customer_id: int
    filename: str
    total_lines: int
    status: ReferenceDocStatus
    error_message: Optional[str] = None
    doc_identifier: Optional[str] = None
    version: Optional[str] = None
    title: Optional[str] = None
    parent_id: Optional[int] = None
    created_at: datetime
    requirement_count: int = 0
    children_count: int = 0

    class Config:
        from_attributes = True


class ReferenceDocumentDetail(ReferenceDocumentResponse):
    """Reference document with requirements list."""
    requirements: list[ReferenceRequirementResponse] = []
    children: list[ReferenceDocumentResponse] = []


# --- Clause Reference Link Schemas (V3) ---

class ClauseReferenceLinkResponse(BaseModel):
    """Schema for clause reference link response."""
    id: int
    clause_id: int
    reference_requirement_id: Optional[int] = None
    reference_document_id: Optional[int] = None
    detected_spec_identifier: Optional[str] = None
    detected_version: Optional[str] = None
    match_status: MatchStatus
    # Nested info for display
    requirement_text: Optional[str] = None
    requirement_title: Optional[str] = None
    requirement_number: Optional[str] = None
    doc_title: Optional[str] = None

    class Config:
        from_attributes = True


# --- Section Schemas (V2) ---

class SectionResponse(BaseModel):
    """Schema for section response."""
    id: int
    document_id: int
    start_line: int
    end_line: int
    section_type: SectionType
    section_title: Optional[str] = None
    section_number: Optional[str] = None
    line_item_number: Optional[int] = None
    order_index: int
    text: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# --- Line Item Schemas (V2) ---

class LineItemResponse(BaseModel):
    """Schema for line item response."""
    id: int
    document_id: int
    section_id: Optional[int] = None
    line_number: Optional[int] = None
    part_number: Optional[str] = None
    description: Optional[str] = None
    quantity: Optional[str] = None
    quality_level: Optional[str] = None
    start_line: Optional[int] = None
    end_line: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


# --- Clause Schemas ---

class ClauseBase(BaseModel):
    """Base clause fields."""
    start_line: int
    end_line: int
    clause_number: Optional[str] = None
    clause_title: Optional[str] = None
    chunk_type: ChunkType
    text: str


class ClauseCreate(ClauseBase):
    """Schema for creating a clause."""
    pass


class ClauseUpdate(BaseModel):
    """Schema for updating a clause (user edits)."""
    scope: Optional[ClauseScope] = None
    line_items: Optional[str] = None
    notes: Optional[str] = None
    review_status: Optional[ReviewStatus] = None
    scope_type: Optional[ScopeType] = None
    applicable_lines: Optional[str] = None


class ClauseResponse(ClauseBase):
    """Schema for clause response."""
    id: int
    document_id: int
    scope: Optional[ClauseScope] = None
    line_items: Optional[str] = None
    notes: Optional[str] = None
    review_status: ReviewStatus
    created_at: datetime
    reviewed_at: Optional[datetime] = None
    # V2 fields
    section_id: Optional[int] = None
    scope_type: Optional[ScopeType] = None
    applicable_lines: Optional[str] = None
    erp_match_status: Optional[str] = None
    is_external_reference: Optional[str] = None
    # V3 fields
    reference_links: list[ClauseReferenceLinkResponse] = []

    class Config:
        from_attributes = True


# --- Document Schemas ---

class DocumentBase(BaseModel):
    """Base document fields."""
    filename: str


class DocumentCreate(DocumentBase):
    """Schema for creating a document."""
    original_text: str
    total_lines: int


class DocumentResponse(DocumentBase):
    """Schema for document response."""
    id: int
    total_lines: int
    status: DocumentStatus
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    clause_count: int = 0
    reviewed_count: int = 0
    flagged_count: int = 0
    customer_id: Optional[int] = None
    customer_name: Optional[str] = None

    class Config:
        from_attributes = True


class DocumentWithClauses(DocumentResponse):
    """Document with all its clauses, sections, and line items."""
    clauses: list[ClauseResponse] = []
    sections: list[SectionResponse] = []
    line_items: list[LineItemResponse] = []


# --- Upload Response ---

class UploadResponse(BaseModel):
    """Response after uploading a document."""
    document_id: int
    filename: str
    status: DocumentStatus
    message: str


# --- Progress/Stats ---

class DocumentStats(BaseModel):
    """Statistics for a document."""
    total_clauses: int
    reviewed: int
    flagged: int
    unreviewed: int
    by_type: dict[str, int]
    by_scope: dict[str, int]
    by_scope_type: dict[str, int] = {}
