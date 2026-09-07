"""Phase 7.2 — Business Recommendation Engine.

Generates ranked strategic, operational, expansion, and risk mitigation
recommendations from business performance metrics, regional signals, and forecasts.
"""

import logging
from typing import Any

from backend.app.schemas.recommendations import (
    AnalyticalInputs,
    BusinessRecommendationsOutput,
    PriorityLevel,
    RecommendationCategory,
    RecommendationItem,
)
from backend.recommendations.foundation import RecommendationFoundation

logger = logging.getLogger(__name__)


class BusinessRecommendationEngine:
    """Core recommendation generator for growth, risk, expansion, and operational strategies."""

    def __init__(self, foundation: RecommendationFoundation | None = None) -> None:
        self.foundation = foundation or RecommendationFoundation()

    def generate_recommendations(
        self,
        data: dict[str, Any] | AnalyticalInputs,
    ) -> BusinessRecommendationsOutput:
        """Analyze business signals and return ranked recommendations."""
        logger.info("Generating business recommendations")
        raw_dict = data.model_dump() if isinstance(data, AnalyticalInputs) else data

        recommendations: list[dict[str, Any]] = []

        # 1. Regional Expansion Analysis
        # Check either direct region_growth dict or nested eda/forecast keys
        regions: dict[str, float] = {}
        if "regions" in raw_dict and isinstance(raw_dict["regions"], dict):
            regions.update(raw_dict["regions"])
        elif "region_growth" in raw_dict and isinstance(raw_dict["region_growth"], dict):
            regions.update(raw_dict["region_growth"])
        elif "region" in raw_dict and "growth" in raw_dict:
            regions[str(raw_dict["region"])] = float(raw_dict["growth"])
        elif "region_growth" in raw_dict and isinstance(raw_dict["region_growth"], (int, float)):
            region_name = str(raw_dict.get("region_name", "Target Region"))
            regions[region_name] = float(raw_dict["region_growth"])

        for reg_name, growth in regions.items():
            growth_val = float(growth)
            # Support both 0.25 (fractional) and 25.0 (percentage)
            pct = growth_val * 100.0 if abs(growth_val) <= 1.0 else growth_val
            if pct >= 20.0:
                impact = self.foundation.compute_impact_score(pct, benchmark=30.0)
                conf = self.foundation.compute_confidence_score(certainty_metric=0.92)
                priority = self.foundation.compute_priority(impact, conf)
                rec = RecommendationItem(
                    opportunity=f"Expand {reg_name} Sales Team",
                    impact_score=impact,
                    confidence_score=conf,
                    priority=priority,
                    category=RecommendationCategory.EXPANSION,
                    action_plan=f"Hire 3-5 account executives and scale field marketing in {reg_name} to capitalize on {pct:.0f}% growth trajectory.",
                    estimated_value=round(pct * 15000.0, 2),
                    details={"region": reg_name, "growth_percentage": pct, "type": "expansion"},
                )
                recommendations.append(rec.model_dump())

        # 2. Revenue Decline / Recovery Analysis
        rev_decline = raw_dict.get("revenue_decline") or raw_dict.get("decline_rate")
        growth_rate = raw_dict.get("growth_rate") or raw_dict.get("revenue_growth")
        if rev_decline is None and growth_rate is not None and float(growth_rate) < 0:
            rev_decline = abs(float(growth_rate))

        if rev_decline is not None:
            dec_val = float(rev_decline)
            pct_decline = dec_val * 100.0 if abs(dec_val) <= 1.0 else dec_val
            if pct_decline >= 10.0:
                impact = self.foundation.compute_impact_score(pct_decline, benchmark=20.0)
                conf = self.foundation.compute_confidence_score(certainty_metric=0.90)
                priority = PriorityLevel.CRITICAL if pct_decline >= 15.0 else self.foundation.compute_priority(impact, conf)
                rec = RecommendationItem(
                    opportunity=f"Execute Revenue Recovery Plan ({pct_decline:.0f}% Decline Detected)",
                    impact_score=impact,
                    confidence_score=conf,
                    priority=priority,
                    category=RecommendationCategory.RISK_MITIGATION,
                    action_plan="Deploy dedicated account-preservation team, offer renewal incentives, and review customer churn drivers.",
                    estimated_value=round(pct_decline * 25000.0, 2),
                    details={"decline_percentage": pct_decline, "type": "recovery"},
                )
                recommendations.append(rec.model_dump())

        # 3. Growth Recommendations
        if (growth_rate is not None and float(growth_rate) >= 0.10) or raw_dict.get("growth_opportunity"):
            g_val = float(growth_rate) if growth_rate else 0.15
            pct_growth = g_val * 100.0 if abs(g_val) <= 1.0 else g_val
            impact = self.foundation.compute_impact_score(pct_growth, benchmark=25.0)
            conf = self.foundation.compute_confidence_score(certainty_metric=0.85)
            priority = self.foundation.compute_priority(impact, conf)
            rec = RecommendationItem(
                opportunity=f"Scale High-Margin Growth Channels (+{pct_growth:.0f}% Trend)",
                impact_score=impact,
                confidence_score=conf,
                priority=priority,
                category=RecommendationCategory.GROWTH,
                action_plan="Increase ad-spend allocation by 20% in top customer tiers and launch premium upsell campaigns.",
                estimated_value=round(pct_growth * 20000.0, 2),
                details={"growth_percentage": pct_growth, "type": "growth"},
            )
            recommendations.append(rec.model_dump())

        # 4. Operational Recommendations
        op_inefficiency = raw_dict.get("operational_inefficiency") or raw_dict.get("process_delay_days", 0)
        if op_inefficiency:
            impact = 65.0
            conf = 80.0
            rec = RecommendationItem(
                opportunity="Streamline Operational Order Processing",
                impact_score=impact,
                confidence_score=conf,
                priority=PriorityLevel.MEDIUM,
                category=RecommendationCategory.OPERATIONAL,
                action_plan="Automate validation workflows and eliminate manual handoffs to reduce cycle times.",
                estimated_value=45000.0,
                details={"metric": op_inefficiency, "type": "operational"},
            )
            recommendations.append(rec.model_dump())

        # Fallback baseline recommendation if input was empty
        if not recommendations:
            rec = RecommendationItem(
                opportunity="Maintain Core Business Operating Plan",
                impact_score=40.0,
                confidence_score=75.0,
                priority=PriorityLevel.LOW,
                category=RecommendationCategory.GENERAL,
                action_plan="Monitor cross-departmental KPIs and reassess at next reporting cycle.",
                estimated_value=0.0,
                details={"type": "baseline"},
            )
            recommendations.append(rec.model_dump())

        # Rank recommendations: Sort by impact_score * confidence_score descending
        recommendations.sort(
            key=lambda item: (item.get("impact_score", 0.0) * item.get("confidence_score", 0.0)),
            reverse=True,
        )

        logger.info("Generated %d ranked business recommendations", len(recommendations))
        return BusinessRecommendationsOutput(recommendations=recommendations)
