"""Base Chunker interface and common utilities (Phase 5.2)."""

import uuid
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
import tiktoken

from backend.app.schemas.chunking import Chunk, ChunkMetadata


class BaseChunker(ABC):
    """Abstract base class for all text chunkers."""

    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200) -> None:
        if chunk_size <= 0:
            raise ValueError("chunk_size must be greater than 0")
        if chunk_overlap < 0:
            raise ValueError("chunk_overlap must be non-negative")
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be strictly less than chunk_size")

        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

        try:
            self._tokenizer = tiktoken.get_encoding("cl100k_base")
        except Exception:
            self._tokenizer = None

    def count_tokens(self, text: str) -> int:
        """Count tokens using tiktoken cl100k_base with character-ratio fallback."""
        if not text:
            return 0
        if self._tokenizer is not None:
            try:
                return len(self._tokenizer.encode(text, disallowed_special=()))
            except Exception:
                pass
        return max(1, len(text) // 4)

    def create_chunk(
        self,
        content: str,
        document_id: str,
        chunk_index: int,
        start_char: int,
        end_char: int,
        source_metadata: Optional[Dict[str, Any]] = None,
    ) -> Chunk:
        """Helper to create a fully populated Chunk instance."""
        meta_dict = dict(source_metadata or {})
        filename = meta_dict.pop("filename", None)
        file_type = meta_dict.pop("file_type", None)

        metadata = ChunkMetadata(
            document_id=document_id,
            chunk_index=chunk_index,
            filename=filename,
            file_type=file_type,
            start_char=start_char,
            end_char=end_char,
            extra=meta_dict,
        )

        return Chunk(
            chunk_id=str(uuid.uuid4()),
            document_id=document_id,
            chunk_index=chunk_index,
            content=content,
            char_count=len(content),
            token_count=self.count_tokens(content),
            metadata=metadata,
        )

    @abstractmethod
    def split_text(
        self,
        text: str,
        document_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> List[Chunk]:
        """Split text into a sequence of standardized Chunk objects."""
        pass
