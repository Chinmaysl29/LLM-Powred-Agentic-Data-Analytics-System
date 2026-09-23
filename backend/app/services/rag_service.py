"""RAG Service Layer (Phase 5.8)."""

from typing import Any, Dict, Optional

from backend.app.schemas.rag_pipeline import (
    RAGIngestRequest,
    RAGIngestResponse,
    RAGQueryRequest,
    RAGResponse,
)
from backend.rag.rag_pipeline import RAGPipeline


# Singleton pipeline instance
_pipeline: Optional[RAGPipeline] = None


def get_pipeline() -> RAGPipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = RAGPipeline()
    return _pipeline


class RAGService:
    """High-level service interface for document ingestion and RAG querying."""

    def __init__(self, pipeline: Optional[RAGPipeline] = None) -> None:
        self._pipeline = pipeline or get_pipeline()

    def ingest_document(
        self,
        document_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        chunking_strategy: str = "recursive",
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
    ) -> RAGIngestResponse:
        request = RAGIngestRequest(
            document_id=document_id,
            content=content,
            metadata=metadata or {},
            chunking_strategy=chunking_strategy,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )
        return self._pipeline.ingest(request)

    def query(
        self,
        query: str,
        session_id: Optional[str] = None,
        top_k: int = 5,
        min_score: float = 0.0,
        use_hybrid: bool = False,
        max_context_tokens: int = 3000,
        filters: Optional[Dict[str, Any]] = None,
    ) -> RAGResponse:
        request = RAGQueryRequest(
            query=query,
            session_id=session_id,
            top_k=top_k,
            min_score=min_score,
            use_hybrid=use_hybrid,
            max_context_tokens=max_context_tokens,
            filters=filters,
        )
        return self._pipeline.query(request)
