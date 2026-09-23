"""Phase 7.8 — Action Prioritization Engine.

Ranks and organizes large sets of cross-departmental recommendations into clear,
actionable priority tiers: Critical, High, Medium, and Low.
"""

import logging
from typing import Any

from backend.app.schemas.recommendations import (
    ActionPrioritizationOutput,
    PriorityLevel,
    RecommendationItem,
    ScoringWeights,
)

logger = logging.getLogger(__name__)


class ActionPrioritizationEngine:
    """Prioritizes and ranks candidate business actions across multi-dimensional criteria."""

    def __init__(self, weights: ScoringWeights | None = None) -> None:
        self.weights = weights or ScoringWeights()

    def calculate_priority_score(
        self,
        impact_score: float,
        confidence_score: float,
        estimated_value: float = 0.0,
        urgency_score: float = 50.0,
    ) -> float:
        """Calculate a composite prioritization score from 0.0 to 100.0."""
        # Value bonus up to 20 points for massive financial magnitude ($250k+)
        value_bonus = min(max(estimated_value / 25000.0, 0.0), 20.0)

        base_score = (
            self.weights.impact_weight * impact_score
            + self.weights.confidence_weight * confidence_score
        )
        composite = base_score + (0.10 * value_bonus) + (self.weights.urgency_weight * urgency_score)
        return round(float(min(max(composite, 0.0), 100.0)), 2)

    def determine_priority_level(
        self,
        composite_score: float,
        impact_score: float,
        estimated_value: float = 0.0,
        explicit_priority: str | None = None,
    ) -> PriorityLevel:
        """Map scores and financial thresholds to standardized priority tiers."""
        # Check explicit input override
        if explicit_priority:
            p_upper = explicit_priority.upper()
            if "CRIT" in p_upper:
                return PriorityLevel.CRITICAL
            if "HIGH" in p_upper:
                return PriorityLevel.HIGH
            if "MED" in p_upper:
                return PriorityLevel.MEDIUM
            if "LOW" in p_upper:
                return PriorityLevel.LOW

        # High revenue/value impact rule: >= $250k or impact >= 85 or composite >= 78 -> Critical
        if estimated_value >= 250000.0 or impact_score >= 85.0 or composite_score >= 78.0:
            return PriorityLevel.CRITICAL
        if estimated_value >= 100000.0 or impact_score >= 65.0 or composite_score >= 58.0:
            return PriorityLevel.HIGH
        if estimated_value >= 25000.0 or impact_score >= 40.0 or composite_score >= 38.0:
            return PriorityLevel.MEDIUM
        return PriorityLevel.LOW

    def prioritize_actions(
        self,
        actions: list[dict[str, Any] | RecommendationItem],
    ) -> ActionPrioritizationOutput:
        """Process, score, and rank a collection of candidate recommendations."""
        logger.info("Prioritizing %d candidate actions", len(actions))
        prioritized: list[dict[str, Any]] = []

        for idx, item in enumerate(actions):
            raw = item.model_dump() if isinstance(item, RecommendationItem) else dict(item)

            title = raw.get("opportunity") or raw.get("action") or raw.get("finding") or f"Action #{idx+1}"
            impact = float(raw.get("impact_score") or raw.get("impact", 50.0))
            conf = float(raw.get("confidence_score") or raw.get("confidence", 75.0))
            est_value = float(
                raw.get("estimated_value")
                or raw.get("estimated_revenue_increase")
                or raw.get("estimated_savings")
                or raw.get("expected_impact")
                or raw.get("expected_savings", 0.0)
            )
            raw_priority = raw.get("priority")

            comp_score = self.calculate_priority_score(
                impact_score=impact,
                confidence_score=conf,
                estimated_value=est_value,
            )

            tier = self.determine_priority_level(
                composite_score=comp_score,
                impact_score=impact,
                estimated_value=est_value,
                explicit_priority=str(raw_priority) if raw_priority else None,
            )

            record = {
                **raw,
                "opportunity": title,
                "impact_score": impact,
                "confidence_score": conf,
                "estimated_value": est_value,
                "priority_score": comp_score,
                "priority": tier.value if hasattr(tier, "value") else str(tier),
            }
            prioritized.append(record)

        # Sort order: Priority Level rank descending, then priority_score descending
        tier_weights = {
            PriorityLevel.CRITICAL.value: 4,
            PriorityLevel.HIGH.value: 3,
            PriorityLevel.MEDIUM.value: 2,
            PriorityLevel.LOW.value: 1,
        }

        prioritized.sort(
            key=lambda x: (
                tier_weights.get(x["priority"], 0),
                x["priority_score"],
                x["estimated_value"],
            ),
            reverse=True,
        )

        # Assign rank ordinal
        for rank, act in enumerate(prioritized, start=1):
            act["rank"] = rank

        logger.info(
            "Action prioritization finished: %d items ranked. Top action: '%s' (%s)",
            len(prioritized),
            prioritized[0]["opportunity"] if prioritized else "None",
            prioritized[0]["priority"] if prioritized else "N/A",
        )
        return ActionPrioritizationOutput(prioritized_actions=prioritized)
