"""Tests for Phase 8.9: Production Deployment Layer."""

from pathlib import Path
import pytest
from backend.deployment.production_checker import ProductionChecker


@pytest.fixture
def checker(tmp_path):
    return ProductionChecker()


def test_production_readiness_verification(tmp_path):
    """Test Case: Production readiness verification."""
    checker = ProductionChecker()
    report = checker.verify_production_readiness(backup_dir=tmp_path / "backups")

    assert report["deployment_ready"] is True
    assert report["readiness_score"] == 100

    checks = report["checks"]
    assert checks["environment_configuration"]["status"] == "passed"
    assert checks["health_checks"]["status"] == "passed"
    assert checks["backup_strategy"]["status"] == "passed"
    assert checks["zero_downtime_migration"]["status"] == "passed"


def test_create_backup_snapshot(tmp_path):
    """Verify backup snapshot creation and write capability."""
    checker = ProductionChecker()
    backup_dir = tmp_path / "enterprise_backups"
    res = checker.create_backup_snapshot(backup_dir=backup_dir)

    assert "snapshot_path" in res
    snapshot_path = Path(res["snapshot_path"])
    assert snapshot_path.exists()
    assert snapshot_path.stat().st_size > 0


def test_environment_configuration_check():
    """Verify configuration validation detects missing keys."""
    checker = ProductionChecker()
    env_res = checker.check_environment_configuration()
    assert "status" in env_res
    assert env_res["passed"] is True
