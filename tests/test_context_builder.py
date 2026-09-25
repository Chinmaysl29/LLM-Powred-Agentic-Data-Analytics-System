"""Tests for Phase 5.7 — Context Builder."""

import pytest
from backend.app.schemas.vector_store import VectorSearchResult
from backend.rag.context_builder import ContextBuilder


def _make_result(chunk_id, doc_id, content, score, filename="report.pdf"):
    return VectorSearchResult(
        chunk_id=chunk_id,
        document_id=doc_id,
        content=content,
        score=score,
        metadata={"filename": filename, "file_type": "pdf"},
    )


def test_context_builder_basic():
    builder = ContextBuilder(max_tokens=4000)
    results = [
        _make_result("c1", "d1", "Revenue grew 14% in Q3 driven by North region.", 0.92),
        _make_result("c2", "d1", "Marketing spend increased 20% with 15% lead lift.", 0.87),
        _make_result("c3", "d2", "Customer churn fell by 8% after ML model deployment.", 0.75),
    ]
    ctx = builder.build(results)
    assert ctx.chunk_count == 3
    assert "[Source 1]" in ctx.formatted_text
    assert "[Source 2]" in ctx.formatted_text
    assert ctx.token_count > 0
    assert not ctx.truncated
    assert len(ctx.sources) == 3


def test_context_builder_token_budget():
    # Very small budget — should truncate
    builder = ContextBuilder(max_tokens=20)
    results = [
        _make_result("c1", "d1", "A" * 200, 0.9),
        _make_result("c2", "d1", "B" * 200, 0.8),
    ]
    ctx = builder.build(results, max_tokens=20)
    assert ctx.truncated is True
    assert ctx.chunk_count <= 1


def test_context_builder_deduplication():
    builder = ContextBuilder(max_tokens=4000)
    duplicate_content = "Revenue grew 14% in North region this quarter."
    results = [
        _make_result("c1", "d1", duplicate_content, 0.95),
        _make_result("c2", "d1", duplicate_content, 0.90),  # duplicate
        _make_result("c3", "d2", "Customer satisfaction score improved by 6 points.", 0.80),
    ]
    ctx = builder.build(results)
    # Should deduplicate — only 2 unique chunks
    assert ctx.chunk_count == 2


def test_context_builder_format_citations():
    builder = ContextBuilder()
    results = [
        _make_result("c1", "d1", "Source one content here.", 0.92),
    ]
    ctx = builder.build(results)
    citations = builder.format_citations(ctx.sources)
    assert "**Sources:**" in citations
    assert "[Source 1]" in citations
    assert "report.pdf" in citations


def test_context_builder_empty_results():
    builder = ContextBuilder()
    ctx = builder.build([])
    assert ctx.chunk_count == 0
    assert ctx.formatted_text == ""
    assert not ctx.truncated
