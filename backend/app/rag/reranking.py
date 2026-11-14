import logging
import threading
from collections.abc import Sequence

from app.config import settings

logger = logging.getLogger(__name__)

_cross_encoder = None
_lock = threading.Lock()
_load_failed = False


def reciprocal_rank_fusion(rankings: Sequence[Sequence[str]], k: int = 60) -> dict[str, float]:
    """Combine several ranked id lists into one score per id."""
    scores: dict[str, float] = {}
    for ranking in rankings:
        for rank, item_id in enumerate(ranking):
            scores[item_id] = scores.get(item_id, 0.0) + 1.0 / (k + rank + 1)
    return scores


def _get_cross_encoder():
    global _cross_encoder, _load_failed
    if not settings.RERANKER_MODEL or _load_failed:
        return None
    if _cross_encoder is None:
        with _lock:
            if _cross_encoder is None and not _load_failed:
                try:
                    from sentence_transformers import CrossEncoder

                    _cross_encoder = CrossEncoder(settings.RERANKER_MODEL, device="cpu")
                except Exception:  # noqa: BLE001
                    logger.exception("Could not load reranker %s; continuing without reranking", settings.RERANKER_MODEL)
                    _load_failed = True
    return _cross_encoder


def rerank(query: str, items: list[tuple[str, str]], top_k: int) -> list[tuple[str, float]] | None:
    """Rerank (id, text) pairs with a cross-encoder. Returns None if no reranker is configured."""
    model = _get_cross_encoder()
    if model is None or not items:
        return None
    scores = model.predict([(query, text) for _, text in items])
    ranked = sorted(zip((i for i, _ in items), (float(s) for s in scores)), key=lambda x: -x[1])
    return ranked[:top_k]
