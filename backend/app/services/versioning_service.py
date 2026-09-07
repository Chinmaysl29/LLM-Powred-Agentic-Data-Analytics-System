"""Checklist proxy for DatasetVersioningService."""

from backend.app.services.dataset_versioning_service import (
    DatasetVersioningService,
    DuplicateVersionError,
    VersioningError,
    VersionNotFoundError,
    get_dataset_versioning_service,
)

VersioningService = DatasetVersioningService
get_versioning_service = get_dataset_versioning_service

__all__ = [
    "DatasetVersioningService",
    "DuplicateVersionError",
    "VersioningError",
    "VersioningService",
    "VersionNotFoundError",
    "get_dataset_versioning_service",
    "get_versioning_service",
]
