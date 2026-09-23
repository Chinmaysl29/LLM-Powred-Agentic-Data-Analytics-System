"""Integration and unit tests for Phase 7.10 — Recommendation Pipeline."""

import pytest
from backend.app.core.exceptions import RecommendationValidationError
from backend.recommendations.pipeline import RecommendationPipeline


def test_end_to_end_recommendation_pipeline_multi_signal():
    """Master Prompt End-to-End Test:

    Input:
      - Revenue Down 12%
      - Marketing ROI Down 18%
      - Inventory Overstock 25%

    Expected:
      - Cost Optimization Recommendation Generated
      - Marketing Optimization Recommendation Generated
      - Inventory Reduction Recommendation Generated
      - Priority Ranking Generated
      - Decision Summary Generated
      - Quantified Business Impact Generated
    """
    pipeline = RecommendationPipeline()

    raw_input = {
        "forecast_results": {
            "growth_rate": -0.12,
            "is_valid": True,
        },
        "eda_results": {
            "revenue": 1000000.0,
            "marketing_spend_ratio": 0.45,
            "marketing_roi": -0.18,
            "inventory_overstock_pct": 0.25,
        },
        "statistics_results": {
            "sample_size": 300,
        },
    }

    result = pipeline.execute_pipeline(raw_input)

    # 1. Verify top-level contract
    assert isinstance(result.recommendations, list)
    assert len(result.recommendations) >= 4
    assert isinstance(result.prioritized_actions, list)
    assert len(result.prioritized_actions) >= 4
    assert result.decision_summary != ""
    assert result.business_impact != ""

    # 2. Verify Cost Optimization Recommendation
    cost_recs = [
        a for a in result.prioritized_actions
        if "cost" in a.get("category", "").lower()
        or "marketing expenditure" in str(a).lower()
        or "operating overhead" in str(a).lower()
    ]
    assert len(cost_recs) >= 1

    # 3. Verify Marketing Optimization Recommendation
    marketing_recs = [
        a for a in result.prioritized_actions
        if "marketing" in a.get("category", "").lower()
        or "campaign optimization" in str(a).lower()
    ]
    assert len(marketing_recs) >= 1

    # 4. Verify Inventory Reduction Recommendation
    inventory_recs = [
        a for a in result.prioritized_actions
        if "inventory" in a.get("category", "").lower()
        or "destocking" in str(a).lower()
        or "overstock" in str(a).lower()
    ]
    assert len(inventory_recs) >= 1

    # 5. Verify Priority Ranking Generated
    ranks = [a["rank"] for a in result.prioritized_actions]
    assert ranks == list(range(1, len(result.prioritized_actions) + 1))
    # Top ranked action should be Critical or High
    assert result.prioritized_actions[0]["priority"] in ["Critical", "High"]

    # 6. Verify Decision Summary & Business Impact
    assert "Executive Decision Brief" in result.decision_summary
    assert "Business Impact" in result.business_impact
    assert "$" in result.business_impact


def test_pipeline_growth_scenario():
    """Test pipeline execution for high-growth business scenario."""
    pipeline = RecommendationPipeline()

    growth_input = {
        "forecast_results": {
            "growth_rate": 0.25,
            "is_valid": True,
        },
        "eda_results": {
            "revenue": 2500000.0,
            "customer_retention": 0.94,
        },
        "statistics_results": {
            "sample_size": 500,
        },
    }

    result = pipeline.execute_pipeline(growth_input)

    assert len(result.prioritized_actions) >= 1
    assert "expansion" in result.decision_summary.lower() or "growth" in result.decision_summary.lower()
    assert result.business_impact != ""


def test_pipeline_missing_forecast_raises_validation_error():
    """Test pipeline enforces validation when forecast data is absent."""
    pipeline = RecommendationPipeline()
    empty_input = {"eda_results": {"revenue": 1000000.0}}

    with pytest.raises(RecommendationValidationError):
        pipeline.execute_pipeline(empty_input)


def test_pipeline_dependency_injection():
    """Test custom dependency injection across all engines."""
    pipeline = RecommendationPipeline()
    assert pipeline.foundation is not None
    assert pipeline.business_engine is not None
    assert pipeline.cost_engine is not None
    assert pipeline.revenue_engine is not None
    assert pipeline.pricing_engine is not None
    assert pipeline.marketing_engine is not None
    assert pipeline.inventory_engine is not None
    assert pipeline.prioritization_engine is not None
    assert pipeline.decision_agent is not None
