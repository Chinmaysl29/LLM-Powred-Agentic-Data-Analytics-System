"""Pydantic schemas for Dataset Quality Engine."""

from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class DatasetQualityBase(BaseModel):
    """Base schema for dataset quality scores."""

    completeness_score: float = Field(..., description="Score based on null percentages (0-100)", ge=0.0, le=100.0)
    uniqueness_score: float = Field(..., description="Score based on duplicates (0-100)", ge=0.0, le=100.0)
    consistency_score: float = Field(..., description="Score based on data type uniformity (0-100)", ge=0.0, le=100.0)
    validity_score: float = Field(..., description="Score based on valid ranges and heuristics (0-100)", ge=0.0, le=100.0)
    integrity_score: float = Field(..., description="Score based on structural integrity (0-100)", ge=0.0, le=100.0)
    overall_score: float = Field(..., description="Weighted average quality score (0-100)", ge=0.0, le=100.0)
    quality_classification: str = Field(..., description="Enum classification: Excellent, Good, Fair, Poor")


class DatasetQualityCreate(DatasetQualityBase):
    """Schema for creating a dataset quality record."""
    
    dataset_id: str = Field(..., description="ID of the dataset")


class DatasetQualityResponse(DatasetQualityBase):
    """Schema for returning dataset quality via API."""

    model_config = ConfigDict(from_attributes=True)
    
    dataset_id: str = Field(..., description="ID of the dataset")
    created_at: datetime = Field(..., description="Timestamp of quality assessment")
    updated_at: datetime = Field(..., description="Timestamp of last update")
