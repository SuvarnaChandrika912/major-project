"""Deterministic test doubles. Outputs are synthetic and exist only to exercise the pipeline."""

import hashlib
import math
from typing import Any

from pydantic import BaseModel

from app.config import settings
from app.services.llm_service import LLMService


class FakeEmbedder:
    dimension = settings.EMBEDDING_DIMENSION

    def _vec(self, text: str) -> list[float]:
        digest = hashlib.sha256(text.encode()).digest()
        raw = [digest[i % len(digest)] / 255.0 - 0.5 for i in range(self.dimension)]
        norm = math.sqrt(sum(v * v for v in raw)) or 1.0
        return [v / norm for v in raw]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._vec(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._vec(text)


_OUTPUTS: dict[str, dict[str, Any]] = {
    "ProductSpecification": {"product_name": "test widget", "product_category": "widgets",
                             "search_keywords": ["widget", "stainless steel"], "clarification_questions": []},
    "StandardsOutput": {"summary": "Clause 4.1 covers material [1].",
                        "claims": ["Clause 4.1 requires food grade stainless steel [1]"],
                        "relevant_standards": ["IS 99999:2024", "IS 12345"]},
    "CertificationOutput": {"summary": "Certification evidence reviewed [1].", "claims": ["Evidence reviewed [1]"]},
    "TestingOutput": {"summary": "Leakage test required [1].", "claims": ["A leakage test is required [1]"],
                      "required_tests": [{"test": "Leakage", "clause_number": "5.1", "citation": "[1]"}]},
    "ConsumerOutput": {"summary": "Verify marks using official resources [R1].", "claims": ["Use official resources [R1]"],
                       "resources_used": ["R1"]},
    "ComplianceOutput": {"summary": "One requirement lacks data [1].", "claims": ["Material is specified in clause 4.1 [1]"],
                         "checklist": [{"requirement": "Food grade stainless steel body", "clause_number": "4.1",
                                        "citation": "[1]", "status": "missing_information", "notes": ""},
                                       {"requirement": "Invented requirement", "clause_number": "9.9",
                                        "citation": "[1]", "status": "meets", "notes": ""}],
                         "missing_specifications": ["Body material"], "required_documents": []},
    "LLMVerdict": {"supported_claims": [], "unsupported_claims": [], "contradictions": [], "confidence": 0.9,
                   "evidence_sufficient": True},
    "ComposedAnswer": {"answer": "Synthetic answer: the widget body must be stainless steel [1]. Invalid [42].",
                       "follow_up_questions": ["What tests apply?"]},
    "ReportContent": {"executive_summary": "Synthetic executive summary [1].",
                      "sections": [{"heading": "Findings", "content": "- Item one\n- Item two"}],
                      "recommendations": ["Provide body material"], "limitations": []},
}


class FakeLLM(LLMService):
    def __init__(self, available: bool = True) -> None:
        super().__init__()
        self.available = available
        self.calls: list[str] = []

    def is_available(self, force: bool = False) -> bool:
        return self.available

    def status(self) -> str:
        return "ready (fake)" if self.available else "unavailable (fake)"

    def chat(self, system: str, user: str, retries: int = 2) -> str:
        self.ensure_available()
        self.calls.append("chat")
        return user.split("Text:\n", 1)[-1]

    def chat_json(self, system: str, user: str, schema: type[BaseModel], retries: int = 2) -> BaseModel:
        self.ensure_available()
        self.calls.append(schema.__name__)
        if schema.__name__ == "SupervisorPlan":
            from app.agents.supervisor_agent import keyword_intent

            return schema.model_validate({"intent": keyword_intent(user).value, "sub_tasks": [], "agents": []})
        return schema.model_validate(_OUTPUTS.get(schema.__name__, {}))
