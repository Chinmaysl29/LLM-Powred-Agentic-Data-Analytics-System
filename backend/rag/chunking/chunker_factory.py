"""Chunker Factory and Registry (Phase 5.2)."""

from typing import Dict, Type
from backend.app.schemas.chunking import ChunkingStrategy
from backend.rag.chunking.base_chunker import BaseChunker
from backend.rag.chunking.fixed_chunker import FixedSizeChunker
from backend.rag.chunking.recursive_chunker import RecursiveCharacterChunker
from backend.rag.chunking.semantic_chunker import SemanticChunker
from backend.rag.chunking.table_aware_chunker import TableAwareChunker


class ChunkerFactory:
    """Factory to create and resolve text chunker strategies."""

    _REGISTRY: Dict[str, Type[BaseChunker]] = {
        ChunkingStrategy.RECURSIVE.value: RecursiveCharacterChunker,
        ChunkingStrategy.SEMANTIC.value: SemanticChunker,
        ChunkingStrategy.TABLE_AWARE.value: TableAwareChunker,
        ChunkingStrategy.FIXED.value: FixedSizeChunker,
    }

    @classmethod
    def get_chunker(
        cls,
        strategy: str | ChunkingStrategy = ChunkingStrategy.RECURSIVE,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
    ) -> BaseChunker:
        strat_key = strategy.value if isinstance(strategy, ChunkingStrategy) else str(strategy).lower()
        chunker_cls = cls._REGISTRY.get(strat_key)
        if not chunker_cls:
            chunker_cls = cls._REGISTRY.get(ChunkingStrategy.RECURSIVE.value, RecursiveCharacterChunker)
        return chunker_cls(chunk_size=chunk_size, chunk_overlap=chunk_overlap)

