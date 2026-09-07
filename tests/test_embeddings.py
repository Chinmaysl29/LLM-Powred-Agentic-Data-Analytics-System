"""Tests for Phase 5.3 — Embedding Engine."""

import pytest
from backend.app.schemas.embedding import EmbeddingProvider
from backend.rag.embeddings.base_embedding import BaseEmbedding
from backend.rag.embeddings.bge_embedding import BGEEmbedding
from backend.rag.embeddings.embedding_factory import EmbeddingFactory
from backend.rag.embeddings.miniLM_embedding import MiniLMEmbedding
from backend.rag.embeddings.openai_embedding import OpenAIEmbedding


def test_minilm_embedding_dimension_and_normalization() -> None:
    embedder = MiniLMEmbedding()
    assert embedder.dimension == 384

    doc = "Enterprise data analyst system with AI agents."
    vec = embedder.embed_query(doc)
    assert len(vec) == 384

    # Norm should be close to 1.0
    norm = sum(x * x for x in vec) ** 0.5
    assert abs(norm - 1.0) < 1e-3


def test_embedding_similarity_math() -> None:
    embedder = MiniLMEmbedding()
    text_a = "Quarterly financial sales revenue report"
    text_b = "Quarterly financial earnings report"
    text_c = "Ancient dinosaur fossils paleontology excavation"

    vec_a = embedder.embed_query(text_a)
    vec_b = embedder.embed_query(text_b)
    vec_c = embedder.embed_query(text_c)

    sim_identical = embedder.cosine_similarity(vec_a, vec_a)
    sim_related = embedder.cosine_similarity(vec_a, vec_b)
    sim_unrelated = embedder.cosine_similarity(vec_a, vec_c)

    assert abs(sim_identical - 1.0) < 1e-4
    assert sim_related > sim_unrelated


def test_batch_document_embedding() -> None:
    embedder = MiniLMEmbedding()
    texts = [
        "First document text",
        "Second document text",
        "Third document text",
    ]
    vecs = embedder.embed_documents(texts)
    assert len(vecs) == 3
    for v in vecs:
        assert len(v) == 384


def test_openai_embedding_dimensions() -> None:
    embedder = OpenAIEmbedding()
    assert embedder.dimension == 1536

    vec = embedder.embed_query("Sample natural language query")
    assert len(vec) == 1536
    norm = sum(x * x for x in vec) ** 0.5
    assert abs(norm - 1.0) < 1e-3


def test_embedding_factory() -> None:
    e_local = EmbeddingFactory.get_embedding(EmbeddingProvider.LOCAL)
    assert isinstance(e_local, BaseEmbedding)
    assert e_local.dimension == 384

    e_minilm = EmbeddingFactory.get_embedding("minilm")
    assert isinstance(e_minilm, MiniLMEmbedding)

    e_openai = EmbeddingFactory.get_embedding("openai")
    assert isinstance(e_openai, OpenAIEmbedding)
    assert e_openai.dimension == 1536

    e_bge = EmbeddingFactory.get_embedding("bge")
    assert isinstance(e_bge, BGEEmbedding)

    with pytest.raises(ValueError, match="Unknown embedding provider"):
        EmbeddingFactory.get_embedding("unsupported_provider")
