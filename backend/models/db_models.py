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
    PROCESSING = "processing"
    READY = "ready"
    ERROR = "error"


class ReviewStatus(str, enum.Enum):
    """Review status of a clause."""
    UNREVIEWED = "unreviewed"
    REVIEWED = "reviewed"
    FLAGGED = "flagged"


class ClauseScope(str, enum.Enum):
    """What a clause applies to."""
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

    @property
    def reviewed_count(self) -> int:
        return sum(1 for c in self.clauses if c.review_status == ReviewStatus.REVIEWED)

    @property
    def flagged_count(self) -> int:
        return sum(1 for c in self.clauses if c.review_status == ReviewStatus.FLAGGED)


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

    # User-editable fields
    scope = Column(SQLEnum(ClauseScope), nullable=True)
    line_items = Column(String(255), nullable=True)  # Comma-separated line item numbers
    notes = Column(Text, nullable=True)
    review_status = Column(SQLEnum(ReviewStatus), default=ReviewStatus.UNREVIEWED)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    reviewed_at = Column(DateTime, nullable=True)

    # Relationships
    document = relationship("Document", back_populates="clauses")
