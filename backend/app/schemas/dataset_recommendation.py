from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime

class DatasetRecommendationBase(BaseModel):
    recommendation_type: str
    severity: str
    priority_score: int
    status: str = "active"
    column_name: Optional[str] = None
    description: str
    suggested_action: str
    estimated_quality_gain: float
    algorithm_metadata: Optional[dict] = None
    prerequisites: Optional[List[str]] = None

class DatasetRecommendationCreate(DatasetRecommendationBase):
    dataset_id: str
    version_id: str
    version_number: int
    created_by: str

class DatasetRecommendationResponse(DatasetRecommendationBase):
    recommendation_id: str
    dataset_id: str
    version_id: str
    version_number: int
    created_at: datetime
    resolved_at: Optional[datetime] = None
    created_by: str
    
    model_config = ConfigDict(from_attributes=True)

class DatasetRecommendationListResponse(BaseModel):
    dataset_id: str
    version_id: str
    total_count: int
    active_count: int
    critical_count: int
    recommendations: List[DatasetRecommendationResponse]
    estimated_quality_after_all_fixes: float
    summary: str
