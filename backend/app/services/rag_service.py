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
        try:
            from backend.rag.vectorstores.chromadb_store import ChromaDBStore
            from backend.app.core.config import get_settings
            settings = get_settings()
            store = ChromaDBStore(
                collection_name="rag_chunks",
                host=settings.chroma_host,
                port=settings.chroma_port,
            )
            _pipeline = RAGPipeline(vector_store=store)
        except Exception:
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
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
        auto_chunk: bool = True,
    ) -> RAGIngestResponse:
        meta = metadata or {}
        if auto_chunk and (chunk_size is None or chunk_size == 1000):
            try:
                from backend.rag.dynamic_chunking import get_dynamic_chunking_service
                dyn_svc = get_dynamic_chunking_service()
                fname = str(meta.get("file_name", "") or meta.get("filename", ""))
                ftype = str(meta.get("file_type", "") or meta.get("filetype", ""))
                dyn_cfg = dyn_svc.get_config(content, filename=fname, file_type=ftype)
                chunk_size = dyn_cfg.chunk_size
                chunk_overlap = dyn_cfg.chunk_overlap
                chunking_strategy = dyn_cfg.strategy
                meta["detected_category"] = dyn_cfg.category
            except Exception:
                chunk_size = chunk_size or 500
                chunk_overlap = chunk_overlap or 100
        else:
            chunk_size = chunk_size or 500
            chunk_overlap = chunk_overlap or 100

        request = RAGIngestRequest(
            document_id=document_id,
            content=content,
            metadata=meta,
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
