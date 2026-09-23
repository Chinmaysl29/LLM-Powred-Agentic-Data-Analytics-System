"""Tests for Phase 9.3: End-to-End Testing Framework."""

from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from backend.validation.e2e_journey_runner import E2EJourneyRunner


@pytest.fixture
def e2e_runner():
    return E2EJourneyRunner()


@pytest.fixture
def historical_sales_data():
    dates = pd.date_range("2025-01-01", periods=45, freq="D")
    sales = np.linspace(200, 600, 45) + np.random.normal(0, 10, 45)
    return pd.DataFrame({
        "date": dates,
        "revenue": sales,
        "units": np.random.randint(10, 50, 45),
    })


def test_complete_analyst_user_journey(e2e_runner, historical_sales_data):
    """Test Case: Full E2E User Journey (Upload -> Ask Question -> Forecast -> Recommendations -> Report)."""
    journey = e2e_runner.run_complete_analyst_journey(
        df=historical_sales_data,
        user_question="What is our 14-day revenue outlook and action plan?",
        target_column="revenue",
        date_column="date",
        forecast_horizon=14,
    )

    assert journey["e2e_status"] == "SUCCESS"
    assert journey["user_journey_completed"] is True
    assert journey["journey_duration_ms"] > 0

    steps = journey["steps"]

    # 1. Upload
    assert steps["upload_dataset"]["status"] == "completed"
    assert steps["upload_dataset"]["rows"] == 45

    # 2. Ask Question
    assert steps["ask_question"]["status"] == "completed"
    assert "revenue" in steps["ask_question"]["answer"]

    # 3. Forecast
    assert steps["generate_forecast"]["status"] == "completed"
    assert steps["generate_forecast"]["points"] == 14

    # 4. Recommendations
    assert steps["generate_recommendations"]["status"] == "completed"
    assert steps["generate_recommendations"]["count"] >= 2

    # 5. Report
    assert steps["generate_report"]["status"] == "completed"
    assert steps["generate_report"]["file_url"].endswith(".pdf")

    # 6. Dashboard
    assert steps["render_dashboard"]["status"] == "completed"
    assert steps["render_dashboard"]["widgets_count"] >= 5
