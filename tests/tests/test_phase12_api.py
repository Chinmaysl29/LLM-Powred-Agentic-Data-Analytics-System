"""Integration tests for Phase 12 Enterprise Expansion & Scale REST API."""

import pytest
from fastapi.testclient import TestClient

from backend.app.main import create_app
from backend.enterprise.multi_tenant import TenantManager


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_tenant():
    tm = TenantManager()
    tm.reset()
    yield
    tm.reset()


def test_api_create_and_list_tenants(client):
    # POST /api/v1/enterprise/tenants
    resp = client.post(
        "/api/v1/enterprise/tenants",
        json={
            "name": "Acme API Test Tenant",
            "slug": "acme-api-test",
            "tier": "enterprise",
            "admin_email": "admin@acme-api.com",
        },
    )
    assert resp.status_code == 201
    tenant = resp.json()
    assert tenant["slug"] == "acme-api-test"
    tenant_id = tenant["id"]

    # GET /api/v1/enterprise/tenants/{tenant_id}
    get_resp = client.get(f"/api/v1/enterprise/tenants/{tenant_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["name"] == "Acme API Test Tenant"

    # GET /api/v1/enterprise/tenants/{tenant_id}/stats
    stats_resp = client.get(f"/api/v1/enterprise/tenants/{tenant_id}/stats")
    assert stats_resp.status_code == 200
    assert "storage_utilization_pct" in stats_resp.json()


def test_api_workspace_management(client):
    # Create workspace
    resp = client.post(
        "/api/v1/enterprise/workspaces",
        json={
            "tenant_id": "system",
            "name": "Finance Department",
            "department": "Finance",
            "owner_id": "usr-finance-lead",
        },
    )
    assert resp.status_code == 201
    ws = resp.json()
    ws_id = ws["id"]

    # List workspaces
    list_resp = client.get("/api/v1/enterprise/workspaces?tenant_id=system")
    assert list_resp.status_code == 200
    assert len(list_resp.json()) >= 2

    # Add member
    mem_resp = client.post(
        f"/api/v1/enterprise/workspaces/{ws_id}/members",
        json={"user_id": "usr-analyst-2", "email": "analyst2@tenant.com", "role": "editor"},
    )
    assert mem_resp.status_code == 200
    assert mem_resp.json()["role"] == "editor"


def test_api_collaboration(client):
    # Add comment
    resp = client.post(
        "/api/v1/enterprise/comments",
        json={
            "tenant_id": "system",
            "workspace_id": "ws-system-default",
            "target_type": "dataset",
            "target_id": "ds-1",
            "author_id": "usr-1",
            "author_name": "Sarah",
            "content": "Check out these revenue projections @steve!",
        },
    )
    assert resp.status_code == 201
    comment = resp.json()
    assert "steve" in comment["mentions"]

    # List comments
    list_resp = client.get("/api/v1/enterprise/comments?target_type=dataset&target_id=ds-1")
    assert list_resp.status_code == 200
    assert len(list_resp.json()) >= 1

    # Activity feed
    act_resp = client.get("/api/v1/enterprise/activity-feed?tenant_id=system")
    assert act_resp.status_code == 200
    assert len(act_resp.json()) >= 1


def test_api_connector_marketplace(client):
    # Catalog
    cat_resp = client.get("/api/v1/enterprise/connectors/catalog")
    assert cat_resp.status_code == 200
    assert len(cat_resp.json()) >= 8

    # Install connector
    inst_resp = client.post(
        "/api/v1/enterprise/connectors/install",
        json={
            "tenant_id": "system",
            "connector_id": "bigquery",
            "instance_name": "Production BigQuery",
            "auth_method": "service_account",
            "credentials": {"sa_key": "my_google_service_account_json_key"},
        },
    )
    assert inst_resp.status_code == 201
    installed = inst_resp.json()
    inst_id = installed["id"]

    # Test connection
    test_resp = client.post(f"/api/v1/enterprise/connectors/{inst_id}/test")
    assert test_resp.status_code == 200
    assert test_resp.json()["status"] == "HEALTHY"


def test_api_multi_agent_missions(client):
    # List specialist agents
    agents_resp = client.get("/api/v1/enterprise/agents")
    assert agents_resp.status_code == 200
    assert len(agents_resp.json()) == 5

    # Submit mission
    sub_resp = client.post(
        "/api/v1/enterprise/missions",
        json={
            "tenant_id": "system",
            "workspace_id": "ws-system-default",
            "title": "API Multi-Agent Discovery",
            "goal": "Coordinate all specialist agents to assess performance",
        },
    )
    assert sub_resp.status_code == 201
    mission_id = sub_resp.json()["id"]

    # Execute mission
    exec_resp = client.post(f"/api/v1/enterprise/missions/{mission_id}/execute")
    assert exec_resp.status_code == 200
    assert exec_resp.json()["status"] == "completed"
    assert len(exec_resp.json()["contributions"]) == 5


def test_api_model_hub(client):
    # Model catalog
    models_resp = client.get("/api/v1/enterprise/models")
    assert models_resp.status_code == 200
    assert len(models_resp.json()) >= 6

    # Model routing
    route_resp = client.post("/api/v1/enterprise/models/route", json={"strategy": "latency_optimized"})
    assert route_resp.status_code == 200
    assert "selected_model" in route_resp.json()


def test_api_mobile_feed(client):
    resp = client.get("/api/v1/enterprise/mobile/feed?tenant_id=system")
    assert resp.status_code == 200
    assert len(resp.json()) >= 4


def test_api_global_scale_and_ecosystem(client):
    # Topology
    topo_resp = client.get("/api/v1/enterprise/global/topology")
    assert topo_resp.status_code == 200
    assert len(topo_resp.json()) == 5

    # Route request
    route_resp = client.post("/api/v1/enterprise/global/route?tenant_id=system&operation=read&client_country=DE")
    assert route_resp.status_code == 200
    assert route_resp.json()["assigned_region"] == "eu-central-1"

    # Ecosystem status
    eco_resp = client.get("/api/v1/enterprise/ecosystem/status")
    assert eco_resp.status_code == 200
    assert eco_resp.json()["platform_health_score"] == 100.0

    # Enterprise readiness scorecard
    ready_resp = client.get("/api/v1/enterprise/ecosystem/readiness")
    assert ready_resp.status_code == 200
    assert ready_resp.json()["overall_score"] == 100.0
