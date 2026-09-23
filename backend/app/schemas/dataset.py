"""Pydantic request and response schemas for Dataset foundation operations."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class DatasetResponse(BaseModel):
    """Schema representing a persisted dataset entity."""

    model_config = ConfigDict(from_attributes=True)

    dataset_id: str = Field(..., description="Unique dataset identifier")
    dataset_name: str = Field(..., description="Human-readable name of the dataset")
    file_name: str = Field(..., description="Original filename of the uploaded file")
    file_type: str = Field(..., description="Extension/format type (csv, xlsx, json)")
    file_path: str = Field(..., description="Storage file path on disk")
    original_path: str | None = Field(None, description="Immutable source file path")
    json_path: str | None = Field(None, description="JSON preview or document artifact path")
    canonical_path: str | None = Field(None, description="Canonical tabular artifact path")
    canonical_format: str | None = Field(None, description="Canonical storage format")
    content_hash: str | None = Field(None, description="SHA-256 of the original file")
    size_bytes: int | None = Field(None, description="Source file size in bytes")
    row_count: int | None = Field(None, description="Parsed tabular row count")
    column_count: int | None = Field(None, description="Parsed tabular column count")
    version: int = Field(default=1, description="Dataset version number")
    last_active_version_id: str | None = Field(None, description="UUID of the current active version")
    status: str = Field(default="uploaded", description="Current lifecycle status")
    created_at: datetime = Field(..., description="Timestamp of dataset creation")
    updated_at: datetime = Field(..., description="Timestamp of last update")


class DatasetUploadResponse(DatasetResponse):
    """Schema representing upload response including pipeline summary."""

    message: str = Field(default="Dataset uploaded successfully")
    version_info: dict | None = Field(None, description="Initial version information")
    quality_score: float | None = Field(None, description="Overall data quality score")
    classification: str | None = Field(None, description="Quality classification")
    recommendations_summary: str | None = Field(None, description="Summary of generated cleaning recommendations")


class DatasetUpdate(BaseModel):
    """Schema for partial updates to a dataset record."""

    dataset_name: str | None = Field(None, min_length=1, max_length=255)
    status: str | None = Field(None, min_length=1, max_length=50)


class DatasetListResponse(BaseModel):
    """Paginated list response of datasets."""

    items: list[DatasetResponse]
    total: int
    skip: int
    limit: int
