"""Hybrid retrieval: Pinecone dense search + BM25 keyword search, fused with RRF.

Document status, title and version are always re-read from MySQL so that superseded or
deleted documents are reflected immediately, without rewriting Pinecone metadata.
"""

import logging
import re
import threading
from dataclasses import dataclass, field
from typing import Any

from rank_bm25 import BM25Okapi
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import models
from app.database.connection import SessionLocal
from app.rag.embeddings import get_embedder
from app.rag.pinecone_store import get_store
from app.rag.reranking import reciprocal_rank_fusion, rerank
from app.rag.text_extractor import find_standard_numbers

logger = logging.getLogger(__name__)

_TOKEN_RE = re.compile(r"[\w\.]+", re.UNICODE)


def tokenize(text: str) -> list[str]:
    return [t.strip(".") for t in _TOKEN_RE.findall(text.lower()) if len(t.strip(".")) > 1]


@dataclass
class RetrievedChunk:
    chunk_id: str
    text: str
    score: float
    document_id: int
    standard_number: str | None = None
    standard_title: str | None = None
    clause_number: str | None = None
    section: str | None = None
    page_number: int | None = None
    document_type: str | None = None
    document_version: str | None = None
    amendment_number: str | None = None
    publication_date: str | None = None
    document_status: str | None = None
    source_url: str | None = None
    sources: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


@dataclass
class RetrievalResult:
    chunks: list[RetrievedChunk]
    vector_search_used: bool
    keyword_search_used: bool
    warnings: list[str] = field(default_factory=list)


class _BM25Cache:
    """In-memory BM25 index over document_chunks, rebuilt when the chunk table changes."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._signature: tuple[int, int] | None = None
        self._bm25: BM25Okapi | None = None
        self._ids: list[str] = []
        self._doc_ids: list[int] = []

    def get(self, db: Session) -> tuple[BM25Okapi | None, list[str], list[int]]:
        signature = db.execute(select(func.count(models.DocumentChunk.id), func.max(models.DocumentChunk.id))).one()
        signature = (int(signature[0] or 0), int(signature[1] or 0))
        with self._lock:
            if signature != self._signature:
                rows = db.execute(
                    select(models.DocumentChunk.chunk_id, models.DocumentChunk.document_id, models.DocumentChunk.text,
                           models.DocumentChunk.section, models.DocumentChunk.clause_number)
                ).all()
                corpus = [tokenize(f"{r.section or ''} {r.clause_number or ''} {r.text}") for r in rows]
                self._ids = [r.chunk_id for r in rows]
                self._doc_ids = [r.document_id for r in rows]
                self._bm25 = BM25Okapi(corpus) if corpus else None
                self._signature = signature
            return self._bm25, self._ids, self._doc_ids


_bm25_cache = _BM25Cache()


def _pinecone_filter(document_types: list[str] | None, document_ids: list[int] | None, standard_number: str | None) -> dict:
    clauses: list[dict] = []
    if document_types:
        clauses.append({"document_type": {"$in": document_types}})
    if document_ids:
        clauses.append({"document_id": {"$in": [int(d) for d in document_ids]}})
    if standard_number:
        clauses.append({"standard_number": {"$eq": standard_number}})
    if not clauses:
        return {}
    return clauses[0] if len(clauses) == 1 else {"$and": clauses}


def _allowed_document_ids(db: Session, document_types: list[str] | None, document_ids: list[int] | None,
                          standard_number: str | None, include_superseded: bool) -> set[int]:
    stmt = select(models.BISDocument.id).where(models.BISDocument.ingestion_status == "indexed")
    if document_types:
        stmt = stmt.where(models.BISDocument.document_type.in_(document_types))
    if document_ids:
        stmt = stmt.where(models.BISDocument.id.in_(document_ids))
    if standard_number:
        stmt = stmt.where(models.BISDocument.standard_number == standard_number)
    if not include_superseded:
        stmt = stmt.where(models.BISDocument.status.notin_(["withdrawn"]))
    return set(db.scalars(stmt))


def retrieve(
    query: str,
    top_k: int | None = None,
    document_types: list[str] | None = None,
    document_ids: list[int] | None = None,
    standard_number: str | None = None,
    include_superseded: bool = True,
    db: Session | None = None,
) -> RetrievalResult:
    top_k = top_k or settings.RETRIEVAL_TOP_K
    candidates = top_k * 3
    own_session = db is None
    db = db or SessionLocal()
    warnings: list[str] = []
    try:
        allowed = _allowed_document_ids(db, document_types, document_ids, standard_number, include_superseded)
        if not allowed:
            return RetrievalResult(chunks=[], vector_search_used=False, keyword_search_used=False,
                                   warnings=["No indexed BIS documents match this search."])

        dense_ranking: list[str] = []
        dense_scores: dict[str, float] = {}
        vector_used = False
        if settings.pinecone_configured:
            try:
                vector = get_embedder().embed_query(query)
                matches = get_store().query(
                    vector, top_k=candidates, filters=_pinecone_filter(document_types, document_ids, standard_number)
                )
                for m in matches:
                    if int(m["metadata"].get("document_id", -1)) in allowed:
                        dense_ranking.append(m["id"])
                        dense_scores[m["id"]] = m["score"]
                vector_used = True
            except Exception as exc:  # noqa: BLE001
                logger.warning("Vector search failed: %s", exc)
                warnings.append("Semantic (vector) search is temporarily unavailable; keyword search was used.")
        else:
            warnings.append("Pinecone is not configured; only keyword search was used.")

        sparse_ranking: list[str] = []
        bm25, ids, doc_ids = _bm25_cache.get(db)
        keyword_used = bm25 is not None
        if bm25 is not None:
            q_tokens = tokenize(query)
            # Exact IS numbers in the query are strong signals; repeat them to boost weight.
            for num in find_standard_numbers(query):
                q_tokens += tokenize(num) * 2
            if q_tokens:
                scores = bm25.get_scores(q_tokens)
                ranked = sorted(
                    (i for i in range(len(ids)) if doc_ids[i] in allowed and scores[i] > 0),
                    key=lambda i: -scores[i],
                )[:candidates]
                sparse_ranking = [ids[i] for i in ranked]

        fused = reciprocal_rank_fusion([r for r in (dense_ranking, sparse_ranking) if r])
        if not fused:
            return RetrievalResult(chunks=[], vector_search_used=vector_used, keyword_search_used=keyword_used,
                                   warnings=warnings + ["No relevant passages were found in the indexed documents."])

        ordered_ids = sorted(fused, key=lambda i: -fused[i])[:candidates]
        rows = db.execute(
            select(models.DocumentChunk, models.BISDocument)
            .join(models.BISDocument, models.DocumentChunk.document_id == models.BISDocument.id)
            .where(models.DocumentChunk.chunk_id.in_(ordered_ids))
        ).all()
        by_id = {chunk.chunk_id: (chunk, doc) for chunk, doc in rows}

        chunks: list[RetrievedChunk] = []
        for cid in ordered_ids:
            if cid not in by_id:
                continue
            chunk, doc = by_id[cid]
            sources = (["vector"] if cid in dense_scores else []) + (["keyword"] if cid in sparse_ranking else [])
            chunks.append(
                RetrievedChunk(
                    chunk_id=cid,
                    text=chunk.text,
                    score=round(fused[cid], 5),
                    document_id=doc.id,
                    standard_number=doc.standard_number,
                    standard_title=doc.document_title,
                    clause_number=chunk.clause_number,
                    section=chunk.section,
                    page_number=chunk.page_number,
                    document_type=doc.document_type,
                    document_version=doc.document_version,
                    amendment_number=doc.amendment_number,
                    publication_date=doc.publication_date.isoformat() if doc.publication_date else None,
                    document_status=doc.status,
                    source_url=doc.source_url,
                    sources=sources,
                )
            )

        reranked = rerank(query, [(c.chunk_id, c.text) for c in chunks], top_k)
        if reranked is not None:
            score_map = dict(reranked)
            chunks = sorted((c for c in chunks if c.chunk_id in score_map), key=lambda c: -score_map[c.chunk_id])
            for c in chunks:
                c.score = round(score_map[c.chunk_id], 4)
        return RetrievalResult(chunks=chunks[:top_k], vector_search_used=vector_used,
                               keyword_search_used=keyword_used, warnings=warnings)
    finally:
        if own_session:
            db.close()
