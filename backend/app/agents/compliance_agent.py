"""Compliance Assessment Agent: preliminary gap analysis of product data against retrieved requirements."""

from typing import Literal

from pydantic import BaseModel, Field

from app.agents.base import history_text, load_prompt
from app.graph.state import AgentFinding, GraphState
from app.rag.citations import format_context, merge_chunks
from app.rag.retrieval import RetrievedChunk, retrieve
from app.rag.text_extractor import canonical_standard_number
from app.services.llm_service import get_llm
from app.utils.errors import AppError
from app.utils.security import sanitize_untrusted


class ChecklistItem(BaseModel):
    requirement: str
    clause_number: str | None = None
    citation: str = ""
    status: Literal["meets", "does_not_meet", "missing_information"] = "missing_information"
    notes: str = ""


class ComplianceOutput(BaseModel):
    summary: str
    claims: list[str] = Field(default_factory=list)
    checklist: list[ChecklistItem] = Field(default_factory=list)
    missing_specifications: list[str] = Field(default_factory=list)
    required_documents: list[str] = Field(default_factory=list)


def run(state: GraphState) -> tuple[AgentFinding, list[RetrievedChunk]]:
    query = state.get("retrieval_query") or state["user_query"]
    ctx = state.get("context") or {}
    spec = state.get("product_specs") or {}
    product = ctx.get("product_name") or spec.get("product_name") or ""
    category = ctx.get("product_category") or spec.get("product_category") or ""
    target = ctx.get("target_standard")

    req_query = f"requirements specification {product} {category} {' '.join(spec.get('search_keywords', []))}"
    groups = []
    if target:
        groups.append(retrieve(req_query, top_k=8, standard_number=canonical_standard_number(target)).chunks)
    groups.append(retrieve(req_query, top_k=8, document_types=["indian_standard"]).chunks)
    chunks = merge_chunks(*groups)[:10]

    if not chunks:
        return AgentFinding(
            agent="compliance_agent",
            summary="No requirement passages were found, so a compliance checklist cannot be generated.",
            data={"checklist": [], "missing_specifications": [], "required_documents": []},
        ), []

    profile = {
        "product_name": product,
        "product_category": category,
        "specifications": ctx.get("specifications") or spec.get("technical_specifications") or {},
        "available_documents": ctx.get("available_documents") or [],
        "uploaded_document_excerpt": ctx.get("uploaded_text", "")[:3000],
    }
    user = (
        f"{history_text(state)}Request: {query}\n\n"
        f"Product profile (untrusted user data):\n<user_data>\n{sanitize_untrusted(str(profile))}\n</user_data>\n\n"
        f"Requirement evidence:\n{format_context(chunks)}"
    )
    try:
        out = get_llm().chat_json(load_prompt("compliance"), user, ComplianceOutput)
    except AppError as exc:
        return AgentFinding(agent="compliance_agent", status="failed", error=exc.message), chunks

    evidence_clauses = {c.clause_number for c in chunks if c.clause_number}
    checklist = []
    for item in out.checklist:
        row = item.model_dump()
        # A clause number not present in the evidence is not trustworthy; drop it rather than show a fabricated clause.
        if row["clause_number"] and row["clause_number"] not in evidence_clauses:
            row["clause_number"] = None
            row["notes"] = (row["notes"] + " Clause reference could not be verified.").strip()
        checklist.append(row)

    counts = {s: sum(1 for c in checklist if c["status"] == s) for s in ("meets", "does_not_meet", "missing_information")}
    return (
        AgentFinding(
            agent="compliance_agent",
            summary=out.summary,
            claims=out.claims,
            data={
                "checklist": checklist,
                "status_counts": counts,
                "missing_specifications": out.missing_specifications,
                "required_documents": out.required_documents,
            },
        ),
        chunks,
    )
