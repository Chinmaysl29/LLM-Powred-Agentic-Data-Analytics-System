"""Pydantic schemas for Dataset Versioning Engine."""

from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional


class DatasetVersionBase(BaseModel):
    """Base schema for dataset version."""

    version_number: int = Field(..., ge=1, description="Sequential version number")
    change_type: str = Field(..., description="Type of change: initial_upload, modification, cleaned, transformed")
    transformation_metadata: dict | None = Field(None, description="Metadata about the transformation")
    created_by: str = Field(..., description="User who created the version")


class DatasetVersionCreate(DatasetVersionBase):
    """Schema for creating a dataset version record."""
    
    storage_path: str = Field(..., description="Path to the version's physical file")
    metadata_snapshot: dict = Field(..., description="Immutable snapshot of dataset metadata")
    quality_snapshot: dict = Field(..., description="Immutable snapshot of dataset quality")


class DatasetVersionResponse(DatasetVersionBase):
    """Schema for returning a dataset version via API."""

    model_config = ConfigDict(from_attributes=True)
    
    version_id: str = Field(..., description="UUID of the version")
    dataset_id: str = Field(..., description="UUID of the parent dataset")
    parent_version_id: str | None = Field(None, description="UUID of the parent version")
    is_active: bool = Field(..., description="Whether this version is currently active")
    activated_at: datetime | None = Field(None, description="When this version was activated")
    deactivated_at: datetime | None = Field(None, description="When this version was deactivated")
    created_at: datetime = Field(..., description="When this version was created")
    storage_path: str = Field(..., description="Path to the version's physical file")
    metadata_snapshot: dict = Field(..., description="Immutable snapshot of dataset metadata")
    quality_snapshot: dict = Field(..., description="Immutable snapshot of dataset quality")


class DatasetVersionComparisonResponse(BaseModel):
    """Schema for returning structural comparison of two versions."""

    version_number_1: int = Field(..., description="First version number")
    version_number_2: int = Field(..., description="Second version number")
    rows_added: int = Field(..., description="Number of rows added (absolute value)")
    rows_removed: int = Field(..., description="Number of rows removed (absolute value)")
    columns_added: list[str] = Field(..., description="Columns added in version 2")
    columns_removed: list[str] = Field(..., description="Columns removed in version 2")
    new_columns: list[str] = Field(..., description="Alias for columns_added")
    deleted_columns: list[str] = Field(..., description="Alias for columns_removed")


class DatasetVersionListResponse(BaseModel):
    """Schema for returning paginated dataset versions."""

    versions: list[DatasetVersionResponse] = Field(..., description="List of versions")
    total_count: int = Field(..., description="Total number of versions for dataset")
    current_active_version: int | None = Field(None, description="The currently active version number")
