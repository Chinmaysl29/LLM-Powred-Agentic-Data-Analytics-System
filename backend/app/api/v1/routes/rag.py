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


# -----------------------------------------------------------------------------
# Enterprise RAG Evaluation & Benchmarking (Phase 18.6.2)
# -----------------------------------------------------------------------------

from pydantic import BaseModel, Field
from typing import Any, List, Optional
from backend.rag.rag_evaluation import RAGEvaluationFramework, RAGBenchmark


class EvaluateRAGRequest(BaseModel):
    query: str
    retrieved_chunk_ids: List[str]
    retrieved_texts: List[str]
    relevant_chunk_ids: List[str]
    answer: str
    ground_truth: str = ""
    k: int = 5


class CreateBenchmarkRequest(BaseModel):
    benchmark_id: str = Field(..., description="Unique benchmark ID")
    query: str
    relevant_chunk_ids: List[str]
    ground_truth_answer: str
    category: str = "general"
    metadata: dict[str, Any] = Field(default_factory=dict)


@router.post("/evaluate", summary="Evaluate RAG Retrieval & Generation Quality (Phase 18.6.2)")
def evaluate_rag(request: EvaluateRAGRequest) -> dict[str, Any]:
    """Calculate Precision@K, Recall@K, MRR, NDCG, Context Relevance, Answer Relevance, Groundedness."""
    framework = RAGEvaluationFramework()
    res = framework.evaluate(
        query=request.query,
        retrieved_chunk_ids=request.retrieved_chunk_ids,
        retrieved_texts=request.retrieved_texts,
        relevant_chunk_ids=request.relevant_chunk_ids,
        answer=request.answer,
        ground_truth=request.ground_truth,
        k=request.k,
    )
    return res.to_dict()


@router.get("/eval-history", summary="Get RAG Evaluation History")
def get_rag_eval_history() -> List[dict[str, Any]]:
    """Retrieve full historical evaluations log."""
    framework = RAGEvaluationFramework()
    return framework.load_history()


@router.get("/eval-dashboard", summary="RAG Health & Quality Dashboard (Phase 18.6.2)")
def get_rag_eval_dashboard() -> dict[str, Any]:
    """Summary of RAG quality, average metrics, groundedness, and latest evaluation."""
    framework = RAGEvaluationFramework()
    return framework.health_summary()


@router.get("/benchmarks", summary="List RAG Benchmark Datasets")
def list_rag_benchmarks() -> List[dict[str, Any]]:
    """List all registered RAG benchmark queries and ground truth chunks."""
    framework = RAGEvaluationFramework()
    return framework.load_benchmarks()


@router.post("/benchmarks", summary="Add RAG Benchmark Dataset")
def add_rag_benchmark(request: CreateBenchmarkRequest) -> dict[str, Any]:
    """Register a new ground-truth benchmark item for RAG regression testing."""
    framework = RAGEvaluationFramework()
    bench = RAGBenchmark(
        benchmark_id=request.benchmark_id,
        query=request.query,
        relevant_chunk_ids=request.relevant_chunk_ids,
        ground_truth_answer=request.ground_truth_answer,
        category=request.category,
        metadata=request.metadata,
    )
    framework.add_benchmark(bench)
    return {"status": "created", "benchmark_id": request.benchmark_id}

