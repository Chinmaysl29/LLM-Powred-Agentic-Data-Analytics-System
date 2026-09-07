"""Unit tests for Phase 11.6: Feature Flag System."""

import pytest
from backend.operations.feature_flags import FeatureFlagSystem


@pytest.fixture
def ff_system():
    sys = FeatureFlagSystem()
    return sys


def test_feature_disabled_hidden(ff_system):
    """Test Case: Feature Disabled -> Expected: Feature Hidden/Blocked."""
    # Register explicitly disabled flag
    ff_system.register_flag(
        name="deprecated_legacy_export",
        description="Legacy CSV exporter",
        enabled=False,
    )
    res = ff_system.is_enabled("deprecated_legacy_export")
    assert res["feature"] == "deprecated_legacy_export"
    assert res["enabled"] is False
    assert res["reason"] == "flag_disabled"


def test_feature_enabled_and_toggled(ff_system):
    """Verify enabling and disabling flags at runtime."""
    ff_system.register_flag(
        name="new_sql_optimizer",
        description="Next-gen SQL query plan optimizer",
        enabled=False,
    )
    assert ff_system.is_enabled("new_sql_optimizer")["enabled"] is False

    ff_system.set_enabled("new_sql_optimizer", True)
    assert ff_system.is_enabled("new_sql_optimizer")["enabled"] is True


def test_role_based_targeting(ff_system):
    """Verify role restrictions allow admins/beta-testers while blocking general users."""
    ff_system.register_flag(
        name="beta_agent_feature",
        description="Autonomous action execution",
        enabled=True,
        allowed_roles={"admin", "beta_tester"},
    )

    # General user -> blocked
    assert ff_system.is_enabled("beta_agent_feature", role="viewer")["enabled"] is False
    assert ff_system.is_enabled("beta_agent_feature")["enabled"] is False

    # Admin / beta_tester -> allowed
    assert ff_system.is_enabled("beta_agent_feature", role="admin")["enabled"] is True
    assert ff_system.is_enabled("beta_agent_feature", role="beta_tester")["enabled"] is True


def test_percentage_rollout_distribution(ff_system):
    """Verify percentage rollout activates deterministically for subset of users."""
    ff_system.register_flag(
        name="gradual_ui_refresh",
        description="Gradual 50% rollout",
        enabled=True,
        rollout_percentage=50,
    )

    enabled_count = 0
    total_users = 100
    for i in range(total_users):
        uid = f"user_{i}"
        if ff_system.is_enabled("gradual_ui_refresh", user_id=uid)["enabled"]:
            enabled_count += 1

    # Should be close to 50% (between 35% and 65% across 100 pseudo-random hashes)
    assert 35 <= enabled_count <= 65
