from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, Text, Index, CheckConstraint
from sqlalchemy.dialects.postgresql import JSON
import uuid
from datetime import datetime, UTC

from backend.app.models.base import Base

class DatasetRecommendation(Base):
    __tablename__ = "cleaning_recommendations"

    recommendation_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    dataset_id = Column(String(36), ForeignKey("datasets.dataset_id", ondelete="CASCADE"), nullable=False)
    version_id = Column(String(36), ForeignKey("dataset_versions.version_id", ondelete="CASCADE"), nullable=False)
    version_number = Column(Integer, nullable=False)
    
    # ENUM: 'missing_values', 'duplicates', 'type_conversion', 'outliers', 'consistency', 'quality_improvement'
    recommendation_type = Column(String, nullable=False)
    
    # ENUM: 'critical', 'high', 'medium', 'low'
    severity = Column(String, nullable=False)
    
    priority_score = Column(Integer, nullable=False)
    
    # ENUM: 'active', 'resolved', 'deprecated'
    status = Column(String, default="active", nullable=False)
    
    column_name = Column(String, nullable=True)
    description = Column(Text, nullable=False)
    suggested_action = Column(Text, nullable=False)
    
    estimated_quality_gain = Column(Float, nullable=False, default=0.0)
    algorithm_metadata = Column(JSON, nullable=True)
    prerequisites = Column(JSON, nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    created_by = Column(String, nullable=False)

    __table_args__ = (
        Index("ix_recommendations_dataset_version", "dataset_id", "version_id"),
        Index(
            "ix_recommendations_active",
            "dataset_id", "status",
            postgresql_where=(status == 'active')
        ),
        Index("ix_recommendations_priority", priority_score.desc()),
        CheckConstraint("priority_score >= 0 AND priority_score <= 100", name="chk_priority_score_range")
    )
