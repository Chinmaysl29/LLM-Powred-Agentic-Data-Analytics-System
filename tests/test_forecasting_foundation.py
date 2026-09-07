"""Unit and integration tests for Phase 6.1 Forecasting Foundation.

Tests validate:
1. Dataset Validation (date column, target column, minimum history, missing values)
2. Column and Frequency Detection (daily, weekly, monthly, quarterly, yearly; revenue, sales, demand, inventory)
3. Time Series Preparation (duplicate aggregation, grid regularization, gap filling)
4. Feature Engineering (trend, seasonality, cyclics, lags, rolling statistics, leakage prevention)
5. Service Layer and API Contracts (dependency injection, required output structure)
"""

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from backend.app.schemas.forecasting import (
    ForecastingFoundationConfig,
    FrequencyType,
    TargetDomain,
    ValidationCheckStatus,
)
from backend.app.services.forecasting_foundation_service import (
    ForecastingFoundationService,
)
from backend.forecasting.foundation import (
    FeatureEngineer,
    ForecastingFoundation,
    TimeSeriesDetector,
    TimeSeriesPreparer,
    TimeSeriesValidator,
)


@pytest.fixture
def foundation_service() -> ForecastingFoundationService:
    """Fixture providing ForecastingFoundationService without DB dependencies."""
    return ForecastingFoundationService()


# -----------------------------------------------------------------------------
# 1. Dataset Validation Tests
# -----------------------------------------------------------------------------

def test_validation_passes_for_valid_monthly_dataset():
    dates = pd.date_range("2023-01-01", periods=12, freq="MS")
    df = pd.DataFrame({
        "date": dates,
        "revenue": [100.0, 120.0, 110.0, 130.0, 150.0, 140.0, 160.0, 170.0, 165.0, 180.0, 190.0, 200.0],
    })

    report = TimeSeriesValidator.validate(
        df=df,
        time_col="date",
        target_col="revenue",
        frequency="monthly",
    )

    assert report.is_valid is True
    assert report.status in ["PASSED", "WARNING"]
    assert report.total_rows == 12
    assert report.valid_observations == 12
    assert len(report.rejection_reasons) == 0


def test_validation_rejects_missing_date_column():
    df = pd.DataFrame({
        "customer": ["Alice", "Bob", "Charlie"],
        "revenue": [100.0, 200.0, 300.0],
    })

    report = TimeSeriesValidator.validate(
        df=df,
        time_col=None,
        target_col="revenue",
        frequency="monthly",
    )

    assert report.is_valid is False
    assert report.status == "REJECTED"
    assert any("date" in r.lower() for r in report.rejection_reasons)


def test_validation_rejects_missing_or_non_numeric_target():
    dates = pd.date_range("2023-01-01", periods=12, freq="MS")
    df = pd.DataFrame({
        "date": dates,
        "category": ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L"],
    })

    report = TimeSeriesValidator.validate(
        df=df,
        time_col="date",
        target_col=None,
        frequency="monthly",
    )

    assert report.is_valid is False
    assert report.status == "REJECTED"
    assert any("target" in r.lower() for r in report.rejection_reasons)


def test_validation_rejects_insufficient_historical_data():
    # Only 3 daily points when daily forecasting requires at least 14
    dates = pd.date_range("2023-01-01", periods=3, freq="D")
    df = pd.DataFrame({
        "date": dates,
        "demand": [10.0, 12.0, 15.0],
    })

    report = TimeSeriesValidator.validate(
        df=df,
        time_col="date",
        target_col="demand",
        frequency="daily",
    )

    assert report.is_valid is False
    assert report.status == "REJECTED"
    assert any("insufficient" in r.lower() for r in report.rejection_reasons)


def test_validation_handles_missing_values_threshold():
    dates = pd.date_range("2023-01-01", periods=10, freq="MS")
    # 7 nulls out of 10 (> 50% missing)
    vals = [100.0, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, 120.0, 130.0, 140.0]
    df = pd.DataFrame({"date": dates, "revenue": vals})

    report = TimeSeriesValidator.validate(
        df=df,
        time_col="date",
        target_col="revenue",
        frequency="monthly",
    )

    assert report.is_valid is False
    assert report.status == "REJECTED"
    assert any("missing data" in r.lower() or "missing" in r.lower() for r in report.rejection_reasons)


# -----------------------------------------------------------------------------
# 2. Detection Tests (Time Column, Target Domain, Frequency)
# -----------------------------------------------------------------------------

def test_time_column_detection_variations():
    # 1. 'date'
    df1 = pd.DataFrame({"date": ["2023-01-01"], "sales": [100]})
    assert TimeSeriesDetector.detect_time_column(df1) == "date"

    # 2. 'Order_Date'
    df2 = pd.DataFrame({"Order_Date": ["2023-01-01"], "revenue": [200]})
    assert TimeSeriesDetector.detect_time_column(df2) == "Order_Date"

    # 3. 'timestamp'
    df3 = pd.DataFrame({"timestamp": ["2023-01-01 12:00:00"], "amount": [300]})
    assert TimeSeriesDetector.detect_time_column(df3) == "timestamp"

    # 4. 'ds' (Prophet standard)
    df4 = pd.DataFrame({"ds": ["2023-01-01"], "y": [400]})
    assert TimeSeriesDetector.detect_time_column(df4) == "ds"


def test_target_column_detection_domains():
    # Revenue domain
    df_rev = pd.DataFrame({"date": ["2023-01-01"], "monthly_revenue": [50000.0], "notes": ["test"]})
    col_rev, domain_rev = TimeSeriesDetector.detect_target_column(df_rev)
    assert col_rev == "monthly_revenue"
    assert domain_rev == TargetDomain.REVENUE

    # Sales domain
    df_sales = pd.DataFrame({"date": ["2023-01-01"], "total_sales": [1200.0]})
    col_sales, domain_sales = TimeSeriesDetector.detect_target_column(df_sales)
    assert col_sales == "total_sales"
    assert domain_sales == TargetDomain.SALES

    # Demand domain
    df_demand = pd.DataFrame({"date": ["2023-01-01"], "units_sold": [450]})
    col_demand, domain_demand = TimeSeriesDetector.detect_target_column(df_demand)
    assert col_demand == "units_sold"
    assert domain_demand == TargetDomain.DEMAND

    # Inventory domain
    df_inv = pd.DataFrame({"date": ["2023-01-01"], "stock_level": [8900]})
    col_inv, domain_inv = TimeSeriesDetector.detect_target_column(df_inv)
    assert col_inv == "stock_level"
    assert domain_inv == TargetDomain.INVENTORY


def test_frequency_detection_all_five_cadences():
    # Daily
    daily_dates = pd.date_range("2023-01-01", periods=20, freq="D")
    assert TimeSeriesDetector.detect_frequency(pd.Series(daily_dates)) == FrequencyType.DAILY.value

    # Weekly
    weekly_dates = pd.date_range("2023-01-01", periods=15, freq="W")
    assert TimeSeriesDetector.detect_frequency(pd.Series(weekly_dates)) == FrequencyType.WEEKLY.value

    # Monthly
    monthly_dates = pd.date_range("2023-01-01", periods=12, freq="MS")
    assert TimeSeriesDetector.detect_frequency(pd.Series(monthly_dates)) == FrequencyType.MONTHLY.value

    # Quarterly
    quarterly_dates = pd.date_range("2020-01-01", periods=8, freq="QS")
    assert TimeSeriesDetector.detect_frequency(pd.Series(quarterly_dates)) == FrequencyType.QUARTERLY.value

    # Yearly
    yearly_dates = pd.date_range("2015-01-01", periods=6, freq="YS")
    assert TimeSeriesDetector.detect_frequency(pd.Series(yearly_dates)) == FrequencyType.YEARLY.value


# -----------------------------------------------------------------------------
# 3. Time Series Preparation Tests
# -----------------------------------------------------------------------------

def test_preparation_aggregates_duplicates_and_fills_gaps():
    # 2 transactions on 2023-01-01 (100 and 150 -> sum 250), missing 2023-01-02, 1 on 2023-01-03 (300)
    df = pd.DataFrame({
        "order_date": ["2023-01-01", "2023-01-01", "2023-01-03"],
        "sales": [100.0, 150.0, 300.0],
    })

    prepared = TimeSeriesPreparer.prepare(
        df=df,
        time_col="order_date",
        target_col="sales",
        frequency="daily",
        aggregation_func="sum",
        fill_method="interpolate",
    )

    # Output should have continuous 3 days: 01, 02, 03
    assert len(prepared) == 3
    assert "ds" in prepared.columns
    assert "y" in prepared.columns
    # Day 1 should be aggregated to 250.0
    assert prepared.iloc[0]["y"] == 250.0
    # Day 2 should be interpolated between 250 and 300 -> 275.0
    assert prepared.iloc[1]["y"] == 275.0
    # Day 3 should be 300.0
    assert prepared.iloc[2]["y"] == 300.0


# -----------------------------------------------------------------------------
# 4. Feature Engineering Tests & Leakage Prevention
# -----------------------------------------------------------------------------

def test_feature_engineering_generates_all_components():
    dates = pd.date_range("2023-01-01", periods=16, freq="MS")
    df = pd.DataFrame({
        "ds": dates,
        "y": [float(i * 10 + 100) for i in range(16)],
    })

    feat_df, summary = FeatureEngineer.generate_features(df, frequency="monthly")

    # Trend features
    assert "trend_step" in feat_df.columns
    assert "log_trend" in feat_df.columns
    assert "trend_squared" in feat_df.columns
    assert feat_df["trend_step"].iloc[0] == 0.0
    assert feat_df["trend_step"].iloc[5] == 5.0

    # Calendar & cyclical features
    assert "month" in feat_df.columns
    assert "quarter" in feat_df.columns
    assert "sin_month" in feat_df.columns
    assert "cos_month" in feat_df.columns
    assert feat_df["sin_month"].min() >= -1.0
    assert feat_df["sin_month"].max() <= 1.0

    # Lags
    assert "lag_1" in feat_df.columns
    assert "lag_2" in feat_df.columns

    # Rolling stats
    assert "rolling_mean_2" in feat_df.columns
    assert "rolling_std_2" in feat_df.columns
    assert "ewma_3" in feat_df.columns

    assert summary.total_features > 10


def test_strict_lookahead_leakage_prevention():
    """Verify that features at time index t ONLY use data from t-1 or earlier."""
    dates = pd.date_range("2023-01-01", periods=10, freq="MS")
    y_values = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0]
    df = pd.DataFrame({"ds": dates, "y": y_values})

    feat_df, _ = FeatureEngineer.generate_features(
        df,
        frequency="monthly",
        custom_lags=[1, 2],
        custom_rolling=[2],
    )

    # At index 2 (time t=2, where y=30.0):
    # lag_1 MUST be y[1] = 20.0 (past value)
    assert feat_df.loc[2, "lag_1"] == 20.0
    # lag_2 MUST be y[0] = 10.0 (past value)
    assert feat_df.loc[2, "lag_2"] == 10.0

    # At index 3 (time t=3, where y=40.0):
    # rolling_mean_2 must be computed on shifted series (i.e. mean of y[2] and y[1] -> (30+20)/2 = 25.0)
    # It must NOT include y[3] = 40.0!
    assert feat_df.loc[3, "rolling_mean_2"] == 25.0


# -----------------------------------------------------------------------------
# 5. Service Layer & Output Schema Tests
# -----------------------------------------------------------------------------

def test_forecasting_foundation_service_response_format(foundation_service: ForecastingFoundationService):
    dates = pd.date_range("2023-01-01", periods=12, freq="MS")
    df = pd.DataFrame({
        "timestamp": dates,
        "revenue": [100.0, 110.0, 120.0, 130.0, 140.0, 150.0, 160.0, 170.0, 180.0, 190.0, 200.0, 210.0],
    })

    resp = foundation_service.prepare_dataframe(df)

    # Check the required contract fields
    assert resp.dataset_ready is True
    assert resp.frequency == "monthly"
    assert resp.target_column == "revenue"
    assert resp.time_column == "timestamp"
    assert resp.data_domain == "revenue"
    assert resp.total_records == 12
    assert resp.validation_report.is_valid is True
    assert resp.feature_summary is not None
    assert len(resp.feature_names) > 5
    assert resp.prepared_data_preview is not None
    assert len(resp.prepared_data_preview) > 0


def test_forecasting_foundation_rejects_and_formats_output(foundation_service: ForecastingFoundationService):
    # 2 rows is insufficient for monthly forecasting
    df = pd.DataFrame({
        "date": ["2023-01-01", "2023-02-01"],
        "sales": [50.0, 60.0],
    })

    resp = foundation_service.prepare_dataframe(df)

    assert resp.dataset_ready is False
    assert resp.target_column == "sales"
    assert resp.validation_report.is_valid is False
    assert len(resp.validation_report.rejection_reasons) > 0


# -----------------------------------------------------------------------------
# 6. Direct In-Memory DataFrame Processing
# -----------------------------------------------------------------------------

def test_forecasting_foundation_facade_direct():
    dates = pd.date_range("2022-01-01", periods=20, freq="W")
    df = pd.DataFrame({
        "time": dates,
        "inventory": np.random.randint(100, 500, size=20).astype(float),
    })

    config = ForecastingFoundationConfig(
        time_column="time",
        target_column="inventory",
        frequency=FrequencyType.WEEKLY,
    )

    prepared_df, resp = ForecastingFoundation.process_dataframe(df, config=config)

    assert not prepared_df.empty
    assert resp.dataset_ready is True
    assert resp.frequency == "weekly"
    assert resp.target_column == "inventory"
    assert resp.data_domain == "inventory"
    assert "ds" in prepared_df.columns
    assert "y" in prepared_df.columns
    assert "lag_1" in prepared_df.columns


# -----------------------------------------------------------------------------
# 7. FastAPI Endpoint Integration Tests
# -----------------------------------------------------------------------------

def test_api_prepare_data_endpoint():
    from fastapi import FastAPI
    from backend.app.api.v1.routes.forecasting import router as forecasting_router

    test_app = FastAPI()
    test_app.include_router(forecasting_router, prefix="/api/v1")
    client = TestClient(test_app)

    dates = pd.date_range("2023-01-01", periods=12, freq="MS").strftime("%Y-%m-%d").tolist()
    records = [{"date": d, "revenue": float(i * 100 + 1000)} for i, d in enumerate(dates)]

    payload = {
        "records": records,
        "config": {
            "time_column": "date",
            "target_column": "revenue",
            "frequency": "monthly",
        },
    }

    resp = client.post("/api/v1/forecasting/prepare-data", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["dataset_ready"] is True
    assert data["frequency"] == "monthly"
    assert data["target_column"] == "revenue"
    assert data["total_records"] == 12
    assert "trend_step" in data["feature_names"]


def test_api_validate_endpoint():
    from fastapi import FastAPI
    from backend.app.api.v1.routes.forecasting import router as forecasting_router

    test_app = FastAPI()
    test_app.include_router(forecasting_router, prefix="/api/v1")
    client = TestClient(test_app)

    # Valid dataset
    dates = pd.date_range("2023-01-01", periods=12, freq="MS").strftime("%Y-%m-%d").tolist()
    records = [{"date": d, "revenue": 500.0} for d in dates]

    resp = client.post(
        "/api/v1/forecasting/validate",
        json={"records": records, "frequency": "monthly", "target_column": "revenue", "time_column": "date"},
    )
    assert resp.status_code == 200
    report = resp.json()
    assert report["is_valid"] is True
    assert report["status"] in ["PASSED", "WARNING"]

    # Invalid dataset (insufficient observations)
    short_records = [{"date": "2023-01-01", "revenue": 500.0}]
    resp_short = client.post(
        "/api/v1/forecasting/validate",
        json={"records": short_records, "frequency": "monthly", "target_column": "revenue", "time_column": "date"},
    )
    assert resp_short.status_code == 200
    short_report = resp_short.json()
    assert short_report["is_valid"] is False
    assert short_report["status"] == "REJECTED"

