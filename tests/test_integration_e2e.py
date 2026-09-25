"""
End-to-end integration tests that exercise the full backend pipeline:
1. Upload dataset → all downstream tables → EDA → Statistics → Summary
2. Auth flow: Register → Login → Protected endpoint → Refresh → Logout
3. Orchestrator end-to-end: Query → Intent → Workflow → All agents → Result
4. RAG pipeline: Ingest → Query → Answer
5. Workspace management: Tenant → Workspace → CRUD lifecycle
6. Forecasting pipeline: Validate → Forecast → Scenarios
"""

import io
import json
import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock

import numpy as np
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.database.chromadb import ChromaDatabase
from backend.app.database.postgres import PostgresDatabase, get_db_session
from backend.app.database.redis import RedisCache
from backend.app.main import create_app
from backend.app.models.base import Base
from backend.app.models.dataset import Dataset
from backend.app.models.dataset_metadata import DatasetMetadata
from backend.app.models.dataset_profile import DatasetProfile
from backend.app.models.dataset_quality import DatasetQuality
from backend.app.models.dataset_version import DatasetVersion
from backend.app.models.tenant import Tenant
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
def e2e_client(db_engine, monkeypatch):
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


# ===========================================================================
# E2E 1: Full Dataset Upload Pipeline
# ===========================================================================

class TestE2EDatasetPipeline:
    """Complete dataset upload → all tables → sub-resource endpoints."""

    CSV_DATA = (
        b"product_id,product_name,price,category,quantity\n"
        b"101,Widget,19.99,Tools,50\n"
        b"102,Gadget,29.99,Electronics,30\n"
        b"103,Doohickey,9.99,Misc,100\n"
        b"104,Thingamajig,49.99,Premium,15\n"
        b"105,Whatsit,14.99,Misc,75\n"
    )

    def test_upload_and_full_pipeline(self, e2e_client, db_engine):
        """Upload CSV → verify all 5 downstream tables → all sub-endpoints return data."""

        # Step 1: Upload
        res = e2e_client.post(
            "/api/v1/datasets/upload",
            files={"file": ("products.csv", io.BytesIO(self.CSV_DATA), "text/csv")},
            data={"dataset_name": "E2E Product Catalog"},
        )
        assert res.status_code == 201, res.text
        ds_id = res.json()["dataset_id"]
        assert ds_id

        # Step 2: Verify DB persistence
        SessionFactory = sessionmaker(bind=db_engine)
        with SessionFactory() as s:
            assert s.query(Dataset).filter_by(dataset_id=ds_id).count() == 1
            assert s.query(DatasetMetadata).filter_by(dataset_id=ds_id).count() == 1
            assert s.query(DatasetProfile).filter_by(dataset_id=ds_id).count() == 1
            assert s.query(DatasetQuality).filter_by(dataset_id=ds_id).count() == 1
            assert s.query(DatasetVersion).filter_by(dataset_id=ds_id).count() >= 1

        # Step 3: GET /datasets/{id}
        get_res = e2e_client.get(f"/api/v1/datasets/{ds_id}")
        assert get_res.status_code == 200
        assert get_res.json()["dataset_id"] == ds_id

        # Step 4: GET /metadata
        meta_res = e2e_client.get(f"/api/v1/datasets/{ds_id}/metadata")
        assert meta_res.status_code == 200
        assert meta_res.json()["row_count"] == 5
        assert "product_name" in meta_res.json()["column_names"]

        # Step 5: GET /profile
        prof_res = e2e_client.get(f"/api/v1/datasets/{ds_id}/profile")
        assert prof_res.status_code == 200
        assert "duplicate_rows" in prof_res.json()

        # Step 6: GET /quality
        qual_res = e2e_client.get(f"/api/v1/datasets/{ds_id}/quality")
        assert qual_res.status_code == 200
        assert "overall_score" in qual_res.json()

        # Step 7: GET /versions
        ver_res = e2e_client.get(f"/api/v1/datasets/{ds_id}/versions")
        assert ver_res.status_code == 200
        assert ver_res.json()["total_count"] >= 1

        # Step 8: GET /recommendations
        rec_res = e2e_client.get(f"/api/v1/datasets/{ds_id}/recommendations")
        assert rec_res.status_code == 200

        # Step 9: DELETE
        del_res = e2e_client.delete(f"/api/v1/datasets/{ds_id}")
        assert del_res.status_code == 200

        # Step 10: Confirm deletion
        assert e2e_client.get(f"/api/v1/datasets/{ds_id}").status_code == 404


# ===========================================================================
# E2E 2: Authentication Flow
# ===========================================================================

class TestE2EAuthFlow:
    """Full auth cycle: register → login → access protected → refresh → logout."""

    def test_full_auth_lifecycle(self, e2e_client):
        email = f"e2e-{uuid.uuid4().hex[:8]}@example.com"
        password = "SecureE2EPass1!"

        # Step 1: Register
        reg_res = e2e_client.post("/api/v1/auth/register", json={
            "email": email,
            "password": password,
            "full_name": "E2E User",
        })
        assert reg_res.status_code == 201
        assert reg_res.json()["email"] == email

        # Step 2: Login
        login_res = e2e_client.post("/api/v1/auth/login", json={
            "email": email, "password": password,
        })
        assert login_res.status_code == 200
        tokens = login_res.json()
        assert "access_token" in tokens
        assert "refresh_token" in tokens

        access_token = tokens["access_token"]
        refresh_token = tokens["refresh_token"]

        # Step 3: Access protected endpoint
        profile_res = e2e_client.get(
            "/api/v1/auth/profile",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert profile_res.status_code == 200
        assert profile_res.json()["email"] == email

        # Step 4: Refresh token
        refresh_res = e2e_client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
        assert refresh_res.status_code == 200
        new_access = refresh_res.json()["access_token"]
        assert new_access != access_token

        # Step 5: Old refresh token must be revoked
        reuse_res = e2e_client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
        assert reuse_res.status_code == 401

        # Step 6: Logout
        logout_res = e2e_client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {new_access}"},
        )
        assert logout_res.status_code == 200
        assert logout_res.json()["status"] == "success"

    def test_wrong_credentials_blocked(self, e2e_client):
        e2e_client.post("/api/v1/auth/register", json={
            "email": "locked@example.com", "password": "ValidPass1!",
        })
        res = e2e_client.post("/api/v1/auth/login", json={
            "email": "locked@example.com", "password": "WrongPassword!",
        })
        assert res.status_code == 401


# ===========================================================================
# E2E 3: Orchestrator End-to-End Pipeline
# ===========================================================================

class TestE2EOrchestratorPipeline:
    """Intent → Workflow → Sequential Agents → Aggregated Result."""

    def test_orchestrator_trend_analysis_full_pipeline(self, e2e_client):
        res = e2e_client.post("/api/v1/orchestrator/execute", json={
            "query": "Show me revenue trends for the last quarter",
        })
        assert res.status_code == 200
        data = res.json()

        assert data["intent"] == "trend_analysis"
        assert data["status"] == "success"
        assert len(data["workflow"]) >= 2
        assert len(data["executed_agents"]) >= 1
        assert data["execution_time_ms"] >= 0
        assert data["summary"]

    def test_orchestrator_forecasting_pipeline(self, e2e_client):
        res = e2e_client.post("/api/v1/orchestrator/execute", json={
            "query": "Forecast sales for the next 6 months",
        })
        assert res.status_code == 200
        data = res.json()
        assert data["intent"] == "forecasting"

    def test_orchestrator_data_quality_pipeline(self, e2e_client):
        res = e2e_client.post("/api/v1/orchestrator/execute", json={
            "query": "Check data quality and find missing values",
        })
        assert res.status_code == 200
        assert res.json()["intent"] == "data_quality"

    def test_intent_then_orchestrate_consistency(self, e2e_client):
        """Intent classification and orchestration must agree on the same intent."""
        query = "Show revenue trends over time"
        intent_res = e2e_client.post("/api/v1/intent/classify", json={"query": query})
        orch_res = e2e_client.post("/api/v1/orchestrator/execute", json={"query": query})

        assert intent_res.status_code == 200
        assert orch_res.status_code == 200
        assert intent_res.json()["intent"] == orch_res.json()["intent"]


# ===========================================================================
# E2E 4: RAG Pipeline
# ===========================================================================

class TestE2ERAGPipeline:
    """Ingest → Query → Validate answer quality."""

    def test_ingest_then_query(self):
        app = create_app()
        with TestClient(app) as c:
            # Ingest a knowledge document
            ingest_res = c.post("/api/v1/rag/ingest", json={
                "document_id": "e2e-knowledge-001",
                "content": (
                    "The company achieved record revenue of $5M in Q3 2024. "
                    "Customer acquisition cost decreased by 18% due to improved targeting. "
                    "Net Promoter Score improved from 42 to 67 year-over-year."
                ),
                "metadata": {"source": "quarterly_report", "year": 2024},
            })
            assert ingest_res.status_code == 200
            assert ingest_res.json()["chunks_created"] >= 1

            # Query the pipeline
            query_res = c.post("/api/v1/rag/query", json={
                "query": "What was the revenue in Q3 2024?",
                "top_k": 3,
            })
            assert query_res.status_code == 200
            assert isinstance(query_res.json()["answer"], str)

    def test_rag_health_check(self):
        app = create_app()
        with TestClient(app) as c:
            res = c.get("/api/v1/rag/health")
        assert res.status_code == 200
        assert res.json()["status"] == "ok"


# ===========================================================================
# E2E 5: Workspace Management Lifecycle
# ===========================================================================

class TestE2EWorkspacePipeline:
    """Create tenant → create workspace → update → delete."""

    def test_full_workspace_lifecycle(self, e2e_client, db_engine):
        # Seed tenant in DB
        SessionFactory = sessionmaker(bind=db_engine)
        tenant_id = uuid.uuid4()
        with SessionFactory() as s:
            t = Tenant(
                id=tenant_id,
                tenant_name="E2E Corp",
                tenant_slug=f"e2e-corp-{tenant_id.hex[:6]}",
            )
            s.add(t)
            s.commit()

        # Create workspace
        create_res = e2e_client.post("/api/v1/workspaces", json={
            "tenant_id": str(tenant_id),
            "workspace_name": "Analytics Hub",
            "workspace_slug": "analytics-hub",
        })
        assert create_res.status_code == 201
        ws_id = create_res.json()["id"]

        # Get workspace
        get_res = e2e_client.get(f"/api/v1/workspaces/{ws_id}")
        assert get_res.status_code == 200
        assert get_res.json()["workspace_name"] == "Analytics Hub"

        # Update workspace
        upd_res = e2e_client.put(f"/api/v1/workspaces/{ws_id}", json={
            "workspace_name": "Updated Analytics Hub",
            "status": "active",
        })
        assert upd_res.status_code == 200
        assert upd_res.json()["workspace_name"] == "Updated Analytics Hub"

        # List workspaces
        list_res = e2e_client.get(f"/api/v1/workspaces?tenant_id={tenant_id}")
        assert list_res.status_code == 200
        items = list_res.json()["items"]
        assert any(w["id"] == ws_id for w in items)

        # Delete workspace
        del_res = e2e_client.delete(f"/api/v1/workspaces/{ws_id}")
        assert del_res.status_code == 200

        # Confirm gone
        assert e2e_client.get(f"/api/v1/workspaces/{ws_id}").status_code == 404


# ===========================================================================
# E2E 6: Forecasting Pipeline
# ===========================================================================

class TestE2EForecastingPipeline:
    """Validate → Forecast (ARIMA) → Scenarios."""

    def _records(self, n=36):
        base = datetime(2021, 1, 1)
        np.random.seed(99)
        vals = np.linspace(1000, 5000, n) + np.random.normal(0, 100, n)
        return [
            {
                "date": (base + timedelta(days=30 * i)).strftime("%Y-%m-%d"),
                "value": float(max(v, 1.0)),
            }
            for i in range(n)
        ]

    def test_validate_then_forecast(self):
        app = create_app()
        with TestClient(app) as c:
            # Validate
            val_res = c.post("/api/v1/forecasting/validate", json={
                "records": self._records(36),
                "time_column": "date",
                "target_column": "value",
                "frequency": "monthly",
            })
            assert val_res.status_code == 200
            assert val_res.json()["is_valid"] is True

            # Forecast
            fc_res = c.post("/api/v1/forecasting/arima", json={
                "series": self._records(36),
                "target": "revenue",
                "horizon": 6,
                "frequency": "monthly",
            })
            assert fc_res.status_code == 200
            assert len(fc_res.json()["forecast_values"]) == 6

    def test_full_pipeline_endpoint(self):
        app = create_app()
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from sqlalchemy.pool import StaticPool

        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(bind=engine)
        SessionFactory = sessionmaker(bind=engine)

        def override_db():
            s = SessionFactory()
            try:
                yield s
            finally:
                s.close()

        app.dependency_overrides[get_db_session] = override_db

        with TestClient(app) as c:
            res = c.post("/api/v1/forecasting/pipeline", json={
                "series": self._records(36),
                "target": "revenue",
                "horizon": 6,
                "frequency": "monthly",
                "what_if_query": "marketing +10%",
            })
        assert res.status_code == 200
        Base.metadata.drop_all(bind=engine)
        app.dependency_overrides.clear()


# ===========================================================================
# E2E 7: Audit Trail Lifecycle
# ===========================================================================

class TestE2EAuditTrail:
    """Record → Query → Export → Get by ID."""

    def test_audit_record_and_query(self, e2e_client):
        # Record event
        rec_res = e2e_client.post("/api/v1/audit", json={
            "actor": "e2e-user",
            "action": "dataset.upload",
            "resource_type": "dataset",
            "resource_id": "ds-e2e-001",
            "details": {"file_name": "sales.csv"},
            "status": "success",
        })
        assert rec_res.status_code == 201
        event_id = rec_res.json()["id"]

        # Query all events
        query_res = e2e_client.get("/api/v1/audit?actor=e2e-user")
        assert query_res.status_code == 200
        events = query_res.json()
        assert any(e["id"] == event_id for e in events)

        # Export JSON
        export_res = e2e_client.get("/api/v1/audit/export?format=json")
        assert export_res.status_code == 200
