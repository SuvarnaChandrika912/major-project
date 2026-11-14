"""Structure-aware chunking.

Documents are first split at clause / annex headings so that each chunk maps to a
single clause (keeping its number, section title and page). Long clauses are split at
paragraph boundaries with a small overlap; very short fragments are merged into the
preceding chunk of the same top-level section.
"""

from dataclasses import dataclass

from app.rag.pdf_processor import PageContent
from app.rag.text_extractor import detect_clause_heading

MAX_CHARS = 1800
MIN_CHARS = 200
OVERLAP_CHARS = 200


@dataclass
class Chunk:
    chunk_index: int
    text: str
    clause_number: str | None
    section: str | None
    page_number: int
    annex: str | None = None


@dataclass
class _Segment:
    clause_number: str | None
    section: str | None
    annex: str | None
    page_number: int
    lines: list[str]

    @property
    def text(self) -> str:
        return "\n".join(self.lines).strip()


def _top_level(clause: str | None) -> str | None:
    if not clause:
        return None
    if clause.startswith("Annex"):
        return clause
    return clause.split(".")[0].split("-")[0]


def _split_long(text: str) -> list[str]:
    if len(text) <= MAX_CHARS:
        return [text]
    paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
    parts: list[str] = []
    current = ""
    for para in paragraphs:
        while len(para) > MAX_CHARS:
            cut = para.rfind(". ", 0, MAX_CHARS)
            cut = cut + 1 if cut > MAX_CHARS // 2 else MAX_CHARS
            if current:
                parts.append(current)
                current = ""
            parts.append(para[:cut].strip())
            para = para[cut:].strip()
        if len(current) + len(para) + 1 > MAX_CHARS and current:
            parts.append(current)
            current = current[-OVERLAP_CHARS:].split(" ", 1)[-1] + "\n" + para
        else:
            current = f"{current}\n{para}" if current else para
    if current.strip():
        parts.append(current.strip())
    return parts


def chunk_pages(pages: list[PageContent], include_tables: bool = True) -> list[Chunk]:
    segments: list[_Segment] = []
    section_titles: dict[str, str] = {}
    current = _Segment(clause_number=None, section=None, annex=None, page_number=pages[0].page_number if pages else 1, lines=[])
    current_annex: str | None = None

    for page in pages:
        page_lines = page.text.split("\n")
        if include_tables:
            page_lines += [f"\n[Table, page {page.page_number}]\n{t}" for t in page.tables]
        for line in page_lines:
            heading = detect_clause_heading(line)
            if heading:
                clause, title = heading
                if clause.startswith("Annex"):
                    current_annex = clause
                elif current_annex and clause[0].isdigit() and "." not in clause and int(clause) <= 2:
                    # A new numbered clause "1" after an annex usually means a new document body.
                    current_annex = None
                top = _top_level(clause)
                if title and top and (clause == top or top not in section_titles):
                    section_titles.setdefault(top, title)
                if current.lines:
                    segments.append(current)
                current = _Segment(
                    clause_number=clause,
                    section=section_titles.get(top or "", title or None),
                    annex=current_annex,
                    page_number=page.page_number,
                    lines=[line.strip()],
                )
            else:
                if not current.lines:
                    current.page_number = page.page_number
                current.lines.append(line)
    if current.lines:
        segments.append(current)

    merged: list[_Segment] = []
    for seg in segments:
        if not seg.text:
            continue
        if (
            merged
            and len(seg.text) < MIN_CHARS
            and _top_level(merged[-1].clause_number) == _top_level(seg.clause_number)
            and len(merged[-1].text) + len(seg.text) < MAX_CHARS
        ):
            merged[-1].lines.extend(seg.lines)
        else:
            merged.append(seg)

    chunks: list[Chunk] = []
    for seg in merged:
        for part in _split_long(seg.text):
            if len(part.strip()) < 20:
                continue
            chunks.append(
                Chunk(
                    chunk_index=len(chunks),
                    text=part.strip(),
                    clause_number=seg.clause_number,
                    section=seg.section,
                    page_number=seg.page_number,
                    annex=seg.annex,
                )
            )
    return chunks
