"""Unit tests for Phase 11.2: Product Analytics Engine."""

from datetime import datetime, timedelta, timezone
import pytest
from backend.operations.product_analytics import (
    ProductAnalyticsEngine,
    UsageEventType,
)


@pytest.fixture
def analytics_engine():
    return ProductAnalyticsEngine()


def test_dataset_upload_event_recorded(analytics_engine):
    """Test Case: User uploads dataset -> Expected: Usage Event Recorded."""
    event = analytics_engine.record_event(
        event_type=UsageEventType.DATASET_UPLOAD,
        user_id="user_analytics_01",
        metadata={"filename": "q3_revenue.csv", "rows": 1000},
    )
    assert event["event_type"] == "dataset_upload"
    assert event["user_id"] == "user_analytics_01"
    assert event["event_id"].startswith("ev_")

    metrics = analytics_engine.get_metrics()
    assert metrics["dataset_uploads"] == 1
    assert metrics["daily_active_users"] == 1
    assert metrics["forecast_usage"] == 0


def test_forecast_and_query_metrics(analytics_engine):
    """Verify multiple feature events update respective counters and DAU/WAU."""
    analytics_engine.record_event(UsageEventType.QUERY_EXECUTED, user_id="u1")
    analytics_engine.record_event(UsageEventType.QUERY_EXECUTED, user_id="u2")
    analytics_engine.record_event(UsageEventType.FORECAST_RUN, user_id="u1")
    analytics_engine.record_event(UsageEventType.REPORT_GENERATED, user_id="u3")
    analytics_engine.record_event(UsageEventType.DASHBOARD_USAGE, user_id="u2")

    metrics = analytics_engine.get_metrics()
    assert metrics["queries_executed"] == 2
    assert metrics["forecast_usage"] == 1
    assert metrics["reports_generated"] == 1
    assert metrics["dashboard_usage"] == 1
    assert metrics["daily_active_users"] == 3


def test_active_users_time_windowing(analytics_engine):
    """Verify distinct DAU, WAU, and MAU categorization."""
    now = datetime.now(timezone.utc)
    # Event today
    analytics_engine.record_event(UsageEventType.USER_LOGIN, user_id="user_today", custom_time=now)
    # Event 3 days ago (in WAU and MAU, but not DAU)
    analytics_engine.record_event(UsageEventType.USER_LOGIN, user_id="user_3d", custom_time=now - timedelta(days=3))
    # Event 15 days ago (in MAU, but not DAU/WAU)
    analytics_engine.record_event(UsageEventType.USER_LOGIN, user_id="user_15d", custom_time=now - timedelta(days=15))
    # Event 45 days ago (outside MAU)
    analytics_engine.record_event(UsageEventType.USER_LOGIN, user_id="user_45d", custom_time=now - timedelta(days=45))

    metrics = analytics_engine.get_metrics(reference_time=now)
    assert metrics["daily_active_users"] == 1
    assert metrics["weekly_active_users"] == 2
    assert metrics["monthly_active_users"] == 3


def test_missing_user_id_rejected(analytics_engine):
    """Verify ValueError is raised if user_id is empty."""
    with pytest.raises(ValueError, match="user_id is required"):
        analytics_engine.record_event(UsageEventType.DATASET_UPLOAD, user_id="")
