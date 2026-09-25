"""Tests for Phase 5.2 — Chunking Engine."""

import pytest
from backend.app.schemas.chunking import ChunkingStrategy
from backend.app.schemas.document_loader import DocumentMetadata, LoadedDocument
from backend.app.services.chunking_service import ChunkingService
from backend.rag.chunking.chunker_factory import ChunkerFactory
from backend.rag.chunking.fixed_chunker import FixedSizeChunker
from backend.rag.chunking.recursive_chunker import RecursiveCharacterChunker
from backend.rag.chunking.semantic_chunker import SemanticChunker
from backend.rag.chunking.table_aware_chunker import TableAwareChunker


def test_recursive_chunker_basic() -> None:
    chunker = RecursiveCharacterChunker(chunk_size=150, chunk_overlap=30)
    text = (
        "Antigravity AI is an enterprise data analyst OS.\n\n"
        "It features dynamic workflow orchestration, exploratory data analysis, and advanced statistics.\n\n"
        "The RAG layer processes unstructured documents such as PDFs, spreadsheets, and technical docs."
    )
    chunks = chunker.split_text(text, document_id="doc-123")
    assert len(chunks) >= 2
    for idx, c in enumerate(chunks):
        assert c.document_id == "doc-123"
        assert c.chunk_index == idx
        assert len(c.content) <= 180
        assert c.token_count > 0
        assert c.metadata.start_char >= 0
        assert c.metadata.end_char > c.metadata.start_char


def test_semantic_chunker_preserves_sentences() -> None:
    chunker = SemanticChunker(chunk_size=120, chunk_overlap=20)
    text = (
        "First complete sentence here. Second complete sentence follows. "
        "Third sentence has further details. Fourth sentence concludes this section."
    )
    chunks = chunker.split_text(text, document_id="doc-sem")
    assert len(chunks) >= 2
    for c in chunks:
        # Should not end with a truncated word
        assert c.content[-1] in ".!?" or c.content.endswith("section.")


def test_table_aware_chunker_preserves_markdown_tables() -> None:
    chunker = TableAwareChunker(chunk_size=180, chunk_overlap=30)
    narrative_and_table = (
        "Here is the annual financial overview:\n\n"
        "| Department | Q1 Revenue | Q2 Revenue | Q3 Revenue | Q4 Revenue |\n"
        "| --- | --- | --- | --- | --- |\n"
        "| Engineering | $100,000 | $120,000 | $130,000 | $150,000 |\n"
        "| Marketing | $80,000 | $90,000 | $95,000 | $110,000 |\n"
        "| Operations | $50,000 | $55,000 | $60,000 | $70,000 |\n"
        "| Support | $30,000 | $35,000 | $40,000 | $45,000 |\n\n"
        "All figures have been audited by internal compliance."
    )
    chunks = chunker.split_text(narrative_and_table, document_id="doc-table")
    assert len(chunks) >= 2

    # Verify that table chunks contain the table header
    table_chunks = [c for c in chunks if "| Department |" in c.content]
    assert len(table_chunks) >= 1
    for tc in table_chunks:
        assert "| Department |" in tc.content
        assert "| --- |" in tc.content


def test_fixed_chunker() -> None:
    chunker = FixedSizeChunker(chunk_size=50, chunk_overlap=10)
    text = "A" * 120
    chunks = chunker.split_text(text, document_id="doc-fixed")
    assert len(chunks) == 3
    assert chunks[0].content == "A" * 50
    assert chunks[0].metadata.start_char == 0
    assert chunks[0].metadata.end_char == 50


def test_chunker_factory() -> None:
    c1 = ChunkerFactory.get_chunker(ChunkingStrategy.RECURSIVE)
    assert isinstance(c1, RecursiveCharacterChunker)

    c2 = ChunkerFactory.get_chunker("semantic")
    assert isinstance(c2, SemanticChunker)

    c3 = ChunkerFactory.get_chunker(ChunkingStrategy.TABLE_AWARE)
    assert isinstance(c3, TableAwareChunker)

    c4 = ChunkerFactory.get_chunker("fixed")
    assert isinstance(c4, FixedSizeChunker)

    with pytest.raises(ValueError, match="Unknown chunking strategy"):
        ChunkerFactory.get_chunker("unsupported_strategy")


def test_chunking_service() -> None:
    service = ChunkingService()
    doc = LoadedDocument(
        document_id="doc-service-1",
        content="Alpha paragraph with content.\n\nBeta paragraph with additional info.",
        metadata=DocumentMetadata(
            filename="test.txt",
            file_type="txt",
            uploaded_at="2026-09-05T00:00:00Z",
            size=100,
        ),
    )

    resp = service.chunk_document(doc, strategy=ChunkingStrategy.RECURSIVE, chunk_size=200)
    assert resp.total_chunks >= 1
    assert resp.document_id == "doc-service-1"
    assert resp.chunks[0].metadata.filename == "test.txt"

    # Multi-document chunking
    doc2 = LoadedDocument(
        document_id="doc-service-2",
        content="Gamma section content.",
        metadata=DocumentMetadata(
            filename="gamma.txt",
            file_type="txt",
            uploaded_at="2026-09-05T00:00:00Z",
            size=50,
        ),
    )
    all_chunks = service.chunk_documents([doc, doc2], chunk_size=100)
    assert len(all_chunks) >= 2
    doc_ids = {c.document_id for c in all_chunks}
    assert doc_ids == {"doc-service-1", "doc-service-2"}
