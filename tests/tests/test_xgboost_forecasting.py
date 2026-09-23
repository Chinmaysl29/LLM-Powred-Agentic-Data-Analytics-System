"""Unit tests for Phase 6.5 XGBoost Forecasting Service."""

import numpy as np
import pandas as pd
import pytest

from backend.app.core.exceptions import ForecastingDatasetValidationError
from backend.app.schemas.forecasting import DataPoint, UnifiedForecastInput
from backend.forecasting.xgboost_forecaster import XGBoostForecaster


def test_xgboost_forecasting_walk_forward_and_bounds():
    np.random.seed(42)
    n = 80
    dates = pd.date_range("2024-01-01", periods=n, freq="D").strftime("%Y-%m-%d").tolist()

    # Time series with trend and noise
    y = [float(500 + i * 3 + np.random.normal(0, 5)) for i in range(n)]
    series = [DataPoint(date=d, value=v) for d, v in zip(dates, y)]

    # Include an exogenous regressor (e.g. marketing_spend)
    marketing = [float(50 + (i % 7) * 10) for i in range(n)]

    inp = UnifiedForecastInput(
        series=series,
        frequency="daily",
        horizon=10,
        confidence_level=0.95,
        target="sales",
        exogenous_regressors={"marketing_spend": marketing},
    )

    forecaster = XGBoostForecaster(n_estimators=30, max_depth=3)
    out = forecaster.forecast(inp)

    # 1. Output contract
    assert out.model_type == "xgboost"
    assert out.target == "sales"
    assert out.frequency == "daily"
    assert out.horizon == 10
    assert len(out.dates) == 10
    assert len(out.forecast) == 10
    assert len(out.lower_bound) == 10
    assert len(out.upper_bound) == 10

    # 2. Bound ordering
    for low, fcast, up in zip(out.lower_bound, out.forecast, out.upper_bound):
        assert low <= fcast <= up

    # 3. Diagnostics: feature_importance
    assert "feature_importance" in out.diagnostics
    assert len(out.diagnostics["feature_importance"]) > 0
    assert "marketing_spend" in out.diagnostics["exogenous_regressors"]


def test_xgboost_minimum_history_rejection():
    # Only 40 points (< 60 minimum required)
    dates = pd.date_range("2024-01-01", periods=40, freq="D").strftime("%Y-%m-%d").tolist()
    series = [DataPoint(date=d, value=float(100 + i)) for i, d in enumerate(dates)]

    inp = UnifiedForecastInput(
        series=series,
        frequency="daily",
        horizon=5,
        target="revenue",
    )

    forecaster = XGBoostForecaster()
    with pytest.raises(ForecastingDatasetValidationError) as exc_info:
        forecaster.forecast(inp)

    assert "at least 60 historical data points" in str(exc_info.value)
