"""Unit tests for Phase 7.4 — Revenue Optimization Engine."""

import pytest
from backend.recommendations.revenue_optimization import RevenueOptimizationEngine


def test_top_customers_undertargeted_generates_upsell_recommendation():
    """Test 1: Top customers under-targeted -> Upsell recommendation generated."""
    engine = RevenueOptimizationEngine()
    revenue_data = {
        "revenue": 2000000.0,
        "top_customers_under_targeted": True,
        "undertargeted_accounts_count": 30,
        "arpu_expansion_gap": 10000.0,
    }

    result = engine.analyze_revenue(revenue_data)

    assert isinstance(result.opportunities, list)
    assert len(result.opportunities) >= 1
    assert result.estimated_revenue_increase > 0

    upsell_opp = next(
        (opp for opp in result.opportunities if opp["type"] == "upsell"),
        None,
    )
    assert upsell_opp is not None
    assert "Upsell" in upsell_opp["opportunity"]
    assert upsell_opp["estimated_revenue_increase"] == 300000.0  # 30 * 10,000


def test_cross_sell_and_revenue_leakage_detection():
    """Test cross-sell expansion and leakage recovery."""
    engine = RevenueOptimizationEngine()
    revenue_data = {
        "revenue": 1500000.0,
        "single_product_accounts": 100,
        "cross_sell_arpu": 4000.0,
        "discount_slippage_pct": 0.08,  # 8% slippage on 1.5M = 120,000
    }

    result = engine.analyze_revenue(revenue_data)

    assert len(result.opportunities) >= 2
    types = [opp["type"] for opp in result.opportunities]
    assert "cross_sell" in types
    assert "leakage_recovery" in types
    assert result.estimated_revenue_increase > 150000.0


def test_baseline_revenue_when_no_signals():
    """Test baseline response when all accounts are fully targeted."""
    engine = RevenueOptimizationEngine()
    revenue_data = {
        "revenue": 1000000.0,
    }

    result = engine.analyze_revenue(revenue_data)

    assert len(result.opportunities) == 1
    assert result.opportunities[0]["type"] == "baseline"
    assert result.estimated_revenue_increase == 0.0
