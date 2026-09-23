"""Unit tests for Phase 6.6 Forecast Validator Service."""

import numpy as np
import pandas as pd
import pytest

from backend.app.schemas.forecasting import (
    DataPoint,
    UnifiedForecastOutput,
)
from backend.forecasting.forecast_validator import ForecastValidator


def test_known_good_forecast_passes_validation():
    # 50 historical points steadily around 100
    dates_hist = pd.date_range("2024-01-01", periods=50, freq="D").strftime("%Y-%m-%d").tolist()
    hist_series = [DataPoint(date=d, value=float(100 + (i % 5))) for i, d in enumerate(dates_hist)]

    # Forecast continues steadily around 100-105
    dates_fcast = pd.date_range("2024-02-20", periods=10, freq="D").strftime("%Y-%m-%d").tolist()
    fcast_vals = [float(102 + (i % 3)) for i in range(10)]
    actuals = [float(101 + (i % 3)) for i in range(10)]

    forecast_out = UnifiedForecastOutput(
        model_type="prophet",
        target="revenue",
        frequency="daily",
        generated_at="2024-02-20T00:00:00Z",
        horizon=10,
        dates=dates_fcast,
        forecast=fcast_vals,
        lower_bound=[v - 5.0 for v in fcast_vals],
        upper_bound=[v + 5.0 for v in fcast_vals],
        diagnostics={},
    )

    validator = ForecastValidator()
    result = validator.evaluate_forecast(
        forecast_output=forecast_out,
        historical_series=hist_series,
        backtest_actuals=actuals,
    )

    assert result.validation_status == "PASSED"
    assert result.mae < 2.0
    assert result.mape < 0.05
    assert len(result.anomalies_detected) == 0
    assert result.quality_score >= 80.0
    assert result.confidence_score >= 80.0


def test_validator_catches_unrealistic_growth_and_spikes():
    # Historical series: gentle changes around 100 (diffs ~ 1-2)
    dates_hist = pd.date_range("2024-01-01", periods=40, freq="D").strftime("%Y-%m-%d").tolist()
    hist_series = [DataPoint(date=d, value=100.0) for d in dates_hist]

    # Injected massive spike to 1000 (10x growth)
    dates_fcast = pd.date_range("2024-02-10", periods=5, freq="D").strftime("%Y-%m-%d").tolist()
    bad_fcast = [100.0, 500.0, 1000.0, 2000.0, 5000.0]

    forecast_out = UnifiedForecastOutput(
        model_type="xgboost",
        target="sales",
        frequency="daily",
        generated_at="2024-02-10T00:00:00Z",
        horizon=5,
        dates=dates_fcast,
        forecast=bad_fcast,
        lower_bound=[v - 10.0 for v in bad_fcast],
        upper_bound=[v + 10.0 for v in bad_fcast],
        diagnostics={},
    )

    validator = ForecastValidator()
    result = validator.evaluate_forecast(
        forecast_output=forecast_out,
        historical_series=hist_series,
    )

    assert result.validation_status == "FAILED"
    assert len(result.anomalies_detected) > 0
    anomaly_types = [a["type"] for a in result.anomalies_detected]
    assert "unrealistic_growth" in anomaly_types or "abnormal_spike" in anomaly_types
    assert result.confidence_score < 70.0
