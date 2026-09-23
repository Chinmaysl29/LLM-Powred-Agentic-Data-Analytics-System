"""Unit tests for Phase 7.2 — Business Recommendation Engine."""

import pytest
from backend.app.schemas.recommendations import PriorityLevel
from backend.recommendations.business_recommendations import BusinessRecommendationEngine
from backend.recommendations.foundation import RecommendationFoundation


def test_region_growth_generates_expansion_recommendation():
    """Test 1: Region Growth = 25% -> Expansion Recommendation Generated."""
    engine = BusinessRecommendationEngine()
    data = {
        "region": "South",
        "growth": 0.25,
    }

    result = engine.generate_recommendations(data)

    assert isinstance(result.recommendations, list)
    assert len(result.recommendations) >= 1

    # Find the expansion recommendation
    expansion_rec = next(
        (r for r in result.recommendations if "South" in r["opportunity"] and "Sales Team" in r["opportunity"]),
        None,
    )
    assert expansion_rec is not None
    assert "Expand South Sales Team" in expansion_rec["opportunity"] or "Expand South Region" in expansion_rec["opportunity"]
    assert expansion_rec["category"] == "expansion"
    assert expansion_rec["impact_score"] > 0
    assert expansion_rec["confidence_score"] > 0


def test_revenue_decline_generates_recovery_recommendation():
    """Test 2: Revenue Decline = 15% -> Recovery Recommendation Generated."""
    engine = BusinessRecommendationEngine()
    data = {
        "revenue_decline": 0.15,
    }

    result = engine.generate_recommendations(data)

    assert len(result.recommendations) >= 1
    recovery_rec = next(
        (r for r in result.recommendations if "Recovery" in r["opportunity"] or "Decline" in r["opportunity"]),
        None,
    )
    assert recovery_rec is not None
    assert recovery_rec["category"] == "risk_mitigation"
    assert recovery_rec["priority"] == PriorityLevel.CRITICAL.value
    assert recovery_rec["estimated_value"] > 0


def test_recommendations_ranking_order():
    """Test that multiple recommendations are ranked by expected impact and confidence."""
    engine = BusinessRecommendationEngine()
    data = {
        "region_growth": {"North": 0.22, "West": 0.35},
        "revenue_decline": 0.18,
        "operational_inefficiency": True,
    }

    result = engine.generate_recommendations(data)

    assert len(result.recommendations) >= 3
    # Verify descending sort order by impact_score * confidence_score
    scores = [r["impact_score"] * r["confidence_score"] for r in result.recommendations]
    assert scores == sorted(scores, reverse=True)


def test_dependency_injection_with_custom_foundation():
    """Test that custom foundation instance is respected."""
    foundation = RecommendationFoundation()
    engine = BusinessRecommendationEngine(foundation=foundation)
    assert engine.foundation is foundation
