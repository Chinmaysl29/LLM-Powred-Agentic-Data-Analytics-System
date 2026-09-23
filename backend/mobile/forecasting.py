"""
Phase 12.8.6 — Mobile Forecasting Module
Mobile-optimized forecasting engine supporting interactive scenario modeling
(Base, Optimistic, Conservative), threshold alert triggers, and trend vectors.
"""

from typing import Dict, Any, List, Optional
import time
from pydantic import BaseModel, Field


class MobileForecastScenario(BaseModel):
    name: str # "Base", "Optimistic", "Conservative"
    projected_total: float
    growth_rate: float
    confidence_interval: tuple
    trajectory_points: List[Dict[str, Any]]


class MobileForecastModel(BaseModel):
    model_id: str
    metric: str
    horizon_days: int
    scenarios: Dict[str, MobileForecastScenario]
    trend: str # "BULLISH", "BEARISH", "NEUTRAL"
    active_alerts: List[Dict[str, Any]] = Field(default_factory=list)
    generated_at: float = Field(default_factory=time.time)


class MobileForecastingService:
    """
    Supplies mobile-friendly forecast trajectories, multi-scenario comparisons,
    and automated variance alerts.
    """

    def __init__(self):
        pass

    def load_forecast(self, metric: str = "Quarterly Revenue", horizon_days: int = 90) -> MobileForecastModel:
        """Load forecast curves decimated for mobile display."""
        days = 10 # 10 checkpoint points for mobile rendering
        base_points = [{"day": i * 9, "value": round(1000000 + i * 85000, 2)} for i in range(days)]
        bull_points = [{"day": i * 9, "value": round(1000000 + i * 115000, 2)} for i in range(days)]
        bear_points = [{"day": i * 9, "value": round(1000000 + i * 45000, 2)} for i in range(days)]

        base_scenario = MobileForecastScenario(
            name="Base",
            projected_total=1765000.0,
            growth_rate=14.2,
            confidence_interval=(1680000.0, 1850000.0),
            trajectory_points=base_points
        )
        bull_scenario = MobileForecastScenario(
            name="Optimistic",
            projected_total=2035000.0,
            growth_rate=22.8,
            confidence_interval=(1920000.0, 2150000.0),
            trajectory_points=bull_points
        )
        bear_scenario = MobileForecastScenario(
            name="Conservative",
            projected_total=1405000.0,
            growth_rate=5.1,
            confidence_interval=(1320000.0, 1490000.0),
            trajectory_points=bear_points
        )

        scenarios = {
            "base": base_scenario,
            "optimistic": bull_scenario,
            "conservative": bear_scenario
        }

        # Evaluate potential threshold alerts
        alerts = self.generate_alerts(metric, base_scenario, target_threshold=1700000.0)

        return MobileForecastModel(
            model_id="fcst-rev-2026",
            metric=metric,
            horizon_days=horizon_days,
            scenarios=scenarios,
            trend="BULLISH" if base_scenario.growth_rate > 10.0 else "NEUTRAL",
            active_alerts=alerts
        )

    def compare_scenarios(self, model: MobileForecastModel, scenario_keys: Optional[List[str]] = None) -> Dict[str, Any]:
        """Produce comparison delta between scenario trajectories."""
        keys = scenario_keys or list(model.scenarios.keys())
        comparison = {}
        for k in keys:
            sc = model.scenarios.get(k)
            if sc:
                comparison[k] = {
                    "projected": sc.projected_total,
                    "growth_rate": sc.growth_rate,
                    "ci_spread": sc.confidence_interval[1] - sc.confidence_interval[0]
                }
        return {"metric": model.metric, "comparison": comparison}

    def generate_alerts(
        self,
        metric: str,
        scenario: MobileForecastScenario,
        target_threshold: float
    ) -> List[Dict[str, Any]]:
        """Trigger alerts if confidence bounds or projected totals deviate from targets."""
        alerts = []
        if scenario.projected_total < target_threshold:
            alerts.append({
                "severity": "critical",
                "title": f"Forecast Miss Alert: {metric}",
                "description": f"Projected total {scenario.projected_total} is below target {target_threshold}."
            })
        elif scenario.confidence_interval[0] < target_threshold:
            alerts.append({
                "severity": "warning",
                "title": f"Risk Threshold Alert: {metric}",
                "description": f"Lower confidence bound crosses below threshold {target_threshold}."
            })
        return alerts
