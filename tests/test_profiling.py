"""Dedicated unit tests for Phase 2.4 Data Profiling Engine & Persistence."""

from pathlib import Path

import pandas as pd
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.core.config import Settings
from backend.app.models.base import Base
from backend.app.models.dataset import Dataset
from backend.app.models.dataset_profile import DatasetProfile
from backend.app.repositories.dataset_profile_repository import DatasetProfileRepository
from backend.app.repositories.dataset_repository import DatasetRepository
from backend.app.services.data_profiling_service import DataProfilingService
from backend.app.services.metadata_extraction_service import MetadataExtractionService
from backend.app.services.profiling_service import ProfilingService
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
def profiling_service(
    metadata_service: MetadataExtractionService,
) -> DataProfilingService:
    return DataProfilingService(metadata_service=metadata_service)


def test_checklist_alias_compatibility(
    metadata_service: MetadataExtractionService,
) -> None:
    """Checklist alias ProfilingService is identical to DataProfilingService."""
    assert ProfilingService is DataProfilingService
    instance = ProfilingService(metadata_service=metadata_service)
    assert isinstance(instance, DataProfilingService)


def test_profiling_duplicates_and_missing(
    profiling_service: DataProfilingService, tmp_path: Path
) -> None:
    """Profile detects duplicate rows and missing cell distribution."""
    csv_file = tmp_path / "profile_test.csv"
    # 5 rows, row 1 and 2 are identical (1 duplicate)
    csv_file.write_text(
        "col1,col2,col3\n"
        "1,A,10.0\n"
        "1,A,10.0\n"
        "2,B,\n"
        "3,,30.0\n"
        "4,D,40.0\n"
    )

    profile = profiling_service.generate_profile("prof-ds-1", str(csv_file), "csv")

    assert profile.dataset_id == "prof-ds-1"
    assert profile.duplicate_rows == 1
    assert profile.duplicate_percentage == pytest.approx(1 / 5)

    # 2 null cells in total (col3 in row 3, col2 in row 4) out of 15 cells
    assert profile.missing_data_profile.null_count == 2
    assert profile.missing_data_profile.null_percentage == pytest.approx(2 / 15)
    assert set(profile.missing_data_profile.columns_with_missing) == {"col2", "col3"}


def test_profiling_numeric_statistics(
    profiling_service: DataProfilingService, tmp_path: Path
) -> None:
    """Profile calculates statistical moments and quantiles for numeric columns."""
    csv_file = tmp_path / "numeric_test.csv"
    csv_file.write_text(
        "val\n"
        "10\n"
        "20\n"
        "30\n"
        "40\n"
        "50\n"
    )

    profile = profiling_service.generate_profile("prof-ds-num", str(csv_file), "csv")

    num_stats = profile.numeric_columns_profile.get("val")
    assert num_stats is not None
    assert num_stats.mean == pytest.approx(30.0)
    assert num_stats.median == pytest.approx(30.0)
    assert num_stats.min == pytest.approx(10.0)
    assert num_stats.max == pytest.approx(50.0)
    assert num_stats.p25 == pytest.approx(20.0)
    assert num_stats.p75 == pytest.approx(40.0)


def test_dataset_profile_repository_crud(in_memory_db: Session) -> None:
    """DatasetProfileRepository can create, get, and delete profile records."""
    dataset_repo = DatasetRepository(db=in_memory_db)
    dataset = Dataset(
        dataset_id="prof-repo-ds",
        dataset_name="Profile Test",
        file_name="profile.csv",
        file_type="csv",
        file_path="/path/profile.csv",
        version=1,
        status="uploaded",
    )
    dataset_repo.create(dataset)

    profile_repo = DatasetProfileRepository(db=in_memory_db)
    profile_record = DatasetProfile(
        dataset_id="prof-repo-ds",
        duplicate_rows=3,
        duplicate_percentage=0.03,
        missing_data_profile={"null_count": 5, "null_percentage": 0.05, "columns_with_missing": ["age"]},
        cardinality_profile={"high_cardinality_columns": ["id"], "low_cardinality_columns": ["country"]},
        numeric_columns_profile={"score": {"mean": 85.0, "median": 86.0, "min": 60.0, "max": 100.0}},
    )

    created = profile_repo.create(profile_record)
    assert created.dataset_id == "prof-repo-ds"
    assert created.duplicate_rows == 3

    retrieved = profile_repo.get("prof-repo-ds")
    assert retrieved is not None
    assert retrieved.duplicate_percentage == pytest.approx(0.03)

    assert profile_repo.delete("prof-repo-ds") is True
    assert profile_repo.get("prof-repo-ds") is None
    assert profile_repo.delete("non-existent") is False
