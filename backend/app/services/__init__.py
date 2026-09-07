"""Application service layer."""

from backend.app.services.storage_service import StorageService, get_storage_service

__all__ = ["StorageService", "get_storage_service"]
