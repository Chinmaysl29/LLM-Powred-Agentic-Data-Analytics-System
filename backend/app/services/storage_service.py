"""Dataset storage service handling file system operations for uploaded datasets."""

import logging
import shutil
from pathlib import Path
from uuid import uuid4

from fastapi import Depends, UploadFile

from backend.app.core.config import Settings, get_settings
from backend.app.core.exceptions import (
    FileSizeExceededError,
    StorageFileNotFoundError,
    UnsupportedFileTypeError,
)

logger = logging.getLogger(__name__)


class StorageService:
    """Service managing file persistence, retrieval, and deletion on local storage."""

    SUPPORTED_EXTENSIONS: set[str] = {".csv", ".xlsx", ".xls", ".json", ".pdf"}

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.upload_dir: Path = settings.upload_path

    async def save_file(
        self, upload: UploadFile, custom_filename: str | None = None
    ) -> tuple[str, str, str, str, int]:
        """Save an uploaded file to storage.

        Validates file extension against supported types (csv, xlsx, json).

        Returns:
            Tuple of (dataset_id, file_name, file_type, file_path, size_bytes)
        """
        original_name = upload.filename or "dataset"
        suffix = Path(original_name).suffix.lower()

        if suffix not in self.SUPPORTED_EXTENSIONS:
            logger.warning("Rejected upload with unsupported file type: %s", suffix)
            raise UnsupportedFileTypeError(
                f"Unsupported file type '{suffix or 'missing extension'}'. "
                f"Supported types are: {', '.join(sorted(ext.lstrip('.') for ext in self.SUPPORTED_EXTENSIONS))}"
            )

        dataset_id = str(uuid4())
        file_name = custom_filename or original_name
        file_type = suffix.lstrip(".")
        target_path = self.dataset_directory(dataset_id) / "original" / Path(original_name).name
        target_path.parent.mkdir(parents=True, exist_ok=True)

        size_bytes = 0
        max_bytes = self.settings.max_file_size_mb * 1024 * 1024

        try:
            with target_path.open("wb") as destination:
                while chunk := await upload.read(1024 * 1024):
                    size_bytes += len(chunk)
                    if size_bytes > max_bytes:
                        logger.warning(
                            "Upload exceeded size limit size_bytes=%d max_bytes=%d",
                            size_bytes,
                            max_bytes,
                        )
                        raise FileSizeExceededError(
                            f"Uploaded file exceeds the maximum allowed size of {self.settings.max_file_size_mb} MB"
                        )
                    destination.write(chunk)
        except Exception:
            target_path.unlink(missing_ok=True)
            raise

        relative_file_path = str(target_path)
        logger.info(
            "Saved dataset file dataset_id=%s file_name=%s file_type=%s size_bytes=%d path=%s",
            dataset_id,
            file_name,
            file_type,
            size_bytes,
            relative_file_path,
        )

        return dataset_id, file_name, file_type, relative_file_path, size_bytes

    def dataset_directory(self, dataset_id: str) -> Path:
        """Return the isolated artifact directory for one validated dataset ID."""
        if not dataset_id or any(char not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-" for char in dataset_id):
            raise ValueError("Invalid dataset identifier")
        return self.upload_dir / "datasets" / dataset_id

    def delete_dataset(self, dataset_id: str) -> bool:
        directory = self.dataset_directory(dataset_id)
        if not directory.exists():
            return False
        shutil.rmtree(directory)
        logger.info("Deleted dataset artifact directory dataset_id=%s", dataset_id)
        return True

    def retrieve_file(self, file_path: str | Path) -> Path:
        """Retrieve a stored dataset file by path.

        Raises FileNotFoundError if the file does not exist on disk.
        """
        path = Path(file_path)
        if not path.is_absolute():
            path = self.upload_dir / path

        if not path.exists() or not path.is_file():
            logger.warning("Requested dataset file not found at path=%s", path)
            raise StorageFileNotFoundError(f"Dataset file not found at path: {file_path}")

        logger.debug("Retrieved dataset file path=%s", path)
        return path

    def delete_file(self, file_path: str | Path) -> bool:
        """Delete a stored dataset file from disk."""
        path = Path(file_path)
        if not path.is_absolute():
            path = self.upload_dir / path

        if path.exists() and path.is_file():
            path.unlink(missing_ok=True)
            logger.info("Deleted dataset file path=%s", path)
            return True

        logger.warning("Dataset file to delete not found at path=%s", path)
        return False


def get_storage_service(settings: Settings = Depends(get_settings)) -> StorageService:
    """FastAPI dependency yielding a configured StorageService instance."""
    return StorageService(settings=settings)
