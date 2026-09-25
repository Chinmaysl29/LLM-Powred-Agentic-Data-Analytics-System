"""Unit & Integration Tests for Phase 10.9: Release Management.

Validates:
- Semantic version parsing and incrementing (major, minor, patch)
- Deployment checklist auditing
- Rollback plan construction
- Test Case: Release Upgrade -> Expected: Successful Version Upgrade
- Rejection of downgrades and unapproved checklists
"""

import pytest
from backend.deployment.release_manager import ReleaseManager, release_manager


@pytest.fixture
def rel_mgr():
    return ReleaseManager()


def test_semver_parsing_and_bumping(rel_mgr):
    """Verify semver increments correctly for major, minor, and patch."""
    assert rel_mgr.parse_semver("v1.0.0") == (1, 0, 0)
    assert rel_mgr.parse_semver("2.4.9") == (2, 4, 9)

    assert rel_mgr.bump_version("v1.0.0", "patch") == "v1.0.1"
    assert rel_mgr.bump_version("v1.0.0", "minor") == "v1.1.0"
    assert rel_mgr.bump_version("v1.0.0", "major") == "v2.0.0"


def test_deployment_checklist_verification(rel_mgr):
    """Verify deployment checklist authorization logic."""
    all_pass = {item["id"]: True for item in rel_mgr.get_deployment_checklist()}
    audit_ok = rel_mgr.verify_checklist(all_pass)
    assert audit_ok["is_authorized"] is True
    assert audit_ok["status"] == "APPROVED"

    # Reject if any item is false
    bad_responses = dict(all_pass)
    bad_responses["tests_passed"] = False
    audit_bad = rel_mgr.verify_checklist(bad_responses)
    assert audit_bad["is_authorized"] is False
    assert "tests_passed" in audit_bad["unapproved_items"]


def test_release_upgrade_successful(rel_mgr):
    """Test Case: Release Upgrade -> Expected: Successful Version Upgrade."""
    res = rel_mgr.upgrade_release(
        current_version="v1.0.0",
        target_version="v1.1.0",
    )
    assert res["status"] == "SUCCESSFUL_VERSION_UPGRADE"
    assert res["previous_version"] == "v1.0.0"
    assert res["upgraded_version"] == "v1.1.0"
    assert res["checklist_verified"] is True
    assert res["rollback_plan_ready"] is True
    assert len(res["rollback_plan"]["steps"]) == 5


def test_reject_downgrade(rel_mgr):
    """Verify attempt to downgrade version throws ValueError."""
    with pytest.raises(ValueError, match="must be greater than current version"):
        rel_mgr.upgrade_release("v2.0.0", "v1.9.0")
