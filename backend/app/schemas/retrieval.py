"""Pydantic schemas for retrieval operations.

This module contains BOTH:
  - Data Retrieval Agent schemas (DataRetrievalFilter, DatasetSchemaResponse, PackagedDatasetContext)
  - RAG Retriever schemas (RetrievalQuery, RetrievalResult)
"""

from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field

from backend.app.schemas.dataset import DatasetResponse
from backend.app.schemas.dataset_metadata import DatasetMetadataResponse
from backend.app.schemas.dataset_profile import DatasetProfileResponse
from backend.app.schemas.dataset_quality import DatasetQualityResponse
from backend.app.schemas.dataset_version import DatasetVersionResponse
from backend.app.schemas.vector_store import VectorSearchResult


# ─────────────────────────────────────────────────────────────────────────────
# Data Retrieval Agent schemas (Phase 3.3)
# ─────────────────────────────────────────────────────────────────────────────

class FilterCondition(BaseModel):
    """A single filter condition for dataset loading."""
    column: str
    operator: Literal["eq", "neq", "gt", "gte", "lt", "lte", "in", "contains"]
    value: Any


class DateRangeFilter(BaseModel):
    """Date range filter for time-series datasets."""
    column: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None


class DataRetrievalFilter(BaseModel):
    """Standardized filter specification for DataRetrievalService."""
    columns: Optional[List[str]] = Field(default=None, description="Columns to include")
    conditions: Optional[List[FilterCondition]] = Field(default=None, description="Row filter conditions")
    date_range: Optional[DateRangeFilter] = Field(default=None, description="Date range filter")


class DatasetSchemaResponse(BaseModel):
    """Schema information for a dataset."""
    columns: List[str] = Field(default_factory=list)
    data_types: Dict[str, str] = Field(default_factory=dict)
    row_count: Optional[int] = None


class PackagedDatasetContext(BaseModel):
    """Complete packaged dataset context for downstream agents."""
    dataset_id: str
    rows: int
    columns: int
    quality_score: Optional[float] = None
    active_version: Optional[int] = None
    dataset: Optional[DatasetResponse] = None
    metadata: Optional[DatasetMetadataResponse] = None
    profile: Optional[DatasetProfileResponse] = None
    quality: Optional[DatasetQualityResponse] = None
    version: Optional[DatasetVersionResponse] = None


class DataRetrievalRequest(BaseModel):
    """Request payload for querying a dataset with optional filters and sampling."""
    version_number: Optional[int] = Field(default=None, description="Specific dataset version to load")
    filters: Optional[DataRetrievalFilter] = Field(default=None, description="Column/row filters to apply")
    sample_size: Optional[int] = Field(default=None, description="Row sample target for large datasets")
    limit: Optional[int] = Field(default=None, description="Maximum rows to return in response")


# ─────────────────────────────────────────────────────────────────────────────
# RAG Retriever schemas (Phase 5.5)
# ─────────────────────────────────────────────────────────────────────────────

class RetrievalQuery(BaseModel):
    """RAG retrieval query parameters."""
    query_text: str = Field(..., description="Natural language query")
    top_k: int = Field(default=5, ge=1, description="Number of chunks to retrieve")
    min_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Minimum relevance score threshold")
    filters: Optional[Dict[str, Any]] = Field(default=None, description="Metadata filters")
    use_hybrid: bool = Field(default=False, description="Enable dense+sparse hybrid retrieval")
    hybrid_alpha: float = Field(default=0.7, ge=0.0, le=1.0, description="Dense weight in hybrid (0=BM25, 1=dense)")


class RetrievalResult(BaseModel):
    """RAG retrieval results from a query."""
    query: str = Field(..., description="Original query text")
    chunks: List[VectorSearchResult] = Field(default_factory=list, description="Retrieved chunks with scores")
    total_retrieved: int = Field(..., description="Number of chunks retrieved")
    retrieval_time_ms: Optional[float] = Field(default=None, description="Retrieval latency in milliseconds")
    strategy: str = Field(default="dense", description="Retrieval strategy used")
