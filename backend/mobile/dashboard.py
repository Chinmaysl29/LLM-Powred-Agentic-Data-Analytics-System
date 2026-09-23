"""
Phase 12.8.3 — Mobile Dashboard Module
Generates responsive mobile executive dashboards with KPI cards,
decimated time-series charts, priority alerts, and forecast highlights.
"""

from typing import Dict, Any, List, Optional
import time
from pydantic import BaseModel, Field


class MobileKPICard(BaseModel):
    id: str
    title: str
    value: str
    change_percentage: float
    trend: str # "UP", "DOWN", "FLAT"
    is_positive: bool = True
    subtitle: str


class MobileChartPayload(BaseModel):
    chart_id: str
    title: str
    chart_type: str # line, bar, area, sparkline
    points: List[Dict[str, Any]]
    total_data_points: int
    decimated: bool = False


class MobileDashboardResponse(BaseModel):
    tenant_id: str
    workspace_id: str
    layout_type: str # phone_stack, tablet_grid
    kpis: List[MobileKPICard]
    charts: List[MobileChartPayload]
    alerts: List[Dict[str, Any]]
    forecast_summary: Dict[str, Any]
    refreshed_at: float = Field(default_factory=time.time)


class MobileDashboardService:
    """
    Constructs bandwidth-optimized, responsive dashboard feeds for mobile and tablet clients.
    """

    def __init__(self):
        pass

    def get_dashboard(
        self,
        tenant_id: str,
        workspace_id: str = "ws-default",
        is_tablet: bool = False,
        max_chart_points: int = 50
    ) -> MobileDashboardResponse:
        """Fetch mobile dashboard layout tailored to screen dimensions."""
        layout_type = "tablet_grid" if is_tablet else "phone_stack"

        kpis = [
            MobileKPICard(
                id="kpi-mrr",
                title="Monthly Recurring Revenue",
                value="$2,840,000",
                change_percentage=14.2,
                trend="UP",
                is_positive=True,
                subtitle="vs previous month"
            ),
            MobileKPICard(
                id="kpi-nrr",
                title="Net Retention Rate",
                value="118.5%",
                change_percentage=2.1,
                trend="UP",
                is_positive=True,
                subtitle="Annual cohort"
            ),
            MobileKPICard(
                id="kpi-cac",
                title="CAC Payback Period",
                value="11.4 mo",
                change_percentage=-8.5,
                trend="DOWN",
                is_positive=True, # reduction in CAC payback is good
                subtitle="Target < 12 mo"
            ),
            MobileKPICard(
                id="kpi-churn",
                title="Gross Churn Rate",
                value="1.45%",
                change_percentage=0.15,
                trend="UP",
                is_positive=False,
                subtitle="Alert threshold 1.50%"
            )
        ]

        # Generate sample dense data points (300 points) and decimate for mobile network efficiency
        raw_points = [{"x": f"Day {i}", "y": round(1000 + i * 12 + (i % 7) * 20, 2)} for i in range(300)]
        decimated_points = self.decimate_points(raw_points, max_points=max_chart_points)

        charts = [
            MobileChartPayload(
                chart_id="chart-revenue-trend",
                title="Daily Revenue Inflow",
                chart_type="area",
                points=decimated_points,
                total_data_points=len(raw_points),
                decimated=len(decimated_points) < len(raw_points)
            )
        ]

        alerts = [
            {
                "id": "alert-01",
                "severity": "warning",
                "title": "EU Churn Influx",
                "message": "Spike in mid-market downgrades in EMEA region.",
                "actionable": True
            }
        ]

        forecast_summary = {
            "metric": "Q4 ARR",
            "projected": "$12.4M",
            "confidence": 0.94,
            "status": "on_track"
        }

        return MobileDashboardResponse(
            tenant_id=tenant_id,
            workspace_id=workspace_id,
            layout_type=layout_type,
            kpis=kpis,
            charts=charts,
            alerts=alerts,
            forecast_summary=forecast_summary
        )

    @staticmethod
    def decimate_points(points: List[Dict[str, Any]], max_points: int = 50) -> List[Dict[str, Any]]:
        """Downsamples points to save bandwidth while preserving key trends."""
        if len(points) <= max_points or max_points <= 2:
            return points

        step = len(points) / float(max_points)
        sampled = []
        for i in range(max_points):
            idx = min(int(round(i * step)), len(points) - 1)
            sampled.append(points[idx])

        if sampled[-1] != points[-1]:
            sampled[-1] = points[-1]

        return sampled
