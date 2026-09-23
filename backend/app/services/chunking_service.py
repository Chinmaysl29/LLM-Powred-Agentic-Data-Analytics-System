"""Chunking Service for RAG pipeline (Phase 5.2)."""

import uuid
from typing import Any, Dict, List, Optional

from backend.app.schemas.chunking import (
    Chunk,
    ChunkingRequest,
    ChunkingResponse,
    ChunkingStrategy,
)
from backend.app.schemas.document_loader import LoadedDocument
from backend.rag.chunking.chunker_factory import ChunkerFactory


class ChunkingService:
    """Orchestrates document chunking using configurable splitting strategies."""

    def __init__(self) -> None:
        pass

    def chunk_text(
        self,
        content: str,
        document_id: Optional[str] = None,
        strategy: ChunkingStrategy | str = ChunkingStrategy.RECURSIVE,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ChunkingResponse:
        doc_id = document_id or str(uuid.uuid4())
        if chunk_overlap >= chunk_size:
            chunk_overlap = max(0, chunk_size // 5)
        chunker = ChunkerFactory.get_chunker(
            strategy=strategy,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )
        chunks = chunker.split_text(content, document_id=doc_id, metadata=metadata)

        strategy_str = strategy.value if isinstance(strategy, ChunkingStrategy) else str(strategy)
        return ChunkingResponse(
            chunks=chunks,
            total_chunks=len(chunks),
            strategy=strategy_str,
            document_id=doc_id,
        )

    def chunk_document(
        self,
        document: LoadedDocument,
        strategy: ChunkingStrategy | str = ChunkingStrategy.RECURSIVE,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
    ) -> ChunkingResponse:
        meta_dict = document.metadata.model_dump()
        return self.chunk_text(
            content=document.content,
            document_id=document.document_id,
            strategy=strategy,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            metadata=meta_dict,
        )

    def chunk_documents(
        self,
        documents: List[LoadedDocument],
        strategy: ChunkingStrategy | str = ChunkingStrategy.RECURSIVE,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
    ) -> List[Chunk]:
        all_chunks: List[Chunk] = []
        for doc in documents:
            resp = self.chunk_document(
                document=doc,
                strategy=strategy,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
            )
            all_chunks.extend(resp.chunks)
        return all_chunks
