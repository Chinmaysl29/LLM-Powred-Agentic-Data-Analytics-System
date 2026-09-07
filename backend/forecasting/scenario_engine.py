"""Phase 6.7 — Scenario Engine Service.

Generates three fixed scenario presets (baseline, optimistic, pessimistic)
by applying structured business assumption multipliers to a validated forecast,
and computes period-by-period delta comparisons.
"""

import logging
from typing import Any

import numpy as np

from backend.app.schemas.forecasting import ScenarioEngineOutput, UnifiedForecastOutput

logger = logging.getLogger(__name__)


class ScenarioEngine:
    """Enterprise scenario simulator generating baseline, optimistic, and pessimistic projections."""

    DEFAULT_OPTIMISTIC_MULTIPLIER = 1.15   # +15% default upside
    DEFAULT_PESSIMISTIC_MULTIPLIER = 0.90  # -10% default downside

    def __init__(
        self,
        default_optimistic: float = DEFAULT_OPTIMISTIC_MULTIPLIER,
        default_pessimistic: float = DEFAULT_PESSIMISTIC_MULTIPLIER,
    ) -> None:
        self.default_optimistic = default_optimistic
        self.default_pessimistic = default_pessimistic

    def _apply_multipliers(
        self,
        forecast_vals: list[float],
        assumptions: dict[str, float] | None,
        default_multiplier: float,
    ) -> tuple[list[float], float]:
        """Apply composite multiplier from named drivers (demand, marketing, price)."""
        if not assumptions:
            eff_mult = default_multiplier
        else:
            # Composite multiplier is product of all dimension factors
            eff_mult = 1.0
            for factor in assumptions.values():
                eff_mult *= float(factor)

        adjusted = [round(float(v * eff_mult), 2) for v in forecast_vals]
        return adjusted, eff_mult

    def generate_scenarios(
        self,
        base_forecast: UnifiedForecastOutput,
        optimistic_assumptions: dict[str, float] | None = None,
        pessimistic_assumptions: dict[str, float] | None = None,
    ) -> ScenarioEngineOutput:
        """Construct three preset futures and comparative variance matrix."""
        logger.info(
            "Scenario generation initiated for model=%s target=%s horizon=%d",
            base_forecast.model_type, base_forecast.target, base_forecast.horizon
        )

        dates = base_forecast.dates
        baseline_vals = [round(float(v), 2) for v in base_forecast.forecast]
        lower_vals = [round(float(v), 2) for v in base_forecast.lower_bound]
        upper_vals = [round(float(v), 2) for v in base_forecast.upper_bound]

        # 1. Baseline Scenario (unmodified validated forecast)
        baseline_dict: dict[str, Any] = {
            "scenario": "baseline",
            "dates": dates,
            "forecast": baseline_vals,
            "lower_bound": lower_vals,
            "upper_bound": upper_vals,
            "total": round(float(np.sum(baseline_vals)), 2),
            "average": round(float(np.mean(baseline_vals)), 2),
            "assumptions": {"multiplier": 1.0},
        }

        # 2. Optimistic Scenario
        opt_vals, opt_mult = self._apply_multipliers(
            baseline_vals, optimistic_assumptions, self.default_optimistic
        )
        optimistic_dict: dict[str, Any] = {
            "scenario": "optimistic",
            "dates": dates,
            "forecast": opt_vals,
            "lower_bound": [round(float(v * opt_mult), 2) for v in lower_vals],
            "upper_bound": [round(float(v * opt_mult), 2) for v in upper_vals],
            "total": round(float(np.sum(opt_vals)), 2),
            "average": round(float(np.mean(opt_vals)), 2),
            "assumptions": optimistic_assumptions or {"multiplier": self.default_optimistic},
            "effective_multiplier": round(opt_mult, 4),
        }

        # 3. Pessimistic Scenario
        pess_vals, pess_mult = self._apply_multipliers(
            baseline_vals, pessimistic_assumptions, self.default_pessimistic
        )
        pessimistic_dict: dict[str, Any] = {
            "scenario": "pessimistic",
            "dates": dates,
            "forecast": pess_vals,
            "lower_bound": [round(float(v * pess_mult), 2) for v in lower_vals],
            "upper_bound": [round(float(v * pess_mult), 2) for v in upper_vals],
            "total": round(float(np.sum(pess_vals)), 2),
            "average": round(float(np.mean(pess_vals)), 2),
            "assumptions": pessimistic_assumptions or {"multiplier": self.default_pessimistic},
            "effective_multiplier": round(pess_mult, 4),
        }

        # 4. Comparative Deltas (Period-by-period and aggregate)
        opt_deltas = [round(float(o - b), 2) for o, b in zip(opt_vals, baseline_vals)]
        pess_deltas = [round(float(p - b), 2) for p, b in zip(pess_vals, baseline_vals)]

        base_total = baseline_dict["total"]
        opt_total = optimistic_dict["total"]
        pess_total = pessimistic_dict["total"]

        comparison_dict: dict[str, Any] = {
            "target": base_forecast.target,
            "horizon": base_forecast.horizon,
            "baseline_total": base_total,
            "optimistic_total": opt_total,
            "pessimistic_total": pess_total,
            "optimistic_delta": round(opt_total - base_total, 2),
            "pessimistic_delta": round(pess_total - base_total, 2),
            "optimistic_pct_change": round(((opt_total - base_total) / (base_total + 1e-8)) * 100, 2),
            "pessimistic_pct_change": round(((pess_total - base_total) / (base_total + 1e-8)) * 100, 2),
            "period_comparisons": [
                {
                    "date": d,
                    "baseline": b,
                    "optimistic": o,
                    "pessimistic": p,
                    "opt_delta": od,
                    "pess_delta": pd,
                }
                for d, b, o, p, od, pd in zip(dates, baseline_vals, opt_vals, pess_vals, opt_deltas, pess_deltas)
            ],
        }

        logger.info(
            "Scenario generation completed baseline=%.2f optimistic=%.2f pessimistic=%.2f",
            base_total, opt_total, pess_total
        )

        return ScenarioEngineOutput(
            baseline=baseline_dict,
            optimistic=optimistic_dict,
            pessimistic=pessimistic_dict,
            comparison=comparison_dict,
        )
