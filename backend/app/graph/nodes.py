"""LangGraph node functions. Each node reads the shared state and returns a partial update."""

import logging
import re
from typing import Any

from app.agents import (
    certification_agent,
    compliance_agent,
    consumer_agent,
    product_agent,
    standards_agent,
    supervisor_agent,
    testing_agent,
    translation_agent,
    verification_agent,
)
from app.agents.base import globalize_markers, run_agent
from app.database import crud
from app.database.connection import SessionLocal
from app.graph.state import GraphState, Intent
from app.rag.citations import build_citations, citation_label, validate_citations
from app.rag.retrieval import RetrievedChunk, retrieve
from app.services.llm_service import get_llm
from app.utils.errors import AppError

logger = logging.getLogger(__name__)

MAX_CITATIONS = 12
_TOKEN_RE = re.compile(r"\[\[cid:([^\]]+)\]\]")
_MARKER_RE = re.compile(r"\[(\d{1,3})\]")
_RECORD_RE = re.compile(r"\[([SLR]\d{1,3})\]")


# ---------- helpers ----------
def _all_chunks(state: GraphState) -> dict[str, RetrievedChunk]:
    out: dict[str, RetrievedChunk] = {}
    for raw in state.get("retrieved_chunks", []):
        out.setdefault(raw["chunk_id"], RetrievedChunk(**raw))
    return out


def cited_chunks(state: GraphState) -> list[RetrievedChunk]:
    by_id = _all_chunks(state)
    return [by_id[c["chunk_id"]] for c in state.get("citations", []) if c["chunk_id"] in by_id]


def processed_findings(state: GraphState) -> list[dict[str, Any]]:
    """Agent findings with chunk tokens converted to global citation numbers."""
    index = {c["chunk_id"]: c["index"] for c in state.get("citations", [])}
    return [globalize_markers(f, index) for f in state.get("agent_findings", [])]


def _records(findings: list[dict]) -> dict[str, dict]:
    records: dict[str, dict] = {}
    for f in findings:
        records.update(f.get("data", {}).get("records", {}) or {})
    return records


def _replace_record_markers(text: str, records: dict[str, dict]) -> str:
    def repl(m: re.Match) -> str:
        rec = records.get(m.group(1))
        if not rec:
            return ""
        name = rec.get("name", m.group(1))
        return f" ([{name}]({rec['url']}))" if rec.get("url") else f" (*{name}*)"

    return _RECORD_RE.sub(repl, text)


# ---------- nodes ----------
def receive_query(state: GraphState) -> dict:
    return {
        "user_query": state["user_query"].strip(),
        "retrieval_attempts": state.get("retrieval_attempts", 0),
        "context": state.get("context") or {},
    }


def detect_language(state: GraphState) -> dict:
    detected = translation_agent.detect_language(state["user_query"])
    return {"detected_language": detected, "response_language": state.get("requested_language") or detected}


def translate_query(state: GraphState) -> dict:
    """Retrieval runs in English; non-English queries are translated with identifiers preserved."""
    if state["detected_language"] == "en":
        return {"retrieval_query": state["user_query"]}
    translated, ok = translation_agent.translate(state["user_query"], "en", state["detected_language"])
    errors = [] if ok else ["translation: query could not be translated; searching with the original text."]
    return {"retrieval_query": translated, "errors": errors}


def supervisor(state: GraphState) -> dict:
    plan = supervisor_agent.plan(state)
    logger.info("Supervisor routed query", extra={"intent": plan.intent.value})
    return {
        "intent": plan.intent.value,
        "sub_tasks": plan.sub_tasks,
        "selected_agents": plan.agents,
        "supervisor_reasoning": plan.reasoning,
    }


def product_node(state: GraphState) -> dict:
    update = run_agent("product_agent", state, product_agent.run)
    finding = update["agent_findings"][0]
    update["product_specs"] = finding.get("data", {}).get("specifications", {}) or {}
    return update


def standards_node(state: GraphState) -> dict:
    return run_agent("standards_agent", state, standards_agent.run)


def certification_node(state: GraphState) -> dict:
    return run_agent("certification_agent", state, certification_agent.run)


def testing_node(state: GraphState) -> dict:
    return run_agent("testing_agent", state, testing_agent.run)


def consumer_node(state: GraphState) -> dict:
    return run_agent("consumer_agent", state, consumer_agent.run)


def compliance_node(state: GraphState) -> dict:
    return run_agent("compliance_agent", state, compliance_agent.run)


def collect_evidence(state: GraphState) -> dict:
    """Merge evidence from all agents into one globally numbered citation list.

    Chunks actually cited by agents come first, then the remaining highest-scoring chunks.
    """
    by_id = _all_chunks(state)
    referenced: list[str] = []
    for f in state.get("agent_findings", []):
        for cid in _TOKEN_RE.findall(str(f)):
            if cid in by_id and cid not in referenced:
                referenced.append(cid)
    rest = sorted((c for cid, c in by_id.items() if cid not in referenced), key=lambda c: -c.score)
    ordered = [by_id[cid] for cid in referenced] + rest
    return {"citations": [c.model_dump() for c in build_citations(ordered[:MAX_CITATIONS])]}


def verification(state: GraphState) -> dict:
    findings = processed_findings(state)
    claims = [c for f in findings if f["status"] == "completed" for c in f.get("claims", [])]
    result = verification_agent.verify(state.get("retrieval_query") or state["user_query"], claims, cited_chunks(state))
    return {"verification": result.model_dump()}


def expand_retrieval(state: GraphState) -> dict:
    """Second retrieval pass without document-type filters when evidence was insufficient."""
    spec = state.get("product_specs") or {}
    query = " ".join(filter(None, [state.get("retrieval_query") or state["user_query"],
                                   spec.get("product_name"), *spec.get("search_keywords", [])]))
    result = retrieve(query, top_k=10)
    return {
        "retrieved_chunks": [c.to_dict() for c in result.chunks],
        "retrieval_attempts": state.get("retrieval_attempts", 0) + 1,
    }


def _fallback_answer(state: GraphState, chunks: list[RetrievedChunk], reason: str) -> str:
    if not chunks:
        return (
            f"{reason}\n\nNo relevant passages were found in the indexed BIS documents for this question. "
            "Please rephrase the question, add product details, or check the official BIS website."
        )
    lines = [f"{reason}\n\nThe most relevant passages found in the indexed BIS documents are:"]
    for i, c in enumerate(chunks[:5], start=1):
        label = citation_label(build_citations([c])[0])
        lines.append(f"- **{label}**: {c.text[:300].strip()}… [{i}]")
    return "\n".join(lines)


def generate_response(state: GraphState) -> dict:
    chunks = cited_chunks(state)
    findings = processed_findings(state)
    verification_result = state.get("verification", {})
    records = _records(findings)

    follow_ups: list[str] = []
    try:
        get_llm().ensure_available()
        composed = supervisor_agent.compose({**state, "agent_findings": findings}, chunks)
        answer, follow_ups = composed.answer, composed.follow_up_questions
    except AppError as exc:
        answer = _fallback_answer(state, chunks, f"**Note:** {exc.message}")

    answer, invalid = validate_citations(answer, len(chunks))
    answer = _replace_record_markers(answer, records)

    # Keep only citations referenced in the answer and renumber them sequentially.
    used = sorted({int(m) for m in _MARKER_RE.findall(answer)})
    citations = state.get("citations", [])
    if used:
        renumber = {old: new for new, old in enumerate(used, start=1)}
        answer = _MARKER_RE.sub(lambda m: f"[{renumber[int(m.group(1))]}]" if int(m.group(1)) in renumber else "", answer)
        citations = [{**citations[old - 1], "index": renumber[old]} for old in used if old <= len(citations)]
    else:
        citations = citations[:5]

    clarifications = [q for f in findings for q in f.get("clarification_questions", [])][:3]
    if verification_result.get("evidence_status") == "INSUFFICIENT" and clarifications:
        answer += "\n\n**To give a more precise answer, please tell me:**\n" + "\n".join(f"- {q}" for q in clarifications)

    structured: dict[str, Any] = {"supervisor_reasoning": state.get("supervisor_reasoning", ""),
                                  "sub_tasks": state.get("sub_tasks", [])}
    for f in findings:
        if f["status"] == "completed":
            structured[f["agent"]] = {k: v for k, v in f.get("data", {}).items() if k != "records"}
    if invalid:
        structured["removed_invalid_citations"] = invalid

    return {
        "final_response": answer.strip(),
        "follow_up_questions": follow_ups[:3],
        "clarification_questions": clarifications,
        "citations": citations,
        "structured": structured,
    }


def translate_response(state: GraphState) -> dict:
    target = state.get("response_language") or "en"
    if target == "en":
        return {}
    answer, ok = translation_agent.translate(state["final_response"], target, "en")
    follow_ups = [translation_agent.translate(q, target, "en")[0] for q in state.get("follow_up_questions", [])]
    update: dict[str, Any] = {"final_response": answer, "follow_up_questions": follow_ups}
    if not ok:
        update["errors"] = ["translation: the answer is shown in English because translation was unavailable."]
    return update


def save_conversation(state: GraphState) -> dict:
    if not state.get("persist") or not state.get("session_id"):
        return {"message_id": None}
    findings = state.get("agent_findings", [])
    trace = [
        {"agent": f["agent"], "status": f["status"], "summary": (f.get("summary") or f.get("error") or "")[:300],
         "duration_ms": f.get("duration_ms", 0)}
        for f in findings
    ]
    extra = {
        "citations": state.get("citations", []),
        "verification": state.get("verification", {}),
        "follow_up_questions": state.get("follow_up_questions", []),
        "clarification_questions": state.get("clarification_questions", []),
        "agent_trace": trace,
        "language": state.get("response_language", "en"),
        "structured": globalize_markers(state.get("structured", {}), {}),
    }
    with SessionLocal() as db:
        msg = crud.add_message(
            db,
            session_id=state["session_id"],
            role="assistant",
            message=state["final_response"],
            agent_used=",".join(f["agent"] for f in findings) or "supervisor_agent",
            intent=state.get("intent"),
            extra=extra,
        )
    return {"message_id": msg.id}


# Intent value list kept here so routing stays consistent with the supervisor's enum.
VALID_INTENTS = {i.value for i in Intent}
