"""Checklist proxy for MetadataExtractionService."""

from backend.app.services.metadata_extraction_service import (
    MetadataExtractionService,
    get_metadata_extraction_service,
)

MetadataService = MetadataExtractionService
get_metadata_service = get_metadata_extraction_service

__all__ = [
    "MetadataExtractionService",
    "MetadataService",
    "get_metadata_extraction_service",
    "get_metadata_service",
]
