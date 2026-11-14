"""PDF extraction with PyMuPDF, falling back to Tesseract OCR for scanned pages."""

import logging
from dataclasses import dataclass, field
from pathlib import Path

import fitz  # PyMuPDF
from PIL import Image

from app.rag.ocr import ocr_image, tesseract_available
from app.rag.text_extractor import normalize_text

logger = logging.getLogger(__name__)

MIN_TEXT_CHARS = 40
OCR_DPI = 300


@dataclass
class PageContent:
    page_number: int
    text: str
    headings: list[str] = field(default_factory=list)
    tables: list[str] = field(default_factory=list)
    used_ocr: bool = False


@dataclass
class ExtractedDocument:
    pages: list[PageContent]
    title: str | None
    page_count: int
    used_ocr: bool
    warnings: list[str] = field(default_factory=list)

    @property
    def full_text(self) -> str:
        return "\n\n".join(p.text for p in self.pages)


def _table_to_markdown(rows: list[list]) -> str:
    clean = [[(str(c) if c is not None else "").replace("\n", " ").strip() for c in row] for row in rows if row]
    if not clean:
        return ""
    width = max(len(r) for r in clean)
    clean = [r + [""] * (width - len(r)) for r in clean]
    lines = ["| " + " | ".join(clean[0]) + " |", "|" + "---|" * width]
    lines += ["| " + " | ".join(r) + " |" for r in clean[1:]]
    return "\n".join(lines)


def _extract_headings(page: fitz.Page) -> list[str]:
    """Treat text noticeably larger than the page's body font, or bold short lines, as headings."""
    data = page.get_text("dict")
    sizes: list[float] = []
    lines: list[tuple[str, float, bool]] = []
    for block in data.get("blocks", []):
        for line in block.get("lines", []):
            text = "".join(span.get("text", "") for span in line.get("spans", [])).strip()
            if not text:
                continue
            spans = line.get("spans", [])
            size = max((s.get("size", 0) for s in spans), default=0)
            bold = any("bold" in s.get("font", "").lower() or (s.get("flags", 0) & 16) for s in spans)
            sizes.append(size)
            lines.append((text, size, bold))
    if not sizes:
        return []
    body = sorted(sizes)[len(sizes) // 2]
    return [t for t, s, b in lines if len(t) < 150 and (s >= body + 1.5 or (b and len(t) < 90))]


def _extract_tables(page: fitz.Page) -> list[str]:
    tables: list[str] = []
    try:
        found = page.find_tables()
        for table in found.tables:
            md = _table_to_markdown(table.extract())
            if md:
                tables.append(md)
    except Exception as exc:  # noqa: BLE001 - table detection is best-effort
        logger.debug("Table extraction failed on page %s: %s", page.number + 1, exc)
    return tables


def _ocr_page(page: fitz.Page) -> str:
    pix = page.get_pixmap(dpi=OCR_DPI)
    image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    return ocr_image(image)


def extract_pdf(path: str | Path, extract_tables: bool = True) -> ExtractedDocument:
    pages: list[PageContent] = []
    warnings: list[str] = []
    used_ocr_any = False
    ocr_ok = tesseract_available()

    with fitz.open(path) as doc:
        if doc.needs_pass:
            raise ValueError("Password-protected PDFs are not supported.")
        title = (doc.metadata or {}).get("title") or None
        for page in doc:
            text = page.get_text("text") or ""
            used_ocr = False
            if len(text.strip()) < MIN_TEXT_CHARS and page.get_images():
                if ocr_ok:
                    try:
                        text = _ocr_page(page)
                        used_ocr = used_ocr_any = True
                    except Exception as exc:  # noqa: BLE001
                        warnings.append(f"OCR failed on page {page.number + 1}: {exc}")
                else:
                    warnings.append(f"Page {page.number + 1} appears scanned but Tesseract OCR is unavailable.")
            headings = [] if used_ocr else _extract_headings(page)
            tables = _extract_tables(page) if extract_tables and not used_ocr else []
            pages.append(
                PageContent(
                    page_number=page.number + 1,
                    text=normalize_text(text),
                    headings=headings,
                    tables=tables,
                    used_ocr=used_ocr,
                )
            )
        page_count = doc.page_count

    if not title:
        for p in pages[:2]:
            if p.headings:
                title = p.headings[0]
                break
    return ExtractedDocument(pages=pages, title=title, page_count=page_count, used_ocr=used_ocr_any, warnings=warnings)
