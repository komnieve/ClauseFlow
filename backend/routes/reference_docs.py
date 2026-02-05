"""Reference document CRUD and upload endpoints."""

import io

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Optional

from pypdf import PdfReader

from database import get_db
from models.db_models import Customer, ReferenceDocument, ReferenceRequirement, ReferenceDocStatus
from models.schemas import (
    ReferenceDocumentResponse,
    ReferenceDocumentDetail,
    ReferenceRequirementResponse,
)

router = APIRouter(tags=["reference-docs"])


def _ref_doc_response(ref_doc: ReferenceDocument) -> ReferenceDocumentResponse:
    """Build a ReferenceDocumentResponse from a DB model."""
    return ReferenceDocumentResponse(
        id=ref_doc.id,
        customer_id=ref_doc.customer_id,
        filename=ref_doc.filename,
        total_lines=ref_doc.total_lines,
        status=ref_doc.status,
        error_message=ref_doc.error_message,
        doc_identifier=ref_doc.doc_identifier,
        version=ref_doc.version,
        title=ref_doc.title,
        parent_id=ref_doc.parent_id,
        created_at=ref_doc.created_at,
        requirement_count=len(ref_doc.requirements or []),
        children_count=len(ref_doc.children or []),
    )


@router.post("/api/customers/{customer_id}/reference-docs/upload", response_model=ReferenceDocumentResponse)
async def upload_reference_doc(
    customer_id: int,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    doc_identifier: Optional[str] = Form(None),
    version: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    """Upload a reference document (PDF or text) for a customer."""
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    content = await file.read()
    filename = file.filename or "unnamed.txt"

    # Handle PDF
    if filename.lower().endswith(".pdf"):
        try:
            pdf_reader = PdfReader(io.BytesIO(content))
            text_parts = []
            for page in pdf_reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
            text = "\n".join(text_parts)
            if not text.strip():
                raise HTTPException(status_code=400, detail="Could not extract text from PDF")
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to parse PDF: {str(e)}")
    else:
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            raise HTTPException(status_code=400, detail="File must be UTF-8 encoded text or PDF")

    total_lines = len(text.split("\n"))

    ref_doc = ReferenceDocument(
        customer_id=customer_id,
        filename=filename,
        original_text=text,
        total_lines=total_lines,
        status=ReferenceDocStatus.PROCESSING,
        doc_identifier=doc_identifier,
        version=version,
    )
    db.add(ref_doc)
    db.commit()
    db.refresh(ref_doc)

    # Process in background
    background_tasks.add_task(_process_reference_doc_background, ref_doc.id, text)

    return _ref_doc_response(ref_doc)


def _process_reference_doc_background(ref_doc_id: int, text: str):
    """Background task to process a reference document."""
    from database import SessionLocal
    try:
        from services.reference_extractor import process_reference_document
        db = SessionLocal()
        try:
            process_reference_document(ref_doc_id, text, db)
        finally:
            db.close()
    except Exception as e:
        print(f"Reference doc processing failed for {ref_doc_id}: {e}")
        db = SessionLocal()
        try:
            ref_doc = db.query(ReferenceDocument).filter(ReferenceDocument.id == ref_doc_id).first()
            if ref_doc:
                ref_doc.status = ReferenceDocStatus.ERROR
                ref_doc.error_message = str(e)
                db.commit()
        finally:
            db.close()


@router.get("/api/customers/{customer_id}/reference-docs", response_model=list[ReferenceDocumentResponse])
def list_reference_docs(customer_id: int, db: Session = Depends(get_db)):
    """List reference documents for a customer."""
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    docs = (
        db.query(ReferenceDocument)
        .filter(ReferenceDocument.customer_id == customer_id)
        .order_by(ReferenceDocument.doc_identifier, ReferenceDocument.version)
        .all()
    )
    return [_ref_doc_response(d) for d in docs]


@router.get("/api/reference-docs/{ref_doc_id}", response_model=ReferenceDocumentDetail)
def get_reference_doc(ref_doc_id: int, db: Session = Depends(get_db)):
    """Get a reference document with its requirements."""
    ref_doc = db.query(ReferenceDocument).filter(ReferenceDocument.id == ref_doc_id).first()
    if not ref_doc:
        raise HTTPException(status_code=404, detail="Reference document not found")

    return ReferenceDocumentDetail(
        id=ref_doc.id,
        customer_id=ref_doc.customer_id,
        filename=ref_doc.filename,
        total_lines=ref_doc.total_lines,
        status=ref_doc.status,
        error_message=ref_doc.error_message,
        doc_identifier=ref_doc.doc_identifier,
        version=ref_doc.version,
        title=ref_doc.title,
        parent_id=ref_doc.parent_id,
        created_at=ref_doc.created_at,
        requirement_count=len(ref_doc.requirements or []),
        children_count=len(ref_doc.children or []),
        requirements=[ReferenceRequirementResponse.model_validate(r) for r in (ref_doc.requirements or [])],
        children=[_ref_doc_response(c) for c in (ref_doc.children or [])],
    )


@router.delete("/api/reference-docs/{ref_doc_id}")
def delete_reference_doc(ref_doc_id: int, db: Session = Depends(get_db)):
    """Delete a reference document and its requirements."""
    ref_doc = db.query(ReferenceDocument).filter(ReferenceDocument.id == ref_doc_id).first()
    if not ref_doc:
        raise HTTPException(status_code=404, detail="Reference document not found")

    db.delete(ref_doc)
    db.commit()
    return {"message": "Reference document deleted"}
