import uuid
from datetime import date
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.config import settings
from app.database import models
from app.database.connection import get_db
from app.database.schemas import DocumentDetail, DocumentOut, DocumentType
from app.dependencies import get_admin_user, get_current_user
from app.rag.ingestion import delete_document_vectors, ingest_document, safe_filename, sha256_bytes, validate_pdf_bytes
from app.rag.text_extractor import canonical_standard_number
from app.utils.errors import AppError, NotFoundError

router = APIRouter(prefix="/api/documents", tags=["Documents"])

DOCUMENT_STATUSES = {"current", "superseded", "withdrawn", "draft"}


@router.post("/upload", response_model=DocumentOut, status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    background: BackgroundTasks,
    file: UploadFile = File(...),
    document_title: str = Form(..., min_length=3, max_length=500),
    document_type: DocumentType = Form(...),
    standard_number: str | None = Form(None),
    document_version: str | None = Form(None),
    amendment_number: str | None = Form(None),
    publication_date: date | None = Form(None),
    source_url: str | None = Form(None),
    document_status: str = Form("current"),
    admin: models.User = Depends(get_admin_user),
    db: Session = Depends(get_db),
) -> models.BISDocument:
    data = await file.read()
    try:
        validate_pdf_bytes(data, file.filename or "")
    except ValueError as exc:
        raise AppError(str(exc), status_code=400) from exc
    if document_status not in DOCUMENT_STATUSES:
        raise AppError(f"document_status must be one of {', '.join(sorted(DOCUMENT_STATUSES))}.")
    if source_url and not source_url.startswith(("https://", "http://")):
        raise AppError("source_url must be an http(s) URL.")

    file_hash = sha256_bytes(data)
    duplicate = db.scalar(select(models.BISDocument).where(models.BISDocument.file_hash == file_hash))
    if duplicate:
        raise AppError(f"This file was already uploaded as '{duplicate.document_title}' (id {duplicate.id}).", status_code=409)

    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)
    path = upload_dir / f"{uuid.uuid4().hex}_{safe_filename(file.filename or 'document.pdf')}"
    path.write_bytes(data)

    doc = models.BISDocument(
        document_title=document_title.strip(),
        document_type=document_type,
        standard_number=canonical_standard_number(standard_number) if standard_number else None,
        document_version=(document_version or "").strip() or None,
        amendment_number=(amendment_number or "").strip() or None,
        publication_date=publication_date,
        source_url=source_url,
        file_path=str(path),
        file_hash=file_hash,
        status=document_status,
        ingestion_status="pending",
        uploaded_by=admin.id,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    background.add_task(ingest_document, doc.id)
    return doc


@router.get("", response_model=list[DocumentOut])
def list_documents(
    document_type: str | None = None,
    ingestion_status: str | None = None,
    _user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    stmt = select(models.BISDocument).order_by(models.BISDocument.created_at.desc())
    if document_type:
        stmt = stmt.where(models.BISDocument.document_type == document_type)
    if ingestion_status:
        stmt = stmt.where(models.BISDocument.ingestion_status == ingestion_status)
    return list(db.scalars(stmt))


@router.get("/{document_id}", response_model=DocumentDetail)
def get_document(document_id: int, _user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    doc = db.scalar(select(models.BISDocument).options(selectinload(models.BISDocument.chunks))
                    .where(models.BISDocument.id == document_id))
    if doc is None:
        raise NotFoundError("Document not found.")
    return doc


@router.patch("/{document_id}/status", response_model=DocumentOut)
def update_status(document_id: int, payload: dict, _admin: models.User = Depends(get_admin_user), db: Session = Depends(get_db)):
    doc = db.get(models.BISDocument, document_id)
    if doc is None:
        raise NotFoundError("Document not found.")
    new_status = payload.get("status")
    if new_status not in DOCUMENT_STATUSES:
        raise AppError(f"status must be one of {', '.join(sorted(DOCUMENT_STATUSES))}.")
    doc.status = new_status
    for std in db.scalars(select(models.IndianStandard).where(models.IndianStandard.document_id == doc.id)):
        std.status = new_status
    db.commit()
    return doc


@router.post("/{document_id}/reindex", response_model=DocumentOut, status_code=status.HTTP_202_ACCEPTED)
def reindex(document_id: int, background: BackgroundTasks, _admin: models.User = Depends(get_admin_user), db: Session = Depends(get_db)):
    doc = db.get(models.BISDocument, document_id)
    if doc is None:
        raise NotFoundError("Document not found.")
    delete_document_vectors(db, doc.id)
    doc.ingestion_status = "pending"
    doc.error_message = None
    db.commit()
    background.add_task(ingest_document, doc.id)
    return doc


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(document_id: int, _admin: models.User = Depends(get_admin_user), db: Session = Depends(get_db)) -> None:
    doc = db.get(models.BISDocument, document_id)
    if doc is None:
        raise NotFoundError("Document not found.")
    try:
        delete_document_vectors(db, doc.id)
    except AppError as exc:
        raise AppError(f"Could not delete vectors from Pinecone: {exc.message}", status_code=502) from exc
    db.query(models.IndianStandard).filter(models.IndianStandard.document_id == doc.id).delete()
    Path(doc.file_path).unlink(missing_ok=True)
    db.delete(doc)
    db.commit()
