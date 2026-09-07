"""Tests for Phase 12.5 — Advanced Agent Ecosystem."""

import pytest
from backend.enterprise.agent_ecosystem import (
    AgentEcosystem,
    AgentRole,
    MissionStatus,
)


@pytest.fixture(autouse=True)
def reset_agent_ecosystem():
    eco = AgentEcosystem()
    eco.reset()
    yield
    eco.reset()


def test_registered_specialist_agents():
    eco = AgentEcosystem()
    agents = eco.get_registered_agents()
    assert len(agents) == 5
    roles = [a.role for a in agents]
    assert AgentRole.DATA_ENGINEER in roles
    assert AgentRole.STATISTICAL_AUDITOR in roles
    assert AgentRole.ANOMALY_SCOUT in roles
    assert AgentRole.FORECASTING_TOURNAMENT in roles
    assert AgentRole.EXECUTIVE_BRIEFING in roles


def test_submit_and_execute_multi_agent_mission():
    eco = AgentEcosystem()
    mission = eco.submit_mission(
        tenant_id="tenant-1",
        workspace_id="ws-strategy",
        title="Q4 Revenue Forecast & Risk Audit",
        goal="Audit Q3 actuals, detect potential leakage, and forecast Q4 revenue trajectory.",
        dataset_id="ds-sales-2026",
    )
    assert mission.id.startswith("msn-")
    assert mission.status == MissionStatus.PENDING

    # Execute autonomous multi-agent pipeline
    completed = eco.execute_mission(mission.id)
    assert completed.status == MissionStatus.COMPLETED
    assert len(completed.contributions) == 5

    # Check contributions from specialist agents
    contributions_roles = [c.agent_role for c in completed.contributions]
    assert AgentRole.DATA_ENGINEER in contributions_roles
    assert AgentRole.EXECUTIVE_BRIEFING in contributions_roles

    # Check consensus outputs
    assert completed.executive_summary is not None
    assert len(completed.action_items) >= 2
    assert completed.completed_at is not None
