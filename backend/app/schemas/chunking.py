"""Schemas for the RAG Chunking Engine (Phase 5.2)."""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ChunkingStrategy(str, Enum):
    RECURSIVE = "recursive"
    SEMANTIC = "semantic"
    TABLE_AWARE = "table_aware"
    FIXED = "fixed"


class ChunkMetadata(BaseModel):
    """Metadata container for individual text chunks."""
    document_id: str = Field(..., description="ID of source document")
    chunk_index: int = Field(..., description="0-indexed position of chunk in document")
    filename: Optional[str] = Field(default=None, description="Original filename")
    file_type: Optional[str] = Field(default=None, description="File type/extension")
    start_char: int = Field(default=0, description="Character start offset in source text")
    end_char: int = Field(default=0, description="Character end offset in source text")
    extra: Dict[str, Any] = Field(default_factory=dict, description="Format or domain metadata")


class Chunk(BaseModel):
    """Standardized representation of an ingested document chunk."""
    chunk_id: str = Field(..., description="Unique UUID for this chunk")
    document_id: str = Field(..., description="Parent document UUID")
    chunk_index: int = Field(..., description="Ordinal chunk index")
    content: str = Field(..., description="Normalized chunk text content")
    char_count: int = Field(..., description="Character count of chunk")
    token_count: int = Field(..., description="Estimated/calculated token count")
    metadata: ChunkMetadata = Field(..., description="Chunk-level metadata")


class ChunkingRequest(BaseModel):
    """Request payload for chunking operations."""
    content: str = Field(..., description="Raw or normalized text to chunk")
    document_id: Optional[str] = Field(default=None, description="Parent document identifier")
    strategy: ChunkingStrategy = Field(default=ChunkingStrategy.RECURSIVE, description="Chunking strategy")
    chunk_size: int = Field(default=1000, description="Target chunk size in characters/tokens")
    chunk_overlap: int = Field(default=200, description="Overlap between consecutive chunks")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Optional metadata to inherit")


class ChunkingResponse(BaseModel):
    """Response envelope for chunking operations."""
    chunks: List[Chunk] = Field(default_factory=list, description="Generated chunks")
    total_chunks: int = Field(..., description="Number of chunks generated")
    strategy: str = Field(..., description="Chunking strategy utilized")
    document_id: Optional[str] = Field(default=None, description="Source document ID")
