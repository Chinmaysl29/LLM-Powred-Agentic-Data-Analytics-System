"""Dataset service wrapper for backward compatibility."""

from fastapi import UploadFile

from backend.app.core.config import get_settings
from backend.app.services.storage_service import StorageService


async def save_dataset(upload: UploadFile) -> dict:
    """Save an uploaded dataset file using StorageService."""
    settings = get_settings()
    service = StorageService(settings)
    dataset_id, file_name, file_type, file_path, size_bytes = await service.save_file(upload)
    return {
        "dataset_id": dataset_id,
        "dataset_name": file_name,
        "file_name": file_name,
        "file_type": file_type,
        "file_path": file_path,
        "version": 1,
        "status": "uploaded",
    }
