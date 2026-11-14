"""Product Classification Agent: extracts product attributes and finds candidate standards from evidence."""

from app.agents.base import history_text, load_prompt
from app.graph.state import AgentFinding, GraphState, ProductSpecification
from app.rag.retrieval import RetrievedChunk, retrieve
from app.services.llm_service import get_llm
from app.utils.errors import AppError


def run(state: GraphState) -> tuple[AgentFinding, list[RetrievedChunk]]:
    query = state.get("retrieval_query") or state["user_query"]
    ctx = state.get("context") or {}
    form_details = "\n".join(f"{k}: {v}" for k, v in ctx.items() if isinstance(v, (str, int, float)) and v)
    user = f"{history_text(state)}User request:\n{query}"
    if form_details:
        user += f"\n\nProduct details supplied in the form (user data):\n{form_details}"

    try:
        spec = get_llm().chat_json(load_prompt("product"), user, ProductSpecification)
    except AppError as exc:
        spec = ProductSpecification(product_name=ctx.get("product_name"), product_category=ctx.get("product_category"))
        if not spec.product_name:
            return AgentFinding(agent="product_agent", status="failed", error=exc.message), []

    keywords = " ".join(
        filter(None, [spec.product_name, spec.product_category, spec.material, spec.usage, *spec.search_keywords])
    )
    result = retrieve(f"{keywords} {query}".strip(), top_k=6, document_types=["indian_standard"])

    # Candidate standards come only from retrieved documents, never from model memory.
    candidates: list[dict] = []
    for i, chunk in enumerate(result.chunks, start=1):
        if chunk.standard_number and all(c["standard_number"] != chunk.standard_number for c in candidates):
            candidates.append(
                {"standard_number": chunk.standard_number, "title": chunk.standard_title,
                 "status": chunk.document_status, "evidence": f"[{i}]"}
            )

    summary = f"Identified product: {spec.product_name or 'not specified'}"
    if spec.product_category:
        summary += f" (category: {spec.product_category})"
    summary += f". {len(candidates)} candidate standard(s) found in indexed documents." if candidates else ". No matching standards found in indexed documents."

    return (
        AgentFinding(
            agent="product_agent",
            summary=summary,
            claims=[f"Candidate standard {c['standard_number']} ({c['title']}) matched the product {c['evidence']}" for c in candidates],
            data={"specifications": spec.model_dump(), "candidate_standards": candidates},
            clarification_questions=spec.clarification_questions[:3],
        ),
        result.chunks,
    )
