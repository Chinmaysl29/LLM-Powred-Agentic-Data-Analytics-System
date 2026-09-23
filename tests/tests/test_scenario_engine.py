"""Unit tests for Phase 6.7 Scenario Engine Service."""

import pytest

from backend.app.schemas.forecasting import UnifiedForecastOutput
from backend.forecasting.scenario_engine import ScenarioEngine


@pytest.fixture
def sample_forecast() -> UnifiedForecastOutput:
    return UnifiedForecastOutput(
        model_type="prophet",
        target="revenue",
        frequency="monthly",
        generated_at="2024-01-01T00:00:00Z",
        horizon=3,
        dates=["2024-02-01", "2024-03-01", "2024-04-01"],
        forecast=[1000.0, 1100.0, 1200.0],
        lower_bound=[900.0, 1000.0, 1100.0],
        upper_bound=[1100.0, 1200.0, 1300.0],
        diagnostics={},
    )


def test_scenario_engine_default_multipliers(sample_forecast: UnifiedForecastOutput):
    engine = ScenarioEngine()
    out = engine.generate_scenarios(sample_forecast)

    # 1. Baseline is unmodified
    assert out.baseline["forecast"] == [1000.0, 1100.0, 1200.0]
    assert out.baseline["total"] == 3300.0

    # 2. Default optimistic is +15%
    expected_opt = [1150.0, 1265.0, 1380.0]
    assert out.optimistic["forecast"] == expected_opt
    assert out.optimistic["total"] == sum(expected_opt)

    # 3. Default pessimistic is -10%
    expected_pess = [900.0, 990.0, 1080.0]
    assert out.pessimistic["forecast"] == expected_pess
    assert out.pessimistic["total"] == sum(expected_pess)

    # 4. Comparison checks
    assert out.comparison["baseline_total"] == 3300.0
    assert out.comparison["optimistic_total"] == 3795.0
    assert out.comparison["pessimistic_total"] == 2970.0
    assert out.comparison["optimistic_delta"] == 495.0
    assert out.comparison["pessimistic_delta"] == -330.0


def test_scenario_engine_custom_named_drivers(sample_forecast: UnifiedForecastOutput):
    engine = ScenarioEngine()
    # E.g. marketing +10%, pricing +5% -> 1.10 * 1.05 = 1.155
    opt_drivers = {"marketing": 1.10, "pricing": 1.05}
    # E.g. demand -15%
    pess_drivers = {"demand": 0.85}

    out = engine.generate_scenarios(
        sample_forecast,
        optimistic_assumptions=opt_drivers,
        pessimistic_assumptions=pess_drivers,
    )

    assert out.optimistic["effective_multiplier"] == 1.155
    assert out.pessimistic["effective_multiplier"] == 0.85
    assert out.comparison["optimistic_pct_change"] == pytest.approx(15.5, abs=0.1)
    assert out.comparison["pessimistic_pct_change"] == pytest.approx(-15.0, abs=0.1)
