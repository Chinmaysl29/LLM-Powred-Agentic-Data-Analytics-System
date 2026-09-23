"""Unit tests for Phase 11.4: AI Quality Monitoring."""

import pytest
from backend.operations.ai_quality_monitor import (
    AIQualityMonitor,
    AlertSeverity,
    QualityDefectType,
)


@pytest.fixture
def quality_monitor():
    return AIQualityMonitor(alert_threshold=90.0)


def test_clean_state_quality_score(quality_monitor):
    """Verify initial baseline quality score is 100.0 with no alerts."""
    status = quality_monitor.get_status()
    assert status["quality_score"] == 100.0
    assert status["has_active_alerts"] is False
    assert status["total_defects"] == 0


def test_incorrect_sql_triggers_quality_alert(quality_monitor):
    """Test Case: Incorrect SQL Output -> Expected: Quality Alert Triggered."""
    # First defect: penalty 8.0 -> score = 92.0 (still >= 90.0)
    res1 = quality_monitor.report_defect(
        defect_type=QualityDefectType.INCORRECT_SQL,
        component="sql_agent",
        details="Generated SQL references non-existent column 'revenue_cents'",
    )
    assert res1["quality_score"] == 92.0
    assert res1["alert_triggered"] is False

    # Second defect: penalty 8.0 -> score = 84.0 (< 90.0) -> triggers alert!
    res2 = quality_monitor.report_defect(
        defect_type=QualityDefectType.INCORRECT_SQL,
        component="sql_agent",
        details="Unterminated string literal in generated WHERE clause",
        severity=AlertSeverity.CRITICAL,
    )
    assert res2["quality_score"] == 84.0
    assert res2["alert_triggered"] is True
    assert res2["alert"]["defect_type"] == "incorrect_sql"
    assert "84.0" in res2["alert"]["message"]


def test_hallucination_and_forecast_defects(quality_monitor):
    """Verify hallucination and wrong forecast defects reduce score appropriately."""
    quality_monitor.report_defect(
        defect_type=QualityDefectType.HALLUCINATION,
        component="rag_agent",
        details="Claimed product revenue increased 500% without citation",
    )
    assert quality_monitor.compute_quality_score() == 90.0

    quality_monitor.report_defect(
        defect_type=QualityDefectType.WRONG_FORECAST,
        component="forecast_agent",
        details="Predicted negative values for inventory volume",
    )
    assert quality_monitor.compute_quality_score() == 83.0

    status = quality_monitor.get_status()
    assert status["has_active_alerts"] is True
    assert len(status["alerts"]) >= 1
