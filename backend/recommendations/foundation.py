"""Phase 7.1 — Recommendation Foundation.

Provides the foundational framework and standardized scoring logic for all
downstream recommendation and optimization engines.
Aggregates EDA, statistics, forecasting, validation, and RAG knowledge outputs.
"""

import logging
from typing import Any

from backend.app.core.exceptions import RecommendationValidationError
from backend.app.schemas.recommendations import (
    AnalyticalInputs,
    FoundationRecommendationOutput,
    OpportunityType,
    PriorityLevel,
    RecommendationCategory,
    RecommendationItem,
    ScoringWeights,
)

logger = logging.getLogger(__name__)


class RecommendationFoundation:
    """Standardized framework for input collection, opportunity detection, and multi-criteria scoring."""

    def __init__(self, weights: ScoringWeights | None = None) -> None:
        self.weights = weights or ScoringWeights()

    def validate_inputs(
        self,
        raw_inputs: AnalyticalInputs | dict[str, Any],
        require_forecast: bool = True,
    ) -> AnalyticalInputs:
        """Validate that required analytical inputs are present and properly structured."""
        if isinstance(raw_inputs, dict):
            try:
                inputs = AnalyticalInputs(**raw_inputs)
            except Exception as exc:
                logger.error("Failed to parse analytical inputs: %s", exc)
                raise RecommendationValidationError(
                    f"Invalid analytical inputs structure: {exc}"
                ) from exc
        elif isinstance(raw_inputs, AnalyticalInputs):
            inputs = raw_inputs
        else:
            raise RecommendationValidationError(
                f"Expected AnalyticalInputs or dict, received: {type(raw_inputs).__name__}"
            )

        if require_forecast:
            if not inputs.forecast_results:
                logger.warning("Validation failure: Missing forecast data")
                raise RecommendationValidationError(
                    "Missing forecast data: 'forecast_results' is required for recommendation generation"
                )
            if (
                isinstance(inputs.forecast_results, dict)
                and inputs.forecast_results.get("is_valid") is False
            ):
                logger.warning("Validation failure: Forecast data marked invalid")
                raise RecommendationValidationError(
                    "Provided forecast data is marked as invalid by validator"
                )

        return inputs

    def compute_impact_score(
        self,
        magnitude: float,
        benchmark: float = 100.0,
        max_scale: float = 100.0,
    ) -> float:
        """Calculate a bounded 0-100 impact score reflecting potential business magnitude."""
        if benchmark <= 0:
            benchmark = 1.0
        # Ratio scaled to 100, clamped [0.0, 100.0]
        raw_score = (abs(magnitude) / benchmark) * max_scale
        return round(float(min(max(raw_score, 0.0), 100.0)), 2)

    def compute_confidence_score(
        self,
        sample_size: int = 100,
        certainty_metric: float = 0.85,
        data_quality_score: float = 1.0,
    ) -> float:
        """Calculate a bounded 0-100 confidence score based on sample size and certainty."""
        # Sample size factor: saturates around n=100
        size_factor = min(sample_size / 100.0, 1.0)
        # Certainty metric (e.g. 1 - MAPE or R^2 or retention) clamped [0, 1]
        certainty = min(max(certainty_metric, 0.0), 1.0)
        quality = min(max(data_quality_score, 0.0), 1.0)

        composite = (0.5 * certainty + 0.3 * quality + 0.2 * size_factor) * 100.0
        return round(float(min(max(composite, 0.0), 100.0)), 2)

    def compute_priority(
        self,
        impact_score: float,
        confidence_score: float,
    ) -> PriorityLevel:
        """Map impact and confidence to standardized priority levels."""
        composite = (
            self.weights.impact_weight * impact_score
            + self.weights.confidence_weight * confidence_score
        )
        if composite >= 75.0:
            return PriorityLevel.CRITICAL
        if composite >= 55.0:
            return PriorityLevel.HIGH
        if composite >= 35.0:
            return PriorityLevel.MEDIUM
        return PriorityLevel.LOW

    def detect_opportunities(self, inputs: AnalyticalInputs) -> list[RecommendationItem]:
        """Examine analytical signals and generate scored recommendation items."""
        items: list[RecommendationItem] = []

        # 1. Growth & Expansion signals from forecast or EDA
        fc = inputs.forecast_results or {}
        eda = inputs.eda_results or {}
        stats = inputs.statistics_results or {}

        rev_growth = float(fc.get("revenue_growth_rate", 0.0) or fc.get("growth_rate", 0.0))
        retention = float(eda.get("customer_retention", 0.0) or stats.get("retention_rate", 0.0))

        if rev_growth > 0.10 or (retention >= 0.90 and rev_growth >= 0.0):
            impact = self.compute_impact_score(rev_growth * 100, benchmark=20.0)
            conf = self.compute_confidence_score(
                sample_size=int(stats.get("sample_size", 100)),
                certainty_metric=retention if retention > 0 else 0.85,
            )
            priority = self.compute_priority(impact, conf)
            items.append(
                RecommendationItem(
                    opportunity=f"Accelerate growth strategy: Revenue projected +{rev_growth*100:.1f}% with {retention*100:.1f}% retention",
                    impact_score=impact,
                    confidence_score=conf,
                    priority=priority,
                    category=RecommendationCategory.GROWTH,
                    action_plan="Double down on high-performing segments and scale acquisition marketing.",
                    estimated_value=round(rev_growth * 500000.0, 2),
                    details={"revenue_growth": rev_growth, "customer_retention": retention},
                )
            )

        # 2. Risk Mitigation signals (revenue decline, high volatility)
        if rev_growth < -0.05:
            decline_pct = abs(rev_growth) * 100
            impact = self.compute_impact_score(decline_pct, benchmark=15.0)
            conf = self.compute_confidence_score(certainty_metric=0.88)
            priority = self.compute_priority(impact, conf)
            items.append(
                RecommendationItem(
                    opportunity=f"Mitigate projected revenue contraction of -{decline_pct:.1f}%",
                    impact_score=impact,
                    confidence_score=conf,
                    priority=priority,
                    category=RecommendationCategory.RISK_MITIGATION,
                    action_plan="Implement retention save-desk, pause non-critical discretionary spend, and re-engage dormant accounts.",
                    estimated_value=round(abs(rev_growth) * 400000.0, 2),
                    details={"projected_decline": rev_growth},
                )
            )

        # 3. Cost reduction signals from EDA / metadata
        mkt_spend_ratio = float(eda.get("marketing_spend_ratio", 0.0) or stats.get("marketing_spend_ratio", 0.0))
        if mkt_spend_ratio > 0.40:
            impact = self.compute_impact_score(mkt_spend_ratio * 100, benchmark=50.0)
            conf = self.compute_confidence_score(certainty_metric=0.90)
            priority = self.compute_priority(impact, conf)
            items.append(
                RecommendationItem(
                    opportunity=f"Optimize operational overhead: Marketing expenditure at {mkt_spend_ratio*100:.1f}% of revenue",
                    impact_score=impact,
                    confidence_score=conf,
                    priority=priority,
                    category=RecommendationCategory.COST_OPTIMIZATION,
                    action_plan="Trim underperforming marketing channels and reallocate budget to highest-ROAS ad sets.",
                    estimated_value=round((mkt_spend_ratio - 0.25) * 300000.0, 2),
                    details={"marketing_spend_ratio": mkt_spend_ratio},
                )
            )

        # 4. Inventory signals
        inv_overstock = float(eda.get("inventory_overstock_pct", 0.0) or fc.get("inventory_overstock_pct", 0.0))
        if inv_overstock > 0.15:
            impact = self.compute_impact_score(inv_overstock * 100, benchmark=25.0)
            conf = self.compute_confidence_score(certainty_metric=0.85)
            priority = self.compute_priority(impact, conf)
            items.append(
                RecommendationItem(
                    opportunity=f"Liquidate surplus inventory: {inv_overstock*100:.1f}% stock exceeding projected demand",
                    impact_score=impact,
                    confidence_score=conf,
                    priority=priority,
                    category=RecommendationCategory.INVENTORY,
                    action_plan="Run targeted clearance promotions and pause immediate purchase orders.",
                    estimated_value=round(inv_overstock * 150000.0, 2),
                    details={"overstock_pct": inv_overstock},
                )
            )

        # Fallback default opportunity if no threshold triggered
        if not items:
            impact = 50.0
            conf = 75.0
            items.append(
                RecommendationItem(
                    opportunity="Maintain steady-state operations and monitor key metrics",
                    impact_score=impact,
                    confidence_score=conf,
                    priority=PriorityLevel.MEDIUM,
                    category=RecommendationCategory.GENERAL,
                    action_plan="Continue scheduled reporting and periodic forecast validation.",
                    estimated_value=0.0,
                    details={"status": "baseline"},
                )
            )

        return items

    def generate_recommendation(
        self,
        raw_inputs: AnalyticalInputs | dict[str, Any],
        require_forecast: bool = True,
    ) -> FoundationRecommendationOutput:
        """Core Phase 7.1 entrypoint: validate inputs, score opportunities, and return standard contract."""
        logger.info("Executing Phase 7.1 Recommendation Foundation analysis")
        inputs = self.validate_inputs(raw_inputs, require_forecast=require_forecast)

        opportunities = self.detect_opportunities(inputs)
        # Sort opportunities by composite impact & confidence descending
        opportunities.sort(
            key=lambda x: (
                self.weights.impact_weight * x.impact_score
                + self.weights.confidence_weight * x.confidence_score
            ),
            reverse=True,
        )

        primary = opportunities[0]
        output = FoundationRecommendationOutput(
            opportunity=primary.opportunity,
            impact_score=primary.impact_score,
            confidence_score=primary.confidence_score,
            priority=primary.priority.value if hasattr(primary.priority, "value") else str(primary.priority),
            detected_opportunities=[op.model_dump() for op in opportunities],
        )
        logger.info(
            "Recommendation Foundation completed successfully: '%s' (Priority: %s, Impact: %.1f)",
            output.opportunity,
            output.priority,
            output.impact_score,
        )
        return output
