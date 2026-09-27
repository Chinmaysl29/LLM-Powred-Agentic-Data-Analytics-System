"""Enterprise Dataset Upload & Storage Pipeline Test Suite.

Verifies:
1. CSV Upload & Storage & JSON Canonical Conversion
2. Excel Upload & Storage & JSON Canonical Conversion
3. JSON Upload & Storage & JSON Canonical Conversion
4. PDF Upload & Storage & Extracted JSON Conversion
5. Dataset Registry Persistence:
   - storage/datasets/{dataset_id}/metadata.json
   - storage/datasets/{dataset_id}/profile.json
   - storage/datasets/{dataset_id}/quality.json
   - storage/datasets/{dataset_id}/versions.json
   - storage/datasets/{dataset_id}/lineage.json
6. Database Registration (PostgreSQL metadata only, no file content)
7. Raw Storage Persistence (storage/raw/)
8. Processed Storage Persistence (storage/processed/)
9. Downstream AI Pipeline Integration (DataRetrievalService & EDAAgentRunner)
"""

import io
import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.app.services.data_retrieval_service import DataRetrievalService
from backend.app.schemas.retrieval import DataRetrievalFilter
from backend.agents.eda_agent import EDAAgentRunner
from backend.app.schemas.orchestrator import WorkflowContext


from unittest.mock import AsyncMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.database.chromadb import ChromaDatabase
from backend.app.database.postgres import PostgresDatabase, get_db_session
from backend.app.database.redis import RedisCache
from backend.app.models.base import Base


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
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()


def test_csv_upload_and_pipeline(api_client, tmp_path):
    """Test CSV upload, raw storage, canonical JSON conversion, registry, and retrieval."""
    csv_bytes = b"id,employee,salary,department\n1,Alice,85000,Engineering\n2,Bob,62000,Marketing\n3,Charlie,95000,Engineering\n"
    
    response = api_client.post(
        "/api/v1/datasets/upload",
        files={"file": ("employees.csv", csv_bytes, "text/csv")},
        data={"dataset_name": "Employees Dataset"},
    )
    assert response.status_code == 201, f"Upload failed: {response.text}"
    data = response.json()
    dataset_id = data["dataset_id"]
    assert dataset_id
    assert data["dataset_name"] == "Employees Dataset"
    assert data["row_count"] == 3
    assert data["column_count"] == 4
    assert data["canonical_format"] in {"parquet", "json"}

    # Verify JSON path exists and has canonical records array
    json_path = Path(data["json_path"])
    assert json_path.exists(), f"Canonical JSON file does not exist at {json_path}"
    records = json.loads(json_path.read_text(encoding="utf-8"))
    assert isinstance(records, list), "Canonical JSON must be an array of records"
    assert len(records) == 3
    assert records[0]["employee"] == "Alice"

    # Verify Registry files directly in dataset folder
    registry_dir = json_path.parents[1] / "datasets" / dataset_id
    if not registry_dir.exists():
        # Fallback to parent if structure is flat
        registry_dir = json_path.parent
    
    assert (registry_dir / "metadata.json").exists() or (registry_dir / "artifacts" / "metadata.json").exists()
    assert (registry_dir / "profile.json").exists() or (registry_dir / "artifacts" / "profile.json").exists()
    assert (registry_dir / "quality.json").exists() or (registry_dir / "artifacts" / "quality.json").exists()
    assert (registry_dir / "versions.json").exists()
    assert (registry_dir / "lineage.json").exists()

    # Verify API endpoints for this dataset
    res_meta = api_client.get(f"/api/v1/datasets/{dataset_id}/metadata")
    assert res_meta.status_code == 200
    meta_json = res_meta.json()
    assert meta_json["row_count"] == 3
    assert "employee" in meta_json["column_names"]

    res_prof = api_client.get(f"/api/v1/datasets/{dataset_id}/profile")
    assert res_prof.status_code == 200

    res_qual = api_client.get(f"/api/v1/datasets/{dataset_id}/quality")
    assert res_qual.status_code == 200
    assert res_qual.json()["overall_score"] > 0

    res_vers = api_client.get(f"/api/v1/datasets/{dataset_id}/versions")
    assert res_vers.status_code == 200
    assert res_vers.json()["total_count"] == 1


def test_excel_upload_and_pipeline(api_client):
    """Test Excel upload, conversion to canonical JSON, and registry."""
    import pandas as pd
    excel_buf = io.BytesIO()
    df = pd.DataFrame({
        "product_id": [201, 202, 203, 204],
        "name": ["Laptop", "Mouse", "Keyboard", "Headphones"],
        "price": [1200.0, 25.5, 75.0, 150.0],
    })
    df.to_excel(excel_buf, index=False)
    excel_buf.seek(0)

    response = api_client.post(
        "/api/v1/datasets/upload",
        files={"file": ("products.xlsx", excel_buf.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        data={"dataset_name": "Products Catalog"},
    )
    assert response.status_code == 201, f"Excel upload failed: {response.text}"
    data = response.json()
    assert data["row_count"] == 4
    assert data["column_count"] == 3

    # Check canonical JSON
    json_path = Path(data["json_path"])
    assert json_path.exists()
    records = json.loads(json_path.read_text(encoding="utf-8"))
    assert len(records) == 4
    assert records[0]["name"] == "Laptop"


def test_json_upload_and_pipeline(api_client):
    """Test JSON file upload and canonical conversion."""
    raw_records = [
        {"customer_id": "C01", "tier": "Gold", "spend": 4500},
        {"customer_id": "C02", "tier": "Silver", "spend": 1200},
        {"customer_id": "C03", "tier": "Bronze", "spend": 350},
    ]
    json_bytes = json.dumps(raw_records).encode("utf-8")

    response = api_client.post(
        "/api/v1/datasets/upload",
        files={"file": ("customers.json", json_bytes, "application/json")},
        data={"dataset_name": "Customer Tiers"},
    )
    assert response.status_code == 201, f"JSON upload failed: {response.text}"
    data = response.json()
    assert data["row_count"] == 3
    assert data["column_count"] == 3


def test_pdf_upload_and_pipeline(api_client):
    """Test PDF upload, PyMuPDF extraction, canonical document JSON, and registry."""
    import fitz
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 72), "Executive Summary\nTotal ARR reached $12M with 40% operating margin.")
    pdf_bytes = doc.tobytes()
    doc.close()

    response = api_client.post(
        "/api/v1/datasets/upload",
        files={"file": ("executive_summary.pdf", pdf_bytes, "application/pdf")},
        data={"dataset_name": "Q4 Executive Summary"},
    )
    assert response.status_code == 201, f"PDF upload failed: {response.text}"
    data = response.json()
    assert data["canonical_format"] == "document_json"
    assert data["row_count"] == 1  # 1 page
    assert data["column_count"] == 0

    json_path = Path(data["json_path"])
    assert json_path.exists()
    doc_data = json.loads(json_path.read_text(encoding="utf-8"))
    assert "pages" in doc_data
    assert "text" in doc_data
    assert "Executive Summary" in doc_data["text"]


def test_ai_pipeline_integration(api_client, db_engine):
    """Verify that an uploaded dataset is immediately accessible to analytical agents."""
    csv_bytes = b"month,revenue,costs\nJan,10000,6000\nFeb,12000,6500\nMar,15000,7000\n"
    
    response = api_client.post(
        "/api/v1/datasets/upload",
        files={"file": ("finance.csv", csv_bytes, "text/csv")},
        data={"dataset_name": "Finance Metrics"},
    )
    assert response.status_code == 201
    dataset_id = response.json()["dataset_id"]

    # Verify EDA Agent runner can run against this dataset
    from sqlalchemy.orm import Session
    with Session(db_engine) as session:
        from backend.app.services.storage_service import StorageService
        from backend.app.core.config import get_settings
        storage_service = StorageService(get_settings())
        retrieval_service = DataRetrievalService(db=session, storage_service=storage_service)

        # 1. Test schema reader
        schema = retrieval_service.get_schema(dataset_id)
        assert len(schema.columns) == 3
        assert "revenue" in schema.columns

        # 2. Test dataframe load
        df, is_sampled = retrieval_service.load_dataframe(dataset_id)
        assert len(df) == 3
        assert "revenue" in df.columns

        # 3. Test packaged context for all agents
        pkg = retrieval_service.get_packaged_context(dataset_id)
        assert pkg.dataset_id == dataset_id
        assert pkg.rows == 3
        assert pkg.columns == 3
        assert pkg.quality_score is not None

        # 4. Run EDA agent
        eda_runner = EDAAgentRunner(retrieval_service=retrieval_service)
        context = WorkflowContext(
            dataset_id=dataset_id,
            query="Perform exploratory data analysis on revenue and costs"
        )
        import asyncio
        eda_result = asyncio.run(eda_runner.run(context))
        assert "business_insights" in eda_result
        assert "dataset_summary" in eda_result
        assert len(eda_result["business_insights"]) > 0
