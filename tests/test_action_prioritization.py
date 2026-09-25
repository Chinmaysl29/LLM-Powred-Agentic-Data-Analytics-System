"""Unit tests for Phase 7.8 — Action Prioritization Engine."""

import pytest
from backend.app.schemas.recommendations import PriorityLevel, ScoringWeights
from backend.recommendations.action_prioritization import ActionPrioritizationEngine


def test_high_revenue_impact_recommendation_gets_critical_priority():
    """Test 1: High revenue impact recommendation -> Priority = Critical."""
    engine = ActionPrioritizationEngine()
    actions = [
        {
            "opportunity": "Major Enterprise Upsell Wave",
            "impact_score": 90.0,
            "confidence_score": 85.0,
            "estimated_value": 350000.0,  # High revenue impact (>= $250k)
        },
        {
            "opportunity": "Minor office supply audit",
            "impact_score": 20.0,
            "confidence_score": 50.0,
            "estimated_value": 1500.0,
        },
    ]

    result = engine.prioritize_actions(actions)

    assert isinstance(result.prioritized_actions, list)
    assert len(result.prioritized_actions) == 2

    top_action = result.prioritized_actions[0]
    assert top_action["opportunity"] == "Major Enterprise Upsell Wave"
    assert top_action["priority"] == PriorityLevel.CRITICAL.value
    assert top_action["rank"] == 1


def test_large_batch_recommendations_ranking_50_items():
    """Test ordering and bucketing of 50 incoming recommendations."""
    engine = ActionPrioritizationEngine()
    actions = []
    for i in range(50):
        val = float(i * 10000)
        actions.append({
            "opportunity": f"Action Proposal #{i}",
            "impact_score": float((i * 2) % 100),
            "confidence_score": 75.0,
            "estimated_value": val,
        })

    result = engine.prioritize_actions(actions)

    assert len(result.prioritized_actions) == 50
    # First item must have highest priority tier
    first = result.prioritized_actions[0]
    last = result.prioritized_actions[-1]
    assert first["priority"] in ["Critical", "High"]
    assert last["priority"] in ["Low", "Medium"]
    assert first["rank"] == 1
    assert last["rank"] == 50


def test_dependency_injection_custom_scoring_weights():
    """Test injecting custom scoring weights into prioritization."""
    custom_weights = ScoringWeights(impact_weight=0.9, confidence_weight=0.1, urgency_weight=0.0)
    engine = ActionPrioritizationEngine(weights=custom_weights)

    score = engine.calculate_priority_score(impact_score=100.0, confidence_score=0.0, estimated_value=0.0)
    assert score == 90.0
