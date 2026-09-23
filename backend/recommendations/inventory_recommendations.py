"""Phase 7.7 — Inventory Optimization Engine.

Analyzes stock levels against time-series demand forecasts to mitigate stockout risks,
compute optimal reorder points, and eliminate overstock carrying costs.
"""

import logging
from typing import Any

from backend.app.schemas.recommendations import InventoryOptimizationOutput, PriorityLevel
from backend.recommendations.foundation import RecommendationFoundation

logger = logging.getLogger(__name__)


class InventoryOptimizationEngine:
    """Balances inventory supply against predictive demand forecasts."""

    DEFAULT_HOLDING_COST_RATE = 0.20  # 20% annual holding cost on excess inventory

    def __init__(self, foundation: RecommendationFoundation | None = None) -> None:
        self.foundation = foundation or RecommendationFoundation()

    def calculate_reorder_point(
        self,
        lead_time_days: int,
        daily_demand: float,
        safety_stock: float = 0.0,
    ) -> float:
        """Calculate standard inventory Reorder Point (ROP = d * L + SS)."""
        return round((daily_demand * lead_time_days) + safety_stock, 2)

    def analyze_inventory(self, inventory_data: dict[str, Any]) -> InventoryOptimizationOutput:
        """Evaluate inventory items and generate reorder or destocking actions."""
        logger.info("Executing inventory optimization analysis")
        inventory_actions: list[dict[str, Any]] = []
        total_expected_savings: float = 0.0

        items = inventory_data.get("items", [])
        if not items and ("forecasted_demand" in inventory_data or "current_stock" in inventory_data):
            items = [inventory_data]

        for idx, item in enumerate(items):
            sku = str(item.get("sku") or item.get("product_id") or item.get("name") or f"SKU-{idx+101}")
            stock = float(item.get("current_stock", 0.0))
            demand = float(item.get("forecasted_demand", 0.0))
            unit_cost = float(item.get("unit_cost", 50.0))
            lead_time = int(item.get("lead_time_days", 7))
            safety_stock = float(item.get("safety_stock", 0.15 * demand))

            daily_demand = demand / 30.0 if demand > 0 else 1.0
            rop = self.calculate_reorder_point(lead_time, daily_demand, safety_stock)

            # 1. Stockout Risk (Forecast demand exceeds stock)
            if demand > stock or stock <= rop or item.get("stockout_risk"):
                shortage = max(demand - stock, rop - stock)
                reorder_qty = round(max(shortage + safety_stock, demand * 1.2), 0)
                lost_sales_prevented = round(shortage * unit_cost * 1.5, 2)
                total_expected_savings += lost_sales_prevented

                inventory_actions.append({
                    "sku": sku,
                    "type": "reorder",
                    "finding": f"Forecast demand ({demand:,.0f} units) exceeds available stock ({stock:,.0f} units)",
                    "recommendation": f"Reorder Recommendation: Trigger emergency purchase order of {reorder_qty:,.0f} units to prevent stockout.",
                    "current_stock": stock,
                    "forecasted_demand": demand,
                    "reorder_point": rop,
                    "units_to_order": reorder_qty,
                    "expected_savings": lost_sales_prevented,
                    "priority": PriorityLevel.CRITICAL.value,
                })

            # 2. Overstocking Risk (Current stock significantly exceeds demand)
            elif stock > (demand * 2.0) or item.get("overstock_risk"):
                excess_units = stock - (demand * 1.5)
                holding_savings = round(excess_units * unit_cost * self.DEFAULT_HOLDING_COST_RATE, 2)
                total_expected_savings += holding_savings

                inventory_actions.append({
                    "sku": sku,
                    "type": "destock",
                    "finding": f"Overstock detected: Stock ({stock:,.0f} units) exceeds demand ({demand:,.0f} units) by {((stock/demand)-1)*100:.0f}%",
                    "recommendation": f"Inventory Destocking: Run clearance promotions or pause next purchase cycle for {sku} to eliminate holding costs.",
                    "current_stock": stock,
                    "forecasted_demand": demand,
                    "excess_units": round(excess_units, 0),
                    "expected_savings": holding_savings,
                    "priority": PriorityLevel.HIGH.value if holding_savings > 10000 else PriorityLevel.MEDIUM.value,
                })

        # Fallback if inventory is well balanced
        if not inventory_actions:
            inventory_actions.append({
                "sku": "Inventory Portfolio",
                "type": "balanced",
                "finding": "Stock levels match forecasted demand curves within safety stock buffers",
                "recommendation": "Continue standard replenishment schedules and dynamic reorder monitoring.",
                "expected_savings": 0.0,
                "priority": PriorityLevel.LOW.value,
            })

        logger.info(
            "Inventory optimization identified %d actions with $%.2f total savings",
            len(inventory_actions),
            total_expected_savings,
        )
        return InventoryOptimizationOutput(
            inventory_actions=inventory_actions,
            expected_inventory_savings=round(total_expected_savings, 2),
        )
