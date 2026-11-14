"""Shared LangGraph state and the structured objects agents exchange through it."""

import operator
from enum import Enum
from typing import Annotated, Any, Literal, TypedDict

from pydantic import BaseModel, Field


class Intent(str, Enum):
    GENERAL_BIS_QUERY = "GENERAL_BIS_QUERY"
    PRODUCT_STANDARD_SEARCH = "PRODUCT_STANDARD_SEARCH"
    CERTIFICATION_QUERY = "CERTIFICATION_QUERY"
    LABORATORY_SEARCH = "LABORATORY_SEARCH"
    HALLMARKING_QUERY = "HALLMARKING_QUERY"
    CONSUMER_QUERY = "CONSUMER_QUERY"
    COMPLIANCE_ASSESSMENT = "COMPLIANCE_ASSESSMENT"
    STANDARD_COMPARISON = "STANDARD_COMPARISON"
    DOCUMENT_ANALYSIS = "DOCUMENT_ANALYSIS"


class AgentName(str, Enum):
    PRODUCT = "product_agent"
    STANDARDS = "standards_agent"
    CERTIFICATION = "certification_agent"
    TESTING = "testing_agent"
    CONSUMER = "consumer_agent"
    COMPLIANCE = "compliance_agent"


SPECIALISTS = [
    AgentName.STANDARDS.value,
    AgentName.CERTIFICATION.value,
    AgentName.TESTING.value,
    AgentName.CONSUMER.value,
    AgentName.COMPLIANCE.value,
]


class AgentFinding(BaseModel):
    """Structured output every specialist agent writes into the graph state."""

    agent: str
    status: Literal["completed", "failed", "skipped", "timeout"] = "completed"
    summary: str = ""
    claims: list[str] = Field(default_factory=list, description="Factual statements, each citing evidence like [2]")
    data: dict[str, Any] = Field(default_factory=dict)
    chunk_ids: list[str] = Field(default_factory=list)
    clarification_questions: list[str] = Field(default_factory=list)
    duration_ms: int = 0
    error: str | None = None


class ProductSpecification(BaseModel):
    product_name: str | None = None
    product_category: str | None = None
    material: str | None = None
    usage: str | None = None
    capacity: str | None = None
    technical_specifications: dict[str, str] = Field(default_factory=dict)
    search_keywords: list[str] = Field(default_factory=list)
    clarification_questions: list[str] = Field(default_factory=list)


class GraphState(TypedDict, total=False):
    # Input
    user_query: str
    user_id: int | None
    session_id: int | None
    history: list[dict[str, str]]
    requested_language: str | None
    forced_intent: str | None
    context: dict[str, Any]  # structured inputs from forms (certification wizard, compliance workspace ...)
    persist: bool

    # Language handling
    detected_language: str
    response_language: str
    retrieval_query: str

    # Supervisor
    intent: str
    sub_tasks: list[str]
    selected_agents: list[str]
    supervisor_reasoning: str

    # Shared findings (parallel branches append via reducers)
    product_specs: dict[str, Any]
    retrieved_chunks: Annotated[list[dict[str, Any]], operator.add]
    agent_findings: Annotated[list[dict[str, Any]], operator.add]
    errors: Annotated[list[str], operator.add]

    # Verification
    citations: list[dict[str, Any]]
    verification: dict[str, Any]
    retrieval_attempts: int

    # Output
    final_response: str
    follow_up_questions: list[str]
    clarification_questions: list[str]
    structured: dict[str, Any]
    message_id: int | None
