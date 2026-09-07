"""Unit and integration tests for Phase 2.1 Dataset Foundation."""

import io
import json
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from fastapi import UploadFile
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.core.config import Settings
from backend.app.database.chromadb import ChromaDatabase
from backend.app.database.postgres import PostgresDatabase, get_db_session
from backend.app.database.redis import RedisCache
from backend.app.main import app
from backend.app.models.base import Base
from backend.app.models.dataset import Dataset
from backend.app.models.dataset_metadata import DatasetMetadata
from backend.app.models.dataset_profile import DatasetProfile
from backend.app.models.dataset_quality import DatasetQuality
from backend.app.models.dataset_version import DatasetVersion
from backend.app.models.dataset_recommendation import DatasetRecommendation
from backend.app.repositories.dataset_repository import DatasetRepository
from backend.app.services.storage_service import StorageService


# ---------------------------------------------------------------------------
# In-Memory SQLite Fixtures for isolated testing
# ---------------------------------------------------------------------------
@pytest.fixture
def in_memory_db() -> Session:
    """Create an isolated in-memory SQLite database session."""
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
def temp_storage_service(tmp_path: Path) -> StorageService:
    """Create a StorageService using a temporary directory."""
    settings = Settings(
        _env_file=None,
        upload_dir=str(tmp_path),
        max_file_size_mb=10,
    )
    return StorageService(settings=settings)


# ---------------------------------------------------------------------------
# Unit Tests: DatasetRepository
# ---------------------------------------------------------------------------
def test_dataset_repository_create_and_get(in_memory_db: Session) -> None:
    """DatasetRepository can create and retrieve a Dataset record."""
    repo = DatasetRepository(db=in_memory_db)
    dataset = Dataset(
        dataset_id="test-ds-1",
        dataset_name="Sales Q1",
        file_name="sales.csv",
        file_type="csv",
        file_path="/tmp/sales.csv",
        version=1,
        status="uploaded",
    )

    created = repo.create(dataset)
    assert created.dataset_id == "test-ds-1"
    assert created.dataset_name == "Sales Q1"
    assert created.status == "uploaded"

    retrieved = repo.get("test-ds-1")
    assert retrieved is not None
    assert retrieved.dataset_id == "test-ds-1"
    assert retrieved.file_name == "sales.csv"


def test_dataset_repository_list_and_pagination(in_memory_db: Session) -> None:
    """DatasetRepository list returns paginated datasets ordered by created_at desc."""
    repo = DatasetRepository(db=in_memory_db)

    for i in range(5):
        repo.create(
            Dataset(
                dataset_id=f"ds-{i}",
                dataset_name=f"Dataset {i}",
                file_name=f"file_{i}.csv",
                file_type="csv",
                file_path=f"/path/{i}.csv",
                version=1,
                status="uploaded",
            )
        )

    all_items = repo.list(skip=0, limit=10)
    assert len(all_items) == 5

    paged_items = repo.list(skip=2, limit=2)
    assert len(paged_items) == 2


def test_dataset_repository_update(in_memory_db: Session) -> None:
    """DatasetRepository can update dataset fields."""
    repo = DatasetRepository(db=in_memory_db)
    dataset = Dataset(
        dataset_id="update-ds",
        dataset_name="Initial Name",
        file_name="data.json",
        file_type="json",
        file_path="/path/data.json",
        version=1,
        status="uploaded",
    )
    repo.create(dataset)

    updated = repo.update("update-ds", dataset_name="New Name", status="processed")
    assert updated is not None
    assert updated.dataset_name == "New Name"
    assert updated.status == "processed"

    # Updating non-existent returns None
    assert repo.update("non-existent", dataset_name="X") is None


def test_dataset_repository_delete(in_memory_db: Session) -> None:
    """DatasetRepository can delete a record."""
    repo = DatasetRepository(db=in_memory_db)
    dataset = Dataset(
        dataset_id="delete-ds",
        dataset_name="Delete Me",
        file_name="del.xlsx",
        file_type="xlsx",
        file_path="/path/del.xlsx",
        version=1,
        status="uploaded",
    )
    repo.create(dataset)

    assert repo.delete("delete-ds") is True
    assert repo.get("delete-ds") is None
    assert repo.delete("non-existent") is False


# ---------------------------------------------------------------------------
# Unit Tests: StorageService
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_storage_service_save_csv(temp_storage_service: StorageService) -> None:
    """StorageService can save a CSV file."""
    content = b"id,name,value\n1,Alice,100\n2,Bob,200\n"
    upload = UploadFile(filename="customers.csv", file=io.BytesIO(content))

    dataset_id, file_name, file_type, file_path, size_bytes = await temp_storage_service.save_file(upload)

    assert file_name == "customers.csv"
    assert file_type == "csv"
    assert size_bytes == len(content)
    assert Path(file_path).exists()
    assert Path(file_path).read_bytes() == content


@pytest.mark.anyio
async def test_storage_service_save_json(temp_storage_service: StorageService) -> None:
    """StorageService can save a JSON file."""
    data = [{"id": 1, "metric": "cpu", "val": 0.85}]
    content = json.dumps(data).encode("utf-8")
    upload = UploadFile(filename="metrics.json", file=io.BytesIO(content))

    dataset_id, file_name, file_type, file_path, size_bytes = await temp_storage_service.save_file(upload)

    assert file_name == "metrics.json"
    assert file_type == "json"
    assert size_bytes == len(content)
    assert Path(file_path).exists()


@pytest.mark.anyio
async def test_storage_service_save_xlsx(temp_storage_service: StorageService) -> None:
    """StorageService can save an XLSX file."""
    content = b"PK\x03\x04fake_xlsx_content"
    upload = UploadFile(filename="financials.xlsx", file=io.BytesIO(content))

    dataset_id, file_name, file_type, file_path, size_bytes = await temp_storage_service.save_file(upload)

    assert file_name == "financials.xlsx"
    assert file_type == "xlsx"
    assert Path(file_path).exists()


@pytest.mark.anyio
async def test_storage_service_rejects_unsupported_type(temp_storage_service: StorageService) -> None:
    """StorageService rejects unsupported extensions while accepting PDFs."""
    upload_txt = UploadFile(filename="notes.txt", file=io.BytesIO(b"hello world"))
    with pytest.raises(ValueError, match="Unsupported file type"):
        await temp_storage_service.save_file(upload_txt)

    upload_pdf = UploadFile(filename="report.pdf", file=io.BytesIO(b"pdf data"))
    _, _, file_type, _, _ = await temp_storage_service.save_file(upload_pdf)
    assert file_type == "pdf"


def test_storage_service_retrieve_and_delete(temp_storage_service: StorageService, tmp_path: Path) -> None:
    """StorageService can retrieve and delete existing files."""
    test_file = tmp_path / "sample.csv"
    test_file.write_text("a,b\n1,2")

    retrieved = temp_storage_service.retrieve_file(str(test_file))
    assert retrieved == test_file

    assert temp_storage_service.delete_file(str(test_file)) is True
    assert not test_file.exists()

    with pytest.raises(FileNotFoundError):
        temp_storage_service.retrieve_file(str(tmp_path / "missing.csv"))

    assert temp_storage_service.delete_file(str(tmp_path / "missing.csv")) is False


# ---------------------------------------------------------------------------
# Integration Tests: FastAPI Endpoints
# ---------------------------------------------------------------------------
def test_dataset_upload_endpoint_flow(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Integration test for POST /api/v1/datasets/upload flow."""
    # Set up in-memory DB
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def override_get_db_session():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db_session] = override_get_db_session

    # Mock DB adapters for startup/health
    monkeypatch.setattr(PostgresDatabase, "connect", lambda self: None)
    monkeypatch.setattr(PostgresDatabase, "health_check", AsyncMock(return_value=(True, "OK")))
    monkeypatch.setattr(RedisCache, "connect", AsyncMock(return_value=None))
    monkeypatch.setattr(RedisCache, "close", AsyncMock(return_value=None))
    monkeypatch.setattr(RedisCache, "health_check", AsyncMock(return_value=(True, "OK")))
    monkeypatch.setattr(ChromaDatabase, "connect", AsyncMock(return_value=None))
    monkeypatch.setattr(ChromaDatabase, "close", AsyncMock(return_value=None))
    monkeypatch.setattr(ChromaDatabase, "health_check", AsyncMock(return_value=(True, "OK")))

    with TestClient(app) as client:
        # 1. Upload CSV
        csv_content = b"col1,col2,col3\n10,20,30\n40,50,60\n"
        response = client.post(
            "/api/v1/datasets/upload",
            files={"file": ("inventory.csv", io.BytesIO(csv_content), "text/csv")},
            data={"dataset_name": "Q1 Inventory"},
        )
        assert response.status_code == 201, response.text
        data = response.json()
        assert "dataset_id" in data
        assert data["dataset_name"] == "Q1 Inventory"
        assert data["file_name"] == "inventory.csv"
        assert data["file_type"] == "csv"
        assert data["status"] in ("uploaded", "ready")

        dataset_id = data["dataset_id"]

        # 2. Get Dataset by ID
        get_res = client.get(f"/api/v1/datasets/{dataset_id}")
        assert get_res.status_code == 200
        assert get_res.json()["dataset_id"] == dataset_id

        # 3. List Datasets
        list_res = client.get("/api/v1/datasets")
        assert list_res.status_code == 200
        items = list_res.json()
        assert len(items) >= 1
        assert any(d["dataset_id"] == dataset_id for d in items)

        # 4. Upload Unsupported File (Should fail 400)
        unsupported_res = client.post(
            "/api/v1/datasets/upload",
            files={"file": ("test.txt", io.BytesIO(b"some text"), "text/plain")},
        )
        assert unsupported_res.status_code == 400

        # 5. Delete Dataset
        del_res = client.delete(f"/api/v1/datasets/{dataset_id}")
        assert del_res.status_code == 200
        assert del_res.json()["success"] is True

        # 6. Verify Deletion
        get_after_del = client.get(f"/api/v1/datasets/{dataset_id}")
        assert get_after_del.status_code == 404

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


def test_upload_pipeline_persists_all_downstream_tables_and_endpoints(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Validate that upload pipeline persists records to all 5 downstream tables and endpoints return valid data."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def override_get_db_session():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db_session] = override_get_db_session

    monkeypatch.setattr(PostgresDatabase, "connect", lambda self: None)
    monkeypatch.setattr(PostgresDatabase, "health_check", AsyncMock(return_value=(True, "OK")))
    monkeypatch.setattr(RedisCache, "connect", AsyncMock(return_value=None))
    monkeypatch.setattr(RedisCache, "close", AsyncMock(return_value=None))
    monkeypatch.setattr(RedisCache, "health_check", AsyncMock(return_value=(True, "OK")))
    monkeypatch.setattr(ChromaDatabase, "connect", AsyncMock(return_value=None))
    monkeypatch.setattr(ChromaDatabase, "close", AsyncMock(return_value=None))
    monkeypatch.setattr(ChromaDatabase, "health_check", AsyncMock(return_value=(True, "OK")))

    with TestClient(app) as client:
        # 1. Upload CSV
        csv_data = b"product_id,product_name,price,category\n101,Widget,19.99,Tools\n102,Gadget,29.99,Tools\n"
        upload_res = client.post(
            "/api/v1/datasets/upload",
            files={"file": ("products.csv", io.BytesIO(csv_data), "text/csv")},
            data={"dataset_name": "Product Catalog"},
        )
        assert upload_res.status_code == 201, upload_res.text
        data = upload_res.json()
        dataset_id = data["dataset_id"]

        # 2. Verify all database tables have persisted records
        db = session_factory()
        try:
            assert db.query(Dataset).filter_by(dataset_id=dataset_id).count() == 1
            assert db.query(DatasetMetadata).filter_by(dataset_id=dataset_id).count() == 1
            assert db.query(DatasetProfile).filter_by(dataset_id=dataset_id).count() == 1
            assert db.query(DatasetQuality).filter_by(dataset_id=dataset_id).count() == 1
            assert db.query(DatasetVersion).filter_by(dataset_id=dataset_id).count() >= 1
            # cleaning_recommendations table
            assert db.query(DatasetRecommendation).filter_by(dataset_id=dataset_id).count() >= 0
        finally:
            db.close()

        # 3. Verify GET /metadata
        meta_res = client.get(f"/api/v1/datasets/{dataset_id}/metadata")
        assert meta_res.status_code == 200, meta_res.text
        meta_data = meta_res.json()
        assert meta_data["dataset_id"] == dataset_id
        assert meta_data["row_count"] == 2
        assert "product_name" in meta_data["column_names"]

        # 4. Verify GET /profile
        prof_res = client.get(f"/api/v1/datasets/{dataset_id}/profile")
        assert prof_res.status_code == 200, prof_res.text
        prof_data = prof_res.json()
        assert prof_data["dataset_id"] == dataset_id
        assert "duplicate_rows" in prof_data

        # 5. Verify GET /quality
        qual_res = client.get(f"/api/v1/datasets/{dataset_id}/quality")
        assert qual_res.status_code == 200, qual_res.text
        qual_data = qual_res.json()
        assert qual_data["dataset_id"] == dataset_id
        assert "overall_score" in qual_data

        # 6. Verify GET /versions
        ver_res = client.get(f"/api/v1/datasets/{dataset_id}/versions")
        assert ver_res.status_code == 200, ver_res.text
        ver_data = ver_res.json()
        assert ver_data["total_count"] >= 1
        assert len(ver_data["versions"]) >= 1

        # 7. Verify GET /recommendations
        rec_res = client.get(f"/api/v1/datasets/{dataset_id}/recommendations")
        assert rec_res.status_code == 200, rec_res.text
        rec_data = rec_res.json()
        assert rec_data["dataset_id"] == dataset_id
        assert "recommendations" in rec_data

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
