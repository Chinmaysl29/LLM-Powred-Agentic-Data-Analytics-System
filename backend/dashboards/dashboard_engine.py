"""Enterprise Dashboard Engine for Phase 8.

Supported Widget Types:
- KPI Cards
- Charts (Line, Bar, Scatter)
- Forecast Widget
- Recommendation Widget
- Dataset Widget

Standard Output Format:
{
  "dashboard": {
    "dashboard_id": "dash_101",
    "title": "Revenue Dashboard",
    "widgets": [...]
  }
}
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


class DashboardEngine:
    """Constructs, validates, and manages enterprise interactive dashboards."""

    def __init__(self) -> None:
        self._dashboards: dict[str, dict[str, Any]] = {}

    def create_kpi_card(
        self,
        title: str,
        value: Any,
        subtext: str = "",
        change_pct: float | None = None,
        trend: str = "neutral",
    ) -> dict[str, Any]:
        """Generate a KPI Card widget."""
        return {
            "widget_id": f"kpi_{uuid.uuid4().hex[:6]}",
            "type": "kpi_card",
            "title": title,
            "content": {
                "value": value,
                "subtext": subtext,
                "change_pct": change_pct,
                "trend": trend,
            },
        }

    def create_chart_widget(
        self,
        title: str,
        chart_type: str,
        series: list[dict[str, Any]],
        x_axis: str = "x",
        y_axis: str = "y",
    ) -> dict[str, Any]:
        """Generate a Chart widget (line, bar, scatter)."""
        clean_type = chart_type.lower().strip()
        if clean_type not in {"line", "bar", "scatter", "pie", "area"}:
            clean_type = "line"

        return {
            "widget_id": f"chart_{uuid.uuid4().hex[:6]}",
            "type": "chart",
            "chart_type": clean_type,
            "title": title,
            "content": {
                "chart_type": clean_type,
                "x_axis": x_axis,
                "y_axis": y_axis,
                "series": series,
            },
        }

    def create_forecast_widget(
        self,
        title: str,
        target_column: str,
        forecast_points: list[dict[str, Any]],
        confidence_interval: float = 0.95,
        model_name: str = "Auto-ARIMA",
    ) -> dict[str, Any]:
        """Generate a Forecast widget with predictions and confidence bands."""
        return {
            "widget_id": f"fcst_{uuid.uuid4().hex[:6]}",
            "type": "forecast_widget",
            "title": title,
            "content": {
                "target_column": target_column,
                "model_name": model_name,
                "confidence_interval": confidence_interval,
                "data_points": forecast_points,
            },
        }

    def create_recommendation_widget(
        self,
        title: str,
        recommendations: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Generate a Recommendation action widget."""
        return {
            "widget_id": f"recom_{uuid.uuid4().hex[:6]}",
            "type": "recommendation_widget",
            "title": title,
            "content": {
                "total_recommendations": len(recommendations),
                "items": recommendations,
            },
        }

    def create_dataset_widget(
        self,
        title: str,
        dataset_name: str,
        row_count: int,
        column_count: int,
        columns: list[str],
    ) -> dict[str, Any]:
        """Generate a Dataset overview widget."""
        return {
            "widget_id": f"data_{uuid.uuid4().hex[:6]}",
            "type": "dataset_widget",
            "title": title,
            "content": {
                "dataset_name": dataset_name,
                "row_count": row_count,
                "column_count": column_count,
                "columns": columns,
            },
        }

    def build_dashboard(
        self,
        title: str,
        widgets: list[dict[str, Any]],
        description: str = "",
    ) -> dict[str, Any]:
        """Assemble widgets into a structured dashboard output."""
        dashboard_id = f"dash_{uuid.uuid4().hex[:8]}"
        dashboard_payload = {
            "dashboard_id": dashboard_id,
            "title": title,
            "description": description,
            "widget_count": len(widgets),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "widgets": widgets,
        }

        self._dashboards[dashboard_id] = dashboard_payload
        return {"dashboard": dashboard_payload}

    def create_enterprise_dashboard(
        self,
        title: str = "Enterprise Executive Dashboard",
        description: str = "Comprehensive 360-degree analytics, forecasting, and decisions overview",
    ) -> dict[str, Any]:
        """Construct a complete enterprise dashboard containing all widget types."""
        widgets = [
            # 1. KPI Cards
            self.create_kpi_card("Total Revenue", "$12.4M", "vs last month", 8.4, "up"),
            self.create_kpi_card("Net Profit Margin", "28.5%", "vs target", 2.1, "up"),
            self.create_kpi_card("Forecast Accuracy", "94.8%", "30-day rolling", 0.6, "up"),
            # 2. Charts (Line, Bar, Scatter)
            self.create_chart_widget(
                title="Revenue Trend by Quarter",
                chart_type="line",
                series=[{"date": "2025-Q1", "revenue": 2800000}, {"date": "2025-Q2", "revenue": 3100000}, {"date": "2025-Q3", "revenue": 3450000}],
                x_axis="date",
                y_axis="revenue",
            ),
            self.create_chart_widget(
                title="Regional Cost Distribution",
                chart_type="bar",
                series=[{"region": "North America", "cost": 450000}, {"region": "EMEA", "cost": 320000}, {"region": "APAC", "cost": 210000}],
                x_axis="region",
                y_axis="cost",
            ),
            self.create_chart_widget(
                title="Marketing Spend vs ROI",
                chart_type="scatter",
                series=[{"spend": 10000, "roi": 3.4}, {"spend": 25000, "roi": 4.1}, {"spend": 50000, "roi": 3.8}],
                x_axis="spend",
                y_axis="roi",
            ),
            # 3. Forecast Widget
            self.create_forecast_widget(
                title="90-Day Revenue Projection",
                target_column="monthly_revenue",
                forecast_points=[
                    {"step": 1, "forecast": 3600000, "lower": 3400000, "upper": 3800000},
                    {"step": 2, "forecast": 3750000, "lower": 3500000, "upper": 4000000},
                    {"step": 3, "forecast": 3900000, "lower": 3620000, "upper": 4180000},
                ],
                confidence_interval=0.95,
                model_name="Prophet-Ensemble",
            ),
            # 4. Recommendation Widget
            self.create_recommendation_widget(
                title="Prioritized Decision Recommendations",
                recommendations=[
                    {"title": "Downsize unused cloud GPU clusters", "impact": "$24,000/mo", "priority": "High", "confidence": 0.94},
                    {"title": "Adjust Enterprise Tier discount floor to 15%", "impact": "+$180,000 ARR", "priority": "High", "confidence": 0.89},
                ],
            ),
            # 5. Dataset Widget
            self.create_dataset_widget(
                title="Core Dataset Health",
                dataset_name="enterprise_sales_ledger.csv",
                row_count=125400,
                column_count=24,
                columns=["transaction_id", "date", "customer_id", "amount", "region", "product"],
            ),
        ]

        return self.build_dashboard(title=title, widgets=widgets, description=description)

    def get_dashboard(self, dashboard_id: str) -> dict[str, Any] | None:
        """Retrieve a stored dashboard by ID."""
        d = self._dashboards.get(dashboard_id)
        return {"dashboard": d} if d else None


# Global dashboard engine singleton
dashboard_engine = DashboardEngine()
