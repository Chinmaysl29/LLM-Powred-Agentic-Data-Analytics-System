"""Dedicated unit tests for Phase 2.5 Data Quality Assessment & Persistence."""

from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.core.config import Settings
from backend.app.models.base import Base
from backend.app.models.dataset import Dataset
from backend.app.models.dataset_quality import DatasetQuality
from backend.app.repositories.dataset_profile_repository import DatasetProfileRepository
from backend.app.repositories.dataset_quality_repository import DatasetQualityRepository
from backend.app.repositories.dataset_repository import DatasetRepository
from backend.app.services.data_profiling_service import DataProfilingService
from backend.app.services.data_quality_service import DataQualityService
from backend.app.services.metadata_extraction_service import MetadataExtractionService
from backend.app.services.quality_service import QualityService
from backend.app.services.storage_service import StorageService


@pytest.fixture
def in_memory_db() -> Session:
    """Isolated in-memory SQLite database for testing."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def storage_service(tmp_path: Path) -> StorageService:
    settings = Settings(_env_file=None, upload_dir=str(tmp_path), max_file_size_mb=10)
    return StorageService(settings=settings)


@pytest.fixture
def metadata_service(storage_service: StorageService) -> MetadataExtractionService:
    return MetadataExtractionService(storage_service=storage_service)


@pytest.fixture
def quality_service(
    in_memory_db: Session, metadata_service: MetadataExtractionService
) -> DataQualityService:
    return DataQualityService(
        dataset_repository=DatasetRepository(db=in_memory_db),
        dataset_profile_repository=DatasetProfileRepository(db=in_memory_db),
        metadata_service=metadata_service,
    )


def test_checklist_alias_compatibility(
    in_memory_db: Session, metadata_service: MetadataExtractionService
) -> None:
    """Checklist alias QualityService is identical to DataQualityService."""
    assert QualityService is DataQualityService
    instance = QualityService(
        dataset_repository=DatasetRepository(db=in_memory_db),
        dataset_profile_repository=DatasetProfileRepository(db=in_memory_db),
        metadata_service=metadata_service,
    )
    assert isinstance(instance, DataQualityService)


def test_quality_assessment_clean_dataset(
    quality_service: DataQualityService,
    metadata_service: MetadataExtractionService,
    tmp_path: Path,
) -> None:
    """Clean dataset with no missing values or duplicates scores high."""
    csv_file = tmp_path / "clean.csv"
    csv_file.write_text(
        "id,name,value\n"
        "1,Alice,100\n"
        "2,Bob,200\n"
        "3,Charlie,300\n"
    )

    profiling_service = DataProfilingService(metadata_service=metadata_service)
    profile = profiling_service.generate_profile("clean-ds", str(csv_file), "csv")

    quality = quality_service.assess_quality(
        dataset_id="clean-ds",
        file_path=str(csv_file),
        file_type="csv",
        profile=profile,
    )

    assert quality.dataset_id == "clean-ds"
    assert quality.completeness_score == 100.0
    assert quality.uniqueness_score == 100.0
    assert quality.overall_score >= 80.0
    assert quality.quality_classification in {"Excellent", "Good"}


def test_quality_assessment_degraded_dataset(
    quality_service: DataQualityService,
    metadata_service: MetadataExtractionService,
    tmp_path: Path,
) -> None:
    """Dataset with many missing values and duplicates receives degraded score."""
    csv_file = tmp_path / "dirty.csv"
    # Duplicate rows and empty values
    csv_file.write_text(
        "id,name,value\n"
        "1,,100\n"
        "1,,100\n"
        ",,\n"
        "2,,\n"
    )

    profiling_service = DataProfilingService(metadata_service=metadata_service)
    profile = profiling_service.generate_profile("dirty-ds", str(csv_file), "csv")

    quality = quality_service.assess_quality(
        dataset_id="dirty-ds",
        file_path=str(csv_file),
        file_type="csv",
        profile=profile,
    )

    assert quality.completeness_score < 100.0
    assert quality.uniqueness_score < 100.0
    assert quality.overall_score < 80.0


def test_dataset_quality_repository_crud(in_memory_db: Session) -> None:
    """DatasetQualityRepository can create and retrieve quality records."""
    dataset_repo = DatasetRepository(db=in_memory_db)
    dataset = Dataset(
        dataset_id="quality-repo-ds",
        dataset_name="Quality Test",
        file_name="quality.csv",
        file_type="csv",
        file_path="/path/quality.csv",
        version=1,
        status="uploaded",
    )
    dataset_repo.create(dataset)

    quality_repo = DatasetQualityRepository(db=in_memory_db)
    quality_record = DatasetQuality(
        dataset_id="quality-repo-ds",
        completeness_score=92.5,
        uniqueness_score=98.0,
        consistency_score=90.0,
        validity_score=85.0,
        integrity_score=95.0,
        overall_score=92.1,
        quality_classification="Excellent",
    )

    created = quality_repo.create(quality_record)
    assert created.dataset_id == "quality-repo-ds"
    assert created.overall_score == 92.1

    retrieved = quality_repo.get("quality-repo-ds")
    assert retrieved is not None
    assert retrieved.quality_classification == "Excellent"
    assert retrieved.completeness_score == 92.5
