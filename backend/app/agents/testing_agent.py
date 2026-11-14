"""Testing and Laboratory Agent: testing requirements and evidence-backed laboratory matching."""

from pydantic import BaseModel, Field
from sqlalchemy import or_, select

from app.agents.base import history_text, load_prompt
from app.database import models
from app.database.connection import SessionLocal
from app.graph.state import AgentFinding, GraphState
from app.rag.citations import format_context
from app.rag.retrieval import RetrievedChunk, retrieve, tokenize
from app.services.llm_service import get_llm
from app.utils.errors import AppError

MAX_LABS = 15


class RequiredTest(BaseModel):
    test: str
    clause_number: str | None = None
    citation: str = ""


class LabRecommendation(BaseModel):
    label: str = Field(description="Record label such as L1")
    reason: str


class TestingOutput(BaseModel):
    summary: str
    claims: list[str] = Field(default_factory=list)
    required_tests: list[RequiredTest] = Field(default_factory=list)
    recommended_laboratories: list[LabRecommendation] = Field(default_factory=list)


def find_laboratories(keywords: list[str], state: str | None = None, city: str | None = None) -> list[models.Laboratory]:
    with SessionLocal() as db:
        stmt = select(models.Laboratory)
        if state:
            stmt = stmt.where(models.Laboratory.state == state)
        if city:
            stmt = stmt.where(models.Laboratory.city == city)
        words = [w for w in keywords if len(w) > 3][:8]
        if words:
            conds = []
            for w in words:
                like = f"%{w}%"
                conds += [models.Laboratory.testing_capabilities.ilike(like), models.Laboratory.product_categories.ilike(like)]
            stmt = stmt.where(or_(*conds))
        return list(db.scalars(stmt.limit(MAX_LABS)))


def run(state: GraphState) -> tuple[AgentFinding, list[RetrievedChunk]]:
    query = state.get("retrieval_query") or state["user_query"]
    spec = state.get("product_specs") or {}
    ctx = state.get("context") or {}
    product_terms = " ".join(filter(None, [spec.get("product_name"), spec.get("product_category"), *spec.get("search_keywords", [])]))
    chunks = retrieve(
        f"test methods testing requirements {product_terms} {query}",
        document_types=["indian_standard", "laboratory_information"],
    ).chunks

    labs = find_laboratories(tokenize(product_terms or query), ctx.get("state"), ctx.get("city"))
    records = {
        f"L{i}": {
            "laboratory_id": lab.id, "name": lab.laboratory_name, "city": lab.city or "", "state": lab.state or "",
            "recognition_status": lab.recognition_status or "not recorded",
            "testing_capabilities": lab.testing_capabilities or "", "url": lab.official_source_url or "",
        }
        for i, lab in enumerate(labs, start=1)
    }
    if not chunks and not records:
        return AgentFinding(
            agent="testing_agent",
            summary="No testing requirements or matching laboratory records were found in the knowledge base.",
        ), []

    labs_text = "\n".join(
        f"[{k}] {v['name']} ({v['city']}, {v['state']}) recognition: {v['recognition_status']}; capabilities: {v['testing_capabilities']}"
        for k, v in records.items()
    ) or "No laboratory records matched."
    user = (
        f"{history_text(state)}Question: {query}\nProduct: {product_terms or 'not specified'}\n\n"
        f"Laboratory records:\n{labs_text}\n\nEvidence:\n{format_context(chunks)}"
    )
    try:
        out = get_llm().chat_json(load_prompt("testing"), user, TestingOutput)
    except AppError as exc:
        return AgentFinding(agent="testing_agent", status="failed", error=exc.message, data={"records": records}), chunks

    recommended = [
        {**records[r.label], "reason": r.reason} for r in out.recommended_laboratories if r.label in records
    ]
    return (
        AgentFinding(
            agent="testing_agent",
            summary=out.summary,
            claims=out.claims,
            data={
                "required_tests": [t.model_dump() for t in out.required_tests],
                "recommended_laboratories": recommended,
                "records": records,
            },
        ),
        chunks,
    )
