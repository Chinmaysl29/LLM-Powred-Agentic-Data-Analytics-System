"""Enterprise Dashboard Templates Marketplace Service for Phase 20.6.

Provides 5 industry-standard dashboard templates:
1. Sales Performance Dashboard
2. Finance & P&L Dashboard
3. Marketing & Growth Dashboard
4. HR & People Analytics
5. Operations & Supply Chain

With Intelligent Schema Auto-Mapping:
Analyzes dataset columns and automatically binds them to template slots.
"""

from __future__ import annotations

import logging
from typing import Any
import pandas as pd

from backend.app.services.dashboard_builder_service import get_dashboard_builder_service

logger = logging.getLogger(__name__)


TEMPLATES: list[dict[str, Any]] = [
    {
        "id": "tpl-sales",
        "name": "Sales Performance Dashboard",
        "category": "Sales & Revenue",
        "description": "Comprehensive tracking of gross revenue, average deal size, sales rep quota, and regional conversion rates.",
        "icon": "ShoppingCart",
        "required_slots": {
            "value": ["sales", "revenue", "amount", "total", "price", "order_amt"],
            "date": ["date", "order_date", "timestamp", "created_at", "trans_date"],
            "dimension": ["category", "product", "region", "segment", "country"],
            "entity": ["rep", "sales_rep", "customer", "account", "order_id"],
        },
        "default_kpis": ["Total Revenue", "Avg Deal Size", "Deals Closed", "Quota Attainment"],
    },
    {
        "id": "tpl-finance",
        "name": "Finance & P&L Dashboard",
        "category": "Corporate Finance",
        "description": "Executive financial health tracking EBITDA, gross margin, operating expenses, and cash runway.",
        "icon": "DollarSign",
        "required_slots": {
            "value": ["revenue", "profit", "cogs", "expense", "cost", "margin"],
            "date": ["period", "quarter", "month", "date", "year"],
            "dimension": ["department", "cost_center", "business_unit", "account"],
        },
        "default_kpis": ["Gross Margin", "Operating Income", "EBITDA", "Net Profit"],
    },
    {
        "id": "tpl-marketing",
        "name": "Marketing & Growth Dashboard",
        "category": "Marketing & UA",
        "description": "Campaign attribution, customer acquisition cost (CAC), return on ad spend (ROAS), and conversion funnels.",
        "icon": "Target",
        "required_slots": {
            "value": ["spend", "impressions", "clicks", "conversions", "cost"],
            "date": ["date", "day", "week", "month"],
            "dimension": ["channel", "campaign", "source", "medium", "ad_group"],
        },
        "default_kpis": ["Total Spend", "Blended CAC", "ROAS", "Conversion Rate"],
    },
    {
        "id": "tpl-hr",
        "name": "HR & People Analytics",
        "category": "Human Capital",
        "description": "Workforce planning, headcount trends, voluntary turnover, compensation distribution, and tenure.",
        "icon": "Users",
        "required_slots": {
            "value": ["salary", "compensation", "rating", "tenure_years", "bonus"],
            "date": ["hire_date", "termination_date", "start_date"],
            "dimension": ["department", "role", "location", "gender", "level"],
            "entity": ["employee_id", "emp_id", "name"],
        },
        "default_kpis": ["Total Headcount", "Attrition Rate", "Avg Salary", "Tenure Avg"],
    },
    {
        "id": "tpl-ops",
        "name": "Operations & Supply Chain",
        "category": "Operations",
        "description": "Inventory turnover, stockout frequency, fulfillment lead times, and warehouse capacity utilization.",
        "icon": "Boxes",
        "required_slots": {
            "value": ["inventory", "stock", "quantity", "unit_cost", "lead_time_days"],
            "date": ["order_date", "ship_date", "delivery_date"],
            "dimension": ["warehouse", "location", "supplier", "sku_category"],
            "entity": ["sku", "item_code", "product_id"],
        },
        "default_kpis": ["Stockout Rate", "Inventory Turns", "On-Time SLA", "Stock Value"],
    },
]


class DashboardMarketplaceService:
    """Service providing pre-built templates and automatic schema mapping to datasets."""

    def __init__(self) -> None:
        self.dashboard_builder = get_dashboard_builder_service()

    def get_templates(self) -> list[dict[str, Any]]:
        """Return list of all marketplace templates."""
        return TEMPLATES

    def get_template_by_id(self, template_id: str) -> dict[str, Any]:
        """Fetch template by ID."""
        for tpl in TEMPLATES:
            if tpl["id"] == template_id:
                return tpl
        raise KeyError(f"Template not found: {template_id}")

    def map_dataset_to_template(
        self,
        template_id: str,
        df: pd.DataFrame,
    ) -> dict[str, Any]:
        """Automatically match dataset columns to template slots."""
        tpl = self.get_template_by_id(template_id)
        df_cols = [c.lower() for c in df.columns]
        actual_cols = list(df.columns)

        mapping: dict[str, str | None] = {}
        confidence_scores: dict[str, float] = {}

        for slot_type, candidate_names in tpl["required_slots"].items():
            matched_col = None
            score = 0.0

            # 1. Exact or partial match
            for cand in candidate_names:
                for idx, col in enumerate(df_cols):
                    if cand == col:
                        matched_col = actual_cols[idx]
                        score = 1.0
                        break
                    elif cand in col or col in cand:
                        if not matched_col:
                            matched_col = actual_cols[idx]
                            score = 0.85
                if score == 1.0:
                    break

            # 2. Type fallback
            if not matched_col:
                if slot_type == "value":
                    nums = df.select_dtypes(include=["number"]).columns.tolist()
                    if nums:
                        matched_col = nums[0]
                        score = 0.60
                elif slot_type == "dimension":
                    objs = df.select_dtypes(include=["object", "category", "string"]).columns.tolist()
                    if objs:
                        matched_col = objs[0]
                        score = 0.60
                elif slot_type == "date":
                    dates = [c for c in actual_cols if "date" in c.lower() or "time" in c.lower()]
                    if dates:
                        matched_col = dates[0]
                        score = 0.70

            mapping[slot_type] = matched_col
            confidence_scores[slot_type] = score

        overall_match_pct = round(sum(confidence_scores.values()) / max(1, len(confidence_scores)) * 100, 1)

        return {
            "template_id": template_id,
            "template_name": tpl["name"],
            "slot_mapping": mapping,
            "confidence_scores": confidence_scores,
            "overall_match_pct": overall_match_pct,
            "ready_to_deploy": overall_match_pct >= 50.0,
        }

    def apply_template_to_dataset(
        self,
        template_id: str,
        df: pd.DataFrame,
        workspace_id: str = "default-ws",
        custom_title: str | None = None,
    ) -> dict[str, Any]:
        """Bind dataset to template and generate a fully functional live dashboard."""
        mapping_result = self.map_dataset_to_template(template_id, df)
        tpl = self.get_template_by_id(template_id)

        title = custom_title or f"{tpl['name']} ({workspace_id})"
        prompt = f"Generated from marketplace template: {tpl['name']}"

        # Delegate to DashboardBuilder with mapped context
        dashboard = self.dashboard_builder.create_dashboard_from_prompt(
            prompt=prompt,
            df=df,
            workspace_id=workspace_id,
            title=title,
        )
        dashboard["marketplace_metadata"] = {
            "template_id": template_id,
            "template_name": tpl["name"],
            "slot_mapping": mapping_result["slot_mapping"],
            "match_confidence": mapping_result["overall_match_pct"],
        }
        return dashboard


_marketplace_service = DashboardMarketplaceService()


def get_dashboard_marketplace_service() -> DashboardMarketplaceService:
    return _marketplace_service
