"""
Tests for RAG / Document / Retrieval / Schema API endpoints:
  POST /api/v1/rag/ingest
  POST /api/v1/rag/query
  GET  /api/v1/rag/health
  POST /api/v1/documents/load
  POST /api/v1/documents/load-batch
  GET  /api/v1/documents/supported-formats
  GET  /api/v1/retrieval/{id}/package
  GET  /api/v1/retrieval/{id}/schema
  POST /api/v1/retrieval/{id}/query
  GET  /api/v1/schema
  GET  /api/v1/schema/compact
  GET  /api/v1/schema/tables/{name}
  GET  /api/v1/schema/prompt-context
  POST /api/v1/schema/refresh
"""

import io
import json

import pytest
from fastapi.testclient import TestClient

from backend.app.main import create_app


# ===========================================================================
# Fixtures
# ===========================================================================

@pytest.fixture(scope="module")
def client():
    app = create_app()
    with TestClient(app) as c:
        yield c


# ===========================================================================
# RAG Ingest / Query Tests
# ===========================================================================

class TestRAGEndpoints:

    def test_ingest_document_returns_200(self, client):
        res = client.post("/api/v1/rag/ingest", json={
            "document_id": "test-doc-001",
            "content": "Enterprise AI analytics platform accelerates business decisions.",
            "metadata": {"source": "test"},
        })
        assert res.status_code == 200

    def test_ingest_returns_document_id(self, client):
        data = client.post("/api/v1/rag/ingest", json={
            "document_id": "doc-id-unique-001",
            "content": "Sales performance improved significantly in Q3 2024.",
        }).json()
        assert data["document_id"] == "doc-id-unique-001"

    def test_ingest_returns_chunks_created(self, client):
        data = client.post("/api/v1/rag/ingest", json={
            "document_id": "doc-002",
            "content": "Revenue grew 25% year over year driven by strong enterprise sales.",
        }).json()
        assert "chunks_created" in data
        assert data["chunks_created"] >= 1

    def test_ingest_empty_content_returns_zero_chunks(self, client):
        data = client.post("/api/v1/rag/ingest", json={
            "document_id": "doc-empty",
            "content": "",
        }).json()
        assert data["chunks_created"] == 0

    def test_query_returns_200(self, client):
        # First ingest
        client.post("/api/v1/rag/ingest", json={
            "document_id": "query-doc-1",
            "content": "Customer satisfaction score reached 92% in the latest survey.",
        })
        res = client.post("/api/v1/rag/query", json={"query": "customer satisfaction"})
        assert res.status_code == 200

    def test_query_returns_answer(self, client):
        data = client.post("/api/v1/rag/query", json={"query": "any query"}).json()
        assert "answer" in data
        assert isinstance(data["answer"], str)

    def test_query_with_custom_top_k(self, client):
        data = client.post("/api/v1/rag/query", json={
            "query": "analytics",
            "top_k": 3,
        }).json()
        assert data is not None

    def test_rag_health_returns_ok(self, client):
        res = client.get("/api/v1/rag/health")
        assert res.status_code == 200
        assert res.json()["status"] == "ok"

    def test_ingest_with_custom_chunk_size(self, client):
        data = client.post("/api/v1/rag/ingest", json={
            "document_id": "doc-custom-chunk",
            "content": "This document covers enterprise analytics, business intelligence, and AI-driven insights. " * 5,
            "chunk_size": 100,
            "chunk_overlap": 20,
        }).json()
        assert data["chunks_created"] >= 1


# ===========================================================================
# Document Loader Tests
# ===========================================================================

class TestDocumentLoaderEndpoints:

    def test_load_txt_document_returns_200(self, client):
        res = client.post(
            "/api/v1/documents/load",
            files={"file": ("notes.txt", io.BytesIO(b"This is a test document."), "text/plain")},
        )
        assert res.status_code == 200

    def test_load_txt_returns_status_success(self, client):
        data = client.post(
            "/api/v1/documents/load",
            files={"file": ("test.txt", io.BytesIO(b"Hello world"), "text/plain")},
        ).json()
        assert data["status"] == "success"

    def test_load_txt_returns_document(self, client):
        data = client.post(
            "/api/v1/documents/load",
            files={"file": ("doc.txt", io.BytesIO(b"Content here."), "text/plain")},
        ).json()
        assert "document" in data
        assert data["document"]["content"]

    def test_load_csv_document_returns_200(self, client):
        csv_content = b"name,score\nAlice,95\nBob,87\n"
        res = client.post(
            "/api/v1/documents/load",
            files={"file": ("data.csv", io.BytesIO(csv_content), "text/csv")},
        )
        assert res.status_code == 200

    def test_load_json_document_returns_200(self, client):
        data = json.dumps({"key": "value"}).encode()
        res = client.post(
            "/api/v1/documents/load",
            files={"file": ("data.json", io.BytesIO(data), "application/json")},
        )
        assert res.status_code == 200

    def test_load_empty_file_returns_400(self, client):
        res = client.post(
            "/api/v1/documents/load",
            files={"file": ("empty.txt", io.BytesIO(b""), "text/plain")},
        )
        assert res.status_code == 400

    def test_load_batch_returns_200(self, client):
        res = client.post(
            "/api/v1/documents/load-batch",
            files=[
                ("files", ("doc1.txt", io.BytesIO(b"Document one content"), "text/plain")),
                ("files", ("doc2.txt", io.BytesIO(b"Document two content"), "text/plain")),
            ],
        )
        assert res.status_code == 200

    def test_load_batch_returns_total_loaded(self, client):
        data = client.post(
            "/api/v1/documents/load-batch",
            files=[
                ("files", ("d1.txt", io.BytesIO(b"Content A"), "text/plain")),
                ("files", ("d2.txt", io.BytesIO(b"Content B"), "text/plain")),
            ],
        ).json()
        assert "total_loaded" in data
        assert data["total_loaded"] == 2

    def test_load_batch_mixed_empty_partial_success(self, client):
        data = client.post(
            "/api/v1/documents/load-batch",
            files=[
                ("files", ("ok.txt", io.BytesIO(b"Valid content"), "text/plain")),
                ("files", ("empty.txt", io.BytesIO(b""), "text/plain")),
            ],
        ).json()
        assert data["total_loaded"] == 1
        assert len(data["failed_files"]) == 1

    def test_get_supported_formats_returns_200(self, client):
        res = client.get("/api/v1/documents/supported-formats")
        assert res.status_code == 200

    def test_get_supported_formats_returns_list(self, client):
        data = client.get("/api/v1/documents/supported-formats").json()
        assert isinstance(data, list)
        assert len(data) > 0


# ===========================================================================
# Schema Reader Tests
# ===========================================================================

class TestSchemaEndpoints:

    def test_get_schema_returns_200(self, client):
        res = client.get("/api/v1/schema")
        assert res.status_code == 200

    def test_get_schema_returns_status(self, client):
        data = client.get("/api/v1/schema").json()
        assert "status" in data
        assert data["status"] == "success"

    def test_get_compact_schema_returns_200(self, client):
        res = client.get("/api/v1/schema/compact")
        assert res.status_code == 200

    def test_get_compact_schema_returns_list(self, client):
        data = client.get("/api/v1/schema/compact").json()
        assert isinstance(data, list)

    def test_get_prompt_context_returns_200(self, client):
        res = client.get("/api/v1/schema/prompt-context")
        assert res.status_code == 200

    def test_get_prompt_context_returns_string(self, client):
        data = client.get("/api/v1/schema/prompt-context").json()
        assert "prompt_context" in data
        assert isinstance(data["prompt_context"], str)

    def test_refresh_schema_cache_returns_200(self, client):
        res = client.post("/api/v1/schema/refresh")
        assert res.status_code == 200

    def test_refresh_schema_returns_cache_invalidated(self, client):
        data = client.post("/api/v1/schema/refresh").json()
        assert data["status"] == "cache_invalidated"

    def test_get_nonexistent_table_returns_404(self, client):
        res = client.get("/api/v1/schema/tables/nonexistent_table_xyz")
        assert res.status_code == 404
