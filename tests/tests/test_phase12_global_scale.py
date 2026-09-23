"""Tests for Phase 12.9 — Global Scale Architecture."""

import pytest
from backend.enterprise.global_scale import (
    CloudRegion,
    ComplianceJurisdiction,
    GlobalScaleManager,
)


@pytest.fixture(autouse=True)
def reset_global_scale():
    mgr = GlobalScaleManager()
    mgr.reset()
    yield
    mgr.reset()


def test_global_topology():
    mgr = GlobalScaleManager()
    nodes = mgr.get_topology()
    assert len(nodes) == 5
    primary_nodes = [n for n in nodes if n.is_primary]
    assert len(primary_nodes) == 1
    assert primary_nodes[0].region == CloudRegion.US_EAST


def test_write_routing_to_primary():
    mgr = GlobalScaleManager()
    route = mgr.route_request("tenant-1", operation="write", client_country="DE")
    # All writes must go to primary node regardless of client country
    assert route["assigned_region"] == CloudRegion.US_EAST.value
    assert route["role"] == "PRIMARY"


def test_geo_proximity_read_routing():
    mgr = GlobalScaleManager()
    # European client reading
    eu_route = mgr.route_request("tenant-1", operation="read", client_country="FR")
    assert eu_route["assigned_region"] == CloudRegion.EU_CENTRAL.value

    # Asian client reading
    apac_route = mgr.route_request("tenant-1", operation="read", client_country="SG")
    assert apac_route["assigned_region"] == CloudRegion.APAC_SE.value


def test_strict_tenant_residency_pinning():
    mgr = GlobalScaleManager()
    # German bank pinned to Frankfurt for GDPR compliance
    mgr.pin_tenant_residency("tenant-german-bank", CloudRegion.EU_CENTRAL)

    # Even if requesting from US, read must route to EU
    route = mgr.route_request("tenant-german-bank", operation="read", client_country="US")
    assert route["assigned_region"] == CloudRegion.EU_CENTRAL.value
    assert "GDPR" in route["routed_via"]

    compliance = mgr.check_residency_compliance("tenant-german-bank")
    assert compliance["is_compliant"] is True
    assert compliance["jurisdiction"] == ComplianceJurisdiction.GDPR_EU.value


def test_distributed_locks():
    mgr = GlobalScaleManager()
    key = "lock:dataset:reindex:ds-100"

    # Worker 1 acquires lock
    assert mgr.acquire_lock(key, owner_id="worker-1", ttl_seconds=10.0) is True

    # Worker 2 should fail to acquire same lock
    assert mgr.acquire_lock(key, owner_id="worker-2", ttl_seconds=10.0) is False

    # Worker 1 releases lock
    assert mgr.release_lock(key, owner_id="worker-1") is True

    # Now worker 2 can acquire
    assert mgr.acquire_lock(key, owner_id="worker-2", ttl_seconds=10.0) is True
