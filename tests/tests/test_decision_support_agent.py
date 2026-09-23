"""Unit tests for Phase 7.9 — Decision Support Agent."""

import pytest
from backend.agents.recommendation_agent import DecisionSupportAgent


def test_revenue_decline_forecast_generates_decision_plan():
    """Test 1: Revenue decline forecast -> Decision plan generated."""
    agent = DecisionSupportAgent()
    context = {
        "forecast_results": {"growth_rate": -0.12},
        "revenue_decline": 0.12,
    }

    result = agent.generate_decision_guidance(context)

    assert result.decision_summary != ""
    assert result.recommended_action != ""
    assert "Executive Decision Brief" in result.decision_summary
    assert "contraction" in result.decision_summary.lower() or "decline" in result.decision_summary.lower()
    assert "Revenue Recovery" in result.recommended_action
    assert len(result.strategic_priorities) >= 1
    assert result.risk_assessment != ""


def test_positive_growth_forecast_generates_expansion_plan():
    """Test decision plan for high growth scenario."""
    agent = DecisionSupportAgent()
    context = {
        "forecast_results": {"growth_rate": 0.22},
    }

    result = agent.generate_decision_guidance(context)

    assert "expansion" in result.decision_summary.lower() or "growth" in result.decision_summary.lower()
    assert "Commercial Expansion" in result.recommended_action
    assert len(result.strategic_priorities) >= 3


def test_decision_support_output_schema_adherence():
    """Test output matches the required master prompt format."""
    agent = DecisionSupportAgent()
    context = {"status": "normal"}

    result = agent.generate_decision_guidance(context)

    dumped = result.model_dump()
    assert "decision_summary" in dumped
    assert "recommended_action" in dumped
    assert isinstance(dumped["decision_summary"], str)
    assert isinstance(dumped["recommended_action"], str)
