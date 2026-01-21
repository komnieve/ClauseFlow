"""ClauseFlow API - Contract clause extraction and review."""

import sys
import os
from datetime import datetime
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from database import get_db, init_db
from models.db_models import Document, Clause, DocumentStatus, ReviewStatus, ChunkType as DBChunkType
from models.schemas import (
    ClauseUpdate, ClauseResponse,
    DocumentResponse, DocumentWithClauses,
    UploadResponse, DocumentStats
)
from services.preprocessor import add_line_numbers
from services.clause_extractor import extract_clauses_from_document
from config import settings

# Initialize FastAPI app
app = FastAPI(
    title="ClauseFlow API",
    description="Contract clause extraction and review system",
    version="0.1.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "http://localhost:5174", "http://127.0.0.1:5173", "http://127.0.0.1:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    """Initialize database on startup."""
    init_db()


# --- Document Endpoints ---

@app.post("/api/documents/upload", response_model=UploadResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Upload a document (PDF or text) for clause extraction.

    Processing happens in the background - poll GET /api/documents/{id} for status.
    """
    # Read file content
    content = await file.read()

    # For now, assume text files. PDF support can be added later.
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File must be UTF-8 encoded text")

    # Create document record
    doc = add_line_numbers(text)

    db_document = Document(
        filename=file.filename or "unnamed.txt",
        original_text=text,
        total_lines=doc.total_lines,
        status=DocumentStatus.PROCESSING
    )
    db.add(db_document)
    db.commit()
    db.refresh(db_document)

    # Process in background
    background_tasks.add_task(process_document, db_document.id, text)

    return UploadResponse(
        document_id=db_document.id,
        filename=db_document.filename,
        status=db_document.status,
        message=f"Document uploaded. Processing {doc.total_lines} lines..."
    )


def process_document(document_id: int, text: str):
    """Background task to extract clauses from a document."""
    from database import SessionLocal

    db = SessionLocal()
    try:
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            return

        # Add line numbers and extract clauses
        doc = add_line_numbers(text)

        try:
            result = extract_clauses_from_document(doc)
        except Exception as e:
            document.status = DocumentStatus.ERROR
            document.error_message = str(e)
            db.commit()
            return

        # Save clauses to database
        for ref in result.clauses:
            # Extract the actual text using line references
            lines = doc.original_lines[ref.start_line - 1:ref.end_line]
            clause_text = '\n'.join(lines)

            db_clause = Clause(
                document_id=document_id,
                start_line=ref.start_line,
                end_line=ref.end_line,
                clause_number=ref.clause_number,
                clause_title=ref.clause_title,
                chunk_type=DBChunkType(ref.chunk_type.value),
                text=clause_text,
                review_status=ReviewStatus.UNREVIEWED
            )
            db.add(db_clause)

        document.status = DocumentStatus.READY
        db.commit()

    except Exception as e:
        document = db.query(Document).filter(Document.id == document_id).first()
        if document:
            document.status = DocumentStatus.ERROR
            document.error_message = str(e)
            db.commit()
    finally:
        db.close()


@app.get("/api/documents", response_model=list[DocumentResponse])
def list_documents(db: Session = Depends(get_db)):
    """List all documents."""
    documents = db.query(Document).order_by(Document.created_at.desc()).all()

    result = []
    for doc in documents:
        result.append(DocumentResponse(
            id=doc.id,
            filename=doc.filename,
            total_lines=doc.total_lines,
            status=doc.status,
            error_message=doc.error_message,
            created_at=doc.created_at,
            updated_at=doc.updated_at,
            clause_count=len(doc.clauses),
            reviewed_count=doc.reviewed_count,
            flagged_count=doc.flagged_count
        ))

    return result


@app.get("/api/documents/{document_id}", response_model=DocumentWithClauses)
def get_document(document_id: int, db: Session = Depends(get_db)):
    """Get a document with all its clauses."""
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    return DocumentWithClauses(
        id=document.id,
        filename=document.filename,
        total_lines=document.total_lines,
        status=document.status,
        error_message=document.error_message,
        created_at=document.created_at,
        updated_at=document.updated_at,
        clause_count=len(document.clauses),
        reviewed_count=document.reviewed_count,
        flagged_count=document.flagged_count,
        clauses=[ClauseResponse.model_validate(c) for c in document.clauses]
    )


@app.get("/api/documents/{document_id}/stats", response_model=DocumentStats)
def get_document_stats(document_id: int, db: Session = Depends(get_db)):
    """Get statistics for a document."""
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    by_type = {}
    by_scope = {}
    reviewed = 0
    flagged = 0
    unreviewed = 0

    for clause in document.clauses:
        # Count by type
        type_key = clause.chunk_type.value
        by_type[type_key] = by_type.get(type_key, 0) + 1

        # Count by scope
        if clause.scope:
            scope_key = clause.scope.value
            by_scope[scope_key] = by_scope.get(scope_key, 0) + 1

        # Count by review status
        if clause.review_status == ReviewStatus.REVIEWED:
            reviewed += 1
        elif clause.review_status == ReviewStatus.FLAGGED:
            flagged += 1
        else:
            unreviewed += 1

    return DocumentStats(
        total_clauses=len(document.clauses),
        reviewed=reviewed,
        flagged=flagged,
        unreviewed=unreviewed,
        by_type=by_type,
        by_scope=by_scope
    )


@app.delete("/api/documents/{document_id}")
def delete_document(document_id: int, db: Session = Depends(get_db)):
    """Delete a document and all its clauses."""
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    db.delete(document)
    db.commit()

    return {"message": "Document deleted"}


# --- Clause Endpoints ---

@app.get("/api/documents/{document_id}/clauses", response_model=list[ClauseResponse])
def list_clauses(
    document_id: int,
    chunk_type: Optional[str] = None,
    review_status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List clauses for a document with optional filtering."""
    query = db.query(Clause).filter(Clause.document_id == document_id)

    if chunk_type:
        query = query.filter(Clause.chunk_type == chunk_type)
    if review_status:
        query = query.filter(Clause.review_status == review_status)

    clauses = query.order_by(Clause.start_line).all()
    return [ClauseResponse.model_validate(c) for c in clauses]


@app.get("/api/clauses/{clause_id}", response_model=ClauseResponse)
def get_clause(clause_id: int, db: Session = Depends(get_db)):
    """Get a single clause."""
    clause = db.query(Clause).filter(Clause.id == clause_id).first()
    if not clause:
        raise HTTPException(status_code=404, detail="Clause not found")

    return ClauseResponse.model_validate(clause)


@app.patch("/api/clauses/{clause_id}", response_model=ClauseResponse)
def update_clause(clause_id: int, update: ClauseUpdate, db: Session = Depends(get_db)):
    """Update a clause (scope, notes, review status)."""
    clause = db.query(Clause).filter(Clause.id == clause_id).first()
    if not clause:
        raise HTTPException(status_code=404, detail="Clause not found")

    # Update fields if provided
    if update.scope is not None:
        clause.scope = update.scope
    if update.line_items is not None:
        clause.line_items = update.line_items
    if update.notes is not None:
        clause.notes = update.notes
    if update.review_status is not None:
        clause.review_status = update.review_status
        if update.review_status == ReviewStatus.REVIEWED:
            clause.reviewed_at = datetime.utcnow()

    db.commit()
    db.refresh(clause)

    return ClauseResponse.model_validate(clause)


@app.post("/api/clauses/{clause_id}/mark-reviewed", response_model=ClauseResponse)
def mark_clause_reviewed(clause_id: int, db: Session = Depends(get_db)):
    """Quick action to mark a clause as reviewed."""
    clause = db.query(Clause).filter(Clause.id == clause_id).first()
    if not clause:
        raise HTTPException(status_code=404, detail="Clause not found")

    clause.review_status = ReviewStatus.REVIEWED
    clause.reviewed_at = datetime.utcnow()
    db.commit()
    db.refresh(clause)

    return ClauseResponse.model_validate(clause)


@app.post("/api/clauses/{clause_id}/flag", response_model=ClauseResponse)
def flag_clause(clause_id: int, db: Session = Depends(get_db)):
    """Quick action to flag a clause for later."""
    clause = db.query(Clause).filter(Clause.id == clause_id).first()
    if not clause:
        raise HTTPException(status_code=404, detail="Clause not found")

    clause.review_status = ReviewStatus.FLAGGED
    db.commit()
    db.refresh(clause)

    return ClauseResponse.model_validate(clause)


# --- Export Endpoint ---

@app.get("/api/documents/{document_id}/export")
def export_document(document_id: int, format: str = "json", db: Session = Depends(get_db)):
    """Export document clauses as JSON or CSV."""
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    clauses_data = []
    for clause in document.clauses:
        clauses_data.append({
            "id": clause.id,
            "start_line": clause.start_line,
            "end_line": clause.end_line,
            "clause_number": clause.clause_number,
            "clause_title": clause.clause_title,
            "chunk_type": clause.chunk_type.value,
            "scope": clause.scope.value if clause.scope else None,
            "line_items": clause.line_items,
            "notes": clause.notes,
            "review_status": clause.review_status.value,
            "text": clause.text
        })

    if format == "json":
        return {
            "document": {
                "id": document.id,
                "filename": document.filename,
                "total_lines": document.total_lines,
                "exported_at": datetime.utcnow().isoformat()
            },
            "clauses": clauses_data
        }
    elif format == "csv":
        import csv
        import io
        from fastapi.responses import StreamingResponse

        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=[
            "id", "start_line", "end_line", "clause_number", "clause_title",
            "chunk_type", "scope", "line_items", "notes", "review_status", "text"
        ])
        writer.writeheader()
        writer.writerows(clauses_data)

        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={document.filename}_clauses.csv"}
        )
    else:
        raise HTTPException(status_code=400, detail="Format must be 'json' or 'csv'")


# --- Health Check ---

@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": settings.app_version}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
