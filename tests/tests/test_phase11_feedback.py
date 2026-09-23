"""Unit tests for Phase 11.1: User Feedback Intelligence."""

import pytest
from backend.operations.feedback_intelligence import (
    FeedbackCategory,
    FeedbackChannel,
    FeedbackPriority,
    UserFeedbackIntelligence,
)


@pytest.fixture
def feedback_engine():
    return UserFeedbackIntelligence()


def test_dashboard_slow_classification(feedback_engine):
    """Test Case: Input 'Dashboard is slow' -> Expected: Performance Feedback Created."""
    res = feedback_engine.capture_feedback(
        description="Dashboard is slow",
        channel=FeedbackChannel.DASHBOARD,
        user_id="user_123",
    )
    assert res["feedback_type"] == FeedbackCategory.PERFORMANCE.value
    assert res["priority"] in [FeedbackPriority.HIGH.value, FeedbackPriority.CRITICAL.value]
    assert "Dashboard is slow" in res["description"]
    assert res["feedback_id"].startswith("fb_")


def test_crash_bug_classification(feedback_engine):
    """Verify fatal crash reports trigger critical bug priority."""
    res = feedback_engine.capture_feedback(
        description="App crash with 500 error when uploading large parquet file",
        channel=FeedbackChannel.BUG_REPORT,
        user_id="user_999",
    )
    assert res["feedback_type"] == FeedbackCategory.BUG.value
    assert res["priority"] == FeedbackPriority.CRITICAL.value


def test_feature_request_capture(feedback_engine):
    """Verify feature requests are recognized and logged."""
    res = feedback_engine.capture_feedback(
        description="Would like export to Tableau integration",
        channel=FeedbackChannel.FEATURE_REQUEST,
    )
    assert res["feedback_type"] == FeedbackCategory.FEATURE_REQUEST.value
    assert res["priority"] in [FeedbackPriority.MEDIUM.value, FeedbackPriority.LOW.value]


def test_empty_feedback_rejected(feedback_engine):
    """Verify empty feedback strings raise ValueError."""
    with pytest.raises(ValueError, match="cannot be empty"):
        feedback_engine.capture_feedback(description="")


def test_feedback_analytics_generation(feedback_engine):
    """Verify aggregation metrics for feedback breakdown and priorities."""
    feedback_engine.capture_feedback("Dashboard is slow", FeedbackChannel.DASHBOARD)
    feedback_engine.capture_feedback("System crash on save", FeedbackChannel.BUG_REPORT)
    feedback_engine.capture_feedback("Can we add dark mode?", FeedbackChannel.FEATURE_REQUEST)

    analytics = feedback_engine.generate_feedback_analytics()
    assert analytics["total_feedback"] == 3
    assert FeedbackCategory.PERFORMANCE.value in analytics["category_breakdown"]
    assert FeedbackCategory.BUG.value in analytics["category_breakdown"]
    assert analytics["critical_unresolved_count"] >= 1
    assert len(analytics["top_issues"]) == 3
