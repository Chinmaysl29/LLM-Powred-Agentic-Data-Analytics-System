"""Tests for Phase 8.3: Audit Logging System."""

import pytest
from backend.security.audit_logger import AuditLogger


@pytest.fixture
def logger():
    al = AuditLogger()
    al.clear_history()
    return al


def test_forecast_executed_audit_record(logger):
    """Verify forecast executed audit record matches required output schema."""
    record = logger.log_forecast_run(
        user="analyst@company.com",
        target_column="revenue",
        model_type="prophet",
        horizon=30,
    )
    assert record["event"] == "forecast_executed"
    assert record["user"] == "analyst@company.com"
    assert "timestamp" in record
    assert record["details"]["target_column"] == "revenue"


def test_every_enterprise_action_generates_audit_record(logger):
    """Test Case: Every enterprise action must generate an audit record."""
    u = "operator@enterprise.com"

    r1 = logger.log_login(user=u, ip="192.168.1.100")
    assert r1["event"] == "user_login"
    assert r1["user"] == u

    r2 = logger.log_dataset_upload(user=u, dataset_id="ds-100", filename="sales_q1.csv", row_count=5000)
    assert r2["event"] == "dataset_upload"

    r3 = logger.log_forecast_run(user=u, target_column="mrr")
    assert r3["event"] == "forecast_executed"

    r4 = logger.log_sql_execution(user=u, query="SELECT SUM(total) FROM orders", execution_time_ms=12.5)
    assert r4["event"] == "sql_query_executed"

    r5 = logger.log_recommendation_generation(user=u, domain="pricing", count=3)
    assert r5["event"] == "recommendation_generated"

    r6 = logger.log_report_download(user=u, report_id="rep-888", format_type="pdf")
    assert r6["event"] == "report_downloaded"

    records = logger.get_audit_records(user=u)
    assert len(records) == 6


def test_filter_audit_records(logger):
    """Test filtering records by user and event type."""
    logger.log_login(user="alice@test.com")
    logger.log_login(user="bob@test.com")
    logger.log_forecast_run(user="alice@test.com", target_column="sales")

    alice_records = logger.get_audit_records(user="alice@test.com")
    assert len(alice_records) == 2

    forecast_records = logger.get_audit_records(event="forecast_executed")
    assert len(forecast_records) == 1
    assert forecast_records[0]["user"] == "alice@test.com"
