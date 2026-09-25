"""Integration and unit tests for the Phase 3.4 Data Retrieval Agent."""

import json
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.main import create_app
from backend.app.models.base import Base
from backend.app.core.exceptions import (
    CorruptedFileError,
    DatasetNotFoundError,
    VersionNotFoundError,
)
from backend.app.models.dataset import Dataset
from backend.app.models.dataset_metadata import DatasetMetadata
from backend.app.models.dataset_profile import DatasetProfile
from backend.app.models.dataset_quality import DatasetQuality
from backend.app.models.dataset_version import DatasetVersion
from backend.app.schemas.retrieval import DataRetrievalFilter, FilterCondition, DateRangeFilter
from backend.app.services.data_retrieval_service import DataRetrievalService


@pytest.fixture
def test_dataset_dir(tmp_path: Path) -> Path:
    """Fixture providing a temporary directory for test datasets."""
    d = tmp_path / "datasets"
    d.mkdir()
    
    # Create a small CSV
    csv_file = d / "test_data.csv"
    pd.DataFrame({
        "id": [1, 2, 3, 4, 5],
        "city": ["Bengaluru", "Mumbai", "Delhi", "Chennai", "Bengaluru"],
        "sales": [100, 200, 150, 300, 250],
        "date": ["2023-01-01", "2023-01-02", "2023-01-03", "2023-01-04", "2023-01-05"]
    }).to_csv(csv_file, index=False)
    
    # Create a large CSV to test sampling
    large_csv = d / "large_data.csv"
    pd.DataFrame({
        "id": range(1001),
        "val": range(1001)
    }).to_csv(large_csv, index=False)
    
    return d


@pytest.fixture
def mock_storage_service(test_dataset_dir: Path):
    class MockStorage:
        def retrieve_file(self, path: str):
            return test_dataset_dir / path
    return MockStorage()


@pytest.fixture
def in_memory_db() -> Session:
    """Isolated in-memory SQLite database session."""
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
def api_client() -> TestClient:
    app = create_app()
    return TestClient(app)


@pytest.fixture
def retrieval_db_session(in_memory_db: Session) -> Session:
    """Populate database with test records."""
    ds = Dataset(
        dataset_id="test_ds_1",
        dataset_name="Test Dataset",
        file_name="test_data.csv",
        file_type="csv",
        file_path="test_data.csv",
        status="active"
    )
    v1 = DatasetVersion(
        version_id="v1",
        dataset_id="test_ds_1",
        version_number=1,
        storage_path="test_data.csv",
        change_type="initial_upload",
        metadata_snapshot={},
        quality_snapshot={},
        created_by="test",
        is_active=True
    )
    meta = DatasetMetadata(
        dataset_id="test_ds_1",
        row_count=5,
        column_count=4,
        column_names=["id", "city", "sales", "date"],
        column_types={"id": "int64", "city": "object", "sales": "int64", "date": "object"},
        columns_metadata=[],
        classifications={"numeric": [], "categorical": [], "datetime": [], "boolean": []}
    )
    prof = DatasetProfile(
        dataset_id="test_ds_1",
        duplicate_rows=0,
        duplicate_percentage=0.0,
        missing_data_profile={"null_count": 0, "null_percentage": 0.0, "columns_with_missing": []},
        cardinality_profile={"high_cardinality_columns": [], "low_cardinality_columns": []},
        numeric_columns_profile={
            "sales": {
                "mean": 200.0,
                "median": 200.0,
                "min": 100.0,
                "max": 300.0,
                "std": 50.0,
                "variance": 2500.0,
                "p25": 150.0,
                "p50": 200.0,
                "p75": 250.0,
                "skewness": 0.0,
                "kurtosis": 0.0
            }
        }
    )
    qual = DatasetQuality(
        dataset_id="test_ds_1",
        completeness_score=100.0,
        uniqueness_score=100.0,
        consistency_score=100.0,
        validity_score=100.0,
        integrity_score=100.0,
        overall_score=95.0,
        quality_classification="high"
    )
    
    large_ds = Dataset(
        dataset_id="large_ds",
        dataset_name="Large Dataset",
        file_name="large_data.csv",
        file_type="csv",
        file_path="large_data.csv",
        status="active"
    )
    large_v1 = DatasetVersion(
        version_id="large_v1",
        dataset_id="large_ds",
        version_number=1,
        storage_path="large_data.csv",
        change_type="initial_upload",
        metadata_snapshot={},
        quality_snapshot={},
        created_by="test",
        is_active=True
    )

    in_memory_db.add_all([ds, v1, meta, prof, qual, large_ds, large_v1])
    in_memory_db.commit()
    return in_memory_db


@pytest.fixture
def retrieval_service(retrieval_db_session: Session, mock_storage_service) -> DataRetrievalService:
    return DataRetrievalService(db=retrieval_db_session, storage_service=mock_storage_service)


def test_discover_success(retrieval_service: DataRetrievalService):
    ds, v, m, p, q = retrieval_service.discover("test_ds_1")
    assert ds.dataset_id == "test_ds_1"
    assert v.version_number == 1
    assert m.row_count == 5
    assert p.numeric_columns_profile["sales"]["mean"] == 200
    assert q.overall_score == 95.0


def test_discover_not_found(retrieval_service: DataRetrievalService):
    with pytest.raises(DatasetNotFoundError):
        retrieval_service.discover("unknown")


def test_get_schema_from_metadata(retrieval_service: DataRetrievalService):
    schema = retrieval_service.get_schema("test_ds_1")
    assert schema.columns == ["id", "city", "sales", "date"]
    assert schema.row_count == 5


def test_load_dataframe_full(retrieval_service: DataRetrievalService):
    df, is_sampled = retrieval_service.load_dataframe("test_ds_1")
    assert not is_sampled
    assert len(df) == 5
    assert list(df.columns) == ["id", "city", "sales", "date"]


def test_load_dataframe_filtered(retrieval_service: DataRetrievalService):
    filters = DataRetrievalFilter(
        columns=["city", "sales"],
        conditions=[
            FilterCondition(column="city", operator="eq", value="Bengaluru")
        ]
    )
    df, is_sampled = retrieval_service.load_dataframe("test_ds_1", filters=filters)
    assert not is_sampled
    assert len(df) == 2
    assert list(df.columns) == ["city", "sales"]
    assert all(df["city"] == "Bengaluru")


def test_load_dataframe_date_filter(retrieval_service: DataRetrievalService):
    filters = DataRetrievalFilter(
        date_range=DateRangeFilter(column="date", start_date="2023-01-03", end_date="2023-01-04")
    )
    df, is_sampled = retrieval_service.load_dataframe("test_ds_1", filters=filters)
    assert len(df) == 2
    assert df.iloc[0]["id"] == 3


def test_load_dataframe_sampling(retrieval_service: DataRetrievalService):
    df, is_sampled = retrieval_service.load_dataframe("large_ds", sample_size=100)
    assert is_sampled
    assert len(df) == 100


def test_get_packaged_context(retrieval_service: DataRetrievalService):
    ctx = retrieval_service.get_packaged_context("test_ds_1")
    assert ctx.dataset_id == "test_ds_1"
    assert ctx.rows == 5
    assert ctx.columns == 4
    assert ctx.quality_score == 95.0
    assert ctx.active_version == 1
    assert ctx.metadata is not None
    assert ctx.profile is not None


def test_api_get_package(api_client: TestClient, retrieval_db_session: Session, mock_storage_service):
    # Override dependency
    from backend.app.api.v1.routes.retrieval import get_data_retrieval_service
    
    api_client.app.dependency_overrides[get_data_retrieval_service] = lambda: DataRetrievalService(
        db=retrieval_db_session, storage_service=mock_storage_service
    )
    
    response = api_client.get("/api/v1/retrieval/test_ds_1/package")
    assert response.status_code == 200
    data = response.json()
    assert data["dataset_id"] == "test_ds_1"
    assert data["rows"] == 5
    assert data["quality_score"] == 95.0
    
    # Clean up
    api_client.app.dependency_overrides.clear()


def test_api_post_query(api_client: TestClient, retrieval_db_session: Session, mock_storage_service):
    from backend.app.api.v1.routes.retrieval import get_data_retrieval_service
    
    api_client.app.dependency_overrides[get_data_retrieval_service] = lambda: DataRetrievalService(
        db=retrieval_db_session, storage_service=mock_storage_service
    )
    
    payload = {
        "dataset_id": "test_ds_1",
        "sample_size": 2
    }
    response = api_client.post("/api/v1/retrieval/test_ds_1/query", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["dataset_id"] == "test_ds_1"
    assert data["is_sampled"] is True
    assert data["total_rows_returned"] == 2
    
    api_client.app.dependency_overrides.clear()
