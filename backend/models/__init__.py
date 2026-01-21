"""Models package."""

from .clause import ChunkType, ClauseReference, ExtractionResult, ExtractedClause
from .db_models import Document, Clause, DocumentStatus, ReviewStatus, ClauseScope
from .db_models import ChunkType as DBChunkType
from .schemas import (
    ClauseCreate, ClauseUpdate, ClauseResponse,
    DocumentCreate, DocumentResponse, DocumentWithClauses,
    UploadResponse, DocumentStats
)

__all__ = [
    # Extraction models
    "ChunkType", "ClauseReference", "ExtractionResult", "ExtractedClause",
    # DB models
    "Document", "Clause", "DocumentStatus", "ReviewStatus", "ClauseScope", "DBChunkType",
    # Schemas
    "ClauseCreate", "ClauseUpdate", "ClauseResponse",
    "DocumentCreate", "DocumentResponse", "DocumentWithClauses",
    "UploadResponse", "DocumentStats",
]
