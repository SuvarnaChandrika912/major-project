import logging
import threading
import time
from typing import Any

from app.config import settings
from app.utils.errors import ConfigurationError, ServiceUnavailableError

logger = logging.getLogger(__name__)

UPSERT_BATCH = 100
METADATA_TEXT_LIMIT = 3000


def _clean_metadata(meta: dict[str, Any]) -> dict[str, Any]:
    """Pinecone rejects null metadata values; also keep text within metadata size limits."""
    clean: dict[str, Any] = {}
    for key, value in meta.items():
        if value is None or value == "":
            continue
        if isinstance(value, (str, int, float, bool)):
            clean[key] = value[:METADATA_TEXT_LIMIT] if isinstance(value, str) else value
        elif isinstance(value, list):
            clean[key] = [str(v) for v in value]
        else:
            clean[key] = str(value)
    return clean


class PineconeStore:
    def __init__(self, index: Any = None):
        self._index = index
        self._lock = threading.Lock()

    def _client(self):
        if not settings.pinecone_configured:
            raise ConfigurationError("Pinecone is not configured. Set PINECONE_API_KEY and PINECONE_INDEX_NAME.")
        from pinecone import Pinecone

        return Pinecone(api_key=settings.PINECONE_API_KEY)

    def ensure_index(self) -> Any:
        if self._index is not None:
            return self._index
        with self._lock:
            if self._index is not None:
                return self._index
            from pinecone import ServerlessSpec

            pc = self._client()
            try:
                name = settings.PINECONE_INDEX_NAME
                if not pc.has_index(name):
                    logger.info("Creating Pinecone index %s (dim=%s)", name, settings.EMBEDDING_DIMENSION)
                    pc.create_index(
                        name=name,
                        dimension=settings.EMBEDDING_DIMENSION,
                        metric="cosine",
                        spec=ServerlessSpec(cloud=settings.PINECONE_CLOUD, region=settings.PINECONE_REGION),
                    )
                    for _ in range(60):
                        if pc.describe_index(name).status.get("ready"):
                            break
                        time.sleep(1)
                description = pc.describe_index(name)
                if int(description.dimension) != settings.EMBEDDING_DIMENSION:
                    raise ConfigurationError(
                        f"Pinecone index '{name}' has dimension {description.dimension}, "
                        f"but EMBEDDING_DIMENSION is {settings.EMBEDDING_DIMENSION}."
                    )
                self._index = pc.Index(name)
            except ConfigurationError:
                raise
            except Exception as exc:  # noqa: BLE001
                logger.exception("Pinecone initialisation failed")
                raise ServiceUnavailableError(f"Could not connect to Pinecone: {exc.__class__.__name__}") from exc
        return self._index

    def upsert(self, vectors: list[dict[str, Any]], namespace: str | None = None) -> int:
        index = self.ensure_index()
        ns = namespace or settings.PINECONE_NAMESPACE
        total = 0
        for start in range(0, len(vectors), UPSERT_BATCH):
            batch = [
                {"id": v["id"], "values": v["values"], "metadata": _clean_metadata(v.get("metadata", {}))}
                for v in vectors[start : start + UPSERT_BATCH]
            ]
            for attempt in range(3):
                try:
                    index.upsert(vectors=batch, namespace=ns)
                    break
                except Exception:  # noqa: BLE001
                    if attempt == 2:
                        raise
                    time.sleep(2**attempt)
            total += len(batch)
        return total

    def query(
        self, vector: list[float], top_k: int = 10, filters: dict[str, Any] | None = None, namespace: str | None = None
    ) -> list[dict[str, Any]]:
        index = self.ensure_index()
        response = index.query(
            vector=vector,
            top_k=top_k,
            include_metadata=True,
            filter=filters or None,
            namespace=namespace or settings.PINECONE_NAMESPACE,
        )
        matches = response.get("matches", []) if isinstance(response, dict) else response.matches
        results = []
        for m in matches:
            get = m.get if isinstance(m, dict) else lambda k, d=None, _m=m: getattr(_m, k, d)
            results.append({"id": get("id"), "score": float(get("score") or 0.0), "metadata": dict(get("metadata") or {})})
        return results

    def delete_ids(self, ids: list[str], namespace: str | None = None) -> None:
        if not ids:
            return
        index = self.ensure_index()
        ns = namespace or settings.PINECONE_NAMESPACE
        for start in range(0, len(ids), 1000):
            index.delete(ids=ids[start : start + 1000], namespace=ns)

    def health(self) -> str:
        if not settings.pinecone_configured:
            return "not configured"
        try:
            stats = self.ensure_index().describe_index_stats()
            total = stats.get("total_vector_count") if isinstance(stats, dict) else stats.total_vector_count
            return f"connected ({total} vectors)"
        except Exception as exc:  # noqa: BLE001
            return f"unavailable: {getattr(exc, 'message', exc.__class__.__name__)}"


_store: PineconeStore | None = None


def get_store() -> PineconeStore:
    global _store
    if _store is None:
        _store = PineconeStore()
    return _store


def set_store(store: PineconeStore | None) -> None:
    global _store
    _store = store
