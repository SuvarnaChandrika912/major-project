"""Standards Research Agent: retrieves clauses from Indian Standards and summarises requirements."""

from pydantic import BaseModel, Field

from app.agents.base import history_text, load_prompt
from app.graph.state import AgentFinding, GraphState, Intent
from app.rag.citations import format_context, merge_chunks
from app.rag.retrieval import RetrievedChunk, retrieve
from app.rag.text_extractor import canonical_standard_number, find_standard_numbers
from app.services.llm_service import get_llm
from app.utils.errors import AppError


class StandardsOutput(BaseModel):
    summary: str
    claims: list[str] = Field(default_factory=list)
    relevant_standards: list[str] = Field(default_factory=list)
    related_standards: list[str] = Field(default_factory=list)
    version_notes: list[str] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)


def search_query(state: GraphState) -> str:
    query = state.get("retrieval_query") or state["user_query"]
    spec = state.get("product_specs") or {}
    extra = " ".join(filter(None, [spec.get("product_name"), spec.get("product_category"), *spec.get("search_keywords", [])]))
    return f"{query} {extra}".strip()


def gather_evidence(state: GraphState) -> list[RetrievedChunk]:
    ctx = state.get("context") or {}
    intent = state.get("intent")
    query = search_query(state)

    if intent == Intent.STANDARD_COMPARISON.value and ctx.get("document_ids"):
        groups = [retrieve(query, top_k=5, document_ids=[d]).chunks for d in ctx["document_ids"]]
        return merge_chunks(*groups)
    if ctx.get("document_id"):
        return retrieve(query, top_k=8, document_ids=[int(ctx["document_id"])]).chunks

    types = None if intent == Intent.GENERAL_BIS_QUERY.value else ["indian_standard"]
    chunks = retrieve(query, document_types=types).chunks
    # Exact standard numbers in the question get a dedicated filtered search.
    for num in find_standard_numbers(state["user_query"])[:2]:
        chunks = merge_chunks(retrieve(query, top_k=4, standard_number=canonical_standard_number(num)).chunks, chunks)
    return chunks[:10]


def run(state: GraphState) -> tuple[AgentFinding, list[RetrievedChunk]]:
    chunks = gather_evidence(state)
    if not chunks:
        return AgentFinding(
            agent="standards_agent",
            summary="No relevant passages were found in the indexed BIS documents.",
            data={"missing_information": ["No indexed document matched the query."]},
        ), []

    task = "Compare the standards in the evidence." if state.get("intent") == Intent.STANDARD_COMPARISON.value else "Answer the question."
    focus = (state.get("context") or {}).get("focus")
    user = (
        f"{history_text(state)}Question: {state.get('retrieval_query') or state['user_query']}\n"
        f"Task: {task}{f' Focus on: {focus}' if focus else ''}\n\nEvidence:\n{format_context(chunks)}"
    )
    try:
        out = get_llm().chat_json(load_prompt("standards"), user, StandardsOutput)
    except AppError as exc:
        return AgentFinding(agent="standards_agent", status="failed", error=exc.message), chunks

    evidence_numbers = {c.standard_number for c in chunks if c.standard_number}
    relevant = [canonical_standard_number(s) for s in out.relevant_standards]
    return (
        AgentFinding(
            agent="standards_agent",
            summary=out.summary,
            claims=out.claims,
            data={
                "relevant_standards": [s for s in relevant if s in evidence_numbers],
                "related_standards": out.related_standards,
                "version_notes": out.version_notes,
                "missing_information": out.missing_information,
            },
        ),
        chunks,
    )
