"""Tests for Phase 9.2: Integration Testing Framework."""

import numpy as np
import pandas as pd
import pytest
from backend.validation.integration_harness import IntegrationTestingHarness


@pytest.fixture
def harness():
    return IntegrationTestingHarness()


@pytest.fixture
def sample_sales_df():
    dates = pd.date_range("2025-01-01", periods=30, freq="D")
    revenue = np.linspace(100, 300, 30) + np.random.normal(0, 5, 30)
    costs = revenue * 0.4 + np.random.normal(0, 2, 30)
    return pd.DataFrame({
        "order_date": dates,
        "revenue": revenue,
        "cost": costs,
        "customer_id": [f"cust_{i % 5}" for i in range(30)],
    })


def test_upload_dataset_integration(harness, sample_sales_df):
    """Test Case: Upload Dataset -> Expected: Profile Created, Quality Score Created, Metadata Created."""
    result = harness.process_dataset_upload_pipeline(
        df=sample_sales_df,
        filename="sales_q1.csv",
    )
    assert result["integration_status"] == "PASSED"
    assert result["profile_created"] is True
    assert result["quality_score_created"] is True
    assert result["metadata_created"] is True

    # Validate metadata
    meta = result["metadata"]
    assert meta["row_count"] == 30
    assert meta["column_count"] == 4
    assert "revenue" in meta["columns"]

    # Validate quality
    qual = result["quality"]
    assert qual["overall_quality_score"] > 80.0
    assert qual["completeness_pct"] == 100.0


def test_full_pipeline_upload_to_forecast(harness, sample_sales_df):
    """Test Case: Upload -> Profiling -> Analytics -> Forecast -> Workflow Completes Successfully."""
    res = harness.run_full_integration_pipeline(
        df=sample_sales_df,
        target_column="revenue",
        date_column="order_date",
        filename="enterprise_sales.csv",
    )
    assert res["integration_status"] == "PASSED"
    assert res["profile_created"] is True
    assert res["quality_score_created"] is True
    assert res["metadata_created"] is True
    assert res["forecast_points"] == 5
    assert len(res["stages_completed"]) == 5
    assert "forecasting_execution" in res["stages_completed"]
