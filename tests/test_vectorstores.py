"""Tests for Phase 5.4 — Vector Store Layer."""

import pytest
from backend.rag.embeddings.miniLM_embedding import MiniLMEmbedding
from backend.rag.vectorstores.faiss_store import FaissStore
from backend.rag.vectorstores.in_memory_store import InMemoryVectorStore
from backend.rag.vectorstores.store_factory import VectorStoreFactory, VectorStoreType


def _make_embedder():
    return MiniLMEmbedding()


def _make_vecs(embedder, texts):
    return embedder.embed_documents(texts)


def test_in_memory_store_add_and_search():
    store = InMemoryVectorStore()
    embedder = _make_embedder()

    texts = [
        "Enterprise revenue grew by 14% in Q3.",
        "Customer churn was reduced by implementing ML models.",
        "Ancient fossils discovered in the Sahara Desert.",
    ]
    embeddings = _make_vecs(embedder, texts)

    store.add(
        chunk_ids=["c1", "c2", "c3"],
        document_ids=["d1", "d1", "d2"],
        texts=texts,
        embeddings=embeddings,
        metadatas=[{"filename": "report.pdf"}, {"filename": "report.pdf"}, {"filename": "geo.txt"}],
    )

    assert store.stats().total_vectors == 3
    assert len(store) == 3

    # Dense search
    query_vec = embedder.embed_query("quarterly revenue growth enterprise")
    results = store.search(query_vec, top_k=2)
    assert len(results) >= 1
    assert results[0].score > 0.0
    assert results[0].score <= 1.0
    # Most relevant should be revenue text
    assert "revenue" in results[0].content.lower() or "churn" in results[0].content.lower()


def test_in_memory_store_filter():
    store = InMemoryVectorStore()
    embedder = _make_embedder()
    texts = ["Sales data report", "Marketing campaign data"]
    embeddings = _make_vecs(embedder, texts)
    store.add(
        chunk_ids=["c1", "c2"],
        document_ids=["d1", "d2"],
        texts=texts,
        embeddings=embeddings,
        metadatas=[{"file_type": "pdf"}, {"file_type": "csv"}],
    )
    query_vec = embedder.embed_query("data report")
    results = store.search(query_vec, top_k=5, filters={"file_type": "pdf"})
    assert all(r.metadata.get("file_type") == "pdf" for r in results)


def test_in_memory_store_delete():
    store = InMemoryVectorStore()
    embedder = _make_embedder()
    texts = ["Alpha document", "Beta document"]
    embeddings = _make_vecs(embedder, texts)
    store.add(chunk_ids=["c1", "c2"], document_ids=["d1", "d1"], texts=texts, embeddings=embeddings)
    store.delete(["c1"])
    assert store.stats().total_vectors == 1
    assert store._chunk_ids == ["c2"]


def test_in_memory_store_clear():
    store = InMemoryVectorStore()
    embedder = _make_embedder()
    texts = ["Alpha", "Beta"]
    embeddings = _make_vecs(embedder, texts)
    store.add(chunk_ids=["c1", "c2"], document_ids=["d1", "d1"], texts=texts, embeddings=embeddings)
    store.clear()
    assert store.stats().total_vectors == 0


def test_faiss_store_add_and_search():
    store = FaissStore()
    embedder = _make_embedder()
    texts = [
        "Revenue forecasting model with seasonal adjustment",
        "Employee satisfaction survey results",
    ]
    embeddings = _make_vecs(embedder, texts)
    store.add(
        chunk_ids=["f1", "f2"],
        document_ids=["doc1", "doc1"],
        texts=texts,
        embeddings=embeddings,
    )
    assert store.stats().total_vectors == 2

    query_vec = embedder.embed_query("revenue forecast")
    results = store.search(query_vec, top_k=2)
    assert len(results) >= 1
    assert results[0].score >= 0.0


def test_vector_store_factory():
    store_mem = VectorStoreFactory.get_store(VectorStoreType.IN_MEMORY)
    assert isinstance(store_mem, InMemoryVectorStore)

    store_faiss = VectorStoreFactory.get_store("faiss")
    assert isinstance(store_faiss, FaissStore)

    with pytest.raises(ValueError, match="Unknown vector store type"):
        VectorStoreFactory.get_store("nonexistent_store")
