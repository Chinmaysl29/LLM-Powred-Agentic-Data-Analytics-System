"""Dedicated unit tests for Phase 2.7 Cleaning Recommendations & Persistence."""

from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.models.base import Base
from backend.app.models.dataset import Dataset
from backend.app.models.dataset_profile import DatasetProfile
from backend.app.models.dataset_quality import DatasetQuality
from backend.app.models.dataset_recommendation import DatasetRecommendation
from backend.app.models.dataset_version import DatasetVersion
from backend.app.repositories.dataset_recommendation_repository import DatasetRecommendationRepository
from backend.app.repositories.dataset_repository import DatasetRepository
from backend.app.repositories.dataset_version_repository import DatasetVersionRepository
from backend.app.repositories.recommendation_repository import RecommendationRepository
from backend.app.services.cleaning_recommendation_service import CleaningRecommendationService
from backend.app.services.data_cleaning_recommendation_service import DataCleaningRecommendationService
from backend.app.services.data_profiling_service import DataProfilingService
from backend.app.services.data_quality_service import DataQualityService
from backend.app.services.metadata_extraction_service import MetadataExtractionService
from backend.app.services.storage_service import StorageService
from backend.app.core.config import Settings


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
def recommendation_service(in_memory_db: Session) -> DataCleaningRecommendationService:
    rec_repo = DatasetRecommendationRepository(db=in_memory_db)
    ds_repo = DatasetRepository(db=in_memory_db)
    ver_repo = DatasetVersionRepository(db=in_memory_db)
    return DataCleaningRecommendationService(
        recommendation_repo=rec_repo,
        dataset_repo=ds_repo,
        version_repo=ver_repo,
        db=in_memory_db,
    )


def test_checklist_alias_compatibility(in_memory_db: Session) -> None:
    """Checklist aliases match their actual implementations."""
    assert CleaningRecommendationService is DataCleaningRecommendationService
    assert RecommendationRepository is DatasetRecommendationRepository


def test_table_name_is_cleaning_recommendations() -> None:
    """Audit requirement: Table name must be cleaning_recommendations."""
    assert DatasetRecommendation.__tablename__ == "cleaning_recommendations"


def test_recommendation_generation_and_persistence(
    recommendation_service: DataCleaningRecommendationService,
    in_memory_db: Session,
    tmp_path: Path,
) -> None:
    """Generate recommendations for dirty dataset and persist to cleaning_recommendations table."""
    # 1. Setup Dataset & Version
    ds_repo = DatasetRepository(db=in_memory_db)
    ver_repo = DatasetVersionRepository(db=in_memory_db)

    csv_file = tmp_path / "dirty.csv"
    # Contains missing values, duplicate rows, and inconsistent casing ('apple' and 'Apple')
    csv_file.write_text(
        "id,category,score\n"
        "1,apple,85\n"
        "1,apple,85\n"
        "2,Apple,90\n"
        "3,banana,\n"
        "4,,95\n"
    )

    dataset = Dataset(
        dataset_id="rec-ds-1",
        dataset_name="Rec Test",
        file_name="dirty.csv",
        file_type="csv",
        file_path=str(csv_file),
        version=1,
        status="uploaded",
    )
    ds_repo.create(dataset)

    version = DatasetVersion(
        version_id="ver-uuid-1",
        dataset_id="rec-ds-1",
        version_number=1,
        parent_version_id=None,
        change_type="initial_upload",
        storage_path=str(csv_file),
        metadata_snapshot={},
        quality_snapshot={},
        is_active=True,
        created_by="tester",
    )
    ver_repo.create(version)

    # 2. Extract profile and quality
    storage = StorageService(settings=Settings(_env_file=None, upload_dir=str(tmp_path)))
    meta_svc = MetadataExtractionService(storage_service=storage)
    prof_svc = DataProfilingService(metadata_service=meta_svc)
    profile = prof_svc.generate_profile("rec-ds-1", str(csv_file), "csv")

    qual_svc = DataQualityService(
        dataset_repository=ds_repo,
        dataset_profile_repository=None,  # Not needed for direct assess
        metadata_service=meta_svc,
    )
    quality = qual_svc.assess_quality("rec-ds-1", str(csv_file), "csv", profile)

    # 3. Generate recommendations
    recs = recommendation_service.generate_recommendations(
        dataset_id="rec-ds-1",
        file_path=str(csv_file),
        file_type="csv",
        version_id="ver-uuid-1",
        version_number=1,
        profile=profile,
        quality=quality,
        created_by="tester",
        session=in_memory_db,
    )

    assert len(recs) > 0
    rec_types = {r.recommendation_type for r in recs}
    # Should detect duplicates and/or missing values
    assert "duplicates" in rec_types or "missing_values" in rec_types or "consistency" in rec_types

    # Verify priority score is within valid range
    for r in recs:
        assert 0 <= r.priority_score <= 100

    # 4. Verify persistence in cleaning_recommendations
    persisted = in_memory_db.query(DatasetRecommendation).filter_by(dataset_id="rec-ds-1").all()
    assert len(persisted) == len(recs)

    # 5. Resolve a recommendation
    rec_to_resolve = persisted[0]
    resolved = recommendation_service.recommendation_repo.mark_resolved(
        rec_to_resolve.recommendation_id, session=in_memory_db
    )
    assert resolved.status == "resolved"
    assert resolved.resolved_at is not None

    # Active recommendations should decrease by 1
    active_recs = recommendation_service.recommendation_repo.get_active_recommendations_for_dataset(
        "rec-ds-1", session=in_memory_db
    )
    assert len(active_recs) == len(persisted) - 1
