"""Unit tests for Phase 6.4 ARIMA Forecasting Service."""

import numpy as np
import pandas as pd
import pytest

from backend.app.core.exceptions import ForecastingDatasetValidationError
from backend.app.schemas.forecasting import DataPoint, UnifiedForecastInput
from backend.forecasting.arima_model import ARIMAForecaster


def test_arima_forecasting_order_selection_and_bounds():
    # AR(1) process with trend: y_t = 0.7 * y_{t-1} + trend + noise
    np.random.seed(42)
    n = 50
    dates = pd.date_range("2024-01-01", periods=n, freq="D").strftime("%Y-%m-%d").tolist()

    y = [100.0]
    for i in range(1, n):
        y.append(0.6 * y[-1] + 2.0 + np.random.normal(0, 1.0))

    series = [DataPoint(date=d, value=float(v)) for d, v in zip(dates, y)]

    inp = UnifiedForecastInput(
        series=series,
        frequency="daily",
        horizon=10,
        confidence_level=0.95,
        target="inventory",
    )

    forecaster = ARIMAForecaster()
    out = forecaster.forecast(inp)

    # 1. Output contract
    assert out.model_type == "arima"
    assert out.target == "inventory"
    assert out.frequency == "daily"
    assert out.horizon == 10
    assert len(out.dates) == 10
    assert len(out.forecast) == 10
    assert len(out.lower_bound) == 10
    assert len(out.upper_bound) == 10

    # 2. Bound ordering
    for low, fcast, up in zip(out.lower_bound, out.forecast, out.upper_bound):
        assert low <= fcast <= up

    # 3. Order detection in diagnostics
    assert "order" in out.diagnostics
    order = out.diagnostics["order"]
    assert "p" in order and "d" in order and "q" in order
    assert out.diagnostics["seasonal"] is False
    assert "non-seasonal" in out.diagnostics["limitation"].lower()


def test_arima_minimum_history_rejection():
    # Only 20 points (< 30 minimum required)
    dates = pd.date_range("2024-01-01", periods=20, freq="D").strftime("%Y-%m-%d").tolist()
    series = [DataPoint(date=d, value=float(100 + i)) for i, d in enumerate(dates)]

    inp = UnifiedForecastInput(
        series=series,
        frequency="daily",
        horizon=5,
        target="demand",
    )

    forecaster = ARIMAForecaster()
    with pytest.raises(ForecastingDatasetValidationError) as exc_info:
        forecaster.forecast(inp)

    assert "at least 30 historical data points" in str(exc_info.value)
