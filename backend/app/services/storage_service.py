"""Enterprise Data Lake Storage Service (Phase 18.6.1).

Manages domain-partitioned file persistence, automated directory creation,
storage health checks, data integrity validation, and lifecycle operations across:
- raw (partitioned by csv, excel, json, pdf, parquet)
- canonical (standardized JSON artifacts)
- processed (cleaned & imputed datasets)
- profiles (EDA and statistical profiles)
- quality (data quality reports)
- embeddings (vector metadata & evaluations)
- reports (generated analytical reports)
- forecasts (prediction outputs & evaluations)
- lineage (provenance graphs & dataset history)
- archives (soft-deleted dataset artifacts for disaster recovery)
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import shutil
from pathlib import Path
from typing import Any
from uuid import uuid4

import pandas as pd
from fastapi import Depends, UploadFile

from backend.app.core.config import Settings, get_settings
from backend.app.core.exceptions import (
    FileSizeExceededError,
    StorageFileNotFoundError,
    UnsupportedFileTypeError,
)

logger = logging.getLogger(__name__)


class StorageService:
    """Service managing enterprise data lake storage domains, persistence, and lifecycle."""

    SUPPORTED_EXTENSIONS: set[str] = {".csv", ".xlsx", ".xls", ".json", ".pdf", ".parquet"}

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.upload_dir: Path = settings.upload_path

        # ------------------------------------------------------------------
        # Enterprise Data Lake Storage Domains
        # ------------------------------------------------------------------
        self.raw_dir: Path = self.upload_dir / "raw"
        self.raw_csv_dir: Path = self.raw_dir / "csv"
        self.raw_excel_dir: Path = self.raw_dir / "excel"
        self.raw_json_dir: Path = self.raw_dir / "json"
        self.raw_pdf_dir: Path = self.raw_dir / "pdf"
        self.raw_parquet_dir: Path = self.raw_dir / "parquet"

        self.canonical_dir: Path = self.upload_dir / "canonical"
        self.processed_dir: Path = self.upload_dir / "processed"
        self.profiles_dir: Path = self.upload_dir / "profiles"
        self.quality_dir: Path = self.upload_dir / "quality"
        self.embeddings_dir: Path = self.upload_dir / "embeddings"
        self.reports_dir: Path = self.upload_dir / "reports"
        self.forecasts_dir: Path = self.upload_dir / "forecasts"
        self.lineage_dir: Path = self.upload_dir / "lineage"
        self.archives_dir: Path = self.upload_dir / "archives"

        # Backward compatibility directory references
        self.datasets_dir: Path = self.upload_dir / "datasets"
        self.vectorized_dir: Path = self.upload_dir / "vectorized"

        # Automated directory initialization
        self.ensure_lake_directories()

    def ensure_lake_directories(self) -> None:
        """Create all enterprise data lake domains automatically."""
        domains = (
            self.raw_dir,
            self.raw_csv_dir,
            self.raw_excel_dir,
            self.raw_json_dir,
            self.raw_pdf_dir,
            self.raw_parquet_dir,
            self.canonical_dir,
            self.processed_dir,
            self.profiles_dir,
            self.quality_dir,
            self.embeddings_dir,
            self.reports_dir,
            self.forecasts_dir,
            self.lineage_dir,
            self.archives_dir,
            self.datasets_dir,
            self.vectorized_dir,
        )
        for directory in domains:
            directory.mkdir(parents=True, exist_ok=True)

    def get_raw_type_dir(self, file_type: str) -> Path:
        """Resolve specific raw storage domain by format."""
        norm_type = file_type.lower().lstrip(".")
        if norm_type in ("csv",):
            return self.raw_csv_dir
        elif norm_type in ("xlsx", "xls", "excel"):
            return self.raw_excel_dir
        elif norm_type in ("json",):
            return self.raw_json_dir
        elif norm_type in ("pdf",):
            return self.raw_pdf_dir
        elif norm_type in ("parquet",):
            return self.raw_parquet_dir
        return self.raw_dir

    async def save_file(
        self, upload: UploadFile, custom_filename: str | None = None
    ) -> tuple[str, str, str, str, int]:
        """Save an uploaded file to storage.

        Validates file extension against supported types (csv, xlsx, json, pdf, parquet).
        Partitions raw storage into format domains.

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

        clean_basename = Path(original_name).name
        type_dir = self.get_raw_type_dir(file_type)

        # Store in partitioned domain: storage/raw/{file_type}/{dataset_id}_{original_name}
        partitioned_path = type_dir / f"{dataset_id}_{clean_basename}"
        # Also store in storage/raw for backward compatibility
        raw_target_path = self.raw_dir / f"{dataset_id}_{clean_basename}"
        # Maintain isolated dataset directory for backward compatibility
        isolated_path = self.dataset_directory(dataset_id) / "original" / clean_basename
        isolated_path.parent.mkdir(parents=True, exist_ok=True)

        size_bytes = 0
        max_bytes = self.settings.max_file_size_mb * 1024 * 1024

        try:
            with partitioned_path.open("wb") as part_dest, raw_target_path.open("wb") as raw_dest, isolated_path.open("wb") as iso_dest:
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
                    part_dest.write(chunk)
                    raw_dest.write(chunk)
                    iso_dest.write(chunk)
        except Exception:
            partitioned_path.unlink(missing_ok=True)
            raw_target_path.unlink(missing_ok=True)
            isolated_path.unlink(missing_ok=True)
            raise

        relative_file_path = str(partitioned_path)
        logger.info(
            "Saved dataset file dataset_id=%s file_name=%s file_type=%s size_bytes=%d path=%s",
            dataset_id,
            file_name,
            file_type,
            size_bytes,
            relative_file_path,
        )
        return dataset_id, file_name, file_type, relative_file_path, size_bytes

    # -------------------------------------------------------------------------
    # Domain-Specific Persistence Helpers
    # -------------------------------------------------------------------------

    def save_canonical(self, dataset_id: str, data: Any) -> Path:
        """Save standardized canonical dataset artifact."""
        target_path = self.canonical_dir / f"{dataset_id}.json"
        text_data = json.dumps(data, ensure_ascii=False, indent=2, default=str) if not isinstance(data, str) else data
        target_path.write_text(text_data, encoding="utf-8")
        return target_path

    def save_processed(self, dataset_id: str, data: Any) -> Path:
        """Save cleaned / imputed processed dataset artifact."""
        target_path = self.processed_dir / f"{dataset_id}.json"
        text_data = json.dumps(data, ensure_ascii=False, indent=2, default=str) if not isinstance(data, str) else data
        target_path.write_text(text_data, encoding="utf-8")
        return target_path

    def save_profile(self, dataset_id: str, profile_data: dict[str, Any]) -> Path:
        """Save dataset statistical profile."""
        target_path = self.profiles_dir / f"{dataset_id}.json"
        target_path.write_text(json.dumps(profile_data, indent=2, default=str), encoding="utf-8")
        return target_path

    def save_quality(self, dataset_id: str, quality_data: dict[str, Any]) -> Path:
        """Save data quality evaluation report."""
        target_path = self.quality_dir / f"{dataset_id}.json"
        target_path.write_text(json.dumps(quality_data, indent=2, default=str), encoding="utf-8")
        return target_path

    def save_forecast(self, dataset_id: str, forecast_data: dict[str, Any]) -> Path:
        """Save forecasting results and validation metrics."""
        target_path = self.forecasts_dir / f"{dataset_id}.json"
        target_path.write_text(json.dumps(forecast_data, indent=2, default=str), encoding="utf-8")
        return target_path

    def save_lineage(self, dataset_id: str, lineage_data: dict[str, Any]) -> Path:
        """Save dataset provenance and transformation lineage graph."""
        target_path = self.lineage_dir / f"{dataset_id}.json"
        target_path.write_text(json.dumps(lineage_data, indent=2, default=str), encoding="utf-8")
        return target_path

    def save_embedding_metadata(self, dataset_id: str, metadata: dict[str, Any]) -> Path:
        """Save embedding registry and RAG evaluation metadata."""
        target_path = self.embeddings_dir / f"{dataset_id}.json"
        target_path.write_text(json.dumps(metadata, indent=2, default=str), encoding="utf-8")
        return target_path

    def save_report(self, report_id: str, report_data: dict[str, Any]) -> Path:
        """Save executive report artifact."""
        target_path = self.reports_dir / f"{report_id}.json"
        target_path.write_text(json.dumps(report_data, indent=2, default=str), encoding="utf-8")
        return target_path

    def save_archive(self, dataset_id: str, archive_data: dict[str, Any]) -> Path:
        """Save archive manifest for a soft-deleted dataset."""
        archive_dir = self.archives_dir / dataset_id
        archive_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = archive_dir / "manifest.json"
        manifest_path.write_text(json.dumps(archive_data, indent=2, default=str), encoding="utf-8")
        return manifest_path

    def get_canonical(self, dataset_id: str) -> Any | None:
        """Retrieve standardized canonical dataset artifact if it exists."""
        target_path = self.canonical_dir / f"{dataset_id}.json"
        if not target_path.exists():
            return None
        try:
            return json.loads(target_path.read_text(encoding="utf-8"))
        except Exception:
            return None

    def get_processed(self, dataset_id: str) -> Any | None:
        """Retrieve processed dataset artifact if it exists."""
        target_path = self.processed_dir / f"{dataset_id}.json"
        if not target_path.exists():
            return None
        try:
            return json.loads(target_path.read_text(encoding="utf-8"))
        except Exception:
            return None

    def get_profile(self, dataset_id: str) -> Any | None:
        """Retrieve dataset statistical profile if it exists."""
        target_path = self.profiles_dir / f"{dataset_id}.json"
        if not target_path.exists():
            return None
        try:
            return json.loads(target_path.read_text(encoding="utf-8"))
        except Exception:
            return None

    def get_quality(self, dataset_id: str) -> Any | None:
        """Retrieve dataset quality report if it exists."""
        target_path = self.quality_dir / f"{dataset_id}.json"
        if not target_path.exists():
            return None
        try:
            return json.loads(target_path.read_text(encoding="utf-8"))
        except Exception:
            return None

    def get_forecast(self, dataset_id: str) -> Any | None:
        """Retrieve forecast artifact if it exists."""
        target_path = self.forecasts_dir / f"{dataset_id}.json"
        if not target_path.exists():
            return None
        try:
            return json.loads(target_path.read_text(encoding="utf-8"))
        except Exception:
            return None

    def get_lineage(self, dataset_id: str) -> Any | None:
        """Retrieve dataset lineage if it exists."""
        target_path = self.lineage_dir / f"{dataset_id}.json"
        if not target_path.exists():
            return None
        try:
            return json.loads(target_path.read_text(encoding="utf-8"))
        except Exception:
            return None

    # -------------------------------------------------------------------------
    # Validation & Health Checks
    # -------------------------------------------------------------------------

    def validate_storage_health(self) -> dict[str, Any]:
        """Verify storage domains, permissions, and disk availability."""
        health: dict[str, Any] = {
            "status": "healthy",
            "root_path": str(self.upload_dir),
            "domains": {},
            "free_space_mb": 0.0,
            "total_space_mb": 0.0,
        }

        domains = {
            "raw": self.raw_dir,
            "canonical": self.canonical_dir,
            "processed": self.processed_dir,
            "profiles": self.profiles_dir,
            "quality": self.quality_dir,
            "embeddings": self.embeddings_dir,
            "reports": self.reports_dir,
            "forecasts": self.forecasts_dir,
            "lineage": self.lineage_dir,
            "archives": self.archives_dir,
        }

        all_healthy = True
        for name, p in domains.items():
            accessible = p.exists() and os.access(p, os.W_OK)
            health["domains"][name] = {
                "path": str(p),
                "accessible": accessible,
                "file_count": len(list(p.glob("*"))) if p.exists() else 0,
            }
            if not accessible:
                all_healthy = False

        try:
            usage = shutil.disk_usage(self.upload_dir)
            health["free_space_mb"] = round(usage.free / (1024 * 1024), 2)
            health["total_space_mb"] = round(usage.total / (1024 * 1024), 2)
        except Exception:
            pass

        health["status"] = "healthy" if all_healthy else "degraded"
        health["writable"] = all_healthy
        health["total_domains"] = len(domains)
        return health

    @staticmethod
    def calculate_checksum(file_path: Path) -> str:
        """Compute SHA-256 checksum of a file for integrity verification."""
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(65536):
                sha256.update(chunk)
        return sha256.hexdigest()

    # -------------------------------------------------------------------------
    # Retrieval and Deletion
    # -------------------------------------------------------------------------

    def dataset_directory(self, dataset_id: str) -> Path:
        """Return the isolated artifact directory for one validated dataset ID."""
        if not dataset_id or any(char not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for char in dataset_id):
            raise ValueError("Invalid dataset identifier")
        return self.datasets_dir / dataset_id

    def archive_dataset(self, dataset_id: str, reason: str = "deleted") -> bool:
        """Move all domain artifacts into archives/dataset_id/ for soft-delete recovery."""
        import time
        archive_dir = self.archives_dir / dataset_id
        archive_dir.mkdir(parents=True, exist_ok=True)

        moved_files: list[str] = []

        # Archive domain artifact files
        domain_files = [
            self.canonical_dir / f"{dataset_id}.json",
            self.processed_dir / f"{dataset_id}.json",
            self.profiles_dir / f"{dataset_id}.json",
            self.quality_dir / f"{dataset_id}.json",
            self.forecasts_dir / f"{dataset_id}.json",
            self.lineage_dir / f"{dataset_id}.json",
            self.embeddings_dir / f"{dataset_id}.json",
        ]
        for src in domain_files:
            if src.exists():
                dest = archive_dir / src.name
                shutil.copy2(src, dest)
                moved_files.append(src.name)

        # Archive raw files
        for raw_p in self.raw_dir.rglob(f"{dataset_id}_*"):
            dest = archive_dir / raw_p.name
            shutil.copy2(raw_p, dest)
            moved_files.append(raw_p.name)

        # Write archive manifest
        manifest = {
            "dataset_id": dataset_id,
            "archived_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "reason": reason,
            "archived_files": moved_files,
            "archive_path": str(archive_dir),
        }
        (archive_dir / "manifest.json").write_text(
            json.dumps(manifest, indent=2), encoding="utf-8"
        )
        logger.info("Archived dataset artifacts dataset_id=%s files=%d", dataset_id, len(moved_files))
        return len(moved_files) > 0

    def restore_from_archive(self, dataset_id: str) -> bool:
        """Restore archived dataset artifacts back to their original domains."""
        archive_dir = self.archives_dir / dataset_id
        if not archive_dir.exists():
            logger.warning("Archive not found for dataset_id=%s", dataset_id)
            return False

        domain_map = {
            f"{dataset_id}.json": {
                "canonical": self.canonical_dir,
                "processed": self.processed_dir,
                "profiles": self.profiles_dir,
                "quality": self.quality_dir,
                "forecasts": self.forecasts_dir,
                "lineage": self.lineage_dir,
                "embeddings": self.embeddings_dir,
            }
        }

        restored = 0
        for archived_file in archive_dir.iterdir():
            if archived_file.name == "manifest.json":
                continue
            if archived_file.suffix == ".json" and archived_file.stem == dataset_id:
                # Restore to all domain dirs that the file might belong to
                # (we use the canonical dir as the primary restore target)
                dest = self.canonical_dir / archived_file.name
                if not dest.exists():
                    shutil.copy2(archived_file, dest)
                    restored += 1

        logger.info("Restored dataset artifacts dataset_id=%s count=%d", dataset_id, restored)
        return restored > 0

    def delete_dataset(self, dataset_id: str) -> bool:
        """Archive then clean up all data lake artifacts belonging to a dataset across all domains."""
        deleted = False

        # 0. Archive first (soft-delete for disaster recovery)
        self.archive_dataset(dataset_id, reason="deleted")

        # 1. Isolated dataset folder
        directory = self.dataset_directory(dataset_id)
        if directory.exists():
            shutil.rmtree(directory)
            deleted = True

        # 2. Raw files across all subdomains
        for raw_p in self.raw_dir.rglob(f"{dataset_id}_*"):
            raw_p.unlink(missing_ok=True)
            deleted = True

        # 3. Domain artifacts
        domain_files = [
            self.canonical_dir / f"{dataset_id}.json",
            self.processed_dir / f"{dataset_id}.json",
            self.profiles_dir / f"{dataset_id}.json",
            self.quality_dir / f"{dataset_id}.json",
            self.forecasts_dir / f"{dataset_id}.json",
            self.lineage_dir / f"{dataset_id}.json",
            self.embeddings_dir / f"{dataset_id}.json",
        ]
        for f in domain_files:
            if f.exists():
                f.unlink(missing_ok=True)
                deleted = True

        logger.info("Deleted enterprise dataset storage artifacts dataset_id=%s", dataset_id)
        return deleted

    def retrieve_file(self, file_path: str | Path) -> Path:
        """Retrieve a stored dataset file by path or relative filename."""
        path = Path(file_path)
        if not path.is_absolute():
            path = self.upload_dir / path

        if path.exists() and path.is_file():
            logger.debug("Retrieved dataset file path=%s", path)
            return path

        # Check raw directory and type subdirectories
        filename = Path(file_path).name
        candidates = [
            self.raw_dir / filename,
            self.raw_csv_dir / filename,
            self.raw_excel_dir / filename,
            self.raw_json_dir / filename,
            self.raw_pdf_dir / filename,
            self.canonical_dir / filename,
            self.processed_dir / filename,
        ]
        for c in candidates:
            if c.exists() and c.is_file():
                logger.debug("Retrieved dataset file from domain storage path=%s", c)
                return c

        logger.warning("Requested dataset file not found at path=%s", path)
        raise StorageFileNotFoundError(f"Dataset file not found at path: {file_path}")

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


__all__ = ["StorageService", "get_storage_service"]
