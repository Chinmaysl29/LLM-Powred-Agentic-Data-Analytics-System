"""Tests for Phase 8.5: Dashboard Engine."""

import pytest
from backend.dashboards.dashboard_engine import DashboardEngine


@pytest.fixture
def engine():
    return DashboardEngine()


def test_create_complete_enterprise_dashboard(engine):
    """Test Case: Create complete enterprise dashboard with all widgets."""
    resp = engine.create_enterprise_dashboard(title="Revenue & Operations Dashboard")
    assert "dashboard" in resp
    dashboard = resp["dashboard"]

    assert dashboard["title"] == "Revenue & Operations Dashboard"
    assert "dashboard_id" in dashboard
    assert len(dashboard["widgets"]) >= 5

    widget_types = {w["type"] for w in dashboard["widgets"]}
    assert "kpi_card" in widget_types
    assert "chart" in widget_types
    assert "forecast_widget" in widget_types
    assert "recommendation_widget" in widget_types
    assert "dataset_widget" in widget_types

    # Verify chart subtypes
    chart_subtypes = {w["chart_type"] for w in dashboard["widgets"] if w["type"] == "chart"}
    assert "line" in chart_subtypes
    assert "bar" in chart_subtypes
    assert "scatter" in chart_subtypes


def test_individual_widget_creators(engine):
    """Verify each individual widget builder produces correct schema."""
    kpi = engine.create_kpi_card(title="Monthly Active Users", value="45.2K", change_pct=12.4, trend="up")
    assert kpi["type"] == "kpi_card"
    assert kpi["content"]["value"] == "45.2K"

    fcst = engine.create_forecast_widget(
        title="Revenue Forecast",
        target_column="sales",
        forecast_points=[{"ds": "2026-04", "yhat": 15000}],
    )
    assert fcst["type"] == "forecast_widget"
    assert fcst["content"]["target_column"] == "sales"

    recom = engine.create_recommendation_widget(
        title="Optimization",
        recommendations=[{"id": "r1", "text": "Scale servers"}],
    )
    assert recom["type"] == "recommendation_widget"
    assert recom["content"]["total_recommendations"] == 1

    ds_w = engine.create_dataset_widget(
        title="CRM Data",
        dataset_name="crm.parquet",
        row_count=10000,
        column_count=5,
        columns=["id", "name", "spend", "tier", "created_at"],
    )
    assert ds_w["type"] == "dataset_widget"
    assert ds_w["content"]["column_count"] == 5


def test_dashboard_retrieval(engine):
    """Test building and retrieving dashboard by ID."""
    created = engine.create_enterprise_dashboard(title="Exec Review")
    dash_id = created["dashboard"]["dashboard_id"]

    retrieved = engine.get_dashboard(dash_id)
    assert retrieved is not None
    assert retrieved["dashboard"]["title"] == "Exec Review"
