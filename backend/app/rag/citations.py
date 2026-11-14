"""Citation numbering, LLM context formatting and citation validation."""

import re
from collections.abc import Iterable

from app.database.schemas import Citation
from app.rag.retrieval import RetrievedChunk
from app.utils.security import sanitize_untrusted

_MARKER_RE = re.compile(r"\[(\d{1,3})\]")


def merge_chunks(*groups: Iterable[RetrievedChunk]) -> list[RetrievedChunk]:
    """De-duplicate chunks from several agents, keeping the first (highest-ranked) occurrence."""
    seen: set[str] = set()
    merged: list[RetrievedChunk] = []
    for group in groups:
        for chunk in group:
            if chunk.chunk_id not in seen:
                seen.add(chunk.chunk_id)
                merged.append(chunk)
    return merged


def build_citations(chunks: list[RetrievedChunk]) -> list[Citation]:
    return [
        Citation(
            index=i + 1,
            chunk_id=c.chunk_id,
            document_id=c.document_id,
            standard_number=c.standard_number,
            standard_title=c.standard_title,
            clause_number=c.clause_number,
            section=c.section,
            page_number=c.page_number,
            document_version=c.document_version,
            amendment_number=c.amendment_number,
            document_status=c.document_status,
            document_type=c.document_type,
            source_url=c.source_url,
            excerpt=c.text[:600],
            score=c.score,
        )
        for i, c in enumerate(chunks)
    ]


def format_context(chunks: list[RetrievedChunk], max_chars_per_chunk: int = 1500) -> str:
    """Render evidence for an LLM prompt. Content is wrapped and sanitised as untrusted data."""
    if not chunks:
        return "NO EVIDENCE AVAILABLE."
    blocks = []
    for i, c in enumerate(chunks, start=1):
        header = " | ".join(
            part
            for part in (
                f"[{i}]",
                c.standard_number or "",
                c.standard_title or "",
                f"Clause {c.clause_number}" if c.clause_number else "",
                f"Page {c.page_number}" if c.page_number else "",
                f"Status: {c.document_status}" if c.document_status else "",
                f"Version: {c.document_version}" if c.document_version else "",
            )
            if part
        )
        body = sanitize_untrusted(c.text, max_chars=max_chars_per_chunk)
        blocks.append(f'<document id="{i}">\n{header}\n{body}\n</document>')
    return "\n\n".join(blocks)


def used_markers(answer: str) -> set[int]:
    return {int(m) for m in _MARKER_RE.findall(answer)}


def validate_citations(answer: str, citation_count: int) -> tuple[str, list[int]]:
    """Remove citation markers that point to non-existent sources. Returns (answer, invalid_markers)."""
    invalid: list[int] = []

    def _fix(match: re.Match) -> str:
        n = int(match.group(1))
        if 1 <= n <= citation_count:
            return match.group(0)
        invalid.append(n)
        return ""

    return _MARKER_RE.sub(_fix, answer), sorted(set(invalid))


def citation_label(c: Citation) -> str:
    parts = [c.standard_number or c.standard_title or "Document"]
    if c.clause_number:
        parts.append(f"Clause {c.clause_number}")
    if c.page_number:
        parts.append(f"p. {c.page_number}")
    return ", ".join(parts)
