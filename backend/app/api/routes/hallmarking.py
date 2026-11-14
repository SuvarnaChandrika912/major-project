"""Hallmarking and consumer-help endpoints. Both run the graph with a fixed intent and the consumer agent."""

from fastapi import APIRouter, Depends

from app.database import models
from app.database.schemas import AssistantAnswer, AssistantQuery, Citation, VerificationResult
from app.dependencies import get_current_user
from app.graph.state import Intent
from app.graph.workflow import run_workflow
from app.utils.official_resources import OFFICIAL_RESOURCES

router = APIRouter(prefix="/api", tags=["Hallmarking & Consumer"])


def _answer(query: AssistantQuery, intent: Intent, user: models.User) -> AssistantAnswer:
    state = run_workflow(query.query, user_id=user.id, language=query.language, forced_intent=intent.value)
    resources = state.get("structured", {}).get("consumer_agent", {}).get("official_resources") or [
        {"name": r["name"], "url": r["url"], "purpose": r["purpose"]} for r in OFFICIAL_RESOURCES
    ]
    return AssistantAnswer(
        answer=state["final_response"],
        intent=state.get("intent", intent.value),
        citations=[Citation(**c) for c in state.get("citations", [])],
        verification=VerificationResult(**state.get("verification", {})),
        follow_up_questions=state.get("follow_up_questions", []),
        official_resources=resources,
        agents_used=[f["agent"] for f in state.get("agent_findings", [])],
    )


@router.post("/hallmarking/query", response_model=AssistantAnswer)
def hallmarking_query(payload: AssistantQuery, user: models.User = Depends(get_current_user)) -> AssistantAnswer:
    return _answer(payload, Intent.HALLMARKING_QUERY, user)


@router.post("/consumer/query", response_model=AssistantAnswer)
def consumer_query(payload: AssistantQuery, user: models.User = Depends(get_current_user)) -> AssistantAnswer:
    return _answer(payload, Intent.CONSUMER_QUERY, user)


@router.get("/consumer/resources")
def official_resources(_user: models.User = Depends(get_current_user)) -> list[dict]:
    return [{"name": r["name"], "url": r["url"], "purpose": r["purpose"]} for r in OFFICIAL_RESOURCES]
