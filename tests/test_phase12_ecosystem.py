"""Tests for Phase 12.10 — AI Data Analyst OS Ecosystem Orchestrator."""

import pytest
from backend.enterprise.ecosystem_orchestrator import EcosystemDirector
from backend.enterprise.global_scale import CloudRegion
from backend.enterprise.multi_tenant import TenantManager, TenantTier


@pytest.fixture(autouse=True)
def reset_all():
    tm = TenantManager()
    tm.reset()
    yield
    tm.reset()


def test_ecosystem_overview_all_12_phases():
    director = EcosystemDirector()
    overview = director.get_ecosystem_overview()
    assert overview["platform_health_score"] == 100.0
    summary = overview["phases_summary"]
    assert len(summary) == 12
    for phase_name, stat in summary.items():
        assert "100% OPERATIONAL" in stat


def test_end_to_end_enterprise_customer_onboarding():
    director = EcosystemDirector()
    result = director.onboard_enterprise_customer(
        company_name="MegaCorp Logistics",
        admin_email="cto@megacorp.com",
        slug="megacorp-logistics",
        tier=TenantTier.ENTERPRISE,
        region=CloudRegion.US_EAST,
        initial_connectors=["snowflake", "salesforce"],
    )

    assert result.status == "COMPLETED"
    assert result.tenant_slug == "megacorp-logistics"
    assert result.primary_workspace_id.startswith("ws-")
    assert result.model_budget_usd == 1000.0
    assert "snowflake" in result.connectors_installed


def test_enterprise_readiness_scorecard():
    director = EcosystemDirector()
    scorecard = director.evaluate_enterprise_readiness_scorecard()
    assert scorecard["overall_score"] == 100.0
    assert scorecard["recommendation"] == "APPROVED FOR GLOBAL MULTI-TENANT DEPLOYMENT"
    assert len(scorecard["dimensions"]) == 10
