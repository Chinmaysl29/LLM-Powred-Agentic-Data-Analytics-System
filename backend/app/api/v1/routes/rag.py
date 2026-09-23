"""RAG Pipeline API Endpoints (Phase 5.8)."""

from fastapi import APIRouter, HTTPException

from backend.app.schemas.rag_pipeline import (
    RAGIngestRequest,
    RAGIngestResponse,
    RAGQueryRequest,
    RAGResponse,
)
from backend.app.services.rag_service import RAGService

router = APIRouter(prefix="/rag", tags=["RAG Pipeline"])
_service = RAGService()


@router.post("/ingest", response_model=RAGIngestResponse, summary="Ingest document into RAG pipeline")
def ingest_document(request: RAGIngestRequest) -> RAGIngestResponse:
    """Chunk, embed, and index a document for RAG retrieval."""
    try:
        return _service.ingest_document(
            document_id=request.document_id,
            content=request.content,
            metadata=request.metadata,
            chunking_strategy=request.chunking_strategy,
            chunk_size=request.chunk_size,
            chunk_overlap=request.chunk_overlap,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/query", response_model=RAGResponse, summary="Query RAG pipeline")
def query_rag(request: RAGQueryRequest) -> RAGResponse:
    """Execute a RAG query and return answer with cited sources."""
    try:
        return _service.query(
            query=request.query,
            session_id=request.session_id,
            top_k=request.top_k,
            min_score=request.min_score,
            use_hybrid=request.use_hybrid,
            max_context_tokens=request.max_context_tokens,
            filters=request.filters,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health", summary="RAG pipeline health check")
def rag_health():
    return {"status": "ok", "component": "rag_pipeline"}
