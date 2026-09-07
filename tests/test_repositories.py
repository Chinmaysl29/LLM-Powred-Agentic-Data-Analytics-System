"""
Tests for all repository classes — DatasetRepository, WorkspaceRepository,
and DatasetVersionRepository — using in-memory SQLite.
"""

import uuid
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.models.base import Base
from backend.app.models.dataset import Dataset
from backend.app.models.dataset_metadata import DatasetMetadata
from backend.app.models.dataset_profile import DatasetProfile
from backend.app.models.dataset_quality import DatasetQuality
from backend.app.models.dataset_version import DatasetVersion
from backend.app.models.tenant import Tenant
from backend.app.models.workspace import Workspace
from backend.app.repositories.dataset_repository import DatasetRepository
from backend.app.repositories.dataset_version_repository import DatasetVersionRepository
from backend.app.repositories.workspace_repository import WorkspaceRepository
from backend.app.repositories.dataset_metadata_repository import DatasetMetadataRepository
from backend.app.repositories.dataset_profile_repository import DatasetProfileRepository
from backend.app.repositories.dataset_quality_repository import DatasetQualityRepository


# ===========================================================================
# Fixtures
# ===========================================================================

@pytest.fixture(scope="function")
def db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = Session()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def _dataset(name="Test DS", dsid=None) -> Dataset:
    return Dataset(
        dataset_id=dsid or str(uuid.uuid4()),
        dataset_name=name,
        file_name="data.csv",
        file_type="csv",
        file_path="/tmp/data.csv",
        version=1,
        status="uploaded",
    )


# ===========================================================================
# DatasetRepository Tests
# ===========================================================================

class TestDatasetRepository:

    def test_create_and_get(self, db):
        repo = DatasetRepository(db=db)
        ds = _dataset()
        created = repo.create(ds)
        retrieved = repo.get(created.dataset_id)
        assert retrieved is not None
        assert retrieved.dataset_id == created.dataset_id
        assert retrieved.dataset_name == "Test DS"

    def test_get_nonexistent_returns_none(self, db):
        repo = DatasetRepository(db=db)
        assert repo.get("nonexistent-id") is None

    def test_list_returns_all_datasets(self, db):
        repo = DatasetRepository(db=db)
        for i in range(3):
            repo.create(_dataset(name=f"DS-{i}"))
        items = repo.list(skip=0, limit=100)
        assert len(items) == 3

    def test_list_pagination_skip(self, db):
        repo = DatasetRepository(db=db)
        for i in range(5):
            repo.create(_dataset(name=f"DS-{i}"))
        items = repo.list(skip=2, limit=10)
        assert len(items) == 3

    def test_list_pagination_limit(self, db):
        repo = DatasetRepository(db=db)
        for i in range(5):
            repo.create(_dataset(name=f"DS-{i}"))
        items = repo.list(skip=0, limit=2)
        assert len(items) == 2

    def test_update_fields(self, db):
        repo = DatasetRepository(db=db)
        ds = repo.create(_dataset())
        updated = repo.update(ds.dataset_id, dataset_name="Updated Name", status="processed")
        assert updated.dataset_name == "Updated Name"
        assert updated.status == "processed"

    def test_update_nonexistent_returns_none(self, db):
        repo = DatasetRepository(db=db)
        assert repo.update("nonexistent", dataset_name="X") is None

    def test_delete_existing_returns_true(self, db):
        repo = DatasetRepository(db=db)
        ds = repo.create(_dataset())
        assert repo.delete(ds.dataset_id) is True
        assert repo.get(ds.dataset_id) is None

    def test_delete_nonexistent_returns_false(self, db):
        repo = DatasetRepository(db=db)
        assert repo.delete("does-not-exist") is False

    def test_list_empty_returns_empty_list(self, db):
        repo = DatasetRepository(db=db)
        assert repo.list() == []

    def test_update_does_not_change_unspecified_fields(self, db):
        repo = DatasetRepository(db=db)
        ds = repo.create(_dataset(name="Original"))
        original_path = ds.file_path
        updated = repo.update(ds.dataset_id, status="processed")
        assert updated.file_path == original_path
        assert updated.dataset_name == "Original"

    def test_create_multiple_datasets(self, db):
        repo = DatasetRepository(db=db)
        ids = set()
        for i in range(10):
            ds = repo.create(_dataset(name=f"Multi-{i}"))
            ids.add(ds.dataset_id)
        assert len(ids) == 10
        assert len(repo.list(limit=20)) == 10


# ===========================================================================
# DatasetMetadataRepository Tests
# ===========================================================================

class TestDatasetMetadataRepository:

    def test_create_and_get_metadata(self, db):
        repo = DatasetMetadataRepository(db=db)
        ds_id = str(uuid.uuid4())
        meta = DatasetMetadata(
            dataset_id=ds_id,
            row_count=50,
            column_count=4,
            column_names=["a", "b", "c", "d"],
            column_types={"a": "int"},
            columns_metadata=[],
            classifications={},
        )
        repo.create(meta)
        retrieved = repo.get(ds_id)
        assert retrieved is not None
        assert retrieved.row_count == 50
        assert retrieved.column_count == 4

    def test_get_nonexistent_returns_none(self, db):
        repo = DatasetMetadataRepository(db=db)
        assert repo.get("nonexistent") is None


# ===========================================================================
# DatasetProfileRepository Tests
# ===========================================================================

class TestDatasetProfileRepository:

    def test_create_and_get_profile(self, db):
        repo = DatasetProfileRepository(db=db)
        ds_id = str(uuid.uuid4())
        profile = DatasetProfile(
            dataset_id=ds_id,
            duplicate_rows=1,
            duplicate_percentage=5.0,
            missing_data_profile={"null_count": 2, "null_percentage": 2.0, "columns_with_missing": []},
            cardinality_profile={"high_cardinality_columns": [], "low_cardinality_columns": []},
            numeric_columns_profile={"col1": {"mean": 5.0}},
        )
        repo.create(profile)
        retrieved = repo.get(ds_id)
        assert retrieved is not None
        assert retrieved.duplicate_rows == 1

    def test_get_nonexistent_returns_none(self, db):
        repo = DatasetProfileRepository(db=db)
        assert repo.get("nonexistent") is None


# ===========================================================================
# DatasetQualityRepository Tests
# ===========================================================================

class TestDatasetQualityRepository:

    def test_create_and_get_quality(self, db):
        repo = DatasetQualityRepository(db=db)
        ds_id = str(uuid.uuid4())
        quality = DatasetQuality(
            dataset_id=ds_id,
            overall_score=90.0,
            completeness_score=95.0,
            validity_score=88.0,
            uniqueness_score=85.0,
            consistency_score=87.0,
            integrity_score=90.0,
            quality_classification="good",
        )
        repo.create(quality)
        retrieved = repo.get(ds_id)
        assert retrieved is not None
        assert retrieved.overall_score == 90.0

    def test_get_nonexistent_returns_none(self, db):
        repo = DatasetQualityRepository(db=db)
        assert repo.get("nonexistent") is None


# ===========================================================================
# WorkspaceRepository Tests
# ===========================================================================

class TestWorkspaceRepository:

    def _seed_tenant(self, db) -> Tenant:
        t = Tenant(
            id=uuid.uuid4(),
            tenant_name=f"T-{uuid.uuid4().hex[:6]}",
            tenant_slug=f"t-{uuid.uuid4().hex[:6]}",
        )
        db.add(t)
        db.commit()
        return t

    def _make_ws(self, tenant_id, name="WS") -> Workspace:
        return Workspace(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            workspace_name=name,
            workspace_slug=f"ws-{uuid.uuid4().hex[:6]}",
            status="active",
        )

    def test_create_and_get_workspace(self, db):
        repo = WorkspaceRepository(db=db)
        tenant = self._seed_tenant(db)
        ws = self._make_ws(tenant.id, name="Finance")
        created = repo.create_workspace(ws)
        retrieved = repo.get_workspace(created.id)
        assert retrieved is not None
        assert retrieved.workspace_name == "Finance"

    def test_get_nonexistent_workspace_returns_none(self, db):
        repo = WorkspaceRepository(db=db)
        assert repo.get_workspace(uuid.uuid4()) is None

    def test_list_workspaces_for_tenant(self, db):
        repo = WorkspaceRepository(db=db)
        tenant = self._seed_tenant(db)
        for i in range(3):
            repo.create_workspace(self._make_ws(tenant.id, name=f"WS-{i}"))
        items = repo.list_workspaces(tenant_id=tenant.id)
        assert len(items) == 3

    def test_list_workspaces_filtered_by_status(self, db):
        repo = WorkspaceRepository(db=db)
        tenant = self._seed_tenant(db)
        repo.create_workspace(self._make_ws(tenant.id, name="Active"))
        ws2 = self._make_ws(tenant.id, name="Suspended")
        ws2.status = "suspended"
        repo.create_workspace(ws2)
        active = repo.list_workspaces(tenant_id=tenant.id, status="active")
        assert len(active) == 1
        assert active[0].workspace_name == "Active"

    def test_update_workspace_name(self, db):
        repo = WorkspaceRepository(db=db)
        tenant = self._seed_tenant(db)
        ws = repo.create_workspace(self._make_ws(tenant.id, name="Old Name"))
        updated = repo.update_workspace(ws.id, workspace_name="New Name")
        assert updated is not None
        assert updated.workspace_name == "New Name"

    def test_update_nonexistent_returns_none(self, db):
        repo = WorkspaceRepository(db=db)
        assert repo.update_workspace(uuid.uuid4(), workspace_name="X") is None

    def test_delete_workspace(self, db):
        repo = WorkspaceRepository(db=db)
        tenant = self._seed_tenant(db)
        ws = repo.create_workspace(self._make_ws(tenant.id))
        assert repo.delete_workspace(ws.id) is True
        assert repo.get_workspace(ws.id) is None

    def test_delete_nonexistent_returns_false(self, db):
        repo = WorkspaceRepository(db=db)
        assert repo.delete_workspace(uuid.uuid4()) is False

    def test_get_by_slug(self, db):
        repo = WorkspaceRepository(db=db)
        tenant = self._seed_tenant(db)
        ws = Workspace(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            workspace_name="Slug Test",
            workspace_slug="slug-test-001",
            status="active",
        )
        repo.create_workspace(ws)
        found = repo.get_by_slug(tenant.id, "slug-test-001")
        assert found is not None
        assert found.workspace_name == "Slug Test"

    def test_get_by_slug_wrong_tenant_returns_none(self, db):
        repo = WorkspaceRepository(db=db)
        tenant = self._seed_tenant(db)
        other_tenant = self._seed_tenant(db)
        ws = Workspace(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            workspace_name="Private WS",
            workspace_slug="private-ws-001",
            status="active",
        )
        repo.create_workspace(ws)
        assert repo.get_by_slug(other_tenant.id, "private-ws-001") is None

    def test_memory_fallback_when_no_db(self):
        """WorkspaceRepository with db=None uses in-memory store."""
        repo = WorkspaceRepository(db=None)
        tid = uuid.uuid4()
        ws = Workspace(
            id=uuid.uuid4(),
            tenant_id=tid,
            workspace_name="Memory WS",
            workspace_slug="memory-ws",
            status="active",
        )
        # Manually set timestamps since SQLite triggers won't run
        from datetime import datetime, timezone
        ws.created_at = datetime.now(timezone.utc)
        ws.updated_at = datetime.now(timezone.utc)
        created = repo.create_workspace(ws)
        retrieved = repo.get_workspace(created.id)
        assert retrieved is not None
        assert retrieved.workspace_name == "Memory WS"
        assert repo.delete_workspace(created.id) is True
        assert repo.get_workspace(created.id) is None
