"""Unit tests for Phase 7.1 — Recommendation Foundation."""

import pytest
from backend.app.core.exceptions import RecommendationValidationError
from backend.app.schemas.recommendations import AnalyticalInputs, PriorityLevel, ScoringWeights
from backend.recommendations.foundation import RecommendationFoundation


def test_recommendation_generation_success():
    """Test 1: Revenue Growth = 15%, Customer Retention = 95% -> Recommendation Generated."""
    foundation = RecommendationFoundation()
    raw_inputs = {
        "forecast_results": {"growth_rate": 0.15, "is_valid": True},
        "eda_results": {"customer_retention": 0.95},
        "statistics_results": {"sample_size": 250},
    }

    result = foundation.generate_recommendation(raw_inputs)

    assert result.opportunity != ""
    assert "growth" in result.opportunity.lower() or "revenue" in result.opportunity.lower()
    assert 0.0 <= result.impact_score <= 100.0
    assert 0.0 <= result.confidence_score <= 100.0
    assert result.priority in ["Critical", "High", "Medium", "Low"]
    assert len(result.detected_opportunities) >= 1


def test_missing_forecast_data_raises_validation_error():
    """Test 2: Missing Forecast Data -> RecommendationValidationError."""
    foundation = RecommendationFoundation()
    raw_inputs = {
        "eda_results": {"customer_retention": 0.95},
        "statistics_results": {"sample_size": 250},
        # forecast_results omitted
    }

    with pytest.raises(RecommendationValidationError) as exc_info:
        foundation.generate_recommendation(raw_inputs)

    assert "Missing forecast data" in str(exc_info.value)


def test_invalid_forecast_results_raises_validation_error():
    """Test that forecast marked invalid by upstream validator raises RecommendationValidationError."""
    foundation = RecommendationFoundation()
    raw_inputs = {
        "forecast_results": {"growth_rate": 0.15, "is_valid": False},
    }

    with pytest.raises(RecommendationValidationError) as exc_info:
        foundation.generate_recommendation(raw_inputs)

    assert "marked as invalid" in str(exc_info.value)


def test_scoring_logic_bounds_and_priority_mapping():
    """Test impact, confidence, and priority calculation boundaries."""
    foundation = RecommendationFoundation()

    # Impact score bounds
    assert foundation.compute_impact_score(15.0, benchmark=20.0) == 75.0
    assert foundation.compute_impact_score(500.0, benchmark=20.0) == 100.0
    assert foundation.compute_impact_score(-10.0, benchmark=20.0) == 50.0

    # Confidence score bounds
    conf = foundation.compute_confidence_score(sample_size=150, certainty_metric=0.95, data_quality_score=1.0)
    assert 0.0 <= conf <= 100.0
    assert conf >= 80.0

    # Priority mapping
    assert foundation.compute_priority(90.0, 90.0) == PriorityLevel.CRITICAL
    assert foundation.compute_priority(65.0, 65.0) == PriorityLevel.HIGH
    assert foundation.compute_priority(45.0, 45.0) == PriorityLevel.MEDIUM
    assert foundation.compute_priority(20.0, 20.0) == PriorityLevel.LOW


def test_dependency_injection_custom_weights():
    """Test that injecting custom scoring weights impacts priority calculation."""
    custom_weights = ScoringWeights(impact_weight=0.9, confidence_weight=0.1)
    foundation = RecommendationFoundation(weights=custom_weights)

    # High impact, low confidence: with 0.9 impact weight, composite is 0.9*80 + 0.1*20 = 74 -> HIGH
    p1 = foundation.compute_priority(80.0, 20.0)
    assert p1 == PriorityLevel.HIGH

    # With default weights (0.6, 0.4), composite is 0.6*80 + 0.4*20 = 56 -> HIGH
    # Test critical threshold with 0.9 weight: 0.9*90 + 0.1*20 = 83 -> CRITICAL
    p2 = foundation.compute_priority(90.0, 20.0)
    assert p2 == PriorityLevel.CRITICAL
