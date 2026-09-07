"""Schemas for Context Builder (Phase 5.7)."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ContextSource(BaseModel):
    """Attributed source citation for a retrieved context passage."""
    source_id: str = Field(..., description="Citation label e.g. '[Source 1]'")
    chunk_id: str = Field(..., description="UUID of the originating chunk")
    document_id: str = Field(..., description="UUID of the parent document")
    filename: Optional[str] = Field(default=None, description="Original filename")
    file_type: Optional[str] = Field(default=None, description="File type")
    score: float = Field(..., description="Relevance score of the source")
    preview: str = Field(..., description="Short content preview (first 120 chars)")


class BuiltContext(BaseModel):
    """Assembled, token-budgeted, citation-attributed context ready for LLM."""
    formatted_text: str = Field(..., description="Full concatenated context text with citations")
    sources: List[ContextSource] = Field(default_factory=list, description="Source citations")
    token_count: int = Field(..., description="Estimated total tokens in formatted_text")
    truncated: bool = Field(default=False, description="True if context was truncated due to token limit")
    chunk_count: int = Field(..., description="Number of chunks included")
