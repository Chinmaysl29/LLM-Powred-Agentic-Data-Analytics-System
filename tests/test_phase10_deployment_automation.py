"""Unit & Integration Tests for Phase 10.7: Deployment Automation.

Validates:
- Automated multi-stage deployment (infrastructure, backend, frontend, migrations, health check, go live)
- Test Case: Fresh Deployment -> Expected: System Online
- Automated rollback capability when any stage degrades
- Health check verification
"""

import pytest
from backend.deployment.deployment_automator import DeploymentAutomator, deployment_automator


@pytest.fixture
def automator():
    return DeploymentAutomator()


def test_fresh_deployment_system_online(automator):
    """Test Case: Fresh Deployment -> Expected: System Online."""
    res = automator.execute_deployment(target_version="v1.0.0-gold")
    assert res["status"] == "ONLINE"
    assert res["system_online"] is True
    assert res["active_version"] == "v1.0.0-gold"
    assert len(res["stages"]) == 6
    assert res["rollback"] is None

    # Verify all 6 stages passed
    stage_names = [s["stage"] for s in res["stages"]]
    assert stage_names == [
        "provision_infrastructure",
        "deploy_backend",
        "deploy_frontend",
        "run_migrations",
        "health_check",
        "go_live",
    ]


def test_deployment_migration_failure_triggers_rollback(automator):
    """Verify failure during database migration activates immediate rollback."""
    # First deploy stable base
    automator.execute_deployment(target_version="v1.0.0-stable")

    # Now deploy faulty version
    res = automator.execute_deployment(
        target_version="v1.1.0-bad-migration",
        simulate_failure_stage="run_migrations",
    )
    assert res["status"] == "ROLLED_BACK"
    assert res["system_online"] is False
    assert res["active_version"] == "v1.0.0-stable"
    assert res["rollback"] is not None
    assert res["rollback"]["action"] == "ROLLBACK_EXECUTED"
    assert res["rollback"]["restored_version"] == "v1.0.0-stable"


def test_deployment_health_check_failure_triggers_rollback(automator):
    """Verify failure in health check halts go-live and rolls back."""
    automator.execute_deployment(target_version="v1.0.0-stable")

    res = automator.execute_deployment(
        target_version="v1.2.0-slow-api",
        simulate_failure_stage="health_check",
    )
    assert res["status"] == "ROLLED_BACK"
    assert res["system_online"] is False
    assert res["rollback"]["restored_version"] == "v1.0.0-stable"
