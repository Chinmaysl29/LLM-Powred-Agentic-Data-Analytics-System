"""Unit & Integration Tests for Phase 10.4: Backup & Recovery.

Validates:
- Snapshot creation across all 5 targets (PostgreSQL, Redis, ChromaDB, Reports, Datasets)
- SHA256 integrity verification
- Test Case: Database Failure -> Expected: Restore Successful
- Prevention of restoring corrupted snapshots
"""

import pytest
from backend.deployment.backup_recovery_manager import BackupRecoveryManager, backup_recovery_manager


@pytest.fixture
def backup_mgr(tmp_path):
    return BackupRecoveryManager(backup_root=tmp_path / "backups")


def test_create_full_backup_all_targets(backup_mgr):
    """Verify all 5 target snapshots and manifest are created."""
    res = backup_mgr.create_full_backup(backup_id="test_b1")
    assert res["backup_id"] == "test_b1"
    assert res["total_targets"] == 5
    assert len(res["targets"]) == 5

    expected_targets = {"postgresql", "redis", "chromadb", "reports", "datasets"}
    assert set(res["targets"].keys()) == expected_targets

    # Check manifest file
    manifest_file = backup_mgr.backup_root / "test_b1" / "backup_manifest.json"
    assert manifest_file.exists()


def test_verify_backup_integrity_valid(backup_mgr):
    """Verify SHA256 checksum verification succeeds on untouched backup."""
    backup_mgr.create_full_backup(backup_id="test_b2")
    audit = backup_mgr.verify_backup_integrity("test_b2")
    assert audit["is_valid"] is True
    assert audit["status"] == "PASS"
    assert all(audit["targets_verified"].values())


def test_database_failure_restore_successful(backup_mgr):
    """Test Case: Database Failure -> Expected: Restore Successful."""
    sim = backup_mgr.simulate_database_failure_and_recover()
    assert sim["status"] == "PASS"
    assert sim["recovery_successful"] is True
    assert sim["restore_status"] == "RESTORE_SUCCESSFUL"


def test_tampered_backup_rejected_on_restore(backup_mgr):
    """Verify corrupted/tampered file fails integrity check and blocks restore."""
    backup_mgr.create_full_backup(backup_id="test_tamper")
    tampered_file = backup_mgr.backup_root / "test_tamper" / "postgresql_snapshot.json"
    # Tamper with file
    with open(tampered_file, "a", encoding="utf-8") as f:
        f.write("TAMPERED_MALICIOUS_DATA")

    audit = backup_mgr.verify_backup_integrity("test_tamper")
    assert audit["is_valid"] is False
    assert audit["status"] == "CORRUPTED"
    assert audit["targets_verified"]["postgresql"] is False

    with pytest.raises(RuntimeError, match="Cannot restore corrupted backup"):
        backup_mgr.restore_from_backup("test_tamper")
