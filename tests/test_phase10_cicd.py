"""Unit & Integration Tests for Phase 10.3: CI/CD Pipeline.

Validates:
- Automated pipeline execution across all stages (test, security_scan, docker_build, deploy, health_check)
- Code commit -> Pipeline executes successfully
- Failure detection and automated rollback triggering
- Retention of last known stable deployment tag
"""

import pytest
from backend.deployment.cicd_pipeline import CICDPipeline, cicd_pipeline


@pytest.fixture
def pipeline():
    return CICDPipeline()


def test_successful_pipeline_run_on_code_commit(pipeline):
    """Test Case: Code Commit -> Expected: Pipeline Executes Successfully."""
    res = pipeline.execute_pipeline(commit_sha="commit_abc123")
    assert res["overall_status"] == "SUCCESS"
    assert res["rollback_executed"] is False
    assert len(res["stages"]) == 5
    for stage in res["stages"]:
        assert stage["status"] == "PASSED"
    assert res["current_stable_commit"] == "commit_abc123"


def test_pipeline_failure_triggers_rollback(pipeline):
    """Verify failure at any stage (e.g. security_scan) immediately rolls back."""
    # First set a known stable release
    pipeline.execute_pipeline(commit_sha="stable_release_v1")

    # Now simulate a bad commit with security issues
    res = pipeline.execute_pipeline(commit_sha="flawed_commit_456", simulate_failure_stage="security_scan")
    assert res["overall_status"] == "FAILED"
    assert res["rollback_executed"] is True
    assert res["rollback_info"]["status"] == "ROLLBACK_COMPLETED"
    assert res["rollback_info"]["failed_commit"] == "flawed_commit_456"
    assert res["rollback_info"]["reverted_to"] == "stable_release_v1"
    assert res["current_stable_commit"] == "stable_release_v1"


def test_pipeline_health_check_failure_triggers_rollback(pipeline):
    """Verify deploy with failed health check activates rollback."""
    pipeline.execute_pipeline(commit_sha="stable_v2")
    res = pipeline.execute_pipeline(commit_sha="broken_health_commit", simulate_failure_stage="health_check")
    assert res["overall_status"] == "FAILED"
    assert res["rollback_executed"] is True
    assert res["rollback_info"]["reverted_to"] == "stable_v2"
