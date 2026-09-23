"""Pydantic schemas for RAG Embedding Engine (Phase 5.3)."""

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class EmbeddingProvider(str, Enum):
    OPENAI = "openai"
    MINILM = "minilm"
    BGE = "bge"
    HUGGINGFACE = "huggingface"
    LOCAL = "local"


class EmbeddingRequest(BaseModel):
    """Request payload to generate vector embeddings."""
    texts: List[str] = Field(..., min_length=1, description="List of text strings to embed")
    provider: Optional[EmbeddingProvider] = Field(
        default=EmbeddingProvider.LOCAL,
        description="Target embedding provider",
    )
    model_name: Optional[str] = Field(default=None, description="Optional specific model identifier")


class EmbeddingResponse(BaseModel):
    """Response envelope containing generated vector embeddings."""
    embeddings: List[List[float]] = Field(..., description="List of embedding vectors")
    dimension: int = Field(..., description="Dimensionality of the embedding vectors")
    provider: str = Field(..., description="Provider utilized")
    model_name: str = Field(..., description="Specific model utilized")
    total_tokens: Optional[int] = Field(default=None, description="Total tokens consumed if known")
