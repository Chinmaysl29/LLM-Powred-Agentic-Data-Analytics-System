"""Phase 7.6 — Marketing Intelligence Engine.

Analyzes marketing campaign performance, ROI, customer acquisition cost (CAC),
customer lifetime value (LTV), and channel retention to drive growth efficiency.
"""

import logging
from typing import Any

from backend.app.schemas.recommendations import MarketingIntelligenceOutput, PriorityLevel
from backend.recommendations.foundation import RecommendationFoundation

logger = logging.getLogger(__name__)


class MarketingIntelligenceEngine:
    """Evaluates marketing campaigns, CAC/LTV ratios, and generates campaign optimization actions."""

    BENCHMARK_MIN_ROAS = 2.5       # Target 2.5x Return on Ad Spend
    BENCHMARK_MIN_LTV_CAC = 3.0    # Healthy SaaS/commerce LTV to CAC is >= 3.0

    def __init__(self, foundation: RecommendationFoundation | None = None) -> None:
        self.foundation = foundation or RecommendationFoundation()

    def analyze_campaigns(self, marketing_data: dict[str, Any]) -> MarketingIntelligenceOutput:
        """Evaluate campaign performance, flag low-ROI initiatives, and calculate projected ROI."""
        logger.info("Executing marketing intelligence and campaign ROI analysis")
        marketing_actions: list[dict[str, Any]] = []

        campaigns = marketing_data.get("campaigns", [])
        # Support single-campaign or direct payload dict
        if not campaigns and ("roi" in marketing_data or "spend" in marketing_data or "campaign_name" in marketing_data):
            campaigns = [marketing_data]

        total_spend = 0.0
        total_revenue = 0.0
        optimized_revenue = 0.0

        for idx, camp in enumerate(campaigns):
            name = str(camp.get("campaign_name") or camp.get("name") or f"Campaign #{idx+1}")
            spend = float(camp.get("spend", 10000.0))
            revenue = float(camp.get("revenue", 0.0))
            roi = camp.get("roi")

            if roi is None:
                roi = ((revenue - spend) / spend) if spend > 0 else 0.0
            else:
                roi = float(roi) if abs(float(roi)) <= 2.0 else float(roi) / 100.0
                if revenue == 0.0:
                    revenue = spend * (1.0 + roi)

            total_spend += spend
            total_revenue += revenue

            # 1. Low ROI / Negative ROI Campaign Check
            if roi < 0.20 or camp.get("low_roi"):
                pct_roi = roi * 100.0
                # By reallocating spend to baseline channel, project 2.5x ROAS
                projected_gain = round(spend * 1.5, 2)
                optimized_revenue += (spend * 2.5)

                marketing_actions.append({
                    "campaign": name,
                    "finding": f"Low ROI campaign detected: {name} generated {pct_roi:.1f}% ROI on ${spend:,.2f} spend",
                    "recommendation": f"Campaign Optimization: Pause underperforming ad creatives in {name} and reallocate budget to top-converting audience segments.",
                    "current_roi": round(pct_roi, 2),
                    "projected_gain": projected_gain,
                    "priority": PriorityLevel.CRITICAL.value if roi < 0 else PriorityLevel.HIGH.value,
                })
            else:
                optimized_revenue += revenue

            # 2. CAC vs LTV Check
            cac = camp.get("cac")
            ltv = camp.get("ltv")
            if cac is not None and ltv is not None:
                cac_val = float(cac)
                ltv_val = float(ltv)
                ltv_cac_ratio = ltv_val / cac_val if cac_val > 0 else 0.0
                if ltv_cac_ratio < self.BENCHMARK_MIN_LTV_CAC:
                    marketing_actions.append({
                        "campaign": name,
                        "finding": f"Suboptimal LTV:CAC ratio ({ltv_cac_ratio:.2f}x vs {self.BENCHMARK_MIN_LTV_CAC:.1f}x benchmark)",
                        "recommendation": "Refine audience targeting to higher intent keywords and improve day-30 customer onboarding retention.",
                        "ltv_cac": round(ltv_cac_ratio, 2),
                        "priority": PriorityLevel.HIGH.value,
                    })

        # 3. Overall Portfolio ROI calculation
        if total_spend > 0:
            current_overall_roi = ((total_revenue - total_spend) / total_spend) * 100.0
            expected_roi = ((optimized_revenue - total_spend) / total_spend) * 100.0
        else:
            current_overall_roi = 25.0
            expected_roi = 120.0

        # Fallback if all campaigns are performing above benchmark
        if not marketing_actions:
            marketing_actions.append({
                "campaign": "Portfolio Overall",
                "finding": f"All campaigns performing healthily with overall ROI of {current_overall_roi:.1f}%",
                "recommendation": "Maintain continuous A/B creative testing and scale budget in increments of 15%.",
                "current_roi": round(current_overall_roi, 2),
                "priority": PriorityLevel.LOW.value,
            })

        logger.info(
            "Marketing intelligence identified %d actions with projected ROI of %.1f%%",
            len(marketing_actions),
            expected_roi,
        )
        return MarketingIntelligenceOutput(
            marketing_actions=marketing_actions,
            expected_roi=round(expected_roi, 2),
        )
