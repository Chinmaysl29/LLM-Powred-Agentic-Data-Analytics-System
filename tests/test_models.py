"""
Tests for all SQLAlchemy ORM models.
Validates table creation, column constraints, defaults, relationships,
and serialisation using an in-memory SQLite engine.
"""

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.models.base import Base, TimestampMixin
from backend.app.models.dataset import Dataset
from backend.app.models.dataset_metadata import DatasetMetadata
from backend.app.models.dataset_profile import DatasetProfile
from backend.app.models.dataset_quality import DatasetQuality
from backend.app.models.dataset_version import DatasetVersion
from backend.app.models.tenant import Tenant
from backend.app.models.user import User
from backend.app.models.workspace import Workspace


# ===========================================================================
# Shared Engine / Session Fixture
# ===========================================================================

@pytest.fixture(scope="module")
def engine():
    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=eng)
    yield eng
    Base.metadata.drop_all(bind=eng)
    eng.dispose()


@pytest.fixture(scope="function")
def session(engine):
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    s = Session()
    yield s
    s.rollback()
    s.close()


# ===========================================================================
# Base / TimestampMixin
# ===========================================================================

class TestTimestampMixin:
    """Verify created_at / updated_at columns are present on mixin subclasses."""

    def test_user_has_timestamp_columns(self, engine):
        insp = inspect(engine)
        cols = [c["name"] for c in insp.get_columns("users")]
        assert "created_at" in cols
        assert "updated_at" in cols

    def test_dataset_has_timestamp_columns(self, engine):
        insp = inspect(engine)
        cols = [c["name"] for c in insp.get_columns("datasets")]
        assert "created_at" in cols
        assert "updated_at" in cols


# ===========================================================================
# User Model
# ===========================================================================

class TestUserModel:
    """Tests for the User ORM model."""

    def test_create_user_with_required_fields(self, session):
        user = User(
            id=uuid.uuid4(),
            email="alice@example.com",
            hashed_password="$2b$12$fakehash",
            full_name="Alice Smith",
            role="analyst",
            is_active=True,
        )
        session.add(user)
        session.commit()
        session.refresh(user)

        assert user.email == "alice@example.com"
        assert user.full_name == "Alice Smith"
        assert user.role == "analyst"
        assert user.is_active is True

    def test_user_default_role_is_analyst(self, session):
        user = User(
            id=uuid.uuid4(),
            email="bob@example.com",
            hashed_password="$2b$fakehash",
            full_name="Bob",
        )
        session.add(user)
        session.commit()
        assert user.role == "analyst"

    def test_user_default_is_active_true(self, session):
        user = User(
            id=uuid.uuid4(),
            email="carol@example.com",
            hashed_password="hash",
        )
        session.add(user)
        session.commit()
        assert user.is_active is True

    def test_user_repr_contains_email(self, session):
        user = User(
            id=uuid.uuid4(),
            email="dave@example.com",
            hashed_password="hash",
        )
        session.add(user)
        session.commit()
        assert "dave@example.com" in repr(user)

    def test_user_id_is_uuid(self, session):
        uid = uuid.uuid4()
        user = User(id=uid, email="eve@x.com", hashed_password="hash")
        session.add(user)
        session.commit()
        assert user.id == uid


# ===========================================================================
# Dataset Model
# ===========================================================================

class TestDatasetModel:
    """Tests for the Dataset ORM model."""

    def _make_dataset(self, **overrides) -> Dataset:
        defaults = dict(
            dataset_id=str(uuid.uuid4()),
            dataset_name="Test Dataset",
            file_name="test.csv",
            file_type="csv",
            file_path="/tmp/test.csv",
            version=1,
            status="uploaded",
        )
        defaults.update(overrides)
        return Dataset(**defaults)

    def test_create_dataset(self, session):
        ds = self._make_dataset()
        session.add(ds)
        session.commit()
        session.refresh(ds)
        assert ds.dataset_name == "Test Dataset"
        assert ds.file_type == "csv"
        assert ds.status == "uploaded"
        assert ds.version == 1

    def test_dataset_default_status_uploaded(self, session):
        ds = Dataset(
            dataset_id=str(uuid.uuid4()),
            dataset_name="DS2",
            file_name="x.csv",
            file_type="csv",
            file_path="/tmp/x.csv",
        )
        session.add(ds)
        session.commit()
        assert ds.status == "uploaded"

    def test_dataset_default_version_is_1(self, session):
        ds = Dataset(
            dataset_id=str(uuid.uuid4()),
            dataset_name="DS3",
            file_name="y.csv",
            file_type="csv",
            file_path="/tmp/y.csv",
        )
        session.add(ds)
        session.commit()
        assert ds.version == 1

    def test_dataset_optional_fields_are_none_by_default(self, session):
        ds = self._make_dataset()
        session.add(ds)
        session.commit()
        assert ds.original_path is None
        assert ds.json_path is None
        assert ds.canonical_path is None
        assert ds.content_hash is None

    def test_dataset_repr_contains_name_and_status(self, session):
        ds = self._make_dataset(dataset_name="SalesData")
        session.add(ds)
        session.commit()
        r = repr(ds)
        assert "SalesData" in r
        assert "uploaded" in r


# ===========================================================================
# Tenant Model
# ===========================================================================

class TestTenantModel:
    """Tests for the Tenant ORM model."""

    def test_create_tenant(self, session):
        t = Tenant(
            id=uuid.uuid4(),
            tenant_name="Acme Corp",
            tenant_slug="acme-corp",
            tenant_status="active",
        )
        session.add(t)
        session.commit()
        session.refresh(t)
        assert t.tenant_name == "Acme Corp"
        assert t.tenant_slug == "acme-corp"
        assert t.tenant_status == "active"

    def test_tenant_default_status_active(self, session):
        t = Tenant(
            id=uuid.uuid4(),
            tenant_name="Beta Inc",
            tenant_slug="beta-inc",
        )
        session.add(t)
        session.commit()
        assert t.tenant_status == "active"

    def test_tenant_to_dict(self, session):
        t = Tenant(
            id=uuid.uuid4(),
            tenant_name="Gamma Ltd",
            tenant_slug="gamma-ltd",
        )
        session.add(t)
        session.commit()
        d = t.to_dict()
        assert d["tenant_name"] == "Gamma Ltd"
        assert d["tenant_slug"] == "gamma-ltd"
        assert "created_at" in d
        assert "id" in d

    def test_tenant_slug_is_unique(self, session):
        tid1 = uuid.uuid4()
        tid2 = uuid.uuid4()
        t1 = Tenant(id=tid1, tenant_name="Delta", tenant_slug="delta-slug")
        t2 = Tenant(id=tid2, tenant_name="Delta2", tenant_slug="delta-slug")
        session.add(t1)
        session.commit()
        session.add(t2)
        with pytest.raises(Exception):
            session.commit()
        session.rollback()

    def test_tenant_repr_contains_name(self, session):
        t = Tenant(id=uuid.uuid4(), tenant_name="Repr Corp", tenant_slug="repr-corp")
        assert "Repr Corp" in repr(t)


# ===========================================================================
# Workspace Model
# ===========================================================================

class TestWorkspaceModel:
    """Tests for the Workspace ORM model."""

    def _make_tenant(self, session) -> Tenant:
        t = Tenant(
            id=uuid.uuid4(),
            tenant_name=f"Tenant-{uuid.uuid4().hex[:6]}",
            tenant_slug=f"tenant-{uuid.uuid4().hex[:6]}",
        )
        session.add(t)
        session.commit()
        return t

    def test_create_workspace(self, session):
        tenant = self._make_tenant(session)
        ws = Workspace(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            workspace_name="Finance Analytics",
            workspace_slug="finance-analytics",
            description="Finance team workspace",
            status="active",
        )
        session.add(ws)
        session.commit()
        session.refresh(ws)
        assert ws.workspace_name == "Finance Analytics"
        assert ws.workspace_slug == "finance-analytics"
        assert ws.status == "active"

    def test_workspace_default_status_active(self, session):
        tenant = self._make_tenant(session)
        ws = Workspace(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            workspace_name="Default Status WS",
            workspace_slug=f"default-{uuid.uuid4().hex[:6]}",
        )
        session.add(ws)
        session.commit()
        assert ws.status == "active"

    def test_workspace_to_dict(self, session):
        tenant = self._make_tenant(session)
        ws = Workspace(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            workspace_name="Dict WS",
            workspace_slug=f"dict-ws-{uuid.uuid4().hex[:6]}",
        )
        session.add(ws)
        session.commit()
        d = ws.to_dict()
        assert d["workspace_name"] == "Dict WS"
        assert "id" in d
        assert "tenant_id" in d

    def test_workspace_tenant_slug_unique_per_tenant(self, session):
        tenant = self._make_tenant(session)
        slug = f"unique-{uuid.uuid4().hex[:6]}"
        ws1 = Workspace(
            id=uuid.uuid4(), tenant_id=tenant.id,
            workspace_name="WS1", workspace_slug=slug,
        )
        ws2 = Workspace(
            id=uuid.uuid4(), tenant_id=tenant.id,
            workspace_name="WS2", workspace_slug=slug,
        )
        session.add(ws1)
        session.commit()
        session.add(ws2)
        with pytest.raises(Exception):
            session.commit()
        session.rollback()

    def test_workspace_repr(self, session):
        tenant = self._make_tenant(session)
        ws = Workspace(
            id=uuid.uuid4(), tenant_id=tenant.id,
            workspace_name="Repr WS", workspace_slug=f"repr-{uuid.uuid4().hex[:6]}",
        )
        assert "Repr WS" in repr(ws)


# ===========================================================================
# DatasetMetadata Model
# ===========================================================================

class TestDatasetMetadataModel:
    """Tests for DatasetMetadata ORM model."""

    def test_create_metadata(self, session):
        ds_id = str(uuid.uuid4())
        meta = DatasetMetadata(
            dataset_id=ds_id,
            row_count=100,
            column_count=5,
            column_names=["a", "b", "c", "d", "e"],
            column_types={"a": "int", "b": "str"},
            columns_metadata=[],
            classifications={"numeric": ["a"], "categorical": ["b"]},
        )
        session.add(meta)
        session.commit()
        session.refresh(meta)
        assert meta.row_count == 100
        assert meta.column_count == 5
        assert "a" in meta.column_names

    def test_metadata_dataset_id_is_primary_key(self, session):
        ds_id = str(uuid.uuid4())
        meta = DatasetMetadata(
            dataset_id=ds_id,
            row_count=10,
            column_count=2,
            column_names=["x", "y"],
            column_types={},
            columns_metadata=[],
            classifications={},
        )
        session.add(meta)
        session.commit()
        assert meta.dataset_id == ds_id


# ===========================================================================
# DatasetProfile Model
# ===========================================================================

class TestDatasetProfileModel:
    """Tests for DatasetProfile ORM model."""

    def test_create_profile(self, session):
        ds_id = str(uuid.uuid4())
        profile = DatasetProfile(
            dataset_id=ds_id,
            duplicate_rows=2,
            duplicate_percentage=10.0,
            missing_data_profile={"null_count": 3, "null_percentage": 5.0, "columns_with_missing": ["col1"]},
            cardinality_profile={"high_cardinality_columns": [], "low_cardinality_columns": ["cat"]},
            numeric_columns_profile={"col1": {"mean": 10.0}},
        )
        session.add(profile)
        session.commit()
        session.refresh(profile)
        assert profile.duplicate_rows == 2
        assert profile.missing_data_profile["null_count"] == 3


# ===========================================================================
# DatasetQuality Model
# ===========================================================================

class TestDatasetQualityModel:
    """Tests for DatasetQuality ORM model."""

    def test_create_quality(self, session):
        ds_id = str(uuid.uuid4())
        quality = DatasetQuality(
            dataset_id=ds_id,
            overall_score=88.5,
            completeness_score=95.0,
            validity_score=90.0,
            uniqueness_score=80.0,
            consistency_score=85.0,
            integrity_score=88.0,
            quality_classification="good",
        )
        session.add(quality)
        session.commit()
        session.refresh(quality)
        assert quality.overall_score == 88.5
        assert quality.quality_classification == "good"


# ===========================================================================
# DatasetVersion Model
# ===========================================================================

class TestDatasetVersionModel:
    """Tests for DatasetVersion ORM model."""

    def test_create_version(self, session):
        ver = DatasetVersion(
            version_id=str(uuid.uuid4()),
            dataset_id=str(uuid.uuid4()),
            version_number=1,
            storage_path="/tmp/v1.csv",
            change_type="initial_upload",
            metadata_snapshot={},
            quality_snapshot={},
            created_by="system",
            is_active=True,
        )
        session.add(ver)
        session.commit()
        session.refresh(ver)
        assert ver.version_number == 1
        assert ver.is_active is True
        assert ver.change_type == "initial_upload"
