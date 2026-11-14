"""Certification Agent: certification schemes, procedures and documentation from verified sources."""

from pydantic import BaseModel, Field
from sqlalchemy import select

from app.agents.base import history_text, load_prompt
from app.database import models
from app.database.connection import SessionLocal
from app.graph.state import AgentFinding, GraphState
from app.rag.citations import format_context
from app.rag.retrieval import RetrievedChunk, retrieve
from app.services.llm_service import get_llm
from app.utils.errors import AppError


class CandidateScheme(BaseModel):
    name: str
    reason: str
    citation: str = ""


class CertificationOutput(BaseModel):
    summary: str
    claims: list[str] = Field(default_factory=list)
    candidate_schemes: list[CandidateScheme] = Field(default_factory=list)
    documentation_checklist: list[str] = Field(default_factory=list)
    process_steps: list[str] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)


def _scheme_records() -> dict[str, dict]:
    with SessionLocal() as db:
        schemes = db.scalars(select(models.CertificationScheme).order_by(models.CertificationScheme.scheme_name)).all()
        return {
            f"S{i}": {"name": s.scheme_name, "description": s.description, "requirements": s.requirements or "",
                      "url": s.official_source_url or ""}
            for i, s in enumerate(schemes, start=1)
        }


def run(state: GraphState) -> tuple[AgentFinding, list[RetrievedChunk]]:
    query = state.get("retrieval_query") or state["user_query"]
    spec = state.get("product_specs") or {}
    ctx = state.get("context") or {}
    product = spec.get("product_name") or ctx.get("product_name") or ""
    chunks = retrieve(
        f"certification licence procedure documents {product} {query}",
        document_types=["certification_guideline", "faq"],
    ).chunks
    records = _scheme_records()

    if not chunks and not records:
        return AgentFinding(
            agent="certification_agent",
            summary="No certification guidelines or scheme records are available in the knowledge base yet.",
            data={"missing_information": ["Upload official BIS certification guidelines or add scheme records."]},
        ), []

    records_text = "\n".join(
        f"[{k}] {v['name']}: {v['description']} Requirements: {v['requirements']} URL: {v['url'] or 'not recorded'}"
        for k, v in records.items()
    ) or "No scheme records."
    manufacturer = "\n".join(f"{k}: {v}" for k, v in ctx.items() if isinstance(v, str) and v)
    user = (
        f"{history_text(state)}Question: {query}\n"
        f"{f'Manufacturer and product details (user data):{chr(10)}{manufacturer}{chr(10)}' if manufacturer else ''}"
        f"Product specification extracted: {spec or 'not available'}\n\n"
        f"Scheme records:\n{records_text}\n\nEvidence:\n{format_context(chunks)}"
    )
    try:
        out = get_llm().chat_json(load_prompt("certification"), user, CertificationOutput)
    except AppError as exc:
        return AgentFinding(agent="certification_agent", status="failed", error=exc.message, data={"records": records}), chunks

    known_names = {v["name"].lower() for v in records.values()}
    evidence_text = " ".join(c.text.lower() for c in chunks)
    schemes = [s.model_dump() for s in out.candidate_schemes
               if s.name.lower() in known_names or s.name.lower() in evidence_text]
    links = [{"label": v["name"], "url": v["url"]} for v in records.values() if v["url"]]
    links += [{"label": c.standard_title or "Source document", "url": c.source_url} for c in chunks if c.source_url]

    return (
        AgentFinding(
            agent="certification_agent",
            summary=out.summary,
            claims=out.claims,
            data={
                "candidate_schemes": schemes,
                "documentation_checklist": out.documentation_checklist,
                "process_steps": out.process_steps,
                "missing_information": out.missing_information,
                "official_links": list({l["url"]: l for l in links}.values()),
                "records": records,
            },
        ),
        chunks,
    )
