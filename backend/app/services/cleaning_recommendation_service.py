"""Checklist proxy for DataCleaningRecommendationService."""

from backend.app.services.data_cleaning_recommendation_service import (
    DataCleaningRecommendationService,
    get_data_cleaning_recommendation_service,
)

CleaningRecommendationService = DataCleaningRecommendationService
get_cleaning_recommendation_service = get_data_cleaning_recommendation_service

__all__ = [
    "CleaningRecommendationService",
    "DataCleaningRecommendationService",
    "get_cleaning_recommendation_service",
    "get_data_cleaning_recommendation_service",
]
