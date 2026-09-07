"""
Tests for workspace, audit, chat, operations, and enterprise API endpoints:
  POST /api/v1/workspaces
  GET  /api/v1/workspaces
  GET  /api/v1/workspaces/{id}
  PUT  /api/v1/workspaces/{id}
  DELETE /api/v1/workspaces/{id}
  POST /api/v1/audit
  GET  /api/v1/audit
  GET  /api/v1/audit/search
  GET  /api/v1/audit/{id}
  POST /api/v1/chat
  POST /api/v1/operations/feedback
  GET  /api/v1/operations/feedback/analytics
  POST /api/v1/operations/analytics/events
  GET  /api/v1/operations/analytics/metrics
  GET  /api/v1/operations/quality/status
  GET  /api/v1/operations/feature-flags
  GET  /api/v1/operations/costs
  GET  /api/v1/operations/dashboard
  GET  /api/v1/enterprise/tenants
  POST /api/v1/enterprise/tenants
  GET  /api/v1/enterprise/ecosystem/status
  POST /api/v1/autonomous/start
  GET  /api/v1/autonomous/status
"""

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
from backend.app.main import create_app
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


@pytest.fixture(scope="function")
def tenant_id(db_engine):
    """Seed a tenant in the DB and return its UUID."""
    from backend.app.models.tenant import Tenant
    SessionFactory = sessionmaker(bind=db_engine)
    with SessionFactory() as s:
        tid = uuid.uuid4()
        t = Tenant(
            id=tid,
            tenant_name="Test Tenant",
            tenant_slug=f"test-tenant-{tid.hex[:6]}",
        )
        s.add(t)
        s.commit()
    return str(tid)


# ===========================================================================
# Workspace Endpoint Tests
# ===========================================================================

class TestWorkspaceEndpoints:

    def test_create_workspace_returns_201(self, client, tenant_id):
        res = client.post("/api/v1/workspaces", json={
            "tenant_id": tenant_id,
            "workspace_name": "Finance Analytics",
            "workspace_slug": "finance-analytics",
        })
        assert res.status_code == 201

    def test_create_workspace_returns_workspace_data(self, client, tenant_id):
        data = client.post("/api/v1/workspaces", json={
            "tenant_id": tenant_id,
            "workspace_name": "Marketing Hub",
            "workspace_slug": "marketing-hub",
        }).json()
        assert data["workspace_name"] == "Marketing Hub"
        assert data["status"] == "active"

    def test_create_workspace_auto_generates_id(self, client, tenant_id):
        data = client.post("/api/v1/workspaces", json={
            "tenant_id": tenant_id,
            "workspace_name": "Sales Analytics",
        }).json()
        assert "id" in data
        assert len(data["id"]) > 0

    def test_list_workspaces_returns_200(self, client, tenant_id):
        res = client.get(f"/api/v1/workspaces?tenant_id={tenant_id}")
        assert res.status_code == 200

    def test_list_workspaces_returns_items(self, client, tenant_id):
        client.post("/api/v1/workspaces", json={
            "tenant_id": tenant_id,
            "workspace_name": "WS-List",
        })
        data = client.get(f"/api/v1/workspaces?tenant_id={tenant_id}").json()
        assert "items" in data
        assert isinstance(data["items"], list)

    def test_get_workspace_by_id_returns_200(self, client, tenant_id):
        created = client.post("/api/v1/workspaces", json={
            "tenant_id": tenant_id,
            "workspace_name": "Get WS",
        }).json()
        res = client.get(f"/api/v1/workspaces/{created['id']}")
        assert res.status_code == 200

    def test_get_nonexistent_workspace_returns_404(self, client):
        res = client.get(f"/api/v1/workspaces/{uuid.uuid4()}")
        assert res.status_code == 404

    def test_update_workspace_name_returns_200(self, client, tenant_id):
        created = client.post("/api/v1/workspaces", json={
            "tenant_id": tenant_id,
            "workspace_name": "Old Name",
        }).json()
        res = client.put(f"/api/v1/workspaces/{created['id']}", json={
            "workspace_name": "New Name",
        })
        assert res.status_code == 200
        assert res.json()["workspace_name"] == "New Name"

    def test_delete_workspace_returns_200(self, client, tenant_id):
        created = client.post("/api/v1/workspaces", json={
            "tenant_id": tenant_id,
            "workspace_name": "Delete WS",
        }).json()
        res = client.delete(f"/api/v1/workspaces/{created['id']}")
        assert res.status_code == 200

    def test_delete_nonexistent_workspace_returns_404(self, client):
        res = client.delete(f"/api/v1/workspaces/{uuid.uuid4()}")
        assert res.status_code == 404

    def test_duplicate_slug_in_same_tenant_returns_400(self, client, tenant_id):
        slug = f"unique-slug-{uuid.uuid4().hex[:6]}"
        client.post("/api/v1/workspaces", json={
            "tenant_id": tenant_id,
            "workspace_name": "WS1",
            "workspace_slug": slug,
        })
        res = client.post("/api/v1/workspaces", json={
            "tenant_id": tenant_id,
            "workspace_name": "WS2",
            "workspace_slug": slug,
        })
        assert res.status_code in (400, 422, 409)


# ===========================================================================
# Audit Trail Endpoint Tests
# ===========================================================================

class TestAuditEndpoints:

    def test_record_audit_event_returns_201(self, client):
        res = client.post("/api/v1/audit", json={
            "actor": "user-1",
            "action": "dataset.upload",
            "resource_type": "dataset",
            "resource_id": "ds-001",
        })
        assert res.status_code == 201

    def test_record_audit_event_returns_event_data(self, client):
        data = client.post("/api/v1/audit", json={
            "actor": "admin",
            "action": "user.delete",
            "resource_type": "user",
        }).json()
        assert data["actor"] == "admin"
        assert data["action"] == "user.delete"

    def test_query_audit_events_returns_200(self, client):
        res = client.get("/api/v1/audit")
        assert res.status_code == 200

    def test_query_audit_returns_list(self, client):
        data = client.get("/api/v1/audit").json()
        assert isinstance(data, list)

    def test_query_audit_with_actor_filter(self, client):
        client.post("/api/v1/audit", json={
            "actor": "alice", "action": "view", "resource_type": "report"
        })
        data = client.get("/api/v1/audit?actor=alice").json()
        assert all(e["actor"] == "alice" for e in data)

    def test_search_audit_events_returns_200(self, client):
        res = client.get("/api/v1/audit/search")
        assert res.status_code == 200

    def test_get_audit_event_by_id_returns_404_for_nonexistent(self, client):
        res = client.get(f"/api/v1/audit/{uuid.uuid4()}")
        assert res.status_code == 404

    def test_export_audit_events_json(self, client):
        res = client.get("/api/v1/audit/export?format=json")
        assert res.status_code == 200

    def test_export_audit_events_csv(self, client):
        res = client.get("/api/v1/audit/export?format=csv")
        assert res.status_code == 200


# ===========================================================================
# Chat Endpoint Tests
# ===========================================================================

class TestChatEndpoint:

    def test_chat_returns_200(self, client):
        res = client.post("/api/v1/chat", json={"message": "Show revenue trends"})
        assert res.status_code == 200

    def test_chat_returns_answer(self, client):
        data = client.post("/api/v1/chat", json={"message": "Show sales trends"}).json()
        assert "answer" in data
        assert isinstance(data["answer"], str)

    def test_chat_returns_intent(self, client):
        data = client.post("/api/v1/chat", json={"message": "Show revenue trends"}).json()
        assert "intent" in data

    def test_chat_returns_confidence(self, client):
        data = client.post("/api/v1/chat", json={"message": "Analyze data"}).json()
        assert "confidence" in data
        assert 0.0 <= data["confidence"] <= 1.0

    def test_chat_empty_message_returns_422(self, client):
        res = client.post("/api/v1/chat", json={"message": ""})
        assert res.status_code == 422

    def test_chat_with_dataset_id(self, client):
        data = client.post("/api/v1/chat", json={
            "message": "Analyze this dataset",
            "dataset_id": "ds-123",
        }).json()
        assert "answer" in data


# ===========================================================================
# Operations Endpoint Tests
# ===========================================================================

class TestOperationsEndpoints:

    def test_submit_feedback_returns_201(self):
        app = create_app()
        with TestClient(app) as c:
            res = c.post("/api/v1/operations/feedback", json={
                "description": "The forecasting feature is really helpful for planning.",
                "channel": "dashboard",
            })
        assert res.status_code == 201

    def test_get_feedback_analytics_returns_200(self):
        app = create_app()
        with TestClient(app) as c:
            res = c.get("/api/v1/operations/feedback/analytics")
        assert res.status_code == 200

    def test_record_analytics_event_returns_201(self):
        app = create_app()
        with TestClient(app) as c:
            res = c.post("/api/v1/operations/analytics/events", json={
                "event_type": "dataset_upload",
                "user_id": "user-123",
                "metadata": {"file_type": "csv"},
            })
        assert res.status_code == 201

    def test_get_usage_metrics_returns_200(self):
        app = create_app()
        with TestClient(app) as c:
            res = c.get("/api/v1/operations/analytics/metrics")
        assert res.status_code == 200

    def test_get_quality_status_returns_200(self):
        app = create_app()
        with TestClient(app) as c:
            res = c.get("/api/v1/operations/quality/status")
        assert res.status_code == 200

    def test_list_feature_flags_returns_200(self):
        app = create_app()
        with TestClient(app) as c:
            res = c.get("/api/v1/operations/feature-flags")
        assert res.status_code == 200

    def test_get_cost_analysis_returns_200(self):
        app = create_app()
        with TestClient(app) as c:
            res = c.get("/api/v1/operations/costs")
        assert res.status_code == 200

    def test_get_product_dashboard_returns_200(self):
        app = create_app()
        with TestClient(app) as c:
            res = c.get("/api/v1/operations/dashboard")
        assert res.status_code == 200

    def test_get_orchestrator_status_returns_200(self):
        app = create_app()
        with TestClient(app) as c:
            res = c.get("/api/v1/operations/orchestrator/status")
        assert res.status_code == 200


# ===========================================================================
# Enterprise Endpoint Tests
# ===========================================================================

class TestEnterpriseEndpoints:

    @pytest.fixture(scope="function")
    def enterprise_client(self):
        app = create_app()
        with TestClient(app) as c:
            yield c

    def test_list_tenants_returns_200(self, enterprise_client):
        res = enterprise_client.get("/api/v1/enterprise/tenants")
        assert res.status_code == 200

    def test_list_tenants_returns_list(self, enterprise_client):
        data = enterprise_client.get("/api/v1/enterprise/tenants").json()
        assert isinstance(data, list)

    def test_create_tenant_returns_201(self, enterprise_client):
        res = enterprise_client.post("/api/v1/enterprise/tenants", json={
            "name": "Acme Corp",
            "tier": "professional",
            "admin_email": "admin@acme.com",
        })
        assert res.status_code == 201

    def test_create_tenant_returns_tenant_data(self, enterprise_client):
        data = enterprise_client.post("/api/v1/enterprise/tenants", json={
            "name": "Beta Inc",
            "tier": "enterprise",
        }).json()
        assert "name" in data or "tenant_name" in data

    def test_get_ecosystem_status_returns_200(self, enterprise_client):
        res = enterprise_client.get("/api/v1/enterprise/ecosystem/status")
        assert res.status_code == 200

    def test_get_global_topology_returns_200(self, enterprise_client):
        res = enterprise_client.get("/api/v1/enterprise/global/topology")
        assert res.status_code == 200

    def test_get_model_catalog_returns_200(self, enterprise_client):
        res = enterprise_client.get("/api/v1/enterprise/models")
        assert res.status_code == 200

    def test_get_agents_returns_200(self, enterprise_client):
        res = enterprise_client.get("/api/v1/enterprise/agents")
        assert res.status_code == 200

    def test_get_connector_catalog_returns_200(self, enterprise_client):
        res = enterprise_client.get("/api/v1/enterprise/connectors/catalog")
        assert res.status_code == 200

    def test_get_enterprise_readiness_returns_200(self, enterprise_client):
        res = enterprise_client.get("/api/v1/enterprise/ecosystem/readiness")
        assert res.status_code == 200


# ===========================================================================
# Autonomous Endpoint Tests
# ===========================================================================

class TestAutonomousEndpoints:

    @pytest.fixture(scope="function")
    def auto_client(self):
        app = create_app()
        with TestClient(app) as c:
            yield c

    def test_start_runtime_returns_200(self, auto_client):
        res = auto_client.post("/api/v1/autonomous/start")
        assert res.status_code == 200

    def test_get_status_returns_200(self, auto_client):
        auto_client.post("/api/v1/autonomous/start")
        res = auto_client.get("/api/v1/autonomous/status")
        assert res.status_code == 200

    def test_get_intelligence_returns_200(self, auto_client):
        auto_client.post("/api/v1/autonomous/start")
        res = auto_client.get("/api/v1/autonomous/intelligence")
        assert res.status_code == 200

    def test_get_knowledge_graph_returns_200(self, auto_client):
        auto_client.post("/api/v1/autonomous/start")
        res = auto_client.get("/api/v1/autonomous/knowledge-graph")
        assert res.status_code == 200

    def test_get_cycle_history_returns_200(self, auto_client):
        auto_client.post("/api/v1/autonomous/start")
        res = auto_client.get("/api/v1/autonomous/cycles")
        assert res.status_code == 200

    def test_ingest_business_event_returns_202(self, auto_client):
        auto_client.post("/api/v1/autonomous/start")
        res = auto_client.post("/api/v1/autonomous/events", json={
            "event": {
                "event_id": str(uuid.uuid4()),
                "type": "revenue_alert",
                "value": 1500000,
            }
        })
        assert res.status_code == 202

    def test_simulate_outcomes_returns_200(self, auto_client):
        auto_client.post("/api/v1/autonomous/start")
        res = auto_client.post("/api/v1/autonomous/simulate", json={
            "goal": "Maximize Q4 revenue through pricing optimization"
        })
        assert res.status_code == 200
