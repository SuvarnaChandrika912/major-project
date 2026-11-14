"""Document ingestion: validate -> extract (OCR if needed) -> chunk -> embed -> Pinecone + MySQL."""

import hashlib
import logging
import re
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import crud, models
from app.database.connection import SessionLocal
from app.rag.chunking import Chunk, chunk_pages
from app.rag.embeddings import get_embedder
from app.rag.pdf_processor import extract_pdf
from app.rag.pinecone_store import get_store
from app.rag.text_extractor import canonical_standard_number, find_amendment, find_standard_numbers

logger = logging.getLogger(__name__)

PDF_MAGIC = b"%PDF-"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def validate_pdf_bytes(data: bytes, filename: str) -> None:
    if not filename.lower().endswith(".pdf"):
        raise ValueError("Only PDF files are supported.")
    if len(data) > settings.MAX_UPLOAD_MB * 1024 * 1024:
        raise ValueError(f"File exceeds the {settings.MAX_UPLOAD_MB} MB limit.")
    if not data.startswith(PDF_MAGIC):
        raise ValueError("The file is not a valid PDF.")


def safe_filename(name: str) -> str:
    stem = Path(name).stem
    stem = re.sub(r"[^A-Za-z0-9_.-]+", "_", stem)[:100] or "document"
    return f"{stem}.pdf"


def _extract_scope(chunks: list[Chunk]) -> str | None:
    for c in chunks:
        if (c.section or "").strip().upper().startswith("SCOPE") or (c.clause_number == "1" and "scope" in c.text[:80].lower()):
            return c.text[:1500]
    return None


def _chunk_metadata(doc: models.BISDocument, chunk: Chunk, chunk_id: str) -> dict:
    return {
        "document_id": doc.id,
        "standard_number": doc.standard_number,
        "standard_title": doc.document_title,
        "clause_number": chunk.clause_number,
        "section": chunk.section,
        "page_number": chunk.page_number,
        "document_type": doc.document_type,
        "publication_date": doc.publication_date.isoformat() if doc.publication_date else None,
        "amendment_number": doc.amendment_number,
        "document_version": doc.document_version,
        "document_status": doc.status,
        "source_url": doc.source_url,
        "chunk_id": chunk_id,
        "text": chunk.text,
    }


def _embedding_text(doc: models.BISDocument, chunk: Chunk) -> str:
    header = " | ".join(
        p for p in (doc.standard_number or "", doc.document_title, chunk.section or "",
                    f"Clause {chunk.clause_number}" if chunk.clause_number else "") if p
    )
    return f"{header}\n{chunk.text}"


def _mark_superseded(db: Session, doc: models.BISDocument) -> list[str]:
    """When a newer version of a standard is indexed, mark earlier versions as superseded."""
    if not doc.standard_number:
        return []
    older = db.scalars(
        select(models.BISDocument).where(
            models.BISDocument.standard_number == doc.standard_number,
            models.BISDocument.id != doc.id,
            models.BISDocument.status == "current",
        )
    ).all()
    changed = []
    for other in older:
        newer = (
            (doc.publication_date and other.publication_date and doc.publication_date > other.publication_date)
            or (not other.publication_date and doc.document_version and other.document_version
                and doc.document_version > other.document_version)
        )
        if newer:
            other.status = "superseded"
            for std in db.scalars(select(models.IndianStandard).where(models.IndianStandard.document_id == other.id)):
                std.status = "superseded"
            changed.append(f"{other.document_title} ({other.document_version or other.publication_date})")
    return changed


def ingest_document(document_id: int) -> None:
    """Run the full ingestion pipeline for an uploaded document (executed as a background task)."""
    db = SessionLocal()
    doc = db.get(models.BISDocument, document_id)
    if doc is None:
        db.close()
        return
    try:
        doc.ingestion_status = "processing"
        db.commit()

        extracted = extract_pdf(doc.file_path)
        if not extracted.full_text.strip():
            raise ValueError(
                "No text could be extracted. If the PDF is scanned, install Tesseract OCR and retry."
            )

        first_pages = "\n".join(p.text for p in extracted.pages[:2])
        if not doc.standard_number and doc.document_type == "indian_standard":
            found = find_standard_numbers(first_pages)
            if found:
                doc.standard_number = found[0]
        elif doc.standard_number:
            doc.standard_number = canonical_standard_number(doc.standard_number)
        if not doc.amendment_number:
            doc.amendment_number = find_amendment(first_pages)
        if extracted.title and doc.document_title.lower().endswith(".pdf"):
            doc.document_title = extracted.title[:500]

        chunks = chunk_pages(extracted.pages)
        if not chunks:
            raise ValueError("The document produced no usable text chunks.")

        chunk_ids = [f"doc{doc.id}-c{c.chunk_index}" for c in chunks]

        if settings.pinecone_configured:
            vectors = get_embedder().embed_documents([_embedding_text(doc, c) for c in chunks])
            get_store().upsert(
                [
                    {"id": cid, "values": vec, "metadata": _chunk_metadata(doc, c, cid)}
                    for cid, vec, c in zip(chunk_ids, vectors, chunks)
                ]
            )
        else:
            extracted.warnings.append("Pinecone is not configured; document indexed for keyword search only.")

        db.query(models.DocumentChunk).filter(models.DocumentChunk.document_id == doc.id).delete()
        db.add_all(
            models.DocumentChunk(
                chunk_id=cid,
                document_id=doc.id,
                chunk_index=c.chunk_index,
                section=(c.section or None) and c.section[:500],
                clause_number=c.clause_number,
                page_number=c.page_number,
                text=c.text,
            )
            for cid, c in zip(chunk_ids, chunks)
        )

        if doc.document_type == "indian_standard" and doc.standard_number:
            existing = db.scalar(select(models.IndianStandard).where(models.IndianStandard.document_id == doc.id))
            std = existing or models.IndianStandard(document_id=doc.id, standard_number=doc.standard_number, title=doc.document_title)
            std.standard_number = doc.standard_number
            std.title = doc.document_title
            std.scope = _extract_scope(chunks)
            std.publication_date = doc.publication_date
            std.amendment_number = doc.amendment_number
            std.status = doc.status
            db.add(std)

        superseded = _mark_superseded(db, doc)
        doc.page_count = extracted.page_count
        doc.chunk_count = len(chunks)
        doc.used_ocr = extracted.used_ocr
        doc.ingestion_status = "indexed"
        doc.error_message = "; ".join(extracted.warnings)[:2000] or None
        db.commit()

        if doc.uploaded_by:
            desc = f"{len(chunks)} chunks from {extracted.page_count} pages indexed."
            if superseded:
                desc += " Marked as superseded: " + ", ".join(superseded)
            crud.create_notification(db, doc.uploaded_by, f"Indexed: {doc.document_title}", desc, "ingestion_success")
        logger.info("Indexed document %s with %s chunks", doc.id, len(chunks))
    except Exception as exc:  # noqa: BLE001
        logger.exception("Ingestion failed for document %s", document_id)
        db.rollback()
        doc = db.get(models.BISDocument, document_id)
        if doc:
            doc.ingestion_status = "failed"
            doc.error_message = str(getattr(exc, "message", exc))[:2000]
            db.commit()
            if doc.uploaded_by:
                crud.create_notification(
                    db, doc.uploaded_by, f"Ingestion failed: {doc.document_title}", doc.error_message or "", "ingestion_error"
                )
    finally:
        db.close()


def delete_document_vectors(db: Session, document_id: int) -> None:
    ids = list(db.scalars(select(models.DocumentChunk.chunk_id).where(models.DocumentChunk.document_id == document_id)))
    if ids and settings.pinecone_configured:
        get_store().delete_ids(ids)
