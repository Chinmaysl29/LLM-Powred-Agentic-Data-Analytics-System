"""Unit tests for Phase 7.6 — Marketing Intelligence Engine."""

import pytest
from backend.recommendations.marketing_recommendations import MarketingIntelligenceEngine


def test_low_roi_campaign_generates_optimization_recommendation():
    """Test 1: Low ROI campaign -> Campaign optimization recommendation generated."""
    engine = MarketingIntelligenceEngine()
    marketing_data = {
        "campaign_name": "Summer Paid Search",
        "spend": 50000.0,
        "revenue": 45000.0,  # Negative ROI (-10%)
        "roi": -0.10,
    }

    result = engine.analyze_campaigns(marketing_data)

    assert isinstance(result.marketing_actions, list)
    assert len(result.marketing_actions) >= 1
    assert result.expected_roi > 0

    action = result.marketing_actions[0]
    assert "Summer Paid Search" in action["campaign"]
    assert "Campaign Optimization" in action["recommendation"]
    assert action["current_roi"] == -10.0
    assert action["priority"] in ["Critical", "High"]


def test_cac_ltv_evaluation_and_multiple_campaigns():
    """Test evaluating multiple campaigns with LTV:CAC ratios."""
    engine = MarketingIntelligenceEngine()
    marketing_data = {
        "campaigns": [
            {
                "campaign_name": "Affiliate Network",
                "spend": 20000.0,
                "revenue": 100000.0,
                "roi": 4.0,  # Healthy 400% ROI
                "cac": 120.0,
                "ltv": 600.0,  # 5.0x ratio (healthy)
            },
            {
                "campaign_name": "Display Ads",
                "spend": 30000.0,
                "revenue": 33000.0,
                "roi": 0.10,  # Low 10% ROI
                "cac": 350.0,
                "ltv": 500.0,  # 1.43x ratio (suboptimal)
            },
        ]
    }

    result = engine.analyze_campaigns(marketing_data)

    assert len(result.marketing_actions) >= 2  # Low ROI + Suboptimal LTV:CAC
    actions_text = " ".join([a["recommendation"] for a in result.marketing_actions])
    assert "Campaign Optimization" in actions_text
    assert "Refine audience targeting" in actions_text
    assert result.expected_roi > 50.0
