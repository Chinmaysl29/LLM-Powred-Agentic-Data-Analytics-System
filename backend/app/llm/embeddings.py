"""Embedding service using HuggingFace sentence-transformers.

Provides text embedding for the RAG pipeline, ChromaDB vector store,
and semantic search features. Uses the model specified in EMBEDDING_MODEL env var.
"""

import asyncio
import logging
from functools import lru_cache
from typing import Any

from backend.app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Generate embeddings using HuggingFace sentence-transformers."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._model: Any | None = None
        self._dimension: int = 384  # Default for all-MiniLM-L6-v2

    def _ensure_model(self) -> Any:
        """Lazy-load the sentence transformer model."""
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer

                model_name = self._settings.embedding_model
                self._model = SentenceTransformer(model_name)
                self._dimension = self._model.get_sentence_embedding_dimension()
                logger.info(
                    "Embedding model loaded model=%s dimension=%d",
                    model_name,
                    self._dimension,
                )
            except Exception:
                logger.error("Failed to load embedding model", exc_info=True)
                raise
        return self._model

    @property
    def dimension(self) -> int:
        """Return the embedding dimension of the loaded model."""
        self._ensure_model()
        return self._dimension

    def embed_text(self, text: str) -> list[float]:
        """Generate an embedding vector for a single text string."""
        model = self._ensure_model()
        embedding = model.encode(text, convert_to_numpy=True)
        return embedding.tolist()

    def embed_documents(self, documents: list[str], batch_size: int = 32) -> list[list[float]]:
        """Generate embedding vectors for a batch of documents."""
        model = self._ensure_model()
        embeddings = model.encode(documents, batch_size=batch_size, convert_to_numpy=True)
        return embeddings.tolist()

    async def aembed_text(self, text: str) -> list[float]:
        """Async wrapper for single text embedding."""
        return await asyncio.to_thread(self.embed_text, text)

    async def aembed_documents(self, documents: list[str], batch_size: int = 32) -> list[list[float]]:
        """Async wrapper for batch document embedding."""
        return await asyncio.to_thread(self.embed_documents, documents, batch_size)

    def get_langchain_embeddings(self) -> Any:
        """Return a LangChain-compatible embedding function for use with vectorstores."""
        try:
            from langchain_community.embeddings import HuggingFaceEmbeddings

            return HuggingFaceEmbeddings(
                model_name=self._settings.embedding_model,
                model_kwargs={"device": "cpu"},
                encode_kwargs={"normalize_embeddings": True},
            )
        except Exception:
            logger.error("Failed to create LangChain embeddings", exc_info=True)
            raise


@lru_cache
def get_embedding_service() -> EmbeddingService:
    """Return a singleton embedding service instance."""
    return EmbeddingService(get_settings())
