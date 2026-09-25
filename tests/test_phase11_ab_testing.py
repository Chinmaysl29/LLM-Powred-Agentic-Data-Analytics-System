"""Unit tests for Phase 11.5: A/B Testing Platform."""

import pytest
from backend.operations.ab_testing import (
    ABTestingPlatform,
    MetricDirection,
)


@pytest.fixture
def ab_platform():
    return ABTestingPlatform()


def test_forecast_models_ab_test(ab_platform):
    """Test Case: Two Forecast Models -> Expected: Best Performer Selected."""
    exp = ab_platform.create_experiment(
        name="Prophet vs XGBoost Demand Forecasting",
        variant_a="prophet",
        variant_b="xgboost",
        primary_metric="forecast_accuracy",
        direction=MetricDirection.HIGHER_IS_BETTER,
        min_samples=25,
    )
    exp_id = exp["experiment_id"]

    # Simulate Prophet: mean accuracy 0.82
    for _ in range(30):
        ab_platform.record_result(exp_id, variant="prophet", metric_value=0.82, is_success=True)

    # Simulate XGBoost: mean accuracy 0.94
    for _ in range(30):
        ab_platform.record_result(exp_id, variant="xgboost", metric_value=0.94, is_success=True)

    result = ab_platform.evaluate_winner(exp_id)
    assert result["winner"] == "xgboost"
    assert result["delta"] == 0.12
    assert result["statistically_significant"] is True
    assert result["confidence"] == 0.95


def test_latency_ab_test_lower_is_better(ab_platform):
    """Verify lower-is-better metric (e.g. latency) selects faster model as winner."""
    exp = ab_platform.create_experiment(
        name="Groq vs OpenAI Latency",
        variant_a="openai_gpt4o",
        variant_b="groq_llama3",
        primary_metric="latency_ms",
        direction=MetricDirection.LOWER_IS_BETTER,
        min_samples=20,
    )
    exp_id = exp["experiment_id"]

    for _ in range(25):
        ab_platform.record_result(exp_id, variant="openai_gpt4o", metric_value=850.0)
        ab_platform.record_result(exp_id, variant="groq_llama3", metric_value=120.0)

    result = ab_platform.evaluate_winner(exp_id)
    assert result["winner"] == "groq_llama3"
    assert result["delta"] == 730.0


def test_deterministic_routing(ab_platform):
    """Verify consistent deterministic hash routing per subject ID."""
    exp = ab_platform.create_experiment(
        name="UI Variant Test",
        variant_a="old_nav",
        variant_b="new_nav",
    )
    exp_id = exp["experiment_id"]

    # The same user should always get the exact same variant
    v1 = ab_platform.route_variant(exp_id, "user_alpha_77")
    v2 = ab_platform.route_variant(exp_id, "user_alpha_77")
    assert v1 == v2
    assert v1 in ["old_nav", "new_nav"]
