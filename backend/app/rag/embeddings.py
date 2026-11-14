import logging
import threading
from typing import Any, Protocol

from app.config import settings
from app.utils.errors import ConfigurationError

logger = logging.getLogger(__name__)


class Embedder(Protocol):
    dimension: int

    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...

    def embed_query(self, text: str) -> list[float]: ...


class PineconeInferenceEmbedder:
    batch_size = 32

    def __init__(self, client: Any | None = None):
        if client is None:
            if not settings.PINECONE_API_KEY:
                raise ConfigurationError("PINECONE_API_KEY is required for Pinecone-hosted embeddings.")
            from pinecone import Pinecone

            client = Pinecone(api_key=settings.PINECONE_API_KEY)
        self.client = client
        self.model_name = settings.EMBEDDING_MODEL
        self.dimension = settings.EMBEDDING_DIMENSION

    def _embed(self, texts: list[str], input_type: str) -> list[list[float]]:
        cleaned = [" ".join(text.split()) for text in texts]
        vectors: list[list[float]] = []
        for start in range(0, len(cleaned), self.batch_size):
            batch = cleaned[start : start + self.batch_size]
            response = self.client.inference.embed(
                model=self.model_name,
                inputs=batch,
                parameters={
                    "input_type": input_type,
                    "truncate": "END",
                    "dimension": self.dimension,
                },
            )
            if response.vector_type != "dense":
                raise ValueError(f"Embedding model {self.model_name} returned non-dense vectors.")
            if len(response.data) != len(batch):
                raise ValueError(
                    f"Embedding model {self.model_name} returned {len(response.data)} vectors for {len(batch)} inputs."
                )
            for embedding in response.data:
                if len(embedding.values) != self.dimension:
                    raise ValueError(
                        f"Embedding model {self.model_name} returned {len(embedding.values)} dimensions; "
                        f"expected {self.dimension}."
                    )
                vectors.append(embedding.values)
        return vectors

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._embed(texts, "passage")

    def embed_query(self, text: str) -> list[float]:
        vectors = self._embed([text], "query")
        return vectors[0]


_embedder: Embedder | None = None
_lock = threading.Lock()


def get_embedder() -> Embedder:
    global _embedder
    if _embedder is None:
        with _lock:
            if _embedder is None:
                logger.info("Connecting to Pinecone Inference model %s", settings.EMBEDDING_MODEL)
                _embedder = PineconeInferenceEmbedder()
    return _embedder


def set_embedder(embedder: Embedder | None) -> None:
    """Override the embedder (used by tests)."""
    global _embedder
    _embedder = embedder


def embedder_loaded() -> bool:
    return _embedder is not None
