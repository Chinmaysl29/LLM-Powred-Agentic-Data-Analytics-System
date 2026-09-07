"""Hybrid Retriever: Dense Vector + BM25 with Reciprocal Rank Fusion (Phase 5.6).

RRF formula:
    RRF(d) = alpha / (k + rank_dense(d)) + (1-alpha) / (k + rank_bm25(d))
"""

from typing import Any, Dict, List, Optional

from backend.app.schemas.vector_store import VectorSearchResult
from backend.rag.retrievers.base_retriever import BaseRetriever
from backend.rag.retrievers.bm25_retriever import BM25Retriever
from backend.rag.retrievers.vector_retriever import VectorRetriever


class HybridRetriever(BaseRetriever):
    """Combines dense vector and BM25 sparse retrieval via Reciprocal Rank Fusion."""

    def __init__(
        self,
        dense_retriever: VectorRetriever,
        sparse_retriever: BM25Retriever,
        alpha: float = 0.7,
        rrf_k: int = 60,
    ) -> None:
        self._dense = dense_retriever
        self._sparse = sparse_retriever
        self.alpha = alpha
        self.rrf_k = rrf_k

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        min_score: float = 0.0,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[VectorSearchResult]:
        fetch_k = max(top_k * 3, 20)

        dense_results = self._dense.retrieve(query, top_k=fetch_k, filters=filters)
        sparse_results = self._sparse.retrieve(query, top_k=fetch_k, filters=filters)

        # Build chunk_id → VectorSearchResult map (dense results take content priority)
        chunk_map: Dict[str, VectorSearchResult] = {}
        for r in dense_results:
            chunk_map[r.chunk_id] = r
        for r in sparse_results:
            if r.chunk_id not in chunk_map:
                chunk_map[r.chunk_id] = r

        # Dense RRF scores
        rrf_scores: Dict[str, float] = {}
        for rank, result in enumerate(dense_results):
            rrf_scores[result.chunk_id] = rrf_scores.get(result.chunk_id, 0.0) + self.alpha / (self.rrf_k + rank + 1)

        # Sparse RRF scores
        for rank, result in enumerate(sparse_results):
            rrf_scores[result.chunk_id] = rrf_scores.get(result.chunk_id, 0.0) + (1 - self.alpha) / (self.rrf_k + rank + 1)

        # Normalize RRF scores to [0, 1]
        if rrf_scores:
            max_rrf = max(rrf_scores.values())
            if max_rrf > 0:
                rrf_scores = {k: v / max_rrf for k, v in rrf_scores.items()}

        # Sort and filter
        ranked = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)
        results: List[VectorSearchResult] = []
        for chunk_id, score in ranked:
            if score < min_score:
                continue
            if chunk_id not in chunk_map:
                continue
            original = chunk_map[chunk_id]
            results.append(
                VectorSearchResult(
                    chunk_id=chunk_id,
                    document_id=original.document_id,
                    content=original.content,
                    score=score,
                    metadata=original.metadata,
                )
            )
            if len(results) >= top_k:
                break

        return results
