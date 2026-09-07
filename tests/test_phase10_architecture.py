"""Unit & Integration Tests for Phase 10.1: Production Architecture.

Validates:
- Production topology definition (7 mandatory layers)
- Resource planning & sizing calculations
- Scaling strategy compliance
- Disaster Recovery SLAs (RPO <= 15m, RTO <= 60m)
- Infrastructure reachability validation
"""

import pytest
from backend.deployment.production_architecture import ProductionArchitecture, production_architecture


@pytest.fixture
def arch():
    return ProductionArchitecture()


def test_topology_loading_and_structure(arch):
    """Verify topology JSON exists and can be loaded."""
    data = arch.load_topology()
    assert data["topology_name"] == "ai-data-analyst-os-production"
    assert data["environment"] == "production"
    assert len(data["layers"]) >= 7


def test_network_topology_validation(arch):
    """Verify all 7 mandatory production layers are accounted for."""
    res = arch.validate_network_topology()
    assert res["status"] == "PASS"
    assert res["is_valid"] is True
    assert len(res["missing_layers"]) == 0
    assert "api_gateway" in res["present_layers"]
    assert "database" in res["present_layers"]
    assert "vectorstore" in res["present_layers"]


def test_capacity_sizing_calculator(arch):
    """Verify capacity calculator properly computes replica and pool sizing."""
    res = arch.calculate_capacity_sizing(expected_peak_rps=600, avg_request_duration_ms=100.0)
    assert res["status"] == "PASS"
    assert res["concurrent_requests"] == 60.0
    assert res["recommended_backend_replicas"] >= 5
    assert res["total_worker_processes"] >= 20
    assert res["recommended_db_pool_size"] >= res["total_worker_processes"]


def test_disaster_recovery_plan(arch):
    """Verify disaster recovery targets meet enterprise compliance."""
    dr = arch.validate_disaster_recovery_plan()
    assert dr["status"] == "PASS"
    assert dr["rpo_compliant"] is True
    assert dr["rto_compliant"] is True
    assert dr["rpo_minutes"] <= 15
    assert dr["rto_minutes"] <= 30


def test_infrastructure_reachability_pass(arch):
    """Verify all services pass reachability checks."""
    status = arch.check_infrastructure_reachability()
    assert status["status"] == "PASS"
    assert status["all_services_reachable"] is True
    assert "database" in status["services"]
    assert "cache" in status["services"]
