"""Base Vector Store interface (Phase 5.4)."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from backend.app.schemas.vector_store import IndexStats, VectorSearchResult


class BaseVectorStore(ABC):
    """Abstract interface for all vector store implementations."""

    @abstractmethod
    def add(
        self,
        chunk_ids: List[str],
        document_ids: List[str],
        texts: List[str],
        embeddings: List[List[float]],
        metadatas: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        """Index a batch of chunks with their embeddings."""
        pass

    @abstractmethod
    def search(
        self,
        query_vector: List[float],
        top_k: int = 5,
        min_score: float = 0.0,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[VectorSearchResult]:
        """Run nearest-neighbour similarity search against the index."""
        pass

    @abstractmethod
    def delete(self, chunk_ids: List[str]) -> None:
        """Remove chunks from the index by their IDs."""
        pass

    @abstractmethod
    def clear(self) -> None:
        """Wipe all indexed vectors."""
        pass

    @abstractmethod
    def stats(self) -> IndexStats:
        """Return statistics about the current index state."""
        pass

    def __len__(self) -> int:
        return self.stats().total_vectors
