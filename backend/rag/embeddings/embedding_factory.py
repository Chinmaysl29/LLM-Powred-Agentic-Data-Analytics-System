"""Embedding Factory and Registry (Phase 5.3)."""

from typing import Dict, Optional, Type
from backend.app.schemas.embedding import EmbeddingProvider
from backend.rag.embeddings.base_embedding import BaseEmbedding
from backend.rag.embeddings.bge_embedding import BGEEmbedding, HuggingFaceEmbedding
from backend.rag.embeddings.miniLM_embedding import MiniLMEmbedding
from backend.rag.embeddings.openai_embedding import OpenAIEmbedding


class EmbeddingFactory:
    """Factory to instantiate and resolve vector embedding providers."""

    _REGISTRY: Dict[str, Type[BaseEmbedding]] = {
        EmbeddingProvider.LOCAL.value: MiniLMEmbedding,
        EmbeddingProvider.MINILM.value: MiniLMEmbedding,
        EmbeddingProvider.OPENAI.value: OpenAIEmbedding,
        EmbeddingProvider.BGE.value: BGEEmbedding,
        EmbeddingProvider.HUGGINGFACE.value: HuggingFaceEmbedding,
    }

    @classmethod
    def get_embedding(
        cls,
        provider: EmbeddingProvider | str = EmbeddingProvider.LOCAL,
        model_name: Optional[str] = None,
        **kwargs,
    ) -> BaseEmbedding:
        prov_key = provider.value if isinstance(provider, EmbeddingProvider) else str(provider).lower()
        emb_cls = cls._REGISTRY.get(prov_key)
        if not emb_cls:
            valid = list(cls._REGISTRY.keys())
            raise ValueError(f"Unknown embedding provider '{prov_key}'. Valid providers: {valid}")

        if model_name:
            return emb_cls(model_name=model_name, **kwargs)
        return emb_cls(**kwargs)
