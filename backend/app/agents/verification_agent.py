"""Verification Agent: deterministic evidence checks followed by an LLM support judgement."""

import logging
import re

from pydantic import BaseModel, Field

from app.agents.base import load_prompt
from app.database.schemas import VerificationResult
from app.rag.citations import format_context
from app.rag.retrieval import RetrievedChunk
from app.rag.text_extractor import find_standard_numbers
from app.services.llm_service import get_llm
from app.utils.errors import AppError
from app.utils.security import contains_injection

logger = logging.getLogger(__name__)

_MARKER_RE = re.compile(r"\[(\d{1,3})\]")
_RECORD_RE = re.compile(r"\[[SLR]\d{1,3}\]")
_MONEY_RE = re.compile(r"(₹|rs\.?|inr)\s?\d", re.IGNORECASE)


class LLMVerdict(BaseModel):
    supported_claims: list[str] = Field(default_factory=list)
    unsupported_claims: list[str] = Field(default_factory=list)
    contradictions: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    evidence_sufficient: bool = False


def deterministic_checks(claims: list[str], chunks: list[RetrievedChunk]) -> tuple[list[str], list[str], list[str]]:
    """Returns (claims_to_judge, unsupported, warnings) without using the LLM."""
    evidence_numbers = {c.standard_number for c in chunks if c.standard_number}
    evidence_text = " ".join(c.text for c in chunks)
    evidence_numbers |= set(find_standard_numbers(evidence_text))
    to_judge, unsupported, warnings = [], [], []
    for claim in claims:
        markers = [int(m) for m in _MARKER_RE.findall(claim)]
        if "[?" in claim or any(m < 1 or m > len(chunks) for m in markers):
            unsupported.append(claim)
            continue
        if not markers and not _RECORD_RE.search(claim):
            unsupported.append(claim)
            continue
        unknown = [n for n in find_standard_numbers(claim) if n not in evidence_numbers
                   and not any(n.split(":")[0] == e.split(":")[0] for e in evidence_numbers)]
        if unknown:
            unsupported.append(claim)
            warnings.append(f"Removed a claim referencing {', '.join(unknown)}, which is not in the retrieved documents.")
            continue
        if _MONEY_RE.search(claim) and not _MONEY_RE.search(evidence_text):
            unsupported.append(claim)
            continue
        to_judge.append(claim)
    return to_judge, unsupported, warnings


def verify(question: str, claims: list[str], chunks: list[RetrievedChunk]) -> VerificationResult:
    if not chunks:
        return VerificationResult(
            evidence_status="INSUFFICIENT",
            confidence=0.0,
            unsupported_claims=[c for c in claims if not _RECORD_RE.search(c)],
            warnings=["No supporting passages were found in the indexed BIS documents."],
        )

    to_judge, unsupported, warnings = deterministic_checks(claims, chunks)

    outdated = sorted({
        f"{c.standard_number or c.standard_title} ({c.document_status})"
        for c in chunks if c.document_status in {"superseded", "withdrawn"}
    })
    if outdated:
        warnings.append("Some evidence comes from superseded or withdrawn documents: " + ", ".join(outdated))
    if any(contains_injection(c.text) for c in chunks):
        warnings.append("A retrieved document contained instruction-like text; it was treated as data only.")

    supported: list[str] = []
    confidence = 0.0
    sufficient = False
    try:
        if to_judge or claims:
            user = (
                f"User question: {question}\n\nClaims to verify:\n"
                + "\n".join(f"- {c}" for c in to_judge or ["(no claims; judge evidence sufficiency only)"])
                + f"\n\nEvidence:\n{format_context(chunks, max_chars_per_chunk=1200)}"
            )
            verdict = get_llm().chat_json(load_prompt("verification"), user, LLMVerdict)
            judged_unsupported = {c.strip() for c in verdict.unsupported_claims}
            for claim in to_judge:
                (unsupported if claim.strip() in judged_unsupported else supported).append(claim)
            warnings += [f"Possible contradiction: {c}" for c in verdict.contradictions]
            confidence = verdict.confidence
            sufficient = verdict.evidence_sufficient
    except AppError as exc:
        logger.info("LLM verification unavailable: %s", exc.message)
        supported = to_judge
        confidence = 0.3
        warnings.append("Automated claim verification was limited because the language model was unavailable.")

    if claims:
        support_ratio = len(supported) / max(1, len(claims))
        confidence = round(min(confidence, 0.4 + 0.6 * support_ratio), 2)

    if sufficient and confidence >= 0.6:
        status = "SUFFICIENT"
    elif confidence >= 0.3 or supported:
        status = "PARTIAL"
    else:
        status = "INSUFFICIENT"

    return VerificationResult(
        evidence_status=status,
        confidence=confidence,
        supported_claims=supported,
        unsupported_claims=unsupported,
        warnings=warnings,
        outdated_documents=outdated,
    )
