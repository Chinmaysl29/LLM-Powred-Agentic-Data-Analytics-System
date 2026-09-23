"""Dense Vector Retriever (Phase 5.5)."""

import time
from typing import Any, Dict, List, Optional

from backend.app.schemas.vector_store import VectorSearchResult
from backend.rag.embeddings.base_embedding import BaseEmbedding
from backend.rag.retrievers.base_retriever import BaseRetriever
from backend.rag.vectorstores.base_store import BaseVectorStore


class VectorRetriever(BaseRetriever):
    """Dense vector retriever: embeds query → searches vector store → applies score gate."""

    def __init__(self, embedding_model: BaseEmbedding, vector_store: BaseVectorStore) -> None:
        self._embedder = embedding_model
        self._store = vector_store

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        min_score: float = 0.0,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[VectorSearchResult]:
        query_vec = self._embedder.embed_query(query)
        return self._store.search(query_vector=query_vec, top_k=top_k, min_score=min_score, filters=filters)
