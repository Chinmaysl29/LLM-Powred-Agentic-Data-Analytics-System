"""Tests for Phase 5.8 — RAG Pipeline."""

import pytest
from fastapi.testclient import TestClient

from backend.app.schemas.rag_pipeline import RAGIngestRequest, RAGQueryRequest
from backend.rag.embeddings.miniLM_embedding import MiniLMEmbedding
from backend.rag.rag_pipeline import RAGPipeline
from backend.rag.vectorstores.in_memory_store import InMemoryVectorStore

SAMPLE_DOCUMENT = """
Quarterly Financial Performance Report — Q3 2026

Revenue Overview:
Total revenue for Q3 2026 reached $4.2M, representing a 14% increase year-over-year.
The North region contributed $1.8M (42% of total), followed by South at $1.2M (29%).

Cost Analysis:
Operating costs were $2.8M with EBITDA margin improving to 33%.
Marketing spend increased by $200K to support Q4 pipeline growth.

Key Risks:
Supply chain disruptions may affect Q4 delivery timelines.
Three enterprise contracts valued at $500K are pending renewal negotiations.
"""


def _make_pipeline():
    embedder = MiniLMEmbedding()
    store = InMemoryVectorStore()
    return RAGPipeline(embedding_model=embedder, vector_store=store)


def test_rag_pipeline_ingest():
    pipeline = _make_pipeline()
    request = RAGIngestRequest(
        document_id="doc-q3-report",
        content=SAMPLE_DOCUMENT,
        metadata={"filename": "q3_report.txt", "file_type": "txt"},
        chunking_strategy="recursive",
        chunk_size=400,
        chunk_overlap=80,
    )
    response = pipeline.ingest(request)
    assert response.status == "success"
    assert response.chunks_created >= 2
    assert response.chunks_indexed == response.chunks_created
    assert response.document_id == "doc-q3-report"


def test_rag_pipeline_query_with_context():
    pipeline = _make_pipeline()
    # First ingest
    pipeline.ingest(RAGIngestRequest(
        document_id="doc-q3",
        content=SAMPLE_DOCUMENT,
        metadata={"filename": "q3_report.txt"},
        chunk_size=400,
        chunk_overlap=80,
    ))

    # Then query
    response = pipeline.query(RAGQueryRequest(
        query="What was the total Q3 revenue?",
        top_k=3,
    ))
    assert response.query == "What was the total Q3 revenue?"
    assert len(response.answer) > 10
    assert response.context_tokens > 0


def test_rag_pipeline_query_no_context():
    pipeline = _make_pipeline()
    # Query empty pipeline
    response = pipeline.query(RAGQueryRequest(query="What is the revenue?", top_k=3))
    assert "No relevant documents" in response.answer
    assert response.confidence_score == 0.0


def test_rag_pipeline_session_memory():
    pipeline = _make_pipeline()
    pipeline.ingest(RAGIngestRequest(
        document_id="doc-q3",
        content=SAMPLE_DOCUMENT,
        metadata={"filename": "q3_report.txt"},
        chunk_size=400,
        chunk_overlap=80,
    ))

    # First turn
    resp1 = pipeline.query(RAGQueryRequest(query="What was North region revenue?", session_id="sess-1", top_k=3))
    # Second turn with pronoun reference
    resp2 = pipeline.query(RAGQueryRequest(query="What about the South region?", session_id="sess-1", top_k=3))

    assert resp1.query == "What was North region revenue?"
    assert resp2.query == "What about the South region?"
    # Both should produce answers
    assert len(resp1.answer) > 0
    assert len(resp2.answer) > 0


def test_rag_api_endpoints():
    from backend.main import app
    client = TestClient(app)

    # Health check
    resp = client.get("/api/v1/rag/health")
    assert resp.status_code == 200

    # Ingest
    resp = client.post("/api/v1/rag/ingest", json={
        "document_id": "test-api-doc",
        "content": "Total revenue for the period was $1.5M representing 10% growth.",
        "metadata": {"filename": "test.txt"},
        "chunk_size": 200,
        "chunk_overlap": 40,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"

    # Query
    resp = client.post("/api/v1/rag/query", json={
        "query": "What was the total revenue?",
        "top_k": 3,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "answer" in data
    assert "sources" in data
