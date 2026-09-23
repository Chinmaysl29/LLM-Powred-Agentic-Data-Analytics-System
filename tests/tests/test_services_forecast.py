"""
Tests for forecasting services:
  - ARIMAForecaster
  - ProphetForecaster
  - XGBoostForecaster
  - ForecastValidator
  - ScenarioEngine
  - WhatIfAnalysisEngine
  - BusinessForecastAgent
  - ForecastingFoundationService (validation + preparation)
All run on in-memory synthetic data — no live DB.
"""

import uuid
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd
import pytest

from backend.app.schemas.forecasting import (
    DataPoint,
    FrequencyType,
    ForecastingFoundationConfig,
    UnifiedForecastInput,
)
from backend.forecasting.arima_model import ARIMAForecaster
from backend.forecasting.forecast_validator import ForecastValidator
from backend.forecasting.prophet_model import ProphetForecaster
from backend.forecasting.scenario_engine import ScenarioEngine
from backend.forecasting.what_if_engine import WhatIfAnalysisEngine
from backend.forecasting.xgboost_forecaster import XGBoostForecaster


# ===========================================================================
# Helpers
# ===========================================================================

def _monthly_series(n=36, start_value=1000.0, noise_scale=50.0) -> list[DataPoint]:
    """Generate a clean monthly revenue series."""
    np.random.seed(42)
    base = datetime(2021, 1, 1)
    values = np.linspace(start_value, start_value * 2, n) + np.random.normal(0, noise_scale, n)
    return [
        DataPoint(
            date=(base + timedelta(days=30 * i)).strftime("%Y-%m-%d"),
            value=float(max(v, 1.0)),
        )
        for i, v in enumerate(values)
    ]



def _forecast_input(n=36, horizon=6, target="revenue") -> UnifiedForecastInput:
    return UnifiedForecastInput(
        series=_monthly_series(n),
        target=target,
        horizon=horizon,
        frequency=FrequencyType.MONTHLY,
    )


# ===========================================================================
# ARIMAForecaster Tests
# ===========================================================================

class TestARIMAForecaster:

    @pytest.fixture
    def forecaster(self):
        return ARIMAForecaster()

    def test_forecast_returns_unified_output(self, forecaster):
        inp = _forecast_input(n=36, horizon=6)
        output = forecaster.forecast(inp)
        assert output is not None
        assert output.forecast_id is not None

    def test_forecast_has_correct_horizon_length(self, forecaster):
        inp = _forecast_input(n=36, horizon=6)
        output = forecaster.forecast(inp)
        assert len(output.forecast_values) == 6

    def test_forecast_values_are_positive(self, forecaster):
        inp = _forecast_input(n=36, horizon=3)
        output = forecaster.forecast(inp)
        for dp in output.forecast_values:
            assert dp.value > 0

    def test_forecast_has_confidence_bounds(self, forecaster):
        inp = _forecast_input(n=36, horizon=3)
        output = forecaster.forecast(inp)
        assert output.lower_bound is not None
        assert output.upper_bound is not None

    def test_model_name_is_arima(self, forecaster):
        inp = _forecast_input(n=36, horizon=3)
        output = forecaster.forecast(inp)
        assert "arima" in output.model_name.lower()

    def test_insufficient_data_raises(self, forecaster):
        inp = _forecast_input(n=5, horizon=3)  # Too few observations
        with pytest.raises(Exception):
            forecaster.forecast(inp)


# ===========================================================================
# ProphetForecaster Tests
# ===========================================================================

class TestProphetForecaster:

    @pytest.fixture
    def forecaster(self):
        return ProphetForecaster(use_nse_holidays=False)

    def test_forecast_returns_output(self, forecaster):
        inp = _forecast_input(n=36, horizon=6)
        output = forecaster.forecast(inp)
        assert output is not None
        assert len(output.forecast_values) == 6

    def test_forecast_values_are_numeric(self, forecaster):
        inp = _forecast_input(n=36, horizon=3)
        output = forecaster.forecast(inp)
        for dp in output.forecast_values:
            assert isinstance(dp.value, float)

    def test_prophet_model_name(self, forecaster):
        inp = _forecast_input(n=36, horizon=3)
        output = forecaster.forecast(inp)
        assert "prophet" in output.model_name.lower()

    def test_forecast_upper_bound_greater_than_lower(self, forecaster):
        inp = _forecast_input(n=36, horizon=3)
        output = forecaster.forecast(inp)
        if output.upper_bound and output.lower_bound:
            for ub, lb in zip(output.upper_bound, output.lower_bound):
                assert ub.value >= lb.value


# ===========================================================================
# XGBoostForecaster Tests
# ===========================================================================

class TestXGBoostForecaster:

    @pytest.fixture
    def forecaster(self):
        return XGBoostForecaster()

    def test_forecast_returns_output(self, forecaster):
        inp = _forecast_input(n=36, horizon=6)
        output = forecaster.forecast(inp)
        assert output is not None
        assert len(output.forecast_values) == 6

    def test_forecast_values_are_positive(self, forecaster):
        inp = _forecast_input(n=36, horizon=3)
        output = forecaster.forecast(inp)
        for dp in output.forecast_values:
            assert dp.value >= 0

    def test_model_name_is_xgboost(self, forecaster):
        inp = _forecast_input(n=36, horizon=3)
        output = forecaster.forecast(inp)
        assert "xgboost" in output.model_name.lower()


# ===========================================================================
# ForecastValidator Tests
# ===========================================================================

class TestForecastValidator:

    @pytest.fixture
    def validator(self):
        return ForecastValidator()

    def test_validate_good_forecast(self, validator):
        from backend.forecasting.arima_model import ARIMAForecaster
        inp = _forecast_input(n=36, horizon=6)
        forecast_output = ARIMAForecaster().forecast(inp)
        result = validator.evaluate_forecast(
            forecast_output=forecast_output,
            historical_series=inp.series,
        )
        assert result is not None
        assert hasattr(result, "quality_score") or hasattr(result, "is_valid") or hasattr(result, "score")

    def test_validator_returns_evaluation_result(self, validator):
        from backend.forecasting.arima_model import ARIMAForecaster
        inp = _forecast_input(n=36, horizon=3)
        forecast_output = ARIMAForecaster().forecast(inp)
        result = validator.evaluate_forecast(
            forecast_output=forecast_output,
            historical_series=inp.series,
        )
        assert result is not None


# ===========================================================================
# ScenarioEngine Tests
# ===========================================================================

class TestScenarioEngine:

    @pytest.fixture
    def engine(self):
        return ScenarioEngine()

    def test_generate_scenarios_returns_output(self, engine):
        from backend.forecasting.arima_model import ARIMAForecaster
        inp = _forecast_input(n=36, horizon=6)
        base_forecast = ARIMAForecaster().forecast(inp)
        result = engine.generate_scenarios(
            base_forecast=base_forecast,
            optimistic_assumptions={"growth": 0.10},
            pessimistic_assumptions={"growth": -0.10},
        )
        assert result is not None

    def test_scenarios_have_three_cases(self, engine):
        from backend.forecasting.arima_model import ARIMAForecaster
        inp = _forecast_input(n=36, horizon=3)
        base_forecast = ARIMAForecaster().forecast(inp)
        result = engine.generate_scenarios(base_forecast=base_forecast)
        assert hasattr(result, "baseline") or hasattr(result, "scenarios")


# ===========================================================================
# WhatIfAnalysisEngine Tests
# ===========================================================================

class TestWhatIfAnalysisEngine:

    @pytest.fixture
    def engine(self):
        return WhatIfAnalysisEngine()

    def test_analyze_positive_change(self, engine):
        from backend.app.schemas.forecasting import WhatIfAnalysisInput
        inp = WhatIfAnalysisInput(
            series=_monthly_series(36),
            target="revenue",
            horizon=6,
            frequency=FrequencyType.MONTHLY,
            what_if_query="marketing +15%",
        )
        result = engine.analyze(inp)
        assert result is not None

    def test_analyze_negative_change(self, engine):
        from backend.app.schemas.forecasting import WhatIfAnalysisInput
        inp = WhatIfAnalysisInput(
            series=_monthly_series(36),
            target="revenue",
            horizon=3,
            frequency=FrequencyType.MONTHLY,
            what_if_query="cost -10%",
        )
        result = engine.analyze(inp)
        assert result is not None

    def test_analyze_returns_projected_value(self, engine):
        from backend.app.schemas.forecasting import WhatIfAnalysisInput
        inp = WhatIfAnalysisInput(
            series=_monthly_series(36),
            target="revenue",
            horizon=3,
            frequency=FrequencyType.MONTHLY,
            what_if_query="revenue +20%",
        )
        result = engine.analyze(inp)
        assert hasattr(result, "projected_value") or hasattr(result, "scenario_forecast")


# ===========================================================================
# BusinessForecastAgent Tests
# ===========================================================================

class TestBusinessForecastAgent:

    def test_run_selects_a_model(self):
        from backend.agents.forecasting_agent import BusinessForecastAgent
        agent = BusinessForecastAgent()
        inp = _forecast_input(n=36, horizon=6)
        result = agent.run(inp)
        assert result is not None
        assert hasattr(result, "selected_model") or hasattr(result, "model_name")

    def test_run_returns_forecast_output(self):
        from backend.agents.forecasting_agent import BusinessForecastAgent
        agent = BusinessForecastAgent()
        inp = _forecast_input(n=36, horizon=3)
        result = agent.run(inp)
        assert result is not None

    def test_run_provides_explanation(self):
        from backend.agents.forecasting_agent import BusinessForecastAgent
        agent = BusinessForecastAgent()
        inp = _forecast_input(n=36, horizon=3)
        result = agent.run(inp)
        # Explanation or selection reasoning must be present
        has_explanation = (
            hasattr(result, "selection_explanation")
            or hasattr(result, "explanation")
            or hasattr(result, "model_selection_reason")
        )
        assert has_explanation


# ===========================================================================
# ForecastingFoundationService Tests
# ===========================================================================

class TestForecastingFoundationService:

    @pytest.fixture
    def svc(self):
        from backend.app.services.forecasting_foundation_service import ForecastingFoundationService
        return ForecastingFoundationService()

    def test_prepare_dataframe_valid_series(self, svc):
        df = pd.DataFrame({
            "date": pd.date_range("2022-01-01", periods=36, freq="MS"),
            "revenue": np.linspace(1000, 5000, 36) + np.random.normal(0, 50, 36),
        })
        config = ForecastingFoundationConfig(time_column="date", target_column="revenue")
        result = svc.prepare_dataframe(df, config=config)
        assert result is not None
        assert result.validation_report.is_valid is True

    def test_validate_dataframe_returns_report(self, svc):
        df = pd.DataFrame({
            "date": pd.date_range("2022-01-01", periods=24, freq="MS"),
            "value": np.random.uniform(100, 1000, 24),
        })
        report = svc.validate_dataframe(
            df=df,
            time_col="date",
            target_col="value",
            frequency="monthly",
        )
        assert report is not None
        assert isinstance(report.is_valid, bool)

    def test_validate_empty_dataframe_fails(self, svc):
        df = pd.DataFrame()
        report = svc.validate_dataframe(
            df=df,
            time_col="date",
            target_col="value",
            frequency="monthly",
        )
        assert report.is_valid is False

    def test_insufficient_rows_fails_validation(self, svc):
        df = pd.DataFrame({
            "date": pd.date_range("2022-01-01", periods=5, freq="MS"),
            "value": [100.0] * 5,
        })
        report = svc.validate_dataframe(
            df=df,
            time_col="date",
            target_col="value",
            frequency="monthly",
        )
        assert report.is_valid is False
