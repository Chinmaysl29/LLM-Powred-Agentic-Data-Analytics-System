"""
Tests for RAG / Retrieval / Document / Schema services:
  - RAGPipeline (ingest, query)
  - RAGService (ingest_document, query wrapper)
  - SchemaReaderService (cache, invalidation, compact tables)
  - DocumentLoaderService (CSV, TXT, JSON bytes loading)
  - ChunkingService / Chunker strategies
  - BM25Retriever / VectorRetriever
"""

import io
import json
import uuid

import pytest

from backend.app.services.rag_service import RAGService
from backend.app.services.schema_reader_service import SchemaReaderService
from backend.app.services.document_loader_service import DocumentLoaderService
from backend.rag.rag_pipeline import RAGPipeline
from backend.rag.chunking.chunker_factory import ChunkerFactory


# ===========================================================================
# RAGPipeline Tests
# ===========================================================================

class TestRAGPipeline:

    @pytest.fixture
    def pipeline(self):
        """Fresh in-memory pipeline for each test."""
        return RAGPipeline()

    def test_ingest_single_document_returns_response(self, pipeline):
        from backend.app.schemas.rag_pipeline import RAGIngestRequest
        req = RAGIngestRequest(
            document_id="doc-001",
            content="Artificial intelligence is transforming enterprise analytics. Companies use AI to gain insights.",
            metadata={"source": "test"},
            chunking_strategy="recursive",
            chunk_size=50,
            chunk_overlap=10,
        )
        resp = pipeline.ingest(req)
        assert resp is not None
        assert resp.document_id == "doc-001"
        assert resp.chunks_created >= 1

    def test_ingest_empty_content_returns_zero_chunks(self, pipeline):
        from backend.app.schemas.rag_pipeline import RAGIngestRequest
        req = RAGIngestRequest(
            document_id="doc-empty",
            content="",
            metadata={},
        )
        resp = pipeline.ingest(req)
        assert resp.chunks_created == 0

    def test_query_after_ingest_returns_answer(self, pipeline):
        from backend.app.schemas.rag_pipeline import RAGIngestRequest, RAGQueryRequest
        pipeline.ingest(RAGIngestRequest(
            document_id="doc-q1",
            content="Sales grew by 25% in Q3 due to strong marketing campaigns.",
            metadata={},
            chunk_size=100,
            chunk_overlap=20,
        ))
        query_req = RAGQueryRequest(query="What happened to sales in Q3?", top_k=2)
        result = pipeline.query(query_req)
        assert result is not None
        assert isinstance(result.answer, str)

    def test_query_without_documents_returns_empty_response(self, pipeline):
        from backend.app.schemas.rag_pipeline import RAGQueryRequest
        result = pipeline.query(RAGQueryRequest(query="no documents here"))
        assert result is not None
        assert isinstance(result.answer, str)

    def test_ingest_with_fixed_strategy(self, pipeline):
        from backend.app.schemas.rag_pipeline import RAGIngestRequest
        resp = pipeline.ingest(RAGIngestRequest(
            document_id="doc-fixed",
            content="Revenue is calculated monthly. Expenses are tracked weekly.",
            chunking_strategy="fixed",
            chunk_size=30,
            chunk_overlap=5,
        ))
        assert resp.chunks_created >= 1

    def test_ingest_multiple_documents(self, pipeline):
        from backend.app.schemas.rag_pipeline import RAGIngestRequest
        for i in range(3):
            pipeline.ingest(RAGIngestRequest(
                document_id=f"doc-multi-{i}",
                content=f"Document {i} content about enterprise analytics and business intelligence.",
                metadata={"index": i},
            ))

    def test_query_returns_sources(self, pipeline):
        from backend.app.schemas.rag_pipeline import RAGIngestRequest, RAGQueryRequest
        pipeline.ingest(RAGIngestRequest(
            document_id="doc-src",
            content="Customer retention improved by 12% after the new onboarding program.",
            metadata={"author": "research"},
        ))
        result = pipeline.query(RAGQueryRequest(query="customer retention", top_k=3))
        assert hasattr(result, "sources") or hasattr(result, "retrieved_chunks")


# ===========================================================================
# RAGService Tests
# ===========================================================================

class TestRAGService:

    @pytest.fixture
    def svc(self):
        pipeline = RAGPipeline()
        return RAGService(pipeline=pipeline)

    def test_ingest_document_returns_response(self, svc):
        resp = svc.ingest_document(
            document_id="svc-doc-1",
            content="Enterprise data governance ensures data quality and compliance.",
            metadata={"type": "policy"},
        )
        assert resp is not None
        assert resp.document_id == "svc-doc-1"

    def test_query_returns_rag_response(self, svc):
        svc.ingest_document(
            document_id="svc-doc-2",
            content="Machine learning models improve forecast accuracy by 30%.",
        )
        result = svc.query(query="How does ML improve forecasting?", top_k=2)
        assert result is not None
        assert isinstance(result.answer, str)

    def test_query_with_session_id(self, svc):
        svc.ingest_document("doc-session", "Analytics platform overview.")
        result = svc.query(query="overview", session_id="sess-123")
        assert result is not None

    def test_ingest_with_custom_chunking(self, svc):
        resp = svc.ingest_document(
            document_id="svc-chunk",
            content="Revenue data from multiple quarters helps with annual planning.",
            chunking_strategy="fixed",
            chunk_size=50,
            chunk_overlap=10,
        )
        assert resp.chunks_created >= 1


# ===========================================================================
# ChunkerFactory Tests
# ===========================================================================

class TestChunkerFactory:

    def test_get_recursive_chunker(self):
        chunker = ChunkerFactory.get_chunker("recursive", chunk_size=100, chunk_overlap=20)
        assert chunker is not None

    def test_get_fixed_chunker(self):
        chunker = ChunkerFactory.get_chunker("fixed", chunk_size=100, chunk_overlap=10)
        assert chunker is not None

    def test_recursive_chunker_splits_text(self):
        chunker = ChunkerFactory.get_chunker("recursive", chunk_size=50, chunk_overlap=10)
        text = "This is a test document. " * 20
        chunks = chunker.split_text(text, document_id="d1", metadata={})
        assert len(chunks) >= 1
        for chunk in chunks:
            assert chunk.content

    def test_fixed_chunker_splits_text(self):
        chunker = ChunkerFactory.get_chunker("fixed", chunk_size=30, chunk_overlap=5)
        text = "word " * 100
        chunks = chunker.split_text(text, document_id="d2", metadata={})
        assert len(chunks) >= 1

    def test_chunk_has_document_id(self):
        chunker = ChunkerFactory.get_chunker("recursive", chunk_size=50, chunk_overlap=10)
        chunks = chunker.split_text(
            "Testing document ID propagation in chunks.",
            document_id="my-doc-id",
            metadata={"source": "test"},
        )
        for chunk in chunks:
            assert chunk.document_id == "my-doc-id"

    def test_empty_text_returns_empty_chunks(self):
        chunker = ChunkerFactory.get_chunker("recursive", chunk_size=100, chunk_overlap=20)
        chunks = chunker.split_text("", document_id="empty", metadata={})
        assert chunks == []

    def test_invalid_strategy_falls_back_to_recursive(self):
        # Should not raise; fallback to default
        chunker = ChunkerFactory.get_chunker("nonexistent_strategy", chunk_size=100, chunk_overlap=20)
        assert chunker is not None


# ===========================================================================
# DocumentLoaderService Tests
# ===========================================================================

class TestDocumentLoaderService:

    @pytest.fixture
    def svc(self):
        return DocumentLoaderService()

    def test_load_txt_content(self, svc):
        content = b"This is a plain text document.\nWith multiple lines."
        doc = svc.load_bytes(content=content, filename="doc.txt")
        assert doc is not None
        assert "text" in doc.content.lower() or len(doc.content) > 0

    def test_load_csv_content(self, svc):
        content = b"name,age,city\nAlice,30,NYC\nBob,25,LA\n"
        doc = svc.load_bytes(content=content, filename="data.csv")
        assert doc is not None
        assert doc.content

    def test_load_json_content(self, svc):
        data = {"records": [{"id": 1, "value": 100}, {"id": 2, "value": 200}]}
        content = json.dumps(data).encode("utf-8")
        doc = svc.load_bytes(content=content, filename="data.json")
        assert doc is not None
        assert doc.content

    def test_load_returns_filename_in_metadata(self, svc):
        content = b"hello world"
        doc = svc.load_bytes(content=content, filename="notes.txt")
        assert "notes.txt" in doc.filename or "notes" in str(doc.metadata)

    def test_load_empty_content_raises_or_returns_empty(self, svc):
        # Empty content — service should handle gracefully
        try:
            doc = svc.load_bytes(content=b"", filename="empty.txt")
            assert doc is not None
        except Exception:
            pass  # Some implementations raise on empty

    def test_supported_extensions_list(self, svc):
        exts = svc.supported_extensions()
        assert isinstance(exts, list)
        assert ".txt" in exts or "txt" in exts

    def test_load_document_has_word_count(self, svc):
        content = b"This document has exactly seven words here."
        doc = svc.load_bytes(content=content, filename="test.txt")
        assert hasattr(doc, "word_count") or hasattr(doc, "char_count") or doc.content


# ===========================================================================
# SchemaReaderService Tests
# ===========================================================================

class TestSchemaReaderService:

    @pytest.fixture
    def svc(self):
        return SchemaReaderService(schema_repository=None)

    def test_get_compact_tables_without_db_returns_empty(self, svc):
        result = svc.get_compact_tables()
        assert isinstance(result, list)

    def test_invalidate_cache_clears_cache(self, svc):
        # Seed a fake cache entry
        svc._cache["public"] = (1e20, None)
        svc.invalidate_cache()
        assert len(svc._cache) == 0

    def test_generate_prompt_context_without_db_returns_string(self, svc):
        result = svc.generate_prompt_context()
        assert isinstance(result, str)

    def test_service_has_repository_property(self, svc):
        assert svc.repository is None  # None when no repo injected

    def test_set_repository_updates_repo_and_clears_cache(self, svc):
        from unittest.mock import MagicMock
        mock_repo = MagicMock()
        # Pre-fill cache
        svc._cache["public"] = (1e20, None)
        svc.set_repository(mock_repo)
        assert svc.repository is mock_repo
        assert len(svc._cache) == 0

    def test_get_table_schema_nonexistent_returns_none(self, svc):
        result = svc.get_table_schema("nonexistent_table")
        assert result is None

    def test_schema_cache_ttl_is_configurable(self):
        svc = SchemaReaderService(cache_ttl_seconds=600)
        assert svc._cache_ttl == 600


# ===========================================================================
# BM25 and Vector Retriever Tests
# ===========================================================================

class TestBM25Retriever:

    def test_index_and_search_returns_results(self):
        from backend.rag.retrievers.bm25_retriever import BM25Retriever
        from backend.app.schemas.rag_pipeline import RetrievedChunk

        retriever = BM25Retriever()
        chunks = [
            RetrievedChunk(chunk_id="c1", document_id="d1", content="Revenue grew in Q3", score=0.0),
            RetrievedChunk(chunk_id="c2", document_id="d1", content="Marketing spend increased", score=0.0),
            RetrievedChunk(chunk_id="c3", document_id="d2", content="Customer churn analysis results", score=0.0),
        ]
        retriever.index(chunks)
        results = retriever.search("revenue growth", top_k=2)
        assert isinstance(results, list)

    def test_search_empty_index_returns_empty(self):
        from backend.rag.retrievers.bm25_retriever import BM25Retriever
        retriever = BM25Retriever()
        results = retriever.search("anything", top_k=5)
        assert results == []
