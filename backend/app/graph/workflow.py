"""BIS SAATHI multi-agent graph.

START -> receive_query -> detect_language -> translate_query -> supervisor
      -> [product_agent] -> parallel specialists (Send fan-out) -> collect_evidence
      -> verification -> (insufficient? expand_retrieval -> collect_evidence -> verification)
      -> generate_response -> translate_response -> save_conversation -> END
"""

import logging
from functools import lru_cache
from typing import Any

from langgraph.graph import END, START, StateGraph

from app.graph import nodes
from app.graph.routing import dispatch_specialists, route_after_supervisor, route_after_verification
from app.graph.state import SPECIALISTS, AgentName, GraphState

logger = logging.getLogger(__name__)

SPECIALIST_NODES = {
    AgentName.STANDARDS.value: nodes.standards_node,
    AgentName.CERTIFICATION.value: nodes.certification_node,
    AgentName.TESTING.value: nodes.testing_node,
    AgentName.CONSUMER.value: nodes.consumer_node,
    AgentName.COMPLIANCE.value: nodes.compliance_node,
}


def build_graph():
    graph = StateGraph(GraphState)

    graph.add_node("receive_query", nodes.receive_query)
    graph.add_node("detect_language", nodes.detect_language)
    graph.add_node("translate_query", nodes.translate_query)
    graph.add_node("supervisor", nodes.supervisor)
    graph.add_node(AgentName.PRODUCT.value, nodes.product_node)
    for name, fn in SPECIALIST_NODES.items():
        graph.add_node(name, fn)
    graph.add_node("collect_evidence", nodes.collect_evidence)
    graph.add_node("verification", nodes.verification)
    graph.add_node("expand_retrieval", nodes.expand_retrieval)
    graph.add_node("generate_response", nodes.generate_response)
    graph.add_node("translate_response", nodes.translate_response)
    graph.add_node("save_conversation", nodes.save_conversation)

    graph.add_edge(START, "receive_query")
    graph.add_edge("receive_query", "detect_language")
    graph.add_edge("detect_language", "translate_query")
    graph.add_edge("translate_query", "supervisor")

    fan_out_targets = [*SPECIALISTS, "collect_evidence"]
    graph.add_conditional_edges("supervisor", route_after_supervisor, [AgentName.PRODUCT.value, *fan_out_targets])
    graph.add_conditional_edges(AgentName.PRODUCT.value, dispatch_specialists, fan_out_targets)
    for name in SPECIALIST_NODES:
        graph.add_edge(name, "collect_evidence")

    graph.add_edge("collect_evidence", "verification")
    graph.add_conditional_edges(
        "verification", route_after_verification, ["expand_retrieval", "generate_response"]
    )
    graph.add_edge("expand_retrieval", "collect_evidence")
    graph.add_edge("generate_response", "translate_response")
    graph.add_edge("translate_response", "save_conversation")
    graph.add_edge("save_conversation", END)
    return graph.compile()


@lru_cache
def get_workflow():
    return build_graph()


def run_workflow(
    query: str,
    *,
    user_id: int | None = None,
    session_id: int | None = None,
    history: list[dict[str, str]] | None = None,
    language: str | None = None,
    forced_intent: str | None = None,
    context: dict[str, Any] | None = None,
    persist: bool = False,
) -> GraphState:
    initial: GraphState = {
        "user_query": query,
        "user_id": user_id,
        "session_id": session_id,
        "history": history or [],
        "requested_language": language,
        "forced_intent": forced_intent,
        "context": context or {},
        "persist": persist,
        "retrieved_chunks": [],
        "agent_findings": [],
        "errors": [],
        "retrieval_attempts": 0,
    }
    return get_workflow().invoke(initial, config={"recursion_limit": 40})
