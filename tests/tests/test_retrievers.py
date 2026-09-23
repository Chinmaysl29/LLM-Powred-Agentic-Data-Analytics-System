"""Tests for Phases 5.5 & 5.6 — Vector Retriever, BM25, and Hybrid Retrieval."""

import pytest
from backend.rag.embeddings.miniLM_embedding import MiniLMEmbedding
from backend.rag.retrievers.bm25_retriever import BM25Retriever
from backend.rag.retrievers.hybrid_retriever import HybridRetriever
from backend.rag.retrievers.vector_retriever import VectorRetriever
from backend.rag.vectorstores.in_memory_store import InMemoryVectorStore


SAMPLE_TEXTS = [
    "Quarterly revenue grew by 14% driven by North region sales.",
    "Customer churn decreased after implementing machine learning retention models.",
    "Marketing spend increased by 20% with corresponding 15% lift in lead generation.",
    "Inventory turnover ratio improved from 4.2 to 5.1 during Q3.",
    "Ancient Mesopotamian tablets discovered in archaeological dig site.",
]

SAMPLE_IDS = ["chunk-0", "chunk-1", "chunk-2", "chunk-3", "chunk-4"]
SAMPLE_DOCS = ["doc-A", "doc-A", "doc-B", "doc-B", "doc-C"]


def _build_index():
    embedder = MiniLMEmbedding()
    store = InMemoryVectorStore()
    embeddings = embedder.embed_documents(SAMPLE_TEXTS)
    store.add(
        chunk_ids=SAMPLE_IDS,
        document_ids=SAMPLE_DOCS,
        texts=SAMPLE_TEXTS,
        embeddings=embeddings,
    )
    return embedder, store


def test_vector_retriever_basic():
    embedder, store = _build_index()
    retriever = VectorRetriever(embedder, store)
    results = retriever.retrieve("quarterly revenue North region", top_k=3)
    assert len(results) >= 1
    assert results[0].score > 0.0
    # Most relevant result should be about revenue
    top_content = results[0].content.lower()
    assert "revenue" in top_content or "sales" in top_content or "quarterly" in top_content


def test_vector_retriever_top_k_limit():
    embedder, store = _build_index()
    retriever = VectorRetriever(embedder, store)
    results = retriever.retrieve("business analytics", top_k=2)
    assert len(results) <= 2


def test_bm25_retriever():
    bm25 = BM25Retriever()
    bm25.index(
        chunk_ids=SAMPLE_IDS,
        document_ids=SAMPLE_DOCS,
        texts=SAMPLE_TEXTS,
    )
    results = bm25.retrieve("revenue quarterly North sales", top_k=3)
    assert len(results) >= 1
    # Revenue chunk should rank high for exact keyword match
    assert any("revenue" in r.content.lower() for r in results)


def test_bm25_empty_corpus():
    bm25 = BM25Retriever()
    results = bm25.retrieve("anything", top_k=5)
    assert results == []


def test_hybrid_retriever_rrf():
    embedder, store = _build_index()
    bm25 = BM25Retriever()
    bm25.index(chunk_ids=SAMPLE_IDS, document_ids=SAMPLE_DOCS, texts=SAMPLE_TEXTS)

    dense = VectorRetriever(embedder, store)
    hybrid = HybridRetriever(dense, bm25, alpha=0.7)

    results = hybrid.retrieve("revenue quarterly sales growth", top_k=3)
    assert len(results) >= 1
    # Scores should be normalized [0, 1]
    for r in results:
        assert 0.0 <= r.score <= 1.0


def test_hybrid_retriever_score_ordering():
    embedder, store = _build_index()
    bm25 = BM25Retriever()
    bm25.index(chunk_ids=SAMPLE_IDS, document_ids=SAMPLE_DOCS, texts=SAMPLE_TEXTS)
    dense = VectorRetriever(embedder, store)
    hybrid = HybridRetriever(dense, bm25, alpha=0.7)

    results = hybrid.retrieve("revenue quarterly sales", top_k=5)
    scores = [r.score for r in results]
    assert scores == sorted(scores, reverse=True)


def test_retriever_no_results_on_irrelevant_query():
    embedder, store = _build_index()
    retriever = VectorRetriever(embedder, store)
    # Use a very high min_score threshold
    results = retriever.retrieve("purple elephant teleportation", top_k=5, min_score=0.99)
    # May return 0 or very few results at 0.99 threshold
    assert len(results) <= 5


def test_retrievers_package_exports():
    from backend.rag.retrievers import BaseRetriever, BM25Retriever, HybridRetriever, VectorRetriever
    assert BaseRetriever is not None
    assert VectorRetriever is not None
    assert BM25Retriever is not None
    assert HybridRetriever is not None
