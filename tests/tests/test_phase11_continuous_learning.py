"""Unit tests for Phase 11.8: Continuous Learning Pipeline."""

import pytest
from backend.operations.continuous_learning import (
    ContinuousLearningPipeline,
    LearningSource,
)


@pytest.fixture
def learning_pipeline():
    return ContinuousLearningPipeline()


def test_repeated_user_corrections_trigger_action(learning_pipeline):
    """Test Case: Repeated User Corrections -> Expected: Learning Event Recorded & Action Generated."""
    # First correction
    res1 = learning_pipeline.record_learning_event(
        source=LearningSource.QUERY_HISTORY,
        target_component="sql_agent",
        original_input="Show sales grouped by fiscal quarter",
        user_correction="Need DATE_TRUNC('quarter', date_col) instead of STRFTIME",
    )
    assert res1["event_id"].startswith("learn_")

    # Second correction on same component
    res2 = learning_pipeline.record_learning_event(
        source=LearningSource.QUERY_HISTORY,
        target_component="sql_agent",
        original_input="Quarterly revenue growth",
        user_correction="Use LAG() window function",
    )
    assert res2["event_id"].startswith("learn_")

    improvements = learning_pipeline.get_improvements()
    assert improvements["total_learning_events"] == 2
    actions = improvements["improvement_actions"]
    assert len(actions) >= 1
    assert any(a["target"] == "sql_agent" for a in actions)
    assert any(a["action_type"] == "FEW_SHOT_UPDATE" for a in actions)


def test_forecast_rating_feedback_action(learning_pipeline):
    """Verify negative forecast ratings generate hyperparameter tuning action."""
    learning_pipeline.record_learning_event(
        source=LearningSource.FORECAST_ACCURACY,
        target_component="forecast_agent",
        original_input="14-day sales forecast",
        rating=1,
    )
    learning_pipeline.record_learning_event(
        source=LearningSource.FORECAST_ACCURACY,
        target_component="forecast_agent",
        original_input="30-day inventory demand",
        rating=2,
    )

    improvements = learning_pipeline.get_improvements()
    actions = improvements["improvement_actions"]
    assert any(a["target"] == "forecast_agent" for a in actions)
    assert any(a["action_type"] == "HYPERPARAMETER_TUNING" for a in actions)


def test_baseline_monitoring_action(learning_pipeline):
    """Verify empty event stream returns a valid baseline action."""
    improvements = learning_pipeline.get_improvements()
    assert improvements["total_learning_events"] == 0
    assert len(improvements["improvement_actions"]) == 1
    assert improvements["improvement_actions"][0]["target"] == "platform_wide"
