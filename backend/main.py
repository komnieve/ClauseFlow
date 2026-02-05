"""ClauseFlow API - Contract clause extraction and review (V2 two-pass pipeline)."""

import sys
import os
import io
from datetime import datetime
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pypdf import PdfReader

from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from database import get_db, init_db
from models.db_models import (
    Document, Clause, Section as DBSection, LineItem as DBLineItem,
    DocumentStatus, ReviewStatus, ChunkType as DBChunkType,
    SectionType as DBSectionType, ScopeType as DBScopeType,
)
from models.schemas import (
    ClauseUpdate, ClauseResponse,
    DocumentResponse, DocumentWithClauses,
    UploadResponse, DocumentStats,
    SectionResponse, LineItemResponse,
)
from services.preprocessor import add_line_numbers, extract_lines
from services.clause_extractor import extract_clauses_from_document, extract_clauses_from_section
from services.segmenter import segment_document, validate_segmentation, extract_line_items_from_section
from config import settings

# Initialize FastAPI app
app = FastAPI(
    title="ClauseFlow API",
    description="Contract clause extraction and review system",
    version="0.2.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for demo - restrict in production
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
    V2: Uses two-pass extraction (segmentation → per-section clause extraction).
    """
    # Read file content
    content = await file.read()
    filename = file.filename or "unnamed.txt"

    # Handle PDF files
    if filename.lower().endswith('.pdf'):
        try:
            pdf_reader = PdfReader(io.BytesIO(content))
            text_parts = []
            for page in pdf_reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
            text = '\n'.join(text_parts)
            if not text.strip():
                raise HTTPException(status_code=400, detail="Could not extract text from PDF")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to parse PDF: {str(e)}")
    else:
        # Assume text file
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            raise HTTPException(status_code=400, detail="File must be UTF-8 encoded text or PDF")

    # Create document record
    doc = add_line_numbers(text)

    db_document = Document(
        filename=filename,
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
        message=f"Document uploaded. Processing {doc.total_lines} lines with V2 two-pass extraction..."
    )


def process_document(document_id: int, text: str):
    """
    V2 two-pass background task to extract clauses from a document.

    Pass 1: Segment document into sections (header, T&C, attachments, etc.)
    Pass 2: Extract clauses from each T&C/line-item section with scope context.
    Also extracts line item metadata from the header section.
    """
    from database import SessionLocal

    db = SessionLocal()
    try:
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            return

        # Step 1: Add line numbers
        doc = add_line_numbers(text)

        # Step 2: SEGMENTING — Pass 1
        document.status = DocumentStatus.SEGMENTING
        db.commit()

        try:
            seg_result = segment_document(doc)
        except Exception as e:
            document.status = DocumentStatus.ERROR
            document.error_message = f"Segmentation failed: {str(e)}"
            db.commit()
            return

        # Step 3: Validate segmentation
        sections, seg_warnings = validate_segmentation(seg_result.sections, doc.total_lines)
        if seg_warnings:
            print(f"  Segmentation warnings for doc {document_id}: {seg_warnings}")

        # Step 4: Save Section records
        db_sections = {}  # Map order_index to DB section for later reference
        for idx, sec in enumerate(sections):
            section_text = extract_lines(doc, sec.start_line, sec.end_line)
            db_section = DBSection(
                document_id=document_id,
                start_line=sec.start_line,
                end_line=sec.end_line,
                section_type=DBSectionType(sec.section_type),
                section_title=sec.section_title,
                section_number=sec.section_number,
                line_item_number=sec.line_item_number,
                order_index=idx,
                text=section_text,
            )
            db.add(db_section)
            db.flush()  # Get the ID
            db_sections[idx] = db_section

        db.commit()

        # Step 5: Extract line items from header sections
        for idx, sec in enumerate(sections):
            if sec.section_type == "header":
                try:
                    line_items = extract_line_items_from_section(doc, sec)
                    for item in line_items:
                        db_line_item = DBLineItem(
                            document_id=document_id,
                            section_id=db_sections[idx].id,
                            line_number=item.line_number,
                            part_number=item.part_number,
                            description=item.description,
                            quantity=item.quantity,
                            quality_level=item.quality_level,
                            start_line=item.start_line,
                            end_line=item.end_line,
                        )
                        db.add(db_line_item)
                except Exception as e:
                    print(f"  Warning: Line item extraction failed for section {idx}: {e}")

        db.commit()

        # Step 6: EXTRACTING — Pass 2
        document.status = DocumentStatus.EXTRACTING
        db.commit()

        for idx, sec in enumerate(sections):
            # Only extract clauses from T&C and line_item sections
            if sec.section_type not in ("terms_and_conditions", "line_item"):
                continue

            try:
                result = extract_clauses_from_section(
                    doc,
                    section_start_line=sec.start_line,
                    section_end_line=sec.end_line,
                    section_type=sec.section_type,
                    section_title=sec.section_title,
                )
            except Exception as e:
                print(f"  Warning: Clause extraction failed for section '{sec.section_title}': {e}")
                continue

            # Determine scope from section type
            if sec.section_type == "terms_and_conditions":
                scope_type = DBScopeType.PO_WIDE
            elif sec.section_type == "line_item":
                scope_type = DBScopeType.LINE_SPECIFIC
            else:
                scope_type = None

            # Save clause records
            for ref in result.clauses:
                # Extract actual text using line references
                try:
                    clause_text = extract_lines(doc, ref.start_line, ref.end_line)
                except ValueError:
                    # Skip clauses with invalid line references
                    print(f"  Warning: Invalid line range {ref.start_line}-{ref.end_line} for clause {ref.clause_number}")
                    continue

                db_clause = Clause(
                    document_id=document_id,
                    start_line=ref.start_line,
                    end_line=ref.end_line,
                    clause_number=ref.clause_number,
                    clause_title=ref.clause_title,
                    chunk_type=DBChunkType(ref.chunk_type.value),
                    text=clause_text,
                    review_status=ReviewStatus.UNREVIEWED,
                    section_id=db_sections[idx].id,
                    scope_type=scope_type,
                    applicable_lines=(
                        f"[{sec.line_item_number}]"
                        if sec.section_type == "line_item" and sec.line_item_number
                        else None
                    ),
                )
                db.add(db_clause)

        # Step 7: Done
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
    """Get a document with all its clauses, sections, and line items."""
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
        clauses=[ClauseResponse.model_validate(c) for c in document.clauses],
        sections=[SectionResponse.model_validate(s) for s in document.sections],
        line_items=[LineItemResponse.model_validate(li) for li in document.line_items],
    )


@app.get("/api/documents/{document_id}/stats", response_model=DocumentStats)
def get_document_stats(document_id: int, db: Session = Depends(get_db)):
    """Get statistics for a document."""
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    by_type = {}
    by_scope = {}
    by_scope_type = {}
    reviewed = 0
    flagged = 0
    unreviewed = 0

    for clause in document.clauses:
        # Count by type
        type_key = clause.chunk_type.value
        by_type[type_key] = by_type.get(type_key, 0) + 1

        # Count by scope (V1)
        if clause.scope:
            scope_key = clause.scope.value
            by_scope[scope_key] = by_scope.get(scope_key, 0) + 1

        # Count by scope_type (V2)
        if clause.scope_type:
            scope_type_key = clause.scope_type.value
            by_scope_type[scope_type_key] = by_scope_type.get(scope_type_key, 0) + 1

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
        by_scope=by_scope,
        by_scope_type=by_scope_type,
    )


@app.delete("/api/documents/{document_id}")
def delete_document(document_id: int, db: Session = Depends(get_db)):
    """Delete a document and all its clauses, sections, and line items."""
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    db.delete(document)
    db.commit()

    return {"message": "Document deleted"}


# --- Section Endpoints (V2) ---

@app.get("/api/documents/{document_id}/sections", response_model=list[SectionResponse])
def list_sections(document_id: int, db: Session = Depends(get_db)):
    """List sections for a document (V2 segmentation results)."""
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    sections = (
        db.query(DBSection)
        .filter(DBSection.document_id == document_id)
        .order_by(DBSection.order_index)
        .all()
    )
    return [SectionResponse.model_validate(s) for s in sections]


# --- Line Item Endpoints (V2) ---

@app.get("/api/documents/{document_id}/line-items", response_model=list[LineItemResponse])
def list_line_items(document_id: int, db: Session = Depends(get_db)):
    """List line items for a document (extracted from header section)."""
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    items = (
        db.query(DBLineItem)
        .filter(DBLineItem.document_id == document_id)
        .order_by(DBLineItem.line_number)
        .all()
    )
    return [LineItemResponse.model_validate(li) for li in items]


# --- Clause Endpoints ---

@app.get("/api/documents/{document_id}/clauses", response_model=list[ClauseResponse])
def list_clauses(
    document_id: int,
    chunk_type: Optional[str] = None,
    review_status: Optional[str] = None,
    scope_type: Optional[str] = None,
    section_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """List clauses for a document with optional filtering."""
    query = db.query(Clause).filter(Clause.document_id == document_id)

    if chunk_type:
        query = query.filter(Clause.chunk_type == chunk_type)
    if review_status:
        query = query.filter(Clause.review_status == review_status)
    if scope_type:
        query = query.filter(Clause.scope_type == scope_type)
    if section_id is not None:
        query = query.filter(Clause.section_id == section_id)

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
    """Update a clause (scope, notes, review status, V2 fields)."""
    clause = db.query(Clause).filter(Clause.id == clause_id).first()
    if not clause:
        raise HTTPException(status_code=404, detail="Clause not found")

    # Update V1 fields if provided
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

    # Update V2 fields if provided
    if update.scope_type is not None:
        clause.scope_type = update.scope_type
    if update.applicable_lines is not None:
        clause.applicable_lines = update.applicable_lines

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
    """Export document clauses, sections, and line items as JSON or CSV."""
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
            "scope_type": clause.scope_type.value if clause.scope_type else None,
            "section_id": clause.section_id,
            "applicable_lines": clause.applicable_lines,
            "line_items": clause.line_items,
            "notes": clause.notes,
            "review_status": clause.review_status.value,
            "text": clause.text
        })

    sections_data = []
    for section in document.sections:
        sections_data.append({
            "id": section.id,
            "start_line": section.start_line,
            "end_line": section.end_line,
            "section_type": section.section_type.value,
            "section_title": section.section_title,
            "section_number": section.section_number,
            "order_index": section.order_index,
        })

    line_items_data = []
    for item in document.line_items:
        line_items_data.append({
            "id": item.id,
            "line_number": item.line_number,
            "part_number": item.part_number,
            "description": item.description,
            "quantity": item.quantity,
            "quality_level": item.quality_level,
        })

    if format == "json":
        return {
            "document": {
                "id": document.id,
                "filename": document.filename,
                "total_lines": document.total_lines,
                "exported_at": datetime.utcnow().isoformat()
            },
            "sections": sections_data,
            "line_items": line_items_data,
            "clauses": clauses_data,
        }
    elif format == "csv":
        import csv
        import io

        from fastapi.responses import StreamingResponse

        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=[
            "id", "start_line", "end_line", "clause_number", "clause_title",
            "chunk_type", "scope", "scope_type", "section_id", "applicable_lines",
            "line_items", "notes", "review_status", "text"
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
