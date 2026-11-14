from typing import Literal

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.database import models
from app.database.schemas import (
    DocumentChunkOut,
    DocumentOut,
    StandardDetail,
    StandardOut,
    StandardSearchHit,
    StandardSearchResponse,
)
from app.graph.state import Intent
from app.graph.workflow import run_workflow
from app.rag.citations import build_citations
from app.rag.retrieval import retrieve
from app.rag.text_extractor import STANDARD_NUMBER_RE, canonical_standard_number
from app.utils.errors import AppError, NotFoundError

SearchMode = Literal["auto", "number", "keyword", "semantic"]


def _detect_mode(query: str) -> str:
    if STANDARD_NUMBER_RE.fullmatch(query.strip()) or query.strip().upper().startswith("IS "):
        return "number"
    return "semantic" if len(query.split()) > 3 else "keyword"


def search(db: Session, query: str, mode: SearchMode = "auto", status: str | None = None, limit: int = 20) -> StandardSearchResponse:
    query = query.strip()
    if not query:
        raise AppError("Enter a standard number, product or keyword to search.")
    resolved = _detect_mode(query) if mode == "auto" else mode
    hits: list[StandardSearchHit] = []

    if resolved in ("number", "keyword"):
        stmt = select(models.IndianStandard)
        if resolved == "number":
            canonical = canonical_standard_number(query)
            base = canonical.split(":")[0]
            stmt = stmt.where(or_(models.IndianStandard.standard_number == canonical,
                                  models.IndianStandard.standard_number.ilike(f"{base}%")))
        else:
            like = f"%{query}%"
            stmt = stmt.where(or_(models.IndianStandard.title.ilike(like), models.IndianStandard.scope.ilike(like),
                                  models.IndianStandard.standard_number.ilike(like)))
        if status:
            stmt = stmt.where(models.IndianStandard.status == status)
        for std in db.scalars(stmt.limit(limit)):
            hits.append(StandardSearchHit(standard=StandardOut.model_validate(std), document_id=std.document_id,
                                          standard_number=std.standard_number, title=std.title, status=std.status))

    if resolved in ("keyword", "semantic") or not hits:
        result = retrieve(query, top_k=limit, document_types=["indian_standard"], db=db)
        grouped: dict[int, StandardSearchHit] = {h.document_id: h for h in hits if h.document_id}
        citations = build_citations(result.chunks)
        for chunk, cit in zip(result.chunks, citations):
            if status and chunk.document_status != status:
                continue
            hit = grouped.get(chunk.document_id)
            if hit is None:
                std = db.scalar(select(models.IndianStandard).where(models.IndianStandard.document_id == chunk.document_id))
                hit = StandardSearchHit(
                    standard=StandardOut.model_validate(std) if std else None,
                    document_id=chunk.document_id, standard_number=chunk.standard_number,
                    title=chunk.standard_title, status=chunk.document_status, score=chunk.score,
                )
                grouped[chunk.document_id] = hit
                hits.append(hit)
            if len(hit.matched_clauses) < 3:
                hit.matched_clauses.append(cit)
        message = "; ".join(result.warnings) or None
    else:
        message = None

    if not hits:
        message = message or "No indexed Indian Standards matched your search."
    return StandardSearchResponse(query=query, mode=resolved, results=hits[:limit], message=message)


def get_standard(db: Session, standard_id: int) -> StandardDetail:
    std = db.get(models.IndianStandard, standard_id)
    if std is None:
        raise NotFoundError("Standard not found.")
    doc = db.get(models.BISDocument, std.document_id) if std.document_id else None
    clauses = []
    if doc:
        rows = db.scalars(select(models.DocumentChunk).where(models.DocumentChunk.document_id == doc.id)
                          .order_by(models.DocumentChunk.chunk_index))
        clauses = [DocumentChunkOut.model_validate(c) for c in rows]
    return StandardDetail(**StandardOut.model_validate(std).model_dump(),
                          document=DocumentOut.model_validate(doc) if doc else None, clauses=clauses)


def compare(db: Session, user_id: int, standard_ids: list[int], focus: str | None, language: str | None) -> dict:
    standards = [db.get(models.IndianStandard, sid) for sid in standard_ids]
    if any(s is None for s in standards):
        raise NotFoundError("One or more standards were not found.")
    doc_ids = [s.document_id for s in standards if s.document_id]
    if len(doc_ids) < 2:
        raise AppError("Comparison requires indexed documents for at least two standards.")
    names = ", ".join(f"{s.standard_number} ({s.title})" for s in standards)
    query = f"Compare {names}" + (f" with focus on {focus}" if focus else " covering scope, key requirements and test methods")
    state = run_workflow(query, user_id=user_id, language=language, forced_intent=Intent.STANDARD_COMPARISON.value,
                         context={"document_ids": doc_ids, "focus": focus or ""})
    return {
        "standards": [StandardOut.model_validate(s).model_dump(mode="json") for s in standards],
        "answer": state["final_response"],
        "citations": state.get("citations", []),
        "verification": state.get("verification", {}),
        "structured": state.get("structured", {}),
    }
