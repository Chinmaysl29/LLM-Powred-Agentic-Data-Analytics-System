"""Unit tests for Phase 6.8 What-If Analysis Engine Service."""

import pytest

from backend.app.schemas.forecasting import UnifiedForecastOutput, WhatIfAnalysisInput
from backend.forecasting.what_if_engine import WhatIfAnalysisEngine


@pytest.fixture
def sample_forecast() -> UnifiedForecastOutput:
    return UnifiedForecastOutput(
        model_type="xgboost",
        target="revenue",
        frequency="monthly",
        generated_at="2024-01-01T00:00:00Z",
        horizon=4,
        dates=["2024-02-01", "2024-03-01", "2024-04-01", "2024-05-01"],
        forecast=[2_500_000.0, 2_500_000.0, 2_500_000.0, 2_500_000.0],  # total = 10,000,000
        lower_bound=[2_300_000.0, 2_300_000.0, 2_300_000.0, 2_300_000.0],
        upper_bound=[2_700_000.0, 2_700_000.0, 2_700_000.0, 2_700_000.0],
        diagnostics={"feature_importance": {"marketing": 0.40}},
    )


def test_what_if_marketing_expansion(sample_forecast: UnifiedForecastOutput):
    engine = WhatIfAnalysisEngine()
    req = WhatIfAnalysisInput(
        input_change="marketing +20%",
        base_forecast=sample_forecast,
    )

    out = engine.analyze(req)

    assert out.input_change == "marketing +20%"
    assert out.predicted_revenue > 10_000_000.0
    # +20% with weight 0.40 -> ~+8% growth
    assert out.predicted_growth == pytest.approx(0.08, abs=0.01)
    assert 0.0 < out.predicted_risk < 1.0


def test_what_if_risk_increases_with_larger_change(sample_forecast: UnifiedForecastOutput):
    engine = WhatIfAnalysisEngine()

    req_small = WhatIfAnalysisInput(input_change="demand +5%", base_forecast=sample_forecast)
    out_small = engine.analyze(req_small)

    req_large = WhatIfAnalysisInput(input_change="demand +50%", base_forecast=sample_forecast)
    out_large = engine.analyze(req_large)

    # Larger change produces wider interval expansion and higher stated risk
    assert out_large.predicted_risk > out_small.predicted_risk
    assert out_large.predicted_growth > out_small.predicted_growth
