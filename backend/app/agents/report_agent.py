"""Report Generation Agent: structured reports from verified findings, exported as PDF."""

import io
import re
from datetime import datetime
from typing import Any
from xml.sax.saxutils import escape

from pydantic import BaseModel, Field
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import ListFlowable, ListItem, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.agents.base import load_prompt
from app.services.llm_service import get_llm
from app.utils.errors import AppError

NAVY = colors.HexColor("#0B2559")
REPORT_TITLES = {
    "compliance": "Preliminary Compliance Gap Report",
    "certification_roadmap": "Certification Roadmap",
    "standard_comparison": "Standard Comparison Report",
    "laboratory_recommendation": "Laboratory Recommendation Report",
}
DISCLAIMER = (
    "This is a preliminary, AI-generated report based on documents indexed in BIS SAATHI. "
    "It is not an official BIS certification, approval or decision. Verify all requirements with the "
    "Bureau of Indian Standards before acting on them."
)


class ReportSection(BaseModel):
    heading: str
    content: str


class ReportContent(BaseModel):
    executive_summary: str
    sections: list[ReportSection] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


def compose_report(report_type: str, product_name: str, answer: str, structured: dict, citations: list[dict],
                   verification: dict) -> dict[str, Any]:
    """Build report content with the LLM, falling back to the verified answer if the LLM is unavailable."""
    evidence = "\n".join(
        f"[{c['index']}] {c.get('standard_number') or c.get('standard_title')} clause {c.get('clause_number') or '-'}: "
        f"{c.get('excerpt', '')[:400]}"
        for c in citations
    )
    user = (
        f"Report type: {REPORT_TITLES.get(report_type, report_type)}\nProduct: {product_name}\n\n"
        f"Verified answer:\n{answer}\n\nStructured findings:\n{structured}\n\n"
        f"Verification: {verification}\n\nEvidence:\n{evidence or 'none'}"
    )
    try:
        content = get_llm().chat_json(load_prompt("report"), user, ReportContent).model_dump()
    except AppError:
        content = ReportContent(
            executive_summary=answer,
            limitations=["The language model was unavailable; the report contains the verified answer only."],
        ).model_dump()
    content["limitations"] = list(dict.fromkeys(content.get("limitations", []) + verification.get("warnings", [])))
    return content


def _md_inline(text: str) -> str:
    text = escape(text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"<i>\1</i>", text)
    text = re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)", r'<link href="\2" color="blue">\1</link>', text)
    return text


def _paragraphs(text: str, style: ParagraphStyle, bullet_style: ParagraphStyle) -> list:
    flow: list = []
    bullets: list[str] = []

    def flush():
        if bullets:
            flow.append(ListFlowable([ListItem(Paragraph(_md_inline(b), bullet_style)) for b in bullets],
                                     bulletType="bullet", leftIndent=12))
            bullets.clear()

    for line in text.splitlines():
        s = line.strip()
        if re.match(r"^[-*•]\s+", s):
            bullets.append(re.sub(r"^[-*•]\s+", "", s))
            continue
        flush()
        if not s:
            continue
        s = re.sub(r"^#{1,6}\s*", "", s)
        flow.append(Paragraph(_md_inline(s), style))
    flush()
    return flow


def render_pdf(report: dict[str, Any]) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=18 * mm,
                            bottomMargin=18 * mm, title=report["report_title"], author="BIS SAATHI")
    styles = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=styles["Heading1"], textColor=NAVY, fontSize=18, spaceAfter=6)
    h2 = ParagraphStyle("h2", parent=styles["Heading2"], textColor=NAVY, fontSize=13, spaceBefore=10, spaceAfter=4)
    body = ParagraphStyle("body", parent=styles["BodyText"], fontSize=10, leading=14, alignment=TA_LEFT)
    small = ParagraphStyle("small", parent=body, fontSize=8, leading=11, textColor=colors.HexColor("#475569"))

    data = report["report_data"]
    content = data.get("content", {})
    story: list = [
        Paragraph("BIS SAATHI", small),
        Paragraph(escape(report["report_title"]), h1),
        Paragraph(f"Product: <b>{escape(report['product_name'])}</b> &nbsp;|&nbsp; Generated: "
                  f"{escape(str(report['created_at'])[:16])}", small),
        Spacer(1, 6),
        Paragraph(escape(DISCLAIMER), small),
        Paragraph("Executive summary", h2),
        *_paragraphs(content.get("executive_summary", ""), body, body),
    ]
    for section in content.get("sections", []):
        story.append(Paragraph(escape(section.get("heading", "")), h2))
        story += _paragraphs(section.get("content", ""), body, body)

    checklist = data.get("structured", {}).get("compliance_agent", {}).get("checklist", [])
    if checklist:
        story.append(Paragraph("Compliance checklist", h2))
        rows = [["Requirement", "Clause", "Status", "Notes"]]
        for item in checklist:
            rows.append([Paragraph(_md_inline(item.get("requirement", "")), small), item.get("clause_number") or "-",
                         item.get("status", "").replace("_", " "), Paragraph(_md_inline(item.get("notes", "")), small)])
        table = Table(rows, colWidths=[70 * mm, 20 * mm, 30 * mm, 54 * mm], repeatRows=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), NAVY), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTSIZE", (0, 0), (-1, -1), 8), ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#CBD5E1")),
        ]))
        story.append(table)

    labs = data.get("structured", {}).get("testing_agent", {}).get("recommended_laboratories", [])
    if labs:
        story.append(Paragraph("Recommended laboratories (from verified records)", h2))
        for lab in labs:
            story += _paragraphs(f"- **{lab.get('name')}** ({lab.get('city')}, {lab.get('state')}) — "
                                 f"recognition: {lab.get('recognition_status')}. {lab.get('reason', '')}", body, body)

    for title, key in (("Recommendations", "recommendations"), ("Limitations", "limitations")):
        if content.get(key):
            story.append(Paragraph(title, h2))
            story += _paragraphs("\n".join(f"- {x}" for x in content[key]), body, body)

    citations = data.get("citations", [])
    story.append(Paragraph("References", h2))
    if not citations:
        story.append(Paragraph("No document references were available for this report.", body))
    for c in citations:
        ref = (f"[{c.get('index')}] {c.get('standard_number') or ''} {c.get('standard_title') or ''}"
               f"{', Clause ' + c['clause_number'] if c.get('clause_number') else ''}"
               f"{', p. ' + str(c['page_number']) if c.get('page_number') else ''}"
               f"{', version ' + c['document_version'] if c.get('document_version') else ''}"
               f"{' (' + c['document_status'] + ')' if c.get('document_status') not in (None, 'current') else ''}")
        story.append(Paragraph(escape(ref.strip()), small))
        if c.get("source_url"):
            story.append(Paragraph(f'<link href="{escape(c["source_url"])}" color="blue">{escape(c["source_url"])}</link>', small))

    def footer(canvas, _doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(colors.HexColor("#64748B"))
        canvas.drawString(18 * mm, 10 * mm, f"BIS SAATHI • Preliminary guidance • {datetime.now():%d %b %Y}")
        canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, f"Page {canvas.getPageNumber()}")
        canvas.restoreState()

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return buffer.getvalue()
