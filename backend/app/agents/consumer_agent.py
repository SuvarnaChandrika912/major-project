"""Consumer and Hallmarking Agent: ISI mark, hallmarking, HUID, verification and complaints."""

from pydantic import BaseModel, Field

from app.agents.base import history_text, load_prompt
from app.graph.state import AgentFinding, GraphState, Intent
from app.rag.citations import format_context
from app.rag.retrieval import RetrievedChunk, retrieve
from app.services.llm_service import get_llm
from app.utils.errors import AppError
from app.utils.official_resources import OFFICIAL_RESOURCES


class ConsumerOutput(BaseModel):
    summary: str
    claims: list[str] = Field(default_factory=list)
    steps: list[str] = Field(default_factory=list, description="Practical steps for the consumer, if applicable")
    resources_used: list[str] = Field(default_factory=list, description="Labels such as R1 that are relevant")


def run(state: GraphState) -> tuple[AgentFinding, list[RetrievedChunk]]:
    query = state.get("retrieval_query") or state["user_query"]
    hallmarking = state.get("intent") == Intent.HALLMARKING_QUERY.value
    types = ["hallmarking", "faq"] if hallmarking else ["faq", "certification_guideline", "hallmarking"]
    chunks = retrieve(query, document_types=types).chunks

    records = {r["label"]: {"name": r["name"], "url": r["url"], "purpose": r["purpose"]} for r in OFFICIAL_RESOURCES}
    resources_text = "\n".join(f"[{k}] {v['name']} - {v['purpose']} ({v['url']})" for k, v in records.items())
    user = (
        f"{history_text(state)}Question: {query}\n\nOfficial resources:\n{resources_text}\n\n"
        f"Evidence:\n{format_context(chunks)}"
    )
    try:
        out = get_llm().chat_json(load_prompt("consumer"), user, ConsumerOutput)
    except AppError as exc:
        return AgentFinding(agent="consumer_agent", status="failed", error=exc.message, data={"records": records}), chunks

    used = [records[label] for label in out.resources_used if label in records] or list(records.values())
    return (
        AgentFinding(
            agent="consumer_agent",
            summary=out.summary,
            claims=out.claims,
            data={"steps": out.steps, "official_resources": used, "records": records},
        ),
        chunks,
    )
