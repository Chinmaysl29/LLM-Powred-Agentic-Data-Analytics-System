"""Phase 7.5 — Pricing Intelligence Engine.

Performs price elasticity analysis, pricing trend evaluation, competitor benchmarking,
and scenario simulations for price optimization.
"""

import logging
from typing import Any

from backend.app.schemas.recommendations import PricingIntelligenceOutput, PriorityLevel
from backend.recommendations.foundation import RecommendationFoundation

logger = logging.getLogger(__name__)


class PricingIntelligenceEngine:
    """Evaluates price elasticity, competitor pricing benchmarks, and runs revenue simulations."""

    def __init__(self, foundation: RecommendationFoundation | None = None) -> None:
        self.foundation = foundation or RecommendationFoundation()

    def calculate_elasticity(
        self,
        price_old: float,
        price_new: float,
        quantity_old: float,
        quantity_new: float,
    ) -> float:
        """Calculate price elasticity of demand using standard midpoint formula."""
        if price_old == price_new or (quantity_old + quantity_new) == 0:
            return 0.0

        pct_delta_q = (quantity_new - quantity_old) / ((quantity_old + quantity_new) / 2.0)
        pct_delta_p = (price_new - price_old) / ((price_old + price_new) / 2.0)

        if pct_delta_p == 0:
            return 0.0

        return round(float(pct_delta_q / pct_delta_p), 3)

    def simulate_price_change(
        self,
        current_price: float,
        current_volume: float,
        pct_price_change: float,
        elasticity: float = -0.5,
    ) -> dict[str, Any]:
        """Simulate revenue impact given a percentage price adjustment and elasticity coefficient."""
        # Support both 0.10 (fractional) and 10.0 (percentage)
        delta_p_ratio = pct_price_change if abs(pct_price_change) <= 1.0 else pct_price_change / 100.0

        new_price = current_price * (1.0 + delta_p_ratio)
        pct_volume_change = delta_p_ratio * elasticity
        new_volume = max(0.0, current_volume * (1.0 + pct_volume_change))

        old_revenue = current_price * current_volume
        new_revenue = new_price * new_volume
        revenue_delta = new_revenue - old_revenue

        return {
            "current_price": round(current_price, 2),
            "new_price": round(new_price, 2),
            "price_change_pct": round(delta_p_ratio * 100, 2),
            "current_volume": round(current_volume, 2),
            "projected_volume": round(new_volume, 2),
            "volume_change_pct": round(pct_volume_change * 100, 2),
            "current_revenue": round(old_revenue, 2),
            "projected_revenue": round(new_revenue, 2),
            "projected_revenue_change": round(revenue_delta, 2),
            "elasticity_assumed": elasticity,
            "demand_type": "Inelastic" if abs(elasticity) < 1.0 else ("Elastic" if abs(elasticity) > 1.0 else "Unitary"),
        }

    def analyze_pricing(self, pricing_data: dict[str, Any]) -> PricingIntelligenceOutput:
        """Analyze pricing trends, run simulations, and recommend strategic pricing actions."""
        logger.info("Executing pricing intelligence analysis")
        pricing_actions: list[dict[str, Any]] = []
        total_expected_impact: float = 0.0

        current_price = float(pricing_data.get("current_price", 100.0))
        current_volume = float(pricing_data.get("current_volume", 10000.0))
        elasticity = float(pricing_data.get("elasticity", -0.45))

        # 1. Price Increase Simulation
        sim_delta = pricing_data.get("simulated_price_increase") or pricing_data.get("price_change_pct")
        if sim_delta is not None or "simulation" in pricing_data or "price_increase" in str(pricing_data).lower():
            pct_change = float(sim_delta) if sim_delta is not None else 0.10
            sim_res = self.simulate_price_change(
                current_price=current_price,
                current_volume=current_volume,
                pct_price_change=pct_change,
                elasticity=elasticity,
            )
            rev_change = sim_res["projected_revenue_change"]
            total_expected_impact += rev_change

            direction = "increase" if sim_res["price_change_pct"] > 0 else "decrease"
            pricing_actions.append({
                "action": f"Simulate {abs(sim_res['price_change_pct']):.0f}% Price {direction.capitalize()}",
                "finding": f"Demand is {sim_res['demand_type']} (E_d = {elasticity:.2f}). A {sim_res['price_change_pct']:+.1f}% price move projects a ${rev_change:+,.2f} revenue shift.",
                "recommendation": (
                    f"Implement staged {sim_res['price_change_pct']:+.0f}% price adjustment across premium SKUs."
                    if rev_change > 0
                    else "Avoid price hikes due to elastic customer response; emphasize feature packaging."
                ),
                "simulation": sim_res,
                "expected_impact": rev_change,
                "priority": PriorityLevel.CRITICAL.value if abs(rev_change) >= 50000 else PriorityLevel.HIGH.value,
            })

        # 2. Competitor Pricing Analysis
        competitor_price = pricing_data.get("competitor_price")
        if competitor_price is not None:
            comp_p = float(competitor_price)
            diff_pct = ((current_price - comp_p) / comp_p) * 100
            if diff_pct < -15.0:
                # Underpriced relative to market
                action_gain = round(abs(diff_pct / 100.0) * 0.5 * current_price * current_volume, 2)
                total_expected_impact += action_gain
                pricing_actions.append({
                    "action": "Market Alignment Price Increase",
                    "finding": f"Current price (${current_price:.2f}) is {abs(diff_pct):.1f}% below market competitor benchmark (${comp_p:.2f})",
                    "recommendation": "Gradually close pricing discount gap to align with perceived industry parity.",
                    "expected_impact": action_gain,
                    "priority": PriorityLevel.HIGH.value,
                })
            elif diff_pct > 25.0:
                # Premium risk
                pricing_actions.append({
                    "action": "Value Proposition Justification",
                    "finding": f"Product carries a {diff_pct:.1f}% premium over competitors (${comp_p:.2f})",
                    "recommendation": "Audit conversion friction and bundle onboarding support to preserve premium pricing tier.",
                    "expected_impact": 0.0,
                    "priority": PriorityLevel.MEDIUM.value,
                })

        # Fallback if no specific simulation was passed
        if not pricing_actions:
            sim_res = self.simulate_price_change(current_price, current_volume, 0.05, elasticity)
            total_expected_impact += sim_res["projected_revenue_change"]
            pricing_actions.append({
                "action": "Test 5% Opportunistic Price Increase",
                "finding": f"Baseline elasticity of {elasticity:.2f} indicates revenue expansion opportunity",
                "recommendation": "Conduct an A/B price test on newly acquired non-enterprise signups.",
                "simulation": sim_res,
                "expected_impact": sim_res["projected_revenue_change"],
                "priority": PriorityLevel.MEDIUM.value,
            })

        logger.info(
            "Pricing intelligence completed with %d actions and $%.2f total expected impact",
            len(pricing_actions),
            total_expected_impact,
        )
        return PricingIntelligenceOutput(
            pricing_actions=pricing_actions,
            expected_impact=round(total_expected_impact, 2),
        )
