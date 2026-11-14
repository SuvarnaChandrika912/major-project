"""Shared agent utilities: prompt loading, timeouts, evidence handling."""

import logging
import re
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.config import settings
from app.graph.state import AgentFinding, GraphState
from app.rag.retrieval import RetrievedChunk
from app.utils.errors import AppError

logger = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"
_executor = ThreadPoolExecutor(max_workers=8, thread_name_prefix="agent")


@lru_cache
def load_prompt(name: str) -> str:
    return (PROMPTS_DIR / f"{name}.txt").read_text(encoding="utf-8")


def chunks_from_state(state: GraphState) -> list[RetrievedChunk]:
    seen: set[str] = set()
    result = []
    for raw in state.get("retrieved_chunks", []):
        if raw["chunk_id"] not in seen:
            seen.add(raw["chunk_id"])
            result.append(RetrievedChunk(**raw))
    return result


def history_text(state: GraphState, limit: int = 4) -> str:
    history = state.get("history") or []
    if not history:
        return ""
    lines = [f"{m['role']}: {m['content'][:500]}" for m in history[-limit:]]
    return "Recent conversation (for context only):\n" + "\n".join(lines) + "\n\n"


_LOCAL_MARKER_RE = re.compile(r"\[(\d{1,3})\]")
_TOKEN_RE = re.compile(r"\[\[cid:([^\]]+)\]\]")


def _map_strings(value: Any, fn: Callable[[str], str]) -> Any:
    if isinstance(value, str):
        return fn(value)
    if isinstance(value, list):
        return [_map_strings(v, fn) for v in value]
    if isinstance(value, dict):
        return {k: _map_strings(v, fn) for k, v in value.items()}
    return value


def localize_markers(finding: AgentFinding, chunks: list[RetrievedChunk]) -> AgentFinding:
    """Agents cite their own evidence as [1..k]; convert to chunk-id tokens so citations survive merging."""

    def _sub(text: str) -> str:
        def repl(m: re.Match) -> str:
            n = int(m.group(1))
            return f"[[cid:{chunks[n - 1].chunk_id}]]" if 1 <= n <= len(chunks) else f"[invalid:{n}]"

        return _LOCAL_MARKER_RE.sub(repl, text)

    finding.summary = _sub(finding.summary)
    finding.claims = [_sub(c) for c in finding.claims]
    finding.data = _map_strings(finding.data, _sub)
    return finding


def globalize_markers(value: Any, index_by_chunk: dict[str, int]) -> Any:
    """Convert chunk-id tokens back to global citation numbers [n]."""

    def _sub(text: str) -> str:
        text = _TOKEN_RE.sub(lambda m: f"[{index_by_chunk[m.group(1)]}]" if m.group(1) in index_by_chunk else "", text)
        return text.replace("[invalid:", "[?")

    return _map_strings(value, _sub)


def run_agent(
    name: str, state: GraphState, fn: Callable[[GraphState], tuple[AgentFinding, list[RetrievedChunk]]]
) -> dict[str, Any]:
    """Execute an agent with a timeout and convert its output (or failure) into a graph-state update."""
    start = time.perf_counter()
    future = _executor.submit(fn, state)
    try:
        finding, chunks = future.result(timeout=settings.AGENT_TIMEOUT_SECONDS)
        finding.agent = name
        finding = localize_markers(finding, chunks)
        finding.chunk_ids = finding.chunk_ids or [c.chunk_id for c in chunks]
    except FutureTimeout:
        logger.warning("Agent %s timed out", name, extra={"agent": name})
        finding, chunks = AgentFinding(agent=name, status="timeout", error="Agent timed out."), []
    except AppError as exc:
        finding, chunks = AgentFinding(agent=name, status="failed", error=exc.message), []
    except Exception as exc:  # noqa: BLE001
        logger.exception("Agent %s failed", name, extra={"agent": name})
        finding, chunks = AgentFinding(agent=name, status="failed", error=f"Internal error: {exc.__class__.__name__}"), []
    finding.duration_ms = int((time.perf_counter() - start) * 1000)
    update: dict[str, Any] = {
        "agent_findings": [finding.model_dump()],
        "retrieved_chunks": [c.to_dict() for c in chunks],
    }
    if finding.error:
        update["errors"] = [f"{name}: {finding.error}"]
    return update
