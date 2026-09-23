"""Checklist proxy for DatasetVersionRepository."""

from backend.app.repositories.dataset_version_repository import (
    DatasetVersionRepository,
    get_dataset_version_repository,
)

VersionRepository = DatasetVersionRepository
get_version_repository = get_dataset_version_repository

__all__ = [
    "DatasetVersionRepository",
    "VersionRepository",
    "get_dataset_version_repository",
    "get_version_repository",
]
