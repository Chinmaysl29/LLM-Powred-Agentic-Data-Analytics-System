"""Tests for Phase 9.7: Forecasting Validation Framework."""

import numpy as np
import pytest
from backend.validation.forecast_evaluator import ForecastEvaluator


@pytest.fixture
def evaluator():
    return ForecastEvaluator()


def test_forecast_evaluation_error_metrics(evaluator):
    """Test Case: Known Historical Dataset -> Expected: Acceptable Forecast Error."""
    results = evaluator.evaluate_all_models(horizon=7)

    assert results["status"] == "PASS"
    assert "models" in results
    assert "best_model" in results

    models = results["models"]
    assert "arima" in models
    assert "prophet" in models
    assert "xgboost" in models

    for model_name, metrics in models.items():
        assert "rmse" in metrics
        assert "mae" in metrics
        assert "mape" in metrics
        assert "r2" in metrics

        # Verify acceptable forecast errors
        assert metrics["mape"] < 25.0, f"{model_name} MAPE too high: {metrics['mape']}%"
        assert metrics["rmse"] > 0.0
        assert metrics["mae"] > 0.0
        assert "r2" in metrics


def test_calculate_metrics_edge_cases(evaluator):
    """Verify RMSE, MAE, MAPE, and R2 calculation logic."""
    y_true = np.array([100.0, 110.0, 120.0, 130.0])
    y_pred = np.array([102.0, 108.0, 122.0, 128.0])

    metrics = evaluator.calculate_metrics(y_true, y_pred)
    assert metrics["mae"] == 2.0
    assert metrics["rmse"] == 2.0
    assert metrics["mape"] < 3.0
    assert metrics["r2"] > 0.95
