"""Unit tests for Phase 11.9: Product Intelligence Dashboard."""

import pytest
from backend.operations.ai_quality_monitor import AIQualityMonitor, QualityDefectType
from backend.operations.cost_optimizer import CostOptimizationEngine
from backend.operations.feedback_intelligence import UserFeedbackIntelligence
from backend.operations.product_analytics import ProductAnalyticsEngine, UsageEventType
from backend.operations.product_dashboard import ProductIntelligenceDashboard


@pytest.fixture
def clean_dashboard():
    analytics = ProductAnalyticsEngine()
    quality = AIQualityMonitor(alert_threshold=90.0)
    cost = CostOptimizationEngine(monthly_budget_usd=1000.0)
    feedback = UserFeedbackIntelligence()

    # Populate sample operational telemetry
    analytics.record_event(UsageEventType.USER_LOGIN, user_id="user_admin")
    analytics.record_event(UsageEventType.QUERY_EXECUTED, user_id="user_admin")
    analytics.record_event(UsageEventType.FORECAST_RUN, user_id="user_admin")
    analytics.record_event(UsageEventType.DATASET_UPLOAD, user_id="user_admin")

    return ProductIntelligenceDashboard(
        analytics=analytics,
        quality=quality,
        cost=cost,
        feedback=feedback,
    )


def test_dashboard_request_returns_all_metrics(clean_dashboard):
    """Test Case: Dashboard Request -> Expected: All Metrics Returned."""
    result = clean_dashboard.get_dashboard_summary()
    assert "dashboard" in result
    db = result["dashboard"]

    # Verify all 6 mandatory dimensions are present
    assert "system_health" in db
    assert "usage_metrics" in db
    assert "quality_metrics" in db
    assert "cost_metrics" in db
    assert "forecast_metrics" in db
    assert "recommendation_metrics" in db

    # Verify specific fields inside each section
    assert db["system_health"]["status"] == "HEALTHY"
    assert db["usage_metrics"]["daily_active_users"] == 1
    assert db["usage_metrics"]["forecast_usage"] == 1
    assert db["quality_metrics"]["composite_quality_score"] == 100.0
    assert db["cost_metrics"]["monthly_budget_usd"] == 1000.0


def test_dashboard_health_degradation(clean_dashboard):
    """Verify system_health status transitions to DEGRADED when quality drops."""
    clean_dashboard.quality.report_defect(
        defect_type=QualityDefectType.INCORRECT_SQL,
        component="sql_agent",
        details="Syntax error in recursive CTE",
    )
    clean_dashboard.quality.report_defect(
        defect_type=QualityDefectType.HALLUCINATION,
        component="rag_agent",
        details="Hallucinatory citation provided",
    )

    result = clean_dashboard.get_dashboard_summary()
    assert result["dashboard"]["system_health"]["status"] in ("DEGRADED", "CRITICAL")
    assert result["dashboard"]["system_health"]["active_quality_alerts"] >= 1
