"""Unit tests for Phase 6.3 Prophet Forecasting Service."""

import numpy as np
import pandas as pd
import pytest

from backend.app.core.exceptions import ForecastingDatasetValidationError
from backend.app.schemas.forecasting import DataPoint, UnifiedForecastInput
from backend.forecasting.prophet_model import NSETradingCalendar, ProphetForecaster


def test_nse_holiday_calendar_generation():
    holidays_df = NSETradingCalendar.get_holiday_dataframe(2023, 2026)
    assert not holidays_df.empty
    assert "holiday" in holidays_df.columns
    assert "ds" in holidays_df.columns
    assert any("Republic_Day" in h for h in holidays_df["holiday"])
    assert any("Diwali" in h for h in holidays_df["holiday"])


def test_prophet_forecasting_daily_revenue_horizon_and_bounds():
    dates = pd.date_range("2024-01-01", periods=90, freq="D").strftime("%Y-%m-%d").tolist()
    # Trend + weekly seasonality
    series = [
        DataPoint(date=d, value=float(1000 + i * 5 + 50 * np.sin(2 * np.pi * (i % 7) / 7.0)))
        for i, d in enumerate(dates)
    ]

    inp = UnifiedForecastInput(
        series=series,
        frequency="daily",
        horizon=14,
        confidence_level=0.95,
        target="revenue",
    )

    forecaster = ProphetForecaster(use_nse_holidays=True)
    out = forecaster.forecast(inp)

    # 1. Unified schema verification
    assert out.model_type == "prophet"
    assert out.target == "revenue"
    assert out.frequency == "daily"
    assert out.horizon == 14
    assert len(out.dates) == 14
    assert len(out.forecast) == 14
    assert len(out.lower_bound) == 14
    assert len(out.upper_bound) == 14

    # 2. Bound ordering: lower <= forecast <= upper
    for low, fcast, up in zip(out.lower_bound, out.forecast, out.upper_bound):
        assert low <= fcast <= up

    # 3. Diagnostics: changepoints and NSE holiday flag
    assert "changepoints" in out.diagnostics
    assert out.diagnostics["nse_holidays_applied"] is True


def test_prophet_minimum_history_rejection():
    # Only 5 daily points (< 14 minimum required)
    dates = pd.date_range("2024-01-01", periods=5, freq="D").strftime("%Y-%m-%d").tolist()
    series = [DataPoint(date=d, value=float(100 + i)) for i, d in enumerate(dates)]

    inp = UnifiedForecastInput(
        series=series,
        frequency="daily",
        horizon=7,
        target="sales",
    )

    forecaster = ProphetForecaster()
    with pytest.raises(ForecastingDatasetValidationError) as exc_info:
        forecaster.forecast(inp)

    assert "at least 2 full seasonal cycles" in str(exc_info.value)
