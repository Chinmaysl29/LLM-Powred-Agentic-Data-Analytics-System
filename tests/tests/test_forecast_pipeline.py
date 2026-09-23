"""Unit and integration tests for Phase 6.10 Forecast Pipeline."""

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from backend.app.core.exceptions import ForecastingError
from backend.app.schemas.forecasting import (
    DataPoint,
    ForecastPipelineOutput,
    UnifiedForecastInput,
)
from backend.forecasting.forecast_pipeline import ForecastPipeline


@pytest.fixture
def sample_pipeline_input() -> UnifiedForecastInput:
    # 50 daily revenue observations
    dates = pd.date_range("2024-01-01", periods=50, freq="D").strftime("%Y-%m-%d").tolist()
    series = [DataPoint(date=d, value=float(1000 + i * 10)) for i, d in enumerate(dates)]
    return UnifiedForecastInput(
        series=series,
        frequency="daily",
        horizon=7,
        target="revenue",
    )


def test_forecast_pipeline_full_workflow_execution(sample_pipeline_input: UnifiedForecastInput):
    pipeline = ForecastPipeline()
    output = pipeline.run(
        input_data=sample_pipeline_input,
        what_if_query="marketing +20%",
        optimistic_assumptions={"demand": 1.15},
        pessimistic_assumptions={"demand": 0.90},
    )

    # 1. Pipeline output contract
    assert isinstance(output, ForecastPipelineOutput)
    assert output.run_id != ""

    # 2. Validated Forecast
    assert output.forecast.model_type in ["arima", "prophet", "xgboost"]
    assert len(output.forecast.forecast) == 7
    assert len(output.forecast.dates) == 7

    # 3. Validation
    assert output.validation.validation_status in ["PASSED", "WARNING"]
    assert output.validation.quality_score >= 0.0

    # 4. Scenarios
    assert "baseline" in output.scenarios.baseline["scenario"]
    assert output.scenarios.comparison["optimistic_total"] > output.scenarios.comparison["baseline_total"]
    assert output.scenarios.comparison["pessimistic_total"] < output.scenarios.comparison["baseline_total"]

    # 5. What-If
    assert output.what_if.input_change == "marketing +20%"
    assert output.what_if.predicted_revenue > 0.0
    assert 0.0 <= output.what_if.predicted_risk <= 1.0

    # 6. Structured Recommendations
    assert len(output.recommendations) >= 2
    for rec in output.recommendations:
        assert rec.action != ""
        assert rec.rationale != ""
        assert rec.expected_impact != ""
        assert 0.0 <= rec.confidence <= 1.0

    # 7. Deterministic Business Summary
    assert "Executive Forecast Summary" in output.business_summary
    assert "Baseline Trajectory" in output.business_summary
    assert "Scenario Boundaries" in output.business_summary
    assert "What-If Sensitivity" in output.business_summary


def test_forecast_pipeline_short_circuits_on_failure():
    # Only 2 observations — should fail and raise ForecastingError
    dates = ["2024-01-01", "2024-01-02"]
    series = [DataPoint(date=d, value=100.0) for d in dates]
    bad_input = UnifiedForecastInput(series=series, frequency="daily", horizon=5, target="revenue")

    pipeline = ForecastPipeline()
    with pytest.raises(ForecastingError) as exc_info:
        pipeline.run(bad_input)

    assert "failed" in str(exc_info.value).lower()


def test_api_pipeline_endpoints():
    from fastapi import FastAPI
    from backend.app.api.v1.routes.forecasting import router as forecasting_router

    test_app = FastAPI()
    test_app.include_router(forecasting_router, prefix="/api/v1")
    client = TestClient(test_app)

    # Test /api/v1/forecasting/what-if endpoint
    what_if_payload = {
        "input_change": "pricing +5%",
        "target_metric": "revenue",
    }
    resp_wi = client.post("/api/v1/forecasting/what-if", json=what_if_payload)
    assert resp_wi.status_code == 200
    data_wi = resp_wi.json()
    assert data_wi["input_change"] == "pricing +5%"
    assert "predicted_revenue" in data_wi

    # Test /api/v1/forecasting/arima endpoint
    dates = pd.date_range("2024-01-01", periods=35, freq="D").strftime("%Y-%m-%d").tolist()
    series = [{"date": d, "value": float(200 + i * 2)} for i, d in enumerate(dates)]
    arima_payload = {
        "series": series,
        "frequency": "daily",
        "horizon": 5,
        "target": "inventory",
    }
    resp_ar = client.post("/api/v1/forecasting/arima", json=arima_payload)
    assert resp_ar.status_code == 200
    data_ar = resp_ar.json()
    assert data_ar["model_type"] == "arima"
    assert len(data_ar["forecast"]) == 5
