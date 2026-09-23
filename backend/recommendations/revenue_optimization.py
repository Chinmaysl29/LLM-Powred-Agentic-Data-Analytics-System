"""Phase 7.4 — Revenue Optimization Engine.

Identifies upsell potential, cross-sell opportunities, customer tier expansion,
and plugs revenue leakage across product lines and account segments.
"""

import logging
from typing import Any

from backend.app.schemas.recommendations import PriorityLevel, RevenueOptimizationOutput
from backend.recommendations.foundation import RecommendationFoundation

logger = logging.getLogger(__name__)


class RevenueOptimizationEngine:
    """Identifies upsell, cross-sell, and revenue recovery opportunities."""

    def __init__(self, foundation: RecommendationFoundation | None = None) -> None:
        self.foundation = foundation or RecommendationFoundation()

    def analyze_revenue(self, revenue_data: dict[str, Any]) -> RevenueOptimizationOutput:
        """Scan customer accounts, sales tiers, and product usage to compute revenue expansion."""
        logger.info("Analyzing revenue optimization opportunities")
        opportunities: list[dict[str, Any]] = []
        total_estimated_increase: float = 0.0

        baseline_revenue = float(revenue_data.get("baseline_revenue", revenue_data.get("revenue", 1000000.0)))

        # 1. Upsell Opportunities (Top Customers Under-Targeted)
        under_targeted = revenue_data.get("top_customers_under_targeted")
        if under_targeted is None:
            # Also check nested customer segment metrics
            cust_segments = revenue_data.get("customer_segments", {})
            under_targeted = bool(
                cust_segments.get("enterprise_undertargeted")
                or revenue_data.get("undertargeted_accounts_count", 0) > 0
            )

        if under_targeted:
            undertargeted_count = int(revenue_data.get("undertargeted_accounts_count", 25))
            arpu_gap = float(revenue_data.get("arpu_expansion_gap", 8000.0))
            upsell_increase = round(undertargeted_count * arpu_gap, 2)
            total_estimated_increase += upsell_increase

            opportunities.append({
                "type": "upsell",
                "opportunity": "Upsell Campaign for Under-Targeted Enterprise Accounts",
                "finding": f"Identified {undertargeted_count} top-tier customer accounts operating below optimal license capacity",
                "recommended_action": "Deploy executive account reviews and offer bundled premium seat expansions.",
                "target_segment": "Top Enterprise Tier",
                "estimated_revenue_increase": upsell_increase,
                "priority": PriorityLevel.CRITICAL.value,
            })

        # 2. Cross-Sell Opportunities (Single-product accounts)
        single_product_accounts = int(revenue_data.get("single_product_accounts", 0))
        cross_sell_arpu = float(revenue_data.get("cross_sell_arpu", 3500.0))
        if single_product_accounts > 0 or revenue_data.get("cross_sell_opportunity"):
            accounts = single_product_accounts if single_product_accounts > 0 else 50
            conversion_rate = 0.20  # 20% conversion benchmark
            cross_sell_increase = round(accounts * conversion_rate * cross_sell_arpu, 2)
            total_estimated_increase += cross_sell_increase

            opportunities.append({
                "type": "cross_sell",
                "opportunity": "Cross-Sell Expansion into Multi-Product Suites",
                "finding": f"{accounts} accounts currently utilize only 1 product module with high cross-fit affinity",
                "recommended_action": "Trigger in-app feature trials and packaged solution discounting.",
                "target_segment": "Single-Product Customers",
                "estimated_revenue_increase": cross_sell_increase,
                "priority": PriorityLevel.HIGH.value,
            })

        # 3. Revenue Leakage Mitigation (Discount slippage, churn grace periods)
        discount_slippage_pct = float(revenue_data.get("discount_slippage_pct", 0.0))
        unbilled_usage = float(revenue_data.get("unbilled_usage_amount", 0.0))

        if discount_slippage_pct > 0.05 or unbilled_usage > 0:
            leakage_amount = round(
                (discount_slippage_pct * baseline_revenue) + unbilled_usage, 2
            )
            total_estimated_increase += leakage_amount

            opportunities.append({
                "type": "leakage_recovery",
                "opportunity": "Plug Contractual and Discounting Revenue Leakage",
                "finding": f"Uncontrolled discounting ({discount_slippage_pct*100:.1f}%) and unbilled overages identified",
                "recommended_action": "Enforce automated billing guardrails, limit rep discretionary discounts to 10%, and automate overage invoices.",
                "target_segment": "Contract Operations",
                "estimated_revenue_increase": leakage_amount,
                "priority": PriorityLevel.HIGH.value,
            })

        # Fallback baseline if no gaps provided
        if not opportunities:
            opportunities.append({
                "type": "baseline",
                "opportunity": "Maintain Organic Revenue Trajectory",
                "finding": "Account expansion and net revenue retention are pacing within projected ranges",
                "recommended_action": "Continue standard account management cadence and quarterly renewals.",
                "target_segment": "All Accounts",
                "estimated_revenue_increase": 0.0,
                "priority": PriorityLevel.LOW.value,
            })

        logger.info(
            "Revenue optimization identified %d opportunities with $%.2f total estimated expansion",
            len(opportunities),
            total_estimated_increase,
        )
        return RevenueOptimizationOutput(
            opportunities=opportunities,
            estimated_revenue_increase=round(total_estimated_increase, 2),
        )
