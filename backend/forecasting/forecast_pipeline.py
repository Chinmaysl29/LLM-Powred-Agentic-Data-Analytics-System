"""Phase 6.10 — Forecast Pipeline Service.

Orchestrates the complete predictive intelligence workflow:
Forecast Foundation -> Model Selection -> Forecast Generation -> Validation
-> Scenario Presets -> What-If Sensitivity -> Structured Recommendations
-> Deterministic Executive Business Summary, with database persistence.
"""

import logging
import uuid
from typing import TYPE_CHECKING, Any

import numpy as np

if TYPE_CHECKING:
    from backend.agents.forecasting_agent import BusinessForecastAgent

from backend.app.core.exceptions import ForecastingError
from backend.app.repositories.forecast_run_repository import ForecastRunRepository
from backend.app.schemas.forecasting import (
    ForecastPipelineOutput,
    RecommendationItem,
    ScenarioEngineOutput,
    UnifiedForecastInput,
    UnifiedForecastOutput,
    WhatIfAnalysisInput,
    WhatIfAnalysisOutput,
)
from backend.forecasting.scenario_engine import ScenarioEngine
from backend.forecasting.what_if_engine import WhatIfAnalysisEngine

logger = logging.getLogger(__name__)


class ForecastPipeline:
    """Enterprise end-to-end forecasting orchestrator."""

    def __init__(
        self,
        forecast_agent: "BusinessForecastAgent | None" = None,
        scenario_engine: ScenarioEngine | None = None,
        what_if_engine: WhatIfAnalysisEngine | None = None,
        run_repository: ForecastRunRepository | None = None,
    ) -> None:
        if forecast_agent is None:
            from backend.agents.forecasting_agent import BusinessForecastAgent
            self.forecast_agent = BusinessForecastAgent()
        else:
            self.forecast_agent = forecast_agent
        self.scenario_engine = scenario_engine or ScenarioEngine()
        self.what_if_engine = what_if_engine or WhatIfAnalysisEngine()
        self.run_repository = run_repository or ForecastRunRepository()

    def _generate_recommendations(
        self,
        forecast_out: UnifiedForecastOutput,
        scenarios: ScenarioEngineOutput,
        what_if: WhatIfAnalysisOutput,
    ) -> list[RecommendationItem]:
        """Synthesize structured, deterministic business recommendations from pipeline outputs."""
        recommendations: list[RecommendationItem] = []
        target = forecast_out.target.lower()
        horizon = forecast_out.horizon
        base_total = scenarios.comparison["baseline_total"]
        opt_pct = scenarios.comparison["optimistic_pct_change"]
        pess_pct = scenarios.comparison["pessimistic_pct_change"]

        # Trend direction
        forecast_vals = forecast_out.forecast
        trend_delta = forecast_vals[-1] - forecast_vals[0]
        growth_pct = (trend_delta / (forecast_vals[0] + 1e-8)) * 100.0

        if target in ["revenue", "sales"]:
            if growth_pct >= 0:
                recommendations.append(
                    RecommendationItem(
                        action=f"Capitalize on projected {growth_pct:.1f}% growth trajectory",
                        rationale=(
                            f"Validated {forecast_out.model_type.upper()} forecast projects positive momentum across {horizon} periods "
                            f"(baseline aggregate: ₹{base_total:,.2f}). Optimistic upside offers +{opt_pct:.1f}%."
                        ),
                        expected_impact=f"Potential upside of +₹{scenarios.comparison['optimistic_delta']:,.2f} over baseline.",
                        confidence=0.88,
                    )
                )
            else:
                recommendations.append(
                    RecommendationItem(
                        action="Implement immediate demand stabilization and pricing review",
                        rationale=(
                            f"Forecast indicates contraction of {growth_pct:.1f}%. "
                            f"Pessimistic risk scenario could reduce revenue by ₹{abs(scenarios.comparison['pessimistic_delta']):,.2f}."
                        ),
                        expected_impact="Mitigate potential downstream margin erosion.",
                        confidence=0.85,
                    )
                )

            # Marketing / elasticity recommendation from what-if
            recommendations.append(
                RecommendationItem(
                    action=f"Simulate proactive expansion: {what_if.input_change}",
                    rationale=(
                        f"What-If sensitivity modeling indicates a predicted growth of {what_if.predicted_growth * 100:.1f}% "
                        f"with an uncertainty risk factor of {what_if.predicted_risk:.2f}."
                    ),
                    expected_impact=f"Projected adjusted outcome: ₹{what_if.predicted_revenue:,.2f}.",
                    confidence=0.82,
                )
            )

        elif target in ["inventory", "stock"]:
            min_fcast = min(forecast_vals)
            recommendations.append(
                RecommendationItem(
                    action="Rebalance safety stock and procurement cycle",
                    rationale=(
                        f"Inventory forecast reaches low of {min_fcast:,.1f} units during the horizon. "
                        f"Pessimistic scenario indicates risk of stock-outs under {pess_pct:.1f}% supply variance."
                    ),
                    expected_impact="Ensure 98%+ service level and eliminate stockout disruptions.",
                    confidence=0.90,
                )
            )

        else:
            recommendations.append(
                RecommendationItem(
                    action=f"Align operational capacity with forecasted {target} trend",
                    rationale=f"Forecast indicates {growth_pct:.1f}% trajectory across the {horizon} period planning window.",
                    expected_impact=f"Operational efficiency gain under baseline ₹{base_total:,.2f}.",
                    confidence=0.80,
                )
            )

        return recommendations

    def _build_deterministic_business_summary(
        self,
        forecast_out: UnifiedForecastOutput,
        scenarios: ScenarioEngineOutput,
        what_if: WhatIfAnalysisOutput,
        validation_status: str,
        quality_score: float,
    ) -> str:
        """Construct deterministic, templated executive summary from validated results."""
        target = forecast_out.target.capitalize()
        model_name = forecast_out.model_type.upper()
        horizon = forecast_out.horizon
        freq = forecast_out.frequency
        base_total = scenarios.comparison["baseline_total"]
        opt_pct = scenarios.comparison["optimistic_pct_change"]
        pess_pct = scenarios.comparison["pessimistic_pct_change"]

        forecast_vals = forecast_out.forecast
        trend_delta = forecast_vals[-1] - forecast_vals[0]
        growth_pct = (trend_delta / (forecast_vals[0] + 1e-8)) * 100.0
        trend_word = "increase" if growth_pct >= 0 else "decrease"

        summary = (
            f"### Executive Forecast Summary: {target} ({freq.capitalize()} Horizon: {horizon} Periods)\n\n"
            f"**Model Selection & Quality:** The predictive intelligence agent selected **{model_name}**, "
            f"achieving a **{validation_status}** audit rating with a Model Quality Score of **{quality_score:.1f}/100**.\n\n"
            f"**Baseline Trajectory:** Total projected {target.lower()} across the {horizon} periods is **₹{base_total:,.2f}**, "
            f"reflecting a **{abs(growth_pct):.1f}% {trend_word}** over the projection window.\n\n"
            f"**Scenario Boundaries:** Under optimistic conditions, performance is expected to expand by **+{opt_pct:.1f}%** "
            f"(₹{scenarios.comparison['optimistic_total']:,.2f}), while pessimistic contraction risk indicates a downside of "
            f"**{pess_pct:.1f}%** (₹{scenarios.comparison['pessimistic_total']:,.2f}).\n\n"
            f"**What-If Sensitivity:** Simulating *{what_if.input_change}* demonstrates an expected outcome of "
            f"**₹{what_if.predicted_revenue:,.2f}** ({what_if.predicted_growth * 100:+.1f}% growth) "
            f"with a stated prediction risk metric of **{what_if.predicted_risk:.2f}**."
        )
        return summary

    def run(
        self,
        input_data: UnifiedForecastInput,
        what_if_query: str = "marketing +15%",
        optimistic_assumptions: dict[str, float] | None = None,
        pessimistic_assumptions: dict[str, float] | None = None,
        run_id: str | None = None,
    ) -> ForecastPipelineOutput:
        """Execute complete forecasting pipeline and persist run outcome."""
        run_id = run_id or str(uuid.uuid4())
        logger.info(
            "Forecast Pipeline execution started run_id=%s target=%s horizon=%d",
            run_id, input_data.target, input_data.horizon
        )

        # 1. Model Selection & Generation & Validation via BusinessForecastAgent
        try:
            agent_result = self.forecast_agent.run(input_data)
        except Exception as e:
            logger.error("Pipeline failed during model selection/generation run_id=%s: %s", run_id, e)
            raise ForecastingError(f"Forecast generation failed: {e}")

        forecast_out = agent_result.forecast
        validation_out = agent_result.validation
        validation_out.run_id = run_id

        # 2. Scenario Generation
        try:
            scenarios = self.scenario_engine.generate_scenarios(
                base_forecast=forecast_out,
                optimistic_assumptions=optimistic_assumptions,
                pessimistic_assumptions=pessimistic_assumptions,
            )
        except Exception as e:
            logger.error("Pipeline failed during scenario generation run_id=%s: %s", run_id, e)
            raise ForecastingError(f"Scenario generation failed: {e}")

        # 3. What-If Sensitivity Analysis
        try:
            what_if_input = WhatIfAnalysisInput(
                input_change=what_if_query,
                target_metric=input_data.target,
                base_forecast=forecast_out,
            )
            what_if_out = self.what_if_engine.analyze(what_if_input)
        except Exception as e:
            logger.error("Pipeline failed during what-if analysis run_id=%s: %s", run_id, e)
            raise ForecastingError(f"What-If analysis failed: {e}")

        # 4. Structured Recommendations
        recommendations = self._generate_recommendations(
            forecast_out=forecast_out,
            scenarios=scenarios,
            what_if=what_if_out,
        )

        # 5. Deterministic Business Summary
        business_summary = self._build_deterministic_business_summary(
            forecast_out=forecast_out,
            scenarios=scenarios,
            what_if=what_if_out,
            validation_status=validation_out.validation_status,
            quality_score=validation_out.quality_score,
        )

        pipeline_output = ForecastPipelineOutput(
            run_id=run_id,
            forecast=forecast_out,
            validation=validation_out,
            scenarios=scenarios,
            what_if=what_if_out,
            recommendations=recommendations,
            business_summary=business_summary,
        )

        # 6. Database Persistence
        params_dict = {
            "frequency": input_data.frequency,
            "horizon": input_data.horizon,
            "confidence_level": input_data.confidence_level,
            "what_if_query": what_if_query,
        }
        self.run_repository.save_run(
            run_id=run_id,
            model_type=forecast_out.model_type,
            target=forecast_out.target,
            params=params_dict,
            output=pipeline_output.model_dump(),
        )

        logger.info(
            "Forecast Pipeline completed successfully run_id=%s model=%s status=%s",
            run_id, forecast_out.model_type, validation_out.validation_status
        )

        return pipeline_output
