"""Pydantic schemas for RAG Vector Store Layer (Phase 5.4)."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class VectorSearchResult(BaseModel):
    """Single result from a vector similarity search."""
    chunk_id: str = Field(..., description="UUID of the retrieved chunk")
    document_id: str = Field(..., description="UUID of the parent document")
    content: str = Field(..., description="Text content of the retrieved chunk")
    score: float = Field(..., ge=0.0, le=1.0, description="Cosine similarity score (0-1)")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Chunk metadata")


class IndexStats(BaseModel):
    """Statistics about a vector index."""
    total_vectors: int = Field(..., description="Total number of indexed vectors")
    dimension: int = Field(..., description="Dimensionality of stored vectors")
    index_type: str = Field(..., description="Type of underlying index")
    collections: List[str] = Field(default_factory=list, description="Named collections in the store")


class VectorAddRequest(BaseModel):
    """Request payload for adding vectors to the store."""
    chunk_ids: List[str] = Field(..., description="List of unique chunk identifiers")
    document_ids: List[str] = Field(..., description="Parent document IDs per chunk")
    texts: List[str] = Field(..., description="Text content per chunk")
    embeddings: List[List[float]] = Field(..., description="Pre-computed embedding vectors")
    metadatas: Optional[List[Dict[str, Any]]] = Field(default=None, description="Optional metadata per chunk")


class VectorSearchRequest(BaseModel):
    """Request payload for a vector similarity search."""
    query_vector: List[float] = Field(..., description="Query embedding vector")
    top_k: int = Field(default=5, ge=1, description="Number of results to return")
    min_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Minimum similarity score threshold")
    filters: Optional[Dict[str, Any]] = Field(default=None, description="Metadata filters to apply")
