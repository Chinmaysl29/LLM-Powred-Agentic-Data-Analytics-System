"""Unit tests for Phase 6.9 Business Forecast Agent."""

import numpy as np
import pandas as pd
import pytest

from backend.agents.forecasting_agent import BusinessForecastAgent
from backend.app.schemas.forecasting import DataPoint, UnifiedForecastInput


def test_agent_selects_arima_for_short_series():
    # 40 points (< 60)
    dates = pd.date_range("2024-01-01", periods=40, freq="D").strftime("%Y-%m-%d").tolist()
    series = [DataPoint(date=d, value=float(100 + i * 0.5)) for i, d in enumerate(dates)]

    inp = UnifiedForecastInput(series=series, frequency="daily", horizon=5, target="inventory")
    agent = BusinessForecastAgent()

    model_name, reason, _ = agent.select_model(inp)
    assert model_name == "arima"
    assert "< 60" in reason


def test_agent_selects_xgboost_for_exogenous_multivariate():
    # 80 points with marketing spend exogenous regressor
    dates = pd.date_range("2024-01-01", periods=80, freq="D").strftime("%Y-%m-%d").tolist()
    series = [DataPoint(date=d, value=float(200 + i * 2)) for i, d in enumerate(dates)]
    marketing = [float(50 + (i % 5) * 10) for i in range(80)]

    inp = UnifiedForecastInput(
        series=series,
        frequency="daily",
        horizon=7,
        target="revenue",
        exogenous_regressors={"marketing": marketing},
    )
    agent = BusinessForecastAgent()

    model_name, reason, _ = agent.select_model(inp)
    assert model_name == "xgboost"
    assert "exogenous" in reason.lower()


def test_agent_selects_prophet_for_strong_seasonality():
    # 90 points with strong weekly seasonality
    dates = pd.date_range("2024-01-01", periods=90, freq="D").strftime("%Y-%m-%d").tolist()
    series = [
        DataPoint(date=d, value=float(500 + 100 * np.sin(2 * np.pi * (i % 7) / 7.0)))
        for i, d in enumerate(dates)
    ]

    inp = UnifiedForecastInput(series=series, frequency="daily", horizon=7, target="demand")
    agent = BusinessForecastAgent()

    model_name, reason, _ = agent.select_model(inp)
    assert model_name == "prophet"
    assert "periodic autocorrelation" in reason.lower() or "seasonal" in reason.lower()


def test_agent_end_to_end_execution_and_explanation():
    dates = pd.date_range("2024-01-01", periods=45, freq="D").strftime("%Y-%m-%d").tolist()
    series = [DataPoint(date=d, value=float(100 + i * 0.5)) for i, d in enumerate(dates)]

    inp = UnifiedForecastInput(series=series, frequency="daily", horizon=5, target="sales")
    agent = BusinessForecastAgent()

    out = agent.run(inp)

    assert out.selected_model in ["arima", "prophet", "xgboost"]
    assert len(out.selection_reason) > 20
    assert len(out.forecast.forecast) == 5
    assert out.validation.validation_status in ["PASSED", "WARNING"]
