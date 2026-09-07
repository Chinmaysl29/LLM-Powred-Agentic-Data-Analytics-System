"""Pydantic schemas for Dataset Profiling Engine."""

from pydantic import BaseModel, ConfigDict, Field
from typing import Optional


class NumericProfile(BaseModel):
    """Schema for a numeric column's statistical profile."""

    mean: float = Field(..., description="Mean value")
    median: float = Field(..., description="Median value (50th percentile)")
    mode: float | str | None = Field(None, description="Mode value (first if multiple)")
    min: float = Field(..., description="Minimum value")
    max: float = Field(..., description="Maximum value")
    std: float = Field(..., description="Standard deviation")
    variance: float = Field(..., description="Variance")
    p25: float = Field(..., description="25th percentile")
    p50: float = Field(..., description="50th percentile (median)")
    p75: float = Field(..., description="75th percentile")
    skewness: float = Field(..., description="Skewness of distribution")
    kurtosis: float = Field(..., description="Kurtosis of distribution")


class MissingDataProfile(BaseModel):
    """Schema for overall dataset missing data profile."""

    null_count: int = Field(..., description="Total number of missing values across all columns")
    null_percentage: float = Field(..., description="Percentage of missing values across entire dataset")
    columns_with_missing: list[str] = Field(..., description="List of columns that contain at least one null value")


class CardinalityProfile(BaseModel):
    """Schema for dataset cardinality profile."""

    high_cardinality_columns: list[str] = Field(..., description="Columns with > 50% unique values (if rows > 100)")
    low_cardinality_columns: list[str] = Field(..., description="Columns with very few unique values (< 20)")


class DatasetProfileBase(BaseModel):
    """Base schema for dataset profile data."""

    dataset_id: str = Field(..., description="ID of the dataset")
    duplicate_rows: int = Field(..., description="Number of exact duplicate rows")
    duplicate_percentage: float = Field(..., description="Percentage of duplicate rows")
    missing_data_profile: MissingDataProfile = Field(..., description="Missing data analysis results")
    cardinality_profile: CardinalityProfile = Field(..., description="Cardinality analysis results")
    numeric_columns_profile: dict[str, NumericProfile] = Field(..., description="Statistical profile per numeric column")


class DatasetProfileCreate(DatasetProfileBase):
    """Schema for creating a dataset profile."""
    pass


class DatasetProfileResponse(DatasetProfileBase):
    """Schema for returning dataset profile via API."""

    model_config = ConfigDict(from_attributes=True)
