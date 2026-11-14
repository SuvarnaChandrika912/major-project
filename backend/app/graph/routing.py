"""Conditional edges of the BIS SAATHI graph."""

try:
    from langgraph.types import Send
except ImportError:  # older langgraph
    from langgraph.constants import Send

from app.graph.state import SPECIALISTS, AgentName, GraphState
from app.services.llm_service import get_llm

MAX_RETRIEVAL_ATTEMPTS = 1


def dispatch_specialists(state: GraphState) -> list[Send] | str:
    """Fan out to the selected specialists in parallel; each receives the current shared state."""
    targets = [a for a in state.get("selected_agents", []) if a in SPECIALISTS]
    if not targets:
        return "collect_evidence"
    return [Send(agent, state) for agent in targets]


def route_after_supervisor(state: GraphState) -> list[Send] | str:
    # The product agent runs first so specialists can use the extracted product specification.
    if AgentName.PRODUCT.value in state.get("selected_agents", []):
        return AgentName.PRODUCT.value
    return dispatch_specialists(state)


def route_after_verification(state: GraphState) -> str:
    status = state.get("verification", {}).get("evidence_status")
    if (
        status == "INSUFFICIENT"
        and state.get("retrieval_attempts", 0) < MAX_RETRIEVAL_ATTEMPTS
        and get_llm().is_available()
    ):
        return "expand_retrieval"
    return "generate_response"
