"""Checklist proxy for DataQualityService."""

from backend.app.services.data_quality_service import (
    DataQualityService,
    QualityAssessmentError,
    get_data_quality_service,
)

QualityService = DataQualityService
get_quality_service = get_data_quality_service

__all__ = [
    "DataQualityService",
    "QualityAssessmentError",
    "QualityService",
    "get_data_quality_service",
    "get_quality_service",
]
