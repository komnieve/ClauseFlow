"""SQLAlchemy database models."""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
import enum

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import Base


class DocumentStatus(str, enum.Enum):
    """Status of document processing."""
    UPLOADING = "uploading"
    SEGMENTING = "segmenting"
    EXTRACTING = "extracting"
    PROCESSING = "processing"
    READY = "ready"
    ERROR = "error"


class ReviewStatus(str, enum.Enum):
    """Review status of a clause."""
    UNREVIEWED = "unreviewed"
    REVIEWED = "reviewed"
    FLAGGED = "flagged"


class ClauseScope(str, enum.Enum):
    """What a clause applies to (user-assigned, V1)."""
    ENTIRE_PO = "entire_po"
    LINE_ITEMS = "line_items"
    FLOW_DOWN = "flow_down"
    NO_ACTION = "no_action"


class ChunkType(str, enum.Enum):
    """Type of document chunk."""
    CLAUSE = "clause"
    ADMINISTRATIVE = "administrative"
    BOILERPLATE = "boilerplate"
    HEADER = "header"
    SIGNATURE = "signature"


class SectionType(str, enum.Enum):
    """Type of document section (V2 segmentation)."""
    HEADER = "header"
    LINE_ITEM = "line_item"
    TERMS_AND_CONDITIONS = "terms_and_conditions"
    SIGNATURE = "signature"
    ATTACHMENT = "attachment"
    OTHER = "other"


class ScopeType(str, enum.Enum):
    """Clause scope type (V2, system-assigned from section)."""
    PO_WIDE = "po_wide"
    LINE_SPECIFIC = "line_specific"


class Document(Base):
    """A uploaded document (contract/PO)."""
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    original_text = Column(Text, nullable=False)
    total_lines = Column(Integer, nullable=False)
    status = Column(SQLEnum(DocumentStatus), default=DocumentStatus.UPLOADING)
    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    clauses = relationship("Clause", back_populates="document", cascade="all, delete-orphan")
    sections = relationship("Section", back_populates="document", cascade="all, delete-orphan")
    line_items = relationship("LineItem", back_populates="document", cascade="all, delete-orphan")

    @property
    def reviewed_count(self) -> int:
        return sum(1 for c in self.clauses if c.review_status == ReviewStatus.REVIEWED)

    @property
    def flagged_count(self) -> int:
        return sum(1 for c in self.clauses if c.review_status == ReviewStatus.FLAGGED)


class Section(Base):
    """A section identified during document segmentation (V2)."""
    __tablename__ = "sections"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    start_line = Column(Integer, nullable=False)
    end_line = Column(Integer, nullable=False)
    section_type = Column(SQLEnum(SectionType), nullable=False)
    section_title = Column(String(500), nullable=True)
    section_number = Column(String(50), nullable=True)
    line_item_number = Column(Integer, nullable=True)  # For line_item sections only
    order_index = Column(Integer, nullable=False)
    text = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    document = relationship("Document", back_populates="sections")
    clauses = relationship("Clause", back_populates="section")
    line_items = relationship("LineItem", back_populates="section")


class LineItem(Base):
    """A line item extracted from the document header (V2)."""
    __tablename__ = "line_items"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    section_id = Column(Integer, ForeignKey("sections.id"), nullable=True)
    line_number = Column(Integer, nullable=True)  # PO line item number (1, 2, 3...)
    part_number = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    quantity = Column(String(100), nullable=True)
    quality_level = Column(String(100), nullable=True)
    start_line = Column(Integer, nullable=True)  # Document line where this item starts
    end_line = Column(Integer, nullable=True)  # Document line where this item ends

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    document = relationship("Document", back_populates="line_items")
    section = relationship("Section", back_populates="line_items")


class Clause(Base):
    """A clause extracted from a document."""
    __tablename__ = "clauses"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)

    # Line references (the key innovation - we store references, not copies)
    start_line = Column(Integer, nullable=False)
    end_line = Column(Integer, nullable=False)

    # Extracted metadata
    clause_number = Column(String(50), nullable=True)  # e.g., "1.1", "7.2.3"
    clause_title = Column(String(255), nullable=True)
    chunk_type = Column(SQLEnum(ChunkType), nullable=False)
    text = Column(Text, nullable=False)  # The actual extracted text

    # User-editable fields (V1)
    scope = Column(SQLEnum(ClauseScope), nullable=True)
    line_items = Column(String(255), nullable=True)  # Comma-separated line item numbers
    notes = Column(Text, nullable=True)
    review_status = Column(SQLEnum(ReviewStatus), default=ReviewStatus.UNREVIEWED)

    # V2 fields — section-aware extraction
    section_id = Column(Integer, ForeignKey("sections.id"), nullable=True)
    scope_type = Column(SQLEnum(ScopeType), nullable=True)  # System-assigned from section
    applicable_lines = Column(String(500), nullable=True)  # JSON array like "[1,3,5]"

    # ERP fields (all nullable, for future use)
    erp_match_status = Column(String(50), nullable=True)
    erp_clause_id = Column(String(100), nullable=True)
    erp_revision = Column(String(50), nullable=True)
    erp_date = Column(String(50), nullable=True)
    mismatch_details = Column(Text, nullable=True)
    is_external_reference = Column(String(10), nullable=True)  # "true"/"false"
    external_url = Column(String(1000), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    reviewed_at = Column(DateTime, nullable=True)

    # Relationships
    document = relationship("Document", back_populates="clauses")
    section = relationship("Section", back_populates="clauses")
