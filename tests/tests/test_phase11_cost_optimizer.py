"""Unit tests for Phase 11.7: Cost Optimization Engine."""

import pytest
from backend.operations.cost_optimizer import (
    CostCategory,
    CostOptimizationEngine,
)


@pytest.fixture
def cost_engine():
    return CostOptimizationEngine(monthly_budget_usd=1000.0)


def test_high_openai_spend_triggers_recommendation(cost_engine):
    """Test Case: High OpenAI Spend -> Expected: Optimization Recommendation."""
    # Record 80 Million OpenAI tokens (~$400)
    cost_engine.record_usage(
        category=CostCategory.OPENAI,
        units=80_000_000,
        metadata={"model": "gpt-4o"},
    )

    analysis = cost_engine.get_cost_analysis()
    assert analysis["monthly_cost"] == 400.0
    assert analysis["optimization_savings"] > 0.0
    assert analysis["budget_utilized_percent"] == 40.0

    # Verify recommendation contains routing suggestion
    rec_ids = [r["id"] for r in analysis["recommendations"]]
    assert "REC_LLM_ROUTING" in rec_ids
    assert any("Groq" in r["description"] for r in analysis["recommendations"])


def test_multi_category_spend_tracking(cost_engine):
    """Verify recording and aggregation across multiple providers and services."""
    cost_engine.record_usage(CostCategory.GROQ, units=10_000_000)
    cost_engine.record_usage(CostCategory.GEMINI, units=20_000_000)
    cost_engine.record_usage(CostCategory.EMBEDDINGS, units=50_000_000)
    cost_engine.record_usage(CostCategory.STORAGE, units=500.0)

    analysis = cost_engine.get_cost_analysis()
    assert analysis["monthly_cost"] > 0.0
    assert analysis["category_spend"]["groq"] == 5.0
    assert analysis["category_spend"]["gemini"] == 7.0
    assert analysis["category_spend"]["embeddings"] == 1.0


def test_healthy_spend_default_recommendation(cost_engine):
    """Verify low/nominal spend yields healthy spend status."""
    cost_engine.record_usage(CostCategory.GROQ, units=100_000)
    analysis = cost_engine.get_cost_analysis()
    assert analysis["monthly_cost"] < 1.0
    assert analysis["optimization_savings"] == 0.0
    assert analysis["recommendations"][0]["id"] == "REC_HEALTHY_SPEND"
