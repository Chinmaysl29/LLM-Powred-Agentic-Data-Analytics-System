"""Tests for Phase 12.4 — Connector Marketplace."""

import pytest
from backend.enterprise.connectors import (
    AuthMethod,
    ConnectorCategory,
    ConnectorManager,
    SyncStatus,
)


@pytest.fixture(autouse=True)
def reset_connectors():
    cm = ConnectorManager()
    cm.reset()
    yield
    cm.reset()


def test_catalog_retrieval():
    cm = ConnectorManager()
    catalog = cm.get_catalog()
    assert len(catalog) >= 8

    # Check categories
    data_warehouses = cm.get_catalog(category=ConnectorCategory.DATA_WAREHOUSE)
    assert any(c.id == "snowflake" for c in data_warehouses)
    assert any(c.id == "bigquery" for c in data_warehouses)


def test_install_and_mask_credentials():
    cm = ConnectorManager()
    inst = cm.install_connector(
        tenant_id="tenant-acme",
        connector_id="snowflake",
        instance_name="Acme Enterprise DW",
        auth_method=AuthMethod.BASIC_AUTH,
        credentials={"username": "acme_etl_user", "password": "SuperSecretPassword123!"},
    )
    assert inst.id.startswith("conn-")
    assert inst.status == SyncStatus.CONNECTED
    # Sensitive credentials must be masked
    assert "SuperSecretPassword123!" not in str(inst.credentials_masked)
    assert "..." in inst.credentials_masked["password"]


def test_connection_test_and_schema_discovery():
    cm = ConnectorManager()
    inst = cm.install_connector(
        tenant_id="tenant-acme",
        connector_id="salesforce",
        instance_name="Salesforce CRM",
        auth_method=AuthMethod.OAUTH2,
        credentials={"token": "oauth_bearer_123456789"},
    )

    # Ping test
    test_result = cm.test_connection(inst.id)
    assert test_result["status"] == "HEALTHY"
    assert test_result["authenticated"] is True
    assert test_result["ping_latency_ms"] > 0

    # Schema discovery
    schema = cm.discover_schemas(inst.id)
    assert schema["discovered_tables"] >= 1
    assert "schemas" in schema
    assert len(schema["schemas"][0]["columns"]) >= 1


def test_data_sync_execution():
    cm = ConnectorManager()
    inst = cm.install_connector(
        tenant_id="tenant-acme",
        connector_id="stripe",
        instance_name="Billing Stream",
        auth_method=AuthMethod.API_KEY,
        credentials={"api_key": "sk_live_998877665544"},
    )

    sync_result = cm.sync_data(inst.id, table_name="subscriptions")
    assert sync_result["sync_status"] == "SUCCESS"
    assert sync_result["rows_synced"] > 0
    assert sync_result["bytes_transferred"] > 0
    assert inst.status == SyncStatus.SUCCESS
    assert inst.last_sync_rows == sync_result["rows_synced"]
