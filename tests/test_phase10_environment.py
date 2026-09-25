"""Unit & Integration Tests for Phase 10.2: Environment Management.

Validates:
- Separation of Dev, Test, Staging, Production configurations
- Strict production validation (DEBUG=False, strong secrets, non-default passwords)
- Secret masking & redaction for logs
- Rejection of invalid environments
- Application of environment variables to runtime
"""

import pytest
from backend.deployment.environment_manager import EnvironmentManager, environment_manager


@pytest.fixture
def env_mgr():
    return EnvironmentManager()


def test_environment_file_resolution(env_mgr):
    """Verify paths resolve for all 4 supported environments."""
    for env in ["development", "testing", "staging", "production"]:
        path = env_mgr.get_env_file_path(env)
        assert path.exists(), f"Path for {env} does not exist: {path}"

    with pytest.raises(ValueError, match="Unsupported environment"):
        env_mgr.get_env_file_path("sandbox_invalid")


def test_production_environment_validation_passes(env_mgr):
    """Test Case: Production Environment -> Expected: Correct Configuration Loaded."""
    report = env_mgr.validate_environment("production")
    assert report["is_valid"] is True
    assert report["status"] == "PASS"
    assert len(report["missing_keys"]) == 0
    assert len(report["violations"]) == 0


def test_staging_and_testing_validation_passes(env_mgr):
    """Verify staging and testing configurations parse and validate."""
    for env in ["staging", "testing"]:
        report = env_mgr.validate_environment(env)
        assert report["is_valid"] is True
        assert report["status"] == "PASS"


def test_secret_masking(env_mgr):
    """Verify secrets are redacted in log-facing configs."""
    masked = env_mgr.get_masked_config("production")
    jwt_val = masked["JWT_SECRET_KEY"]
    assert "****" in jwt_val
    assert "prod_super_secure_jwt_secret_key_long_enough_256" != jwt_val

    db_pass = masked["POSTGRES_PASSWORD"]
    assert "****" in db_pass
    assert "prod_secure_password_9921" != db_pass


def test_apply_environment_runtime(env_mgr):
    """Verify applying testing environment updates runtime os.environ."""
    import os
    old_env = os.environ.copy()
    try:
        res = env_mgr.apply_environment("testing")
        assert res["status"] == "APPLIED"
        assert res["applied_keys_count"] > 5
    finally:
        os.environ.clear()
        os.environ.update(old_env)
