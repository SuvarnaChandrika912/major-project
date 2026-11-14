"""Chat orchestration: session handling, history and invoking the LangGraph workflow."""

from typing import Any

from sqlalchemy.orm import Session

from app.database import crud, models
from app.database.schemas import AgentTrace, ChatRequest, ChatResponse, Citation, VerificationResult
from app.graph.workflow import run_workflow
from app.utils.errors import NotFoundError


def _title_from(message: str) -> str:
    title = " ".join(message.split())
    return title[:77] + "…" if len(title) > 80 else title


def state_to_trace(state: dict[str, Any]) -> list[AgentTrace]:
    trace = [AgentTrace(agent="supervisor_agent", status="completed",
                        summary=f"Intent: {state.get('intent')}. {state.get('supervisor_reasoning', '')}"[:300])]
    for f in state.get("agent_findings", []):
        trace.append(AgentTrace(agent=f["agent"], status=f["status"],
                                summary=(f.get("summary") or f.get("error") or "")[:300],
                                duration_ms=f.get("duration_ms", 0)))
    v = state.get("verification", {})
    trace.append(AgentTrace(agent="verification_agent", status="completed",
                            summary=f"Evidence {v.get('evidence_status', 'UNKNOWN')}, confidence {v.get('confidence', 0)}"))
    if state.get("response_language", "en") != "en" or state.get("detected_language", "en") != "en":
        trace.append(AgentTrace(agent="translation_agent", status="completed",
                                summary=f"Detected {state.get('detected_language')}, answered in {state.get('response_language')}"))
    return trace


def handle_message(db: Session, user: models.User, request: ChatRequest) -> ChatResponse:
    if request.session_id:
        session = crud.get_user_session(db, user.id, request.session_id)
        if session is None:
            raise NotFoundError("Conversation not found.")
    else:
        session = crud.create_session(db, user.id, _title_from(request.message))

    history = [{"role": m.role, "content": m.message} for m in crud.recent_history(db, session.id)]
    crud.add_message(db, session_id=session.id, role="user", message=request.message)

    state = run_workflow(
        request.message,
        user_id=user.id,
        session_id=session.id,
        history=history,
        language=request.language or (user.preferred_language if user.preferred_language != "en" else None),
        persist=True,
    )
    agents_used = [f["agent"] for f in state.get("agent_findings", [])]
    return ChatResponse(
        session_id=session.id,
        message_id=state.get("message_id") or 0,
        answer=state["final_response"],
        intent=state.get("intent", ""),
        language=state.get("response_language", "en"),
        agents_used=["supervisor_agent", *agents_used, "verification_agent"],
        citations=[Citation(**c) for c in state.get("citations", [])],
        verification=VerificationResult(**state.get("verification", {})),
        follow_up_questions=state.get("follow_up_questions", []),
        clarification_questions=state.get("clarification_questions", []),
        agent_trace=state_to_trace(state),
        structured=state.get("structured", {}),
    )
