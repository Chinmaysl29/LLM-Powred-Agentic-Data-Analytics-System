"""
Tests for dataset API endpoints:
  POST   /api/v1/datasets/upload
  GET    /api/v1/datasets
  GET    /api/v1/datasets/{id}
  DELETE /api/v1/datasets/{id}
  GET    /api/v1/datasets/{id}/metadata
  GET    /api/v1/datasets/{id}/profile
  GET    /api/v1/datasets/{id}/quality
  GET    /api/v1/datasets/{id}/versions
  GET    /api/v1/datasets/{id}/versions/compare
  GET    /api/v1/datasets/{id}/versions/{n}
  POST   /api/v1/datasets/{id}/versions/{n}/rollback
  GET    /api/v1/datasets/{id}/recommendations
  POST   /api/v1/datasets/{id}/recommendations/{rec_id}/resolve
"""

import io
import json
import uuid
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.database.chromadb import ChromaDatabase
from backend.app.database.postgres import PostgresDatabase, get_db_session
from backend.app.database.redis import RedisCache
from backend.app.models.base import Base
from backend.main import app


# ===========================================================================
# Fixtures
# ===========================================================================

@pytest.fixture(scope="function")
def db_engine():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture(scope="function")
def client(db_engine, monkeypatch):
    monkeypatch.setattr(PostgresDatabase, "connect", lambda self: None)
    monkeypatch.setattr(PostgresDatabase, "health_check", AsyncMock(return_value=(True, "OK")))
    monkeypatch.setattr(RedisCache, "connect", AsyncMock(return_value=None))
    monkeypatch.setattr(RedisCache, "close", AsyncMock(return_value=None))
    monkeypatch.setattr(RedisCache, "health_check", AsyncMock(return_value=(True, "OK")))
    monkeypatch.setattr(ChromaDatabase, "connect", AsyncMock(return_value=None))
    monkeypatch.setattr(ChromaDatabase, "close", AsyncMock(return_value=None))
    monkeypatch.setattr(ChromaDatabase, "health_check", AsyncMock(return_value=(True, "OK")))

    SessionFactory = sessionmaker(bind=db_engine, autoflush=False, autocommit=False)

    def _override_db():
        s = SessionFactory()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[get_db_session] = _override_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


CSV_CONTENT = b"product_id,product_name,price,category\n101,Widget,19.99,Tools\n102,Gadget,29.99,Electronics\n103,Doohickey,9.99,Misc\n"


@pytest.fixture(scope="function")
def uploaded_dataset(client):
    """Upload a CSV and return the response JSON."""
    res = client.post(
        "/api/v1/datasets/upload",
        files={"file": ("products.csv", io.BytesIO(CSV_CONTENT), "text/csv")},
        data={"dataset_name": "Product Catalog"},
    )
    assert res.status_code == 201, res.text
    return res.json()


# ===========================================================================
# Upload Tests
# ===========================================================================

class TestDatasetUpload:

    def test_upload_csv_returns_201(self, client):
        res = client.post(
            "/api/v1/datasets/upload",
            files={"file": ("data.csv", io.BytesIO(CSV_CONTENT), "text/csv")},
        )
        assert res.status_code == 201

    def test_upload_returns_dataset_id(self, client):
        res = client.post(
            "/api/v1/datasets/upload",
            files={"file": ("data.csv", io.BytesIO(CSV_CONTENT), "text/csv")},
        )
        assert "dataset_id" in res.json()

    def test_upload_returns_correct_file_type(self, client):
        res = client.post(
            "/api/v1/datasets/upload",
            files={"file": ("data.csv", io.BytesIO(CSV_CONTENT), "text/csv")},
        )
        assert res.json()["file_type"] == "csv"

    def test_upload_with_custom_name(self, client):
        res = client.post(
            "/api/v1/datasets/upload",
            files={"file": ("data.csv", io.BytesIO(CSV_CONTENT), "text/csv")},
            data={"dataset_name": "My Custom Dataset"},
        )
        assert res.json()["dataset_name"] == "My Custom Dataset"

    def test_upload_json_file(self, client):
        data = [{"x": 1}, {"x": 2}]
        res = client.post(
            "/api/v1/datasets/upload",
            files={"file": ("data.json", io.BytesIO(json.dumps(data).encode()), "application/json")},
        )
        assert res.status_code == 201
        assert res.json()["file_type"] == "json"

    def test_upload_unsupported_type_returns_400(self, client):
        res = client.post(
            "/api/v1/datasets/upload",
            files={"file": ("notes.txt", io.BytesIO(b"some text"), "text/plain")},
        )
        assert res.status_code == 400

    def test_upload_status_is_uploaded(self, client):
        res = client.post(
            "/api/v1/datasets/upload",
            files={"file": ("data.csv", io.BytesIO(CSV_CONTENT), "text/csv")},
        )
        assert res.json()["status"] in ("uploaded", "ready")


    def test_upload_persists_all_downstream_tables(self, client, db_engine):
        from backend.app.models.dataset import Dataset
        from backend.app.models.dataset_metadata import DatasetMetadata
        from backend.app.models.dataset_profile import DatasetProfile
        from backend.app.models.dataset_quality import DatasetQuality
        from backend.app.models.dataset_version import DatasetVersion

        res = client.post(
            "/api/v1/datasets/upload",
            files={"file": ("sales.csv", io.BytesIO(CSV_CONTENT), "text/csv")},
        )
        ds_id = res.json()["dataset_id"]

        SessionFactory = sessionmaker(bind=db_engine)
        with SessionFactory() as s:
            assert s.query(Dataset).filter_by(dataset_id=ds_id).count() == 1
            assert s.query(DatasetMetadata).filter_by(dataset_id=ds_id).count() == 1
            assert s.query(DatasetProfile).filter_by(dataset_id=ds_id).count() == 1
            assert s.query(DatasetQuality).filter_by(dataset_id=ds_id).count() == 1
            assert s.query(DatasetVersion).filter_by(dataset_id=ds_id).count() >= 1


# ===========================================================================
# Get / List Dataset Tests
# ===========================================================================

class TestDatasetGetList:

    def test_get_dataset_by_id_returns_200(self, client, uploaded_dataset):
        ds_id = uploaded_dataset["dataset_id"]
        res = client.get(f"/api/v1/datasets/{ds_id}")
        assert res.status_code == 200

    def test_get_dataset_returns_correct_id(self, client, uploaded_dataset):
        ds_id = uploaded_dataset["dataset_id"]
        data = client.get(f"/api/v1/datasets/{ds_id}").json()
        assert data["dataset_id"] == ds_id

    def test_get_nonexistent_dataset_returns_404(self, client):
        res = client.get("/api/v1/datasets/nonexistent-id-xyz")
        assert res.status_code == 404

    def test_list_datasets_returns_200(self, client, uploaded_dataset):
        res = client.get("/api/v1/datasets")
        assert res.status_code == 200

    def test_list_datasets_returns_list(self, client, uploaded_dataset):
        data = client.get("/api/v1/datasets").json()
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_list_datasets_contains_uploaded_dataset(self, client, uploaded_dataset):
        ds_id = uploaded_dataset["dataset_id"]
        data = client.get("/api/v1/datasets").json()
        assert any(d["dataset_id"] == ds_id for d in data)

    def test_list_with_pagination(self, client):
        for i in range(3):
            client.post(
                "/api/v1/datasets/upload",
                files={"file": (f"file{i}.csv", io.BytesIO(CSV_CONTENT), "text/csv")},
            )
        res = client.get("/api/v1/datasets?skip=0&limit=2")
        assert len(res.json()) <= 2


# ===========================================================================
# Delete Dataset Tests
# ===========================================================================

class TestDatasetDelete:

    def test_delete_existing_dataset_returns_200(self, client, uploaded_dataset):
        ds_id = uploaded_dataset["dataset_id"]
        res = client.delete(f"/api/v1/datasets/{ds_id}")
        assert res.status_code == 200

    def test_delete_returns_success_true(self, client, uploaded_dataset):
        ds_id = uploaded_dataset["dataset_id"]
        data = client.delete(f"/api/v1/datasets/{ds_id}").json()
        assert data["success"] is True

    def test_deleted_dataset_returns_404_on_get(self, client, uploaded_dataset):
        ds_id = uploaded_dataset["dataset_id"]
        client.delete(f"/api/v1/datasets/{ds_id}")
        res = client.get(f"/api/v1/datasets/{ds_id}")
        assert res.status_code == 404

    def test_delete_nonexistent_returns_404(self, client):
        res = client.delete("/api/v1/datasets/nonexistent-id")
        assert res.status_code == 404


# ===========================================================================
# Metadata / Profile / Quality Endpoint Tests
# ===========================================================================

class TestDatasetSubresources:

    def test_get_metadata_returns_200(self, client, uploaded_dataset):
        ds_id = uploaded_dataset["dataset_id"]
        res = client.get(f"/api/v1/datasets/{ds_id}/metadata")
        assert res.status_code == 200

    def test_get_metadata_contains_row_count(self, client, uploaded_dataset):
        ds_id = uploaded_dataset["dataset_id"]
        data = client.get(f"/api/v1/datasets/{ds_id}/metadata").json()
        assert "row_count" in data
        assert data["row_count"] == 3

    def test_get_metadata_contains_column_names(self, client, uploaded_dataset):
        ds_id = uploaded_dataset["dataset_id"]
        data = client.get(f"/api/v1/datasets/{ds_id}/metadata").json()
        assert "column_names" in data
        assert "product_name" in data["column_names"]

    def test_get_metadata_nonexistent_returns_404(self, client):
        res = client.get("/api/v1/datasets/nonexistent/metadata")
        assert res.status_code == 404

    def test_get_profile_returns_200(self, client, uploaded_dataset):
        ds_id = uploaded_dataset["dataset_id"]
        res = client.get(f"/api/v1/datasets/{ds_id}/profile")
        assert res.status_code == 200

    def test_get_profile_contains_duplicate_rows(self, client, uploaded_dataset):
        ds_id = uploaded_dataset["dataset_id"]
        data = client.get(f"/api/v1/datasets/{ds_id}/profile").json()
        assert "duplicate_rows" in data

    def test_get_profile_nonexistent_returns_404(self, client):
        res = client.get("/api/v1/datasets/nonexistent/profile")
        assert res.status_code == 404

    def test_get_quality_returns_200(self, client, uploaded_dataset):
        ds_id = uploaded_dataset["dataset_id"]
        res = client.get(f"/api/v1/datasets/{ds_id}/quality")
        assert res.status_code == 200

    def test_get_quality_contains_overall_score(self, client, uploaded_dataset):
        ds_id = uploaded_dataset["dataset_id"]
        data = client.get(f"/api/v1/datasets/{ds_id}/quality").json()
        assert "overall_score" in data

    def test_get_quality_nonexistent_returns_404(self, client):
        res = client.get("/api/v1/datasets/nonexistent/quality")
        assert res.status_code == 404


# ===========================================================================
# Versioning Tests
# ===========================================================================

class TestDatasetVersions:

    def test_get_versions_returns_200(self, client, uploaded_dataset):
        ds_id = uploaded_dataset["dataset_id"]
        res = client.get(f"/api/v1/datasets/{ds_id}/versions")
        assert res.status_code == 200

    def test_get_versions_contains_at_least_one_version(self, client, uploaded_dataset):
        ds_id = uploaded_dataset["dataset_id"]
        data = client.get(f"/api/v1/datasets/{ds_id}/versions").json()
        assert data["total_count"] >= 1
        assert len(data["versions"]) >= 1

    def test_get_versions_nonexistent_dataset_returns_404(self, client):
        res = client.get("/api/v1/datasets/nonexistent/versions")
        assert res.status_code == 404

    def test_get_specific_version_returns_200(self, client, uploaded_dataset):
        ds_id = uploaded_dataset["dataset_id"]
        res = client.get(f"/api/v1/datasets/{ds_id}/versions/1")
        assert res.status_code == 200

    def test_get_specific_version_number(self, client, uploaded_dataset):
        ds_id = uploaded_dataset["dataset_id"]
        data = client.get(f"/api/v1/datasets/{ds_id}/versions/1").json()
        assert data["version_number"] == 1


# ===========================================================================
# Recommendations Tests
# ===========================================================================

class TestDatasetRecommendations:

    def test_get_recommendations_returns_200(self, client, uploaded_dataset):
        ds_id = uploaded_dataset["dataset_id"]
        res = client.get(f"/api/v1/datasets/{ds_id}/recommendations")
        assert res.status_code == 200

    def test_get_recommendations_has_dataset_id(self, client, uploaded_dataset):
        ds_id = uploaded_dataset["dataset_id"]
        data = client.get(f"/api/v1/datasets/{ds_id}/recommendations").json()
        assert data["dataset_id"] == ds_id

    def test_get_recommendations_has_recommendations_list(self, client, uploaded_dataset):
        ds_id = uploaded_dataset["dataset_id"]
        data = client.get(f"/api/v1/datasets/{ds_id}/recommendations").json()
        assert "recommendations" in data
