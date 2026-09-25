"""Unit tests for Phase 7.3 — Cost Optimization Engine."""

import pytest
from backend.recommendations.cost_optimization import CostOptimizationEngine


def test_high_marketing_spend_generates_cost_optimization_suggestion():
    """Test 1: High marketing spend detected (e.g. Marketing Spend = 60% Revenue) -> Cost optimization suggestion generated."""
    engine = CostOptimizationEngine()
    cost_data = {
        "revenue": 1000000.0,
        "marketing_spend_ratio": 0.60,
    }

    result = engine.analyze_costs(cost_data)

    assert isinstance(result.cost_savings, list)
    assert len(result.cost_savings) >= 1
    assert result.estimated_savings > 0

    mkt_item = next(
        (item for item in result.cost_savings if "Marketing" in item["area"]),
        None,
    )
    assert mkt_item is not None
    assert "Cost Optimization" in mkt_item["recommendation"]
    assert mkt_item["current_spend_ratio"] == 0.60
    assert mkt_item["estimated_savings"] == 350000.0  # (0.60 - 0.25) * 1,000,000


def test_multiple_cost_inefficiencies_detection():
    """Test scanning OPEX, infrastructure, and departmental overspend simultaneously."""
    engine = CostOptimizationEngine()
    cost_data = {
        "revenue": 2000000.0,
        "opex_ratio": 0.80,  # Benchmark is 0.65
        "cloud_waste_pct": 0.20,
        "infrastructure_spend": 100000.0,
        "departments": {
            "engineering": {"budget": 300000.0, "actual": 360000.0}
        },
    }

    result = engine.analyze_costs(cost_data)

    assert len(result.cost_savings) >= 3
    assert result.estimated_savings > 300000.0

    areas = [item["area"] for item in result.cost_savings]
    assert any("OPEX" in a for a in areas)
    assert any("Infrastructure" in a for a in areas)
    assert any("Engineering" in a for a in areas)


def test_healthy_cost_structure_returns_baseline():
    """Test that healthy operating costs return a zero-savings maintenance finding."""
    engine = CostOptimizationEngine()
    cost_data = {
        "revenue": 1000000.0,
        "marketing_spend_ratio": 0.18,  # Below 25% benchmark
        "opex_ratio": 0.50,             # Below 65% benchmark
    }

    result = engine.analyze_costs(cost_data)

    assert len(result.cost_savings) >= 1
    assert result.estimated_savings == 0.0
    assert "healthy" in result.cost_savings[0]["finding"].lower()
