"""Dedicated unit tests for Phase 2.6 Dataset Versioning System & Persistence."""

from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.core.exceptions import VersionNotFoundError
from backend.app.models.base import Base
from backend.app.models.dataset import Dataset
from backend.app.models.dataset_version import DatasetVersion
from backend.app.repositories.dataset_repository import DatasetRepository
from backend.app.repositories.dataset_version_repository import DatasetVersionRepository
from backend.app.repositories.version_repository import VersionRepository
from backend.app.schemas.dataset_metadata import DatasetMetadataCreate, DatasetClassification
from backend.app.schemas.dataset_quality import DatasetQualityCreate
from backend.app.services.dataset_versioning_service import DatasetVersioningService
from backend.app.services.versioning_service import VersioningService


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
def versioning_service(in_memory_db: Session) -> DatasetVersioningService:
    return DatasetVersioningService(
        dataset_repository=DatasetRepository(db=in_memory_db),
        dataset_version_repository=DatasetVersionRepository(db=in_memory_db),
    )


def test_checklist_alias_compatibility(in_memory_db: Session) -> None:
    """Checklist aliases VersioningService and VersionRepository match their implementations."""
    assert VersioningService is DatasetVersioningService
    assert VersionRepository is DatasetVersionRepository


def test_create_initial_version_and_rollback(
    versioning_service: DatasetVersioningService,
    in_memory_db: Session,
    tmp_path: Path,
) -> None:
    """Create initial version v1, then create v2 and test rollback to v1."""
    # 1. Setup Dataset
    dataset_repo = DatasetRepository(db=in_memory_db)
    file_v1 = tmp_path / "v1.csv"
    file_v1.write_text("a,b\n1,2\n")

    dataset = Dataset(
        dataset_id="ver-ds-1",
        dataset_name="Version Test",
        file_name="v1.csv",
        file_type="csv",
        file_path=str(file_v1),
        version=1,
        status="uploaded",
    )
    dataset_repo.create(dataset)

    meta = DatasetMetadataCreate(
        dataset_id="ver-ds-1",
        row_count=1,
        column_count=2,
        column_names=["a", "b"],
        column_types={"a": "int64", "b": "int64"},
        columns_metadata=[],
        classifications=DatasetClassification(numeric=["a", "b"], categorical=[], datetime=[], boolean=[]),
    )
    quality = DatasetQualityCreate(
        dataset_id="ver-ds-1",
        completeness_score=100.0,
        uniqueness_score=100.0,
        consistency_score=100.0,
        validity_score=100.0,
        integrity_score=100.0,
        overall_score=100.0,
        quality_classification="Excellent",
    )

    # 2. Initial Version
    v1 = versioning_service.create_initial_version(
        dataset_id="ver-ds-1",
        file_path=str(file_v1),
        metadata=meta,
        quality=quality,
        created_by="tester",
    )

    assert v1.version_number == 1
    assert v1.is_active is True
    assert v1.parent_version_id is None

    # 3. Create v2
    file_v2 = tmp_path / "v2.csv"
    file_v2.write_text("a,b,c\n1,2,3\n4,5,6\n")

    meta_v2 = DatasetMetadataCreate(
        dataset_id="ver-ds-1",
        row_count=2,
        column_count=3,
        column_names=["a", "b", "c"],
        column_types={"a": "int64", "b": "int64", "c": "int64"},
        columns_metadata=[],
        classifications=DatasetClassification(numeric=["a", "b", "c"], categorical=[], datetime=[], boolean=[]),
    )

    v2 = versioning_service.create_new_version(
        dataset_id="ver-ds-1",
        parent_version_number=1,
        file_path=str(file_v2),
        change_type="add_column",
        transformation_metadata={"action": "added col c"},
        metadata=meta_v2,
        quality=quality,
        created_by="tester",
    )

    assert v2.version_number == 2
    assert v2.parent_version_id == v1.version_id

    # 4. Compare v1 and v2
    diff = versioning_service.compare_versions("ver-ds-1", 1, 2)
    assert diff.rows_added == 1
    assert diff.rows_removed == 0
    assert "c" in diff.columns_added

    # 5. Rollback to v1
    rolled_back = versioning_service.rollback_version("ver-ds-1", 1)
    assert rolled_back.version_number == 1
    assert rolled_back.is_active is True

    # 6. Lineage Chain
    lineage = versioning_service.get_version_lineage("ver-ds-1", 2)
    assert len(lineage) == 2
    assert lineage[0].version_number == 2
    assert lineage[1].version_number == 1


def test_versioning_nonexistent_dataset(
    versioning_service: DatasetVersioningService, tmp_path: Path
) -> None:
    """Attempting to create version for non-existent dataset raises VersionNotFoundError."""
    dummy_file = tmp_path / "dummy.csv"
    dummy_file.write_text("a\n1")

    with pytest.raises((VersionNotFoundError, ValueError)):
        versioning_service.create_initial_version(
            dataset_id="missing-ds",
            file_path=str(dummy_file),
            metadata={"row_count": 1},
            quality={"overall_score": 90.0},
            created_by="test",
        )
