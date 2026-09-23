"""Pydantic schemas for Dataset Metadata."""

from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class ColumnMetadata(BaseModel):
    """Schema for individual column statistics."""

    name: str = Field(..., description="Name of the column")
    type: str = Field(..., description="Data type of the column")
    null_count: int = Field(..., description="Number of null values")
    null_percentage: float = Field(..., description="Percentage of null values (0.0 to 1.0)")
    unique_count: int = Field(..., description="Number of unique values")


class DatasetClassification(BaseModel):
    """Schema for dataset column classifications."""

    numeric: list[str] = Field(default_factory=list, description="List of numeric columns")
    categorical: list[str] = Field(default_factory=list, description="List of categorical columns")
    datetime: list[str] = Field(default_factory=list, description="List of datetime columns")
    boolean: list[str] = Field(default_factory=list, description="List of boolean columns")


class DatasetMetadataBase(BaseModel):
    """Base schema for dataset metadata."""

    dataset_id: str = Field(..., description="ID of the dataset")
    row_count: int = Field(..., description="Total number of rows in the dataset")
    column_count: int = Field(..., description="Total number of columns in the dataset")
    column_names: list[str] = Field(..., description="List of all column names")
    column_types: dict[str, str] = Field(..., description="Mapping of column names to their types")
    columns_metadata: list[ColumnMetadata] = Field(..., description="Detailed statistics for each column")
    classifications: DatasetClassification = Field(..., description="Column classifications")


class DatasetMetadataCreate(DatasetMetadataBase):
    """Schema for creating dataset metadata."""
    pass


class DatasetMetadataResponse(DatasetMetadataBase):
    """Schema for dataset metadata responses."""

    model_config = ConfigDict(from_attributes=True)

    created_at: datetime = Field(..., description="Timestamp of metadata creation")
    updated_at: datetime = Field(..., description="Timestamp of last update")
