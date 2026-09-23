"""BGE & HuggingFace Embedding Providers (Phase 5.3)."""

from typing import List
from backend.rag.embeddings.base_embedding import BaseEmbedding
from backend.rag.embeddings.miniLM_embedding import MiniLMEmbedding


class BGEEmbedding(BaseEmbedding):
    """BGE embedding provider (e.g. BAAI/bge-small-en-v1.5)."""

    def __init__(self, model_name: str = "BAAI/bge-small-en-v1.5") -> None:
        self._model_name = model_name
        self._delegate = MiniLMEmbedding(model_name=model_name)

    @property
    def dimension(self) -> int:
        return self._delegate.dimension

    @property
    def model_name(self) -> str:
        return self._model_name

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return self._delegate.embed_documents(texts)

    def embed_query(self, text: str) -> List[float]:
        return self._delegate.embed_query(text)


class HuggingFaceEmbedding(BaseEmbedding):
    """Generic HuggingFace embedding provider."""

    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2") -> None:
        self._model_name = model_name
        self._delegate = MiniLMEmbedding(model_name=model_name)

    @property
    def dimension(self) -> int:
        return self._delegate.dimension

    @property
    def model_name(self) -> str:
        return self._model_name

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return self._delegate.embed_documents(texts)

    def embed_query(self, text: str) -> List[float]:
        return self._delegate.embed_query(text)
