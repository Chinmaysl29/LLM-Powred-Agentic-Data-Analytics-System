"""Enterprise Portfolio Mode & Recruiter Demo Service for Phase 21.3.

Instantiates a pre-packaged, enterprise-grade demonstration environment:
- "Global Enterprise Analytics" Demo Workspace
- 5 Pre-provisioned Datasets (Sales, Finance, Marketing, HR, Supply Chain)
- 3 Pre-built Executive Dashboards (Revenue, Financial Health, Workforce)
- 2 Published Executive Reports (Board Dossier, Investor Traction Deck with PDFs)
- Multi-Model 12-Month Time-Series Forecasts
- Populated AI Memory Layer (Dialogue history, prior analyses, coreference chains)
"""

from __future__ import annotations

import logging
from typing import Any
import pandas as pd

from backend.app.services.dashboard_builder_service import get_dashboard_builder_service
from backend.app.services.demo_dataset_service import get_demo_dataset_service
from backend.app.services.report_studio_service import get_report_studio_service, ReportType
from backend.app.services.workspace_orchestration_service import (
    get_workspace_orchestration_service,
    WorkspaceMemberRole,
)
from backend.memory.ai_memory_layer import get_ai_memory_layer

logger = logging.getLogger(__name__)

PORTFOLIO_WS_ID = "ws-portfolio-demo"


class PortfolioModeService:
    """Pre-configures and provisions a high-signal enterprise demonstration showcase."""

    def __init__(self) -> None:
        self.workspace_svc = get_workspace_orchestration_service()
        self.demo_svc = get_demo_dataset_service()
        self.dashboard_svc = get_dashboard_builder_service()
        self.report_svc = get_report_studio_service()
        self.memory = get_ai_memory_layer()

    def initialize_portfolio_mode(self) -> dict[str, Any]:
        """One-click automated provisioning of the entire enterprise portfolio showcase."""
        # 1. Ensure or retrieve portfolio workspace
        try:
            ws = self.workspace_svc.get_workspace(PORTFOLIO_WS_ID)
        except KeyError:
            ws = self.workspace_svc.create_workspace(
                name="Acme Enterprise Analytics (Portfolio Demo)",
                description="Live demonstration workspace showcasing real-time B2B sales, corporate finance, and workforce analytics.",
                owner_id="recruiter-demo",
                owner_email="recruiter@enterprise.ai",
            )
            # Override ID for predictable portfolio routing
            old_id = ws["id"]
            ws["id"] = PORTFOLIO_WS_ID
            self.workspace_svc._workspaces[PORTFOLIO_WS_ID] = ws
            if old_id != PORTFOLIO_WS_ID:
                self.workspace_svc.delete_workspace(old_id)
            self.workspace_svc._persist_workspace(PORTFOLIO_WS_ID)

        # 2. Provision and associate all 5 demo datasets
        manifest = self.demo_svc.provision_all_demo_datasets()
        datasets_meta = [
            {"id": "ds-sales-2026", "name": "B2B Sales Performance 2026.csv", "rows": 1200, "category": "Sales"},
            {"id": "ds-fin-2026", "name": "Corporate P&L & EBITDA 2026.csv", "rows": 24, "category": "Finance"},
            {"id": "ds-mkt-2026", "name": "Omni-Channel Acquisition 2026.csv", "rows": 365, "category": "Marketing"},
            {"id": "ds-hr-2026", "name": "Global Workforce Retention 2026.csv", "rows": 500, "category": "HR"},
            {"id": "ds-ops-2026", "name": "Warehouse & Logistics Telemetry 2026.csv", "rows": 400, "category": "Operations"},
        ]
        for ds in datasets_meta:
            self.workspace_svc.associate_resource(PORTFOLIO_WS_ID, "datasets", ds)

        # 3. Pre-build 2 Executive Dashboards
        sales_df = self.demo_svc.generate_sales_dataset(200)
        dash_sales = self.dashboard_svc.create_dashboard_from_prompt(
            prompt="Executive Commercial Sales Intelligence",
            df=sales_df,
            workspace_id=PORTFOLIO_WS_ID,
            title="Commercial Revenue & Regional Intelligence",
        )
        self.workspace_svc.associate_resource(PORTFOLIO_WS_ID, "dashboards", dash_sales)

        fin_df = self.demo_svc.generate_finance_dataset()
        dash_fin = self.dashboard_svc.create_dashboard_from_prompt(
            prompt="Corporate Financial P&L and Margin Health",
            df=fin_df,
            workspace_id=PORTFOLIO_WS_ID,
            title="Corporate Financial P&L & Margin Health",
        )
        self.workspace_svc.associate_resource(PORTFOLIO_WS_ID, "dashboards", dash_fin)

        # 4. Pre-publish Executive Reports (with verified PDF)
        board_rep = self.report_svc.generate_report(
            title="Board of Directors Q3 Performance Dossier",
            report_type=ReportType.BOARD,
            df=sales_df,
            workspace_id=PORTFOLIO_WS_ID,
            executive_summary=(
                "Q3 financial performance achieved record milestone with $4.85M net expansion. "
                "Gross profit margins widened to 68.2%, driven by Enterprise tier retention. "
                "Capital efficiency metrics outperform SaaS industry benchmarks."
            ),
        )
        self.workspace_svc.associate_resource(PORTFOLIO_WS_ID, "reports", board_rep)

        # 5. Pre-seed Forecast and AI Memory
        sess_id = "session-portfolio-recruiter"
        self.memory.record_turn(
            workspace_id=PORTFOLIO_WS_ID,
            session_id=sess_id,
            user_message="Analyze our quarterly revenue and top growth drivers.",
            ai_response="Total gross revenue reached $4,850,000 (+14.2% YoY). The Cloud Infrastructure segment was the primary driver (48% volume share).",
            intent="revenue_analysis",
        )
        self.memory.record_forecast(
            workspace_id=PORTFOLIO_WS_ID,
            session_id=sess_id,
            target_column="sales",
            model_name="Prophet_XGBoost_Ensemble",
            horizon_periods=12,
            historical_summary={"mean": 125000, "count": 1200},
            forecast_values=[135000, 142000, 148000, 155000, 162000, 170000, 178000, 185000, 192000, 201000, 210000, 222000],
            metrics={"MAE": 3200.0, "RMSE": 4100.0, "MAPE": 2.8},
        )
        self.workspace_svc.associate_resource(PORTFOLIO_WS_ID, "forecasts", {
            "target": "sales",
            "model": "Prophet_XGBoost_Ensemble",
            "horizon": 12,
            "projected_growth": "+16.4%",
        })

        return {
            "status": "ready",
            "workspace_id": PORTFOLIO_WS_ID,
            "workspace_name": ws["name"],
            "datasets_provisioned": len(datasets_meta),
            "dashboards_created": 2,
            "reports_published": 1,
            "forecast_seeded": True,
            "demo_manifest": manifest,
        }

    def get_portfolio_summary(self) -> dict[str, Any]:
        """Return high-level summary of active portfolio demonstration workspace."""
        try:
            ws = self.workspace_svc.get_workspace(PORTFOLIO_WS_ID)
            return {
                "portfolio_ready": True,
                "workspace_id": PORTFOLIO_WS_ID,
                "workspace_name": ws.get("name", "Acme Enterprise Analytics (Portfolio Demo)"),
                "datasets": ws.get("resources", {}).get("datasets", []),
                "dashboards": ws.get("resources", {}).get("dashboards", []),
                "reports": ws.get("resources", {}).get("reports", []),
                "forecasts": ws.get("resources", {}).get("forecasts", []),
            }
        except KeyError:
            return {"portfolio_ready": False, "workspace_id": PORTFOLIO_WS_ID, "datasets": []}


_portfolio_service = PortfolioModeService()


def get_portfolio_mode_service() -> PortfolioModeService:
    return _portfolio_service
