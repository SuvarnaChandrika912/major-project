"""Supervisor Agent: intent classification, task decomposition, agent selection and final answer composition."""

import logging
import re

from pydantic import BaseModel, Field

from app.agents.base import history_text, load_prompt
from app.graph.state import SPECIALISTS, AgentName, GraphState, Intent
from app.rag.citations import format_context
from app.rag.retrieval import RetrievedChunk
from app.services.llm_service import get_llm
from app.utils.errors import AppError

logger = logging.getLogger(__name__)

# Base agent plan per intent. Simple intents route to a single specialist.
INTENT_AGENTS: dict[Intent, list[str]] = {
    Intent.GENERAL_BIS_QUERY: [AgentName.STANDARDS.value],
    Intent.PRODUCT_STANDARD_SEARCH: [AgentName.PRODUCT.value, AgentName.STANDARDS.value],
    Intent.CERTIFICATION_QUERY: [AgentName.CERTIFICATION.value],
    Intent.LABORATORY_SEARCH: [AgentName.PRODUCT.value, AgentName.TESTING.value],
    Intent.HALLMARKING_QUERY: [AgentName.CONSUMER.value],
    Intent.CONSUMER_QUERY: [AgentName.CONSUMER.value],
    Intent.COMPLIANCE_ASSESSMENT: [AgentName.PRODUCT.value, AgentName.COMPLIANCE.value, AgentName.STANDARDS.value],
    Intent.STANDARD_COMPARISON: [AgentName.STANDARDS.value],
    Intent.DOCUMENT_ANALYSIS: [AgentName.STANDARDS.value],
}

_KEYWORDS: list[tuple[Intent, tuple[str, ...]]] = [
    (Intent.HALLMARKING_QUERY, ("hallmark", "huid", "jewel", "gold", "silver", "karat", "carat")),
    (Intent.STANDARD_COMPARISON, ("compare", "comparison", "difference between", " vs ", "versus")),
    (Intent.COMPLIANCE_ASSESSMENT, ("comply", "compliance", "checklist", "gap analysis", "does my product meet")),
    (Intent.LABORATORY_SEARCH, ("laboratory", "laboratories", " lab ", "labs", "testing centre", "test report")),
    (Intent.CONSUMER_QUERY, ("complaint", "fake isi", "verify isi", "consumer", "counterfeit", "bis care")),
    (Intent.CERTIFICATION_QUERY, ("certification", "licence", "license", "scheme", "renewal", "fmcs", "crs", "registration", "apply for")),
    (Intent.PRODUCT_STANDARD_SEARCH, ("which standard", "applicable standard", "standard for", "is number", "indian standard for")),
]


class SupervisorPlan(BaseModel):
    intent: Intent
    sub_tasks: list[str] = Field(default_factory=list, max_length=5)
    agents: list[str] = Field(default_factory=list)
    reasoning: str = ""


class ComposedAnswer(BaseModel):
    answer: str
    follow_up_questions: list[str] = Field(default_factory=list, max_length=4)


def keyword_intent(query: str) -> Intent:
    q = f" {query.lower()} "
    for intent, words in _KEYWORDS:
        if any(w in q for w in words):
            return intent
    if re.search(r"\bIS\s*\d", query, re.IGNORECASE):
        return Intent.PRODUCT_STANDARD_SEARCH
    return Intent.GENERAL_BIS_QUERY


def plan(state: GraphState) -> SupervisorPlan:
    query = state.get("retrieval_query") or state["user_query"]
    forced = state.get("forced_intent")
    if forced:
        intent = Intent(forced)
        requested = [a for a in (state.get("context") or {}).get("agents", [])
                     if a in SPECIALISTS or a == AgentName.PRODUCT.value]
        return SupervisorPlan(intent=intent, agents=requested or INTENT_AGENTS[intent],
                              reasoning="Intent fixed by the calling module.")

    llm = get_llm()
    try:
        result = llm.chat_json(
            load_prompt("supervisor"),
            f"{history_text(state)}User request:\n{query}",
            SupervisorPlan,
        )
    except AppError as exc:
        logger.info("Supervisor falling back to keyword routing: %s", exc.message)
        intent = keyword_intent(query)
        return SupervisorPlan(intent=intent, agents=INTENT_AGENTS[intent], reasoning="Keyword-based routing (LLM unavailable).")

    agents = list(INTENT_AGENTS[result.intent])
    # Multi-part requests may need extra specialists, chosen by the LLM but restricted to known agents.
    if len(result.sub_tasks) > 1:
        for a in result.agents:
            if (a in SPECIALISTS or a == AgentName.PRODUCT.value) and a not in agents:
                agents.append(a)
    result.agents = agents
    return result


def _findings_text(findings: list[dict], unsupported: list[str]) -> str:
    lines = []
    for f in findings:
        if f["status"] != "completed":
            lines.append(f"- {f['agent']}: did not complete ({f.get('error') or f['status']}).")
            continue
        claims = [c for c in f.get("claims", []) if c not in unsupported]
        lines.append(f"### {f['agent']}\nSummary: {f.get('summary', '')}")
        lines += [f"- {c}" for c in claims]
        for key in ("candidate_schemes", "documentation_checklist", "process_steps", "required_tests",
                    "recommended_laboratories", "checklist", "missing_specifications", "steps", "version_notes"):
            if f.get("data", {}).get(key):
                lines.append(f"{key}: {f['data'][key]}")
        if f.get("data", {}).get("records"):
            lines.append(f"records: {f['data']['records']}")
    return "\n".join(lines)


def compose(state: GraphState, chunks: list[RetrievedChunk]) -> ComposedAnswer:
    verification = state.get("verification", {})
    unsupported = verification.get("unsupported_claims", [])
    user = (
        f"{history_text(state)}User question:\n{state.get('retrieval_query') or state['user_query']}\n\n"
        f"Detected intent: {state.get('intent')}\n\n"
        f"Verified agent findings:\n{_findings_text(state.get('agent_findings', []), unsupported)}\n\n"
        f"Unsupported claims (must NOT be repeated): {unsupported}\n"
        f"Verification: status={verification.get('evidence_status')}, confidence={verification.get('confidence')}, "
        f"warnings={verification.get('warnings', [])}\n\n"
        f"Evidence:\n{format_context(chunks, max_chars_per_chunk=1000)}\n\n"
        "Write the answer in English. Also propose up to 3 short follow-up questions the user might ask next."
    )
    return get_llm().chat_json(load_prompt("response"), user, ComposedAnswer)
