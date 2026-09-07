"""Unit tests for Phase 7.5 — Pricing Intelligence Engine."""

import pytest
from backend.recommendations.pricing_recommendations import PricingIntelligenceEngine


def test_price_increase_simulation_calculates_projected_revenue_change():
    """Test 1: Price increase simulation -> Projected revenue change calculated."""
    engine = PricingIntelligenceEngine()
    pricing_data = {
        "current_price": 100.0,
        "current_volume": 5000.0,  # Old revenue = 500,000
        "simulated_price_increase": 0.10,  # +10% price
        "elasticity": -0.5,  # Inelastic demand: volume drops 5%, revenue rises
    }

    result = engine.analyze_pricing(pricing_data)

    assert isinstance(result.pricing_actions, list)
    assert len(result.pricing_actions) >= 1
    assert result.expected_impact > 0

    action = result.pricing_actions[0]
    sim = action["simulation"]
    assert sim["new_price"] == 110.0
    assert sim["projected_volume"] == 4750.0  # 5000 * (1 - 0.05)
    assert sim["projected_revenue"] == 522500.0  # 110 * 4750
    assert sim["projected_revenue_change"] == 22500.0  # 522500 - 500000
    assert result.expected_impact == 22500.0


def test_elasticity_calculation_midpoint():
    """Test midpoint arc elasticity calculation."""
    engine = PricingIntelligenceEngine()
    # P: 100 -> 120 (+18.18%), Q: 1000 -> 800 (-22.22%)
    # Ed = -22.22% / 18.18% = -1.22 (elastic)
    e_d = engine.calculate_elasticity(price_old=100.0, price_new=120.0, quantity_old=1000.0, quantity_new=800.0)
    assert e_d < -1.0


def test_competitor_pricing_benchmark():
    """Test competitor price discount gap triggering price alignment action."""
    engine = PricingIntelligenceEngine()
    pricing_data = {
        "current_price": 70.0,
        "competitor_price": 100.0,  # 30% below competitor
        "current_volume": 2000.0,
        "elasticity": -0.4,
    }

    result = engine.analyze_pricing(pricing_data)

    assert len(result.pricing_actions) >= 1
    comp_action = next(
        (a for a in result.pricing_actions if "Market Alignment" in a["action"]),
        None,
    )
    assert comp_action is not None
    assert comp_action["expected_impact"] > 0
