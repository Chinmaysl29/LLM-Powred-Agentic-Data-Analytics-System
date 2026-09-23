"""Checklist proxy for DatasetRecommendationRepository."""

from backend.app.repositories.dataset_recommendation_repository import (
    DatasetRecommendationRepository,
    get_dataset_recommendation_repository,
)

RecommendationRepository = DatasetRecommendationRepository
get_recommendation_repository = get_dataset_recommendation_repository

__all__ = [
    "DatasetRecommendationRepository",
    "RecommendationRepository",
    "get_dataset_recommendation_repository",
    "get_recommendation_repository",
]
