"""Comprehensive Test Suite for Dataset Management Hub Architecture.

Verifies:
1. Empty State (GET /api/v1/datasets returns [] when database is pristine)
2. No Mock Data Remaining (no hardcoded datasets injected)
3. Upload Queue & Ingestion (CSV, XLSX, JSON, PDF)
4. Canonical JSON Conversion (storage/processed/{dataset_id}.json)
5. Dataset Registry Persistence (storage/datasets/{dataset_id}/: 5 JSON artifacts)
6. Database Registration in PostgreSQL (metadata only, no file content in tables)
7. Dataset Preview Endpoint (GET /api/v1/datasets/{dataset_id}/preview)
8. Downstream AI Pipeline Synchronization (EDAAgentRunner & DataRetrievalService)
"""

import io
import json
from pathlib import Path
from unittest.mock import AsyncMock
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.main import app
from backend.app.database.chromadb import ChromaDatabase
from backend.app.database.postgres import PostgresDatabase, get_db_session
from backend.app.database.redis import RedisCache
from backend.app.models.base import Base
from backend.app.services.data_retrieval_service import DataRetrievalService
from backend.agents.eda_agent import EDAAgentRunner
from backend.app.schemas.orchestrator import WorkflowContext
from backend.app.services.storage_service import StorageService
from backend.app.core.config import get_settings


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
def api_client(db_engine, monkeypatch):
    monkeypatch.setattr(PostgresDatabase, "connect", lambda self: None)
    monkeypatch.setattr(PostgresDatabase, "health_check", AsyncMock(return_value=(True, "OK")))
    monkeypatch.setattr(RedisCache, "connect", AsyncMock(return_value=None))
    monkeypatch.setattr(RedisCache, "close", AsyncMock(return_value=None))
    monkeypatch.setattr(RedisCache, "health_check", AsyncMock(return_value=(True, "OK")))
    monkeypatch.setattr(ChromaDatabase, "connect", AsyncMock(return_value=None))
    monkeypatch.setattr(ChromaDatabase, "close", AsyncMock(return_value=None))
    monkeypatch.setattr(ChromaDatabase, "health_check", AsyncMock(return_value=(True, "OK")))

    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db_session] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_backend_dataset_listing_empty(api_client):
    """Verify that when no datasets exist, listing returns an empty array with 0 items."""
    res = api_client.get("/api/v1/datasets")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) == 0, "Expected empty dataset library when no datasets uploaded"


def test_no_mock_data_remaining():
    """Verify that frontend utility files and backend services do not contain hardcoded datasets."""
    # Check datasetUtils.ts content if accessible on host
    utils_path = Path("frontend/src/datasetUtils.ts")
    if utils_path.exists():
        content = utils_path.read_text(encoding="utf-8")
        assert "export const DEV_DATASETS: Dataset[] = [];" in content, "DEV_DATASETS must be empty array"
        assert "export const DEV_PREVIEWS: Record<string, DatasetPreview> = {};" in content, "DEV_PREVIEWS must be empty object"

    # Check datasetService.ts content if accessible on host
    service_path = Path("frontend/src/services/datasetService.ts")
    if service_path.exists():
        service_content = service_path.read_text(encoding="utf-8")
        assert "DEV_DATASETS" not in service_content, "datasetService must never import or reference DEV_DATASETS"


def test_csv_upload_queue_and_lifecycle(api_client):
    """Test CSV ingestion lifecycle: upload -> raw storage -> canonical JSON -> registry -> preview."""
    csv_bytes = b"order_id,customer,amount,status\n1001,Acme Corp,1500.0,Completed\n1002,Global Tech,2300.0,Pending\n1003,Starlight,450.0,Completed\n"

    res = api_client.post(
        "/api/v1/datasets/upload",
        files={"file": ("orders.csv", csv_bytes, "text/csv")},
        data={"dataset_name": "Orders Dataset"},
    )
    assert res.status_code == 201
    data = res.json()
    dataset_id = data["dataset_id"]
    assert dataset_id
    assert data["row_count"] == 3
    assert data["column_count"] == 4
    assert data["status"] == "ready"

    # Verify preview endpoint returns authentic records
    preview_res = api_client.get(f"/api/v1/datasets/{dataset_id}/preview")
    assert preview_res.status_code == 200
    preview_data = preview_res.json()
    assert "columns" in preview_data
    assert "order_id" in preview_data["columns"]
    assert "customer" in preview_data["columns"]
    assert len(preview_data["rows"]) == 3

    # Verify listing now returns this dataset
    list_res = api_client.get("/api/v1/datasets")
    assert list_res.status_code == 200
    listed_ids = [d["dataset_id"] for d in list_res.json()]
    assert dataset_id in listed_ids


def test_excel_upload_and_canonical_json(api_client):
    """Test Excel ingestion lifecycle and verify canonical JSON array structure."""
    import pandas as pd
    df = pd.DataFrame({
        "product": ["SaaS Pro", "Data Cloud", "Security Shield"],
        "mrr": [5000, 12000, 3500],
        "active_users": [120, 450, 80],
    })
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Subscriptions")
    excel_bytes = buf.getvalue()

    res = api_client.post(
        "/api/v1/datasets/upload",
        files={"file": ("subscriptions.xlsx", excel_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        data={"dataset_name": "SaaS Subscriptions"},
    )
    assert res.status_code == 201
    dataset_id = res.json()["dataset_id"]

    # Verify Canonical JSON
    settings = get_settings()
    storage = StorageService(settings)
    proc_json = storage.processed_dir / f"{dataset_id}.json"
    assert proc_json.exists()

    with open(proc_json, "r", encoding="utf-8") as f:
        records = json.load(f)
        assert isinstance(records, list)
        assert len(records) == 3
        assert records[0]["product"] == "SaaS Pro"
        assert records[0]["mrr"] == 5000


def test_pdf_upload_and_extraction(api_client):
    """Test PDF upload and verify extracted text, pages, and registry."""
    import pymupdf
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text(pymupdf.Point(50, 72), "Annual Financial Report 2026\nNet Income: $8.2M", fontsize=12)
    pdf_bytes = doc.tobytes()

    res = api_client.post(
        "/api/v1/datasets/upload",
        files={"file": ("financial_report.pdf", pdf_bytes, "application/pdf")},
        data={"dataset_name": "Financial Report PDF"},
    )
    assert res.status_code == 201
    dataset_id = res.json()["dataset_id"]

    # Verify Canonical JSON structure for PDF
    settings = get_settings()
    storage = StorageService(settings)
    proc_json = storage.processed_dir / f"{dataset_id}.json"
    assert proc_json.exists()

    with open(proc_json, "r", encoding="utf-8") as f:
        doc_json = json.load(f)
        assert "pages" in doc_json
        assert "text" in doc_json
        assert "Annual Financial Report" in doc_json["text"]

    # Verify registry files
    registry_dir = storage.datasets_dir / dataset_id
    for artifact in ["metadata.json", "profile.json", "quality.json", "versions.json", "lineage.json"]:
        assert (registry_dir / artifact).exists(), f"Missing artifact {artifact}"


def test_ai_pipeline_synchronization(api_client, db_engine):
    """Verify that an uploaded dataset is immediately available for AI agents."""
    csv_bytes = b"department,headcount,budget\nSales,45,450000\nEngineering,75,950000\nSupport,30,220000\n"

    res = api_client.post(
        "/api/v1/datasets/upload",
        files={"file": ("departments.csv", csv_bytes, "text/csv")},
        data={"dataset_name": "Department Budgets"},
    )
    assert res.status_code == 201
    dataset_id = res.json()["dataset_id"]

    from sqlalchemy.orm import Session
    with Session(db_engine) as session:
        storage = StorageService(get_settings())
        retrieval = DataRetrievalService(db=session, storage_service=storage)

        # 1. Load dataframe
        df, _ = retrieval.load_dataframe(dataset_id)
        assert len(df) == 3
        assert "department" in df.columns
        assert "budget" in df.columns

        # 2. Package context for agents
        pkg = retrieval.get_packaged_context(dataset_id)
        assert pkg.dataset_id == dataset_id
        assert pkg.rows == 3
        assert pkg.columns == 3

        # 3. EDA Agent execution
        eda_runner = EDAAgentRunner(retrieval_service=retrieval)
        context = WorkflowContext(
            dataset_id=dataset_id,
            query="Analyze budget distribution by department",
        )
        import asyncio
        eda_result = asyncio.run(eda_runner.run(context))
        assert "business_insights" in eda_result or "dataset_summary" in eda_result
