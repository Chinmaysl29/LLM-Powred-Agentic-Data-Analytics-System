"""Base Retriever interface (Phase 5.5)."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from backend.app.schemas.vector_store import VectorSearchResult


class BaseRetriever(ABC):
    """Abstract retriever interface for dense, sparse, and hybrid retrievers."""

    @abstractmethod
    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        min_score: float = 0.0,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[VectorSearchResult]:
        """Retrieve top-k relevant chunks for the given query."""
        pass
