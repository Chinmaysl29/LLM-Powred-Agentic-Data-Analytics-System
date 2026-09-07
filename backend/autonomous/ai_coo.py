"""
Phase 15.8 — AI Chief Operating Officer (COO)
Provides continuous operational intelligence: monitors all departments,
optimises resource allocation, flags bottlenecks, and produces daily
operations briefs for leadership.
"""

from __future__ import annotations

import uuid
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field

logger = logging.getLogger("backend.autonomous.ai_coo")


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class OperationalMetric(BaseModel):
    metric_id:   str   = Field(default_factory=lambda: str(uuid.uuid4()))
    name:        str
    department:  str
    current:     float
    target:      float
    variance:    float      # current – target (positive = over, negative = under)
    variance_pct: float
    trend:       str        # "improving" | "stable" | "degrading"
    status:      str        # "ON_TRACK" | "AT_RISK" | "CRITICAL"


class ResourceAllocationRec(BaseModel):
    department:        str
    current_budget:    float
    recommended_budget: float
    delta:             float
    rationale:         str
    expected_roi:      float    # % return from rebalancing


class CostOpportunity(BaseModel):
    category:    str
    description: str
    annual_savings: float
    effort:      str     # "low" | "medium" | "high"
    priority:    int


class DepartmentHealth(BaseModel):
    department:       str
    efficiency_score: float     # 0–1
    budget_utilisation: float   # spend / budget
    headcount_utilisation: float
    risk_score:       float
    status:           str


class OperationsBrief(BaseModel):
    brief_id:        str        = Field(default_factory=lambda: str(uuid.uuid4()))
    generated_at:    str        = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    executive_summary: str
    department_health: List[DepartmentHealth]
    critical_alerts:   List[str]
    top_opportunities: List[str]
    resource_recommendations: List[ResourceAllocationRec]
    cost_opportunities: List[CostOpportunity]
    kpi_scorecard:     Dict[str, Any]


# ---------------------------------------------------------------------------
# Default operational baseline
# ---------------------------------------------------------------------------

_DEPT_BASELINES: Dict[str, Dict[str, float]] = {
    "Sales":       {"efficiency": 0.78, "budget": 500_000, "spend": 472_000, "headcount": 50, "active": 48, "risk": 0.20},
    "Marketing":   {"efficiency": 0.72, "budget": 300_000, "spend": 295_000, "headcount": 25, "active": 24, "risk": 0.25},
    "Engineering": {"efficiency": 0.85, "budget": 700_000, "spend": 682_000, "headcount": 80, "active": 79, "risk": 0.15},
    "Finance":     {"efficiency": 0.90, "budget": 200_000, "spend": 191_000, "headcount": 15, "active": 15, "risk": 0.10},
    "HR":          {"efficiency": 0.82, "budget": 150_000, "spend": 147_000, "headcount": 10, "active": 10, "risk": 0.12},
    "Operations":  {"efficiency": 0.75, "budget": 400_000, "spend": 394_000, "headcount": 30, "active": 28, "risk": 0.22},
}

_COMPANY_KPIS: Dict[str, Dict[str, float]] = {
    "Revenue":         {"current": 1_250_000, "target": 1_300_000},
    "EBITDA Margin":   {"current": 0.18,       "target": 0.22},
    "Headcount":       {"current": 210,         "target": 200},
    "Churn Rate":      {"current": 0.027,       "target": 0.020},
    "NPS":             {"current": 42,           "target": 50},
    "OTIF":            {"current": 0.91,         "target": 0.95},
    "Employee NPS":    {"current": 34,           "target": 40},
    "Operational Cost":{"current": 2_181_000,   "target": 2_100_000},
}


# ---------------------------------------------------------------------------
# AI COO
# ---------------------------------------------------------------------------

class AICOO:
    """
    AI Chief Operating Officer — continuously monitors and optimises the
    operational health of the enterprise across all departments and KPIs.
    """

    def __init__(self) -> None:
        self._dept_baselines   = {k: dict(v) for k, v in _DEPT_BASELINES.items()}
        self._company_kpis     = {k: dict(v) for k, v in _COMPANY_KPIS.items()}
        self._alert_log: List[str] = []
        logger.info("AI COO initialised.")

    # ------------------------------------------------------------------
    # Monitoring
    # ------------------------------------------------------------------

    def monitor_operations(self) -> List[OperationalMetric]:
        """Collect all company-level operational KPI metrics."""
        metrics: List[OperationalMetric] = []
        for name, vals in self._company_kpis.items():
            current = vals["current"]
            target  = vals["target"]
            var     = round(current - target, 4)
            var_pct = round(var / target * 100, 2) if target != 0 else 0.0

            # Determine trend heuristically
            trend  = "stable"
            status = "ON_TRACK"
            if name in ["Churn Rate", "Operational Cost", "Headcount"]:
                # Lower is better
                if var > 0:
                    status = "CRITICAL" if var_pct > 10 else "AT_RISK"
                    trend  = "degrading"
                else:
                    trend  = "improving"
            else:
                # Higher is better
                if var < 0:
                    status = "CRITICAL" if abs(var_pct) > 10 else "AT_RISK"
                    trend  = "degrading"
                else:
                    trend  = "improving"

            metrics.append(OperationalMetric(
                name=name, department="Company",
                current=current, target=target,
                variance=var, variance_pct=var_pct,
                trend=trend, status=status,
            ))

        return metrics

    def monitor_departments(self) -> List[DepartmentHealth]:
        """Per-department operational health snapshot."""
        healths: List[DepartmentHealth] = []
        for dept, base in self._dept_baselines.items():
            util_budget = round(base["spend"] / base["budget"], 3)
            util_head   = round(base["active"] / base["headcount"], 3)
            risk        = base["risk"]
            eff         = base["efficiency"]

            # Overall dept status
            if eff < 0.70 or risk > 0.30:
                status = "AT_RISK"
            elif eff < 0.60 or risk > 0.40:
                status = "CRITICAL"
            else:
                status = "HEALTHY"

            healths.append(DepartmentHealth(
                department=dept,
                efficiency_score=eff,
                budget_utilisation=util_budget,
                headcount_utilisation=util_head,
                risk_score=risk,
                status=status,
            ))
        return healths

    def identify_operational_risks(self) -> List[str]:
        """Surface bottlenecks, inefficiencies, and risk flags."""
        risks: List[str] = []
        metrics = self.monitor_operations()
        dept_health = self.monitor_departments()

        for m in metrics:
            if m.status in ("AT_RISK", "CRITICAL"):
                risks.append(
                    f"[{m.status}] {m.name}: current {m.current} vs target {m.target} "
                    f"(variance {m.variance_pct:+.1f}%)."
                )

        for d in dept_health:
            if d.status != "HEALTHY":
                risks.append(
                    f"[{d.status}] {d.department} dept: efficiency={d.efficiency_score:.0%}, "
                    f"risk_score={d.risk_score:.0%}."
                )

        self._alert_log.extend(risks)
        logger.info("Operational risks identified: %d", len(risks))
        return risks

    # ------------------------------------------------------------------
    # Optimisation
    # ------------------------------------------------------------------

    def optimise_resources(self) -> List[ResourceAllocationRec]:
        """Recommend budget rebalancing across departments."""
        recs: List[ResourceAllocationRec] = []
        dept_health = self.monitor_departments()

        total_budget = sum(b["budget"] for b in self._dept_baselines.values())
        target_total = total_budget   # keep envelope constant

        for dh in dept_health:
            base  = self._dept_baselines[dh.department]
            curr  = base["budget"]

            # High efficiency + high utilisation → reward with 5% more budget
            # Low efficiency + over-budget → cut by 3%
            if dh.efficiency_score >= 0.85 and dh.budget_utilisation >= 0.95:
                recommended = curr * 1.05
                rationale   = "High efficiency and full utilisation — expand budget to unlock capacity."
                roi         = 12.0
            elif dh.efficiency_score < 0.75:
                recommended = curr * 0.97
                rationale   = "Below-target efficiency — constrain budget pending performance improvement."
                roi         = 5.0
            else:
                recommended = curr
                rationale   = "Stable performance — maintain current budget allocation."
                roi         = 0.0

            delta = recommended - curr
            if abs(delta) > 1:
                recs.append(ResourceAllocationRec(
                    department=dh.department,
                    current_budget=curr,
                    recommended_budget=round(recommended, 0),
                    delta=round(delta, 0),
                    rationale=rationale,
                    expected_roi=roi,
                ))

        return recs

    def optimise_costs(self) -> List[CostOpportunity]:
        """Identify cost reduction opportunities with ROI estimates."""
        return [
            CostOpportunity(
                category="Cloud Infrastructure",
                description="Right-size idle compute instances; enable auto-scaling.",
                annual_savings=84_000,
                effort="low",
                priority=1,
            ),
            CostOpportunity(
                category="SaaS Tool Consolidation",
                description="Consolidate 12 overlapping SaaS tools into 5 platform licences.",
                annual_savings=62_000,
                effort="medium",
                priority=2,
            ),
            CostOpportunity(
                category="Procurement Renegotiation",
                description="Renegotiate top-5 supplier contracts at current volume discounts.",
                annual_savings=95_000,
                effort="medium",
                priority=3,
            ),
            CostOpportunity(
                category="Process Automation",
                description="Automate 3 high-touch manual Finance workflows (invoice matching, reconciliation).",
                annual_savings=48_000,
                effort="high",
                priority=4,
            ),
            CostOpportunity(
                category="Facility Optimisation",
                description="Consolidate office footprint based on hybrid-work attendance patterns.",
                annual_savings=120_000,
                effort="high",
                priority=5,
            ),
        ]

    def track_performance(self) -> Dict[str, Any]:
        """Rolling KPI trend analysis across all company metrics."""
        metrics = self.monitor_operations()
        on_track  = [m for m in metrics if m.status == "ON_TRACK"]
        at_risk   = [m for m in metrics if m.status == "AT_RISK"]
        critical  = [m for m in metrics if m.status == "CRITICAL"]

        return {
            "total_kpis":     len(metrics),
            "on_track":       len(on_track),
            "at_risk":        len(at_risk),
            "critical":       len(critical),
            "overall_health": round(len(on_track) / len(metrics) * 100, 1) if metrics else 100.0,
            "kpi_breakdown":  [
                {"name": m.name, "status": m.status, "variance_pct": m.variance_pct}
                for m in metrics
            ],
        }

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------

    def generate_operations_brief(self) -> OperationsBrief:
        """Full daily operations digest for leadership."""
        dept_health  = self.monitor_departments()
        risks        = self.identify_operational_risks()
        perf         = self.track_performance()
        resource_recs = self.optimise_resources()
        cost_opps    = self.optimise_costs()[:3]

        critical_depts = [d.department for d in dept_health if d.status != "HEALTHY"]
        opportunities  = [
            f"Budget rebalancing: {r.rationale[:60]}…" for r in resource_recs[:3]
        ] + [
            f"Cost saving: {c.category} — ${c.annual_savings:,.0f}/yr" for c in cost_opps[:2]
        ]

        summary = (
            f"Operations overview: {perf['on_track']}/{perf['total_kpis']} KPIs on-track "
            f"({perf['overall_health']:.0f}% health). "
            f"{len(critical_depts)} department(s) require attention: "
            f"{', '.join(critical_depts) or 'None'}. "
            f"Top cost savings opportunity: ${cost_opps[0].annual_savings:,.0f}/yr via "
            f"{cost_opps[0].category}."
        )

        return OperationsBrief(
            executive_summary=summary,
            department_health=dept_health,
            critical_alerts=risks[:5],
            top_opportunities=opportunities,
            resource_recommendations=resource_recs,
            cost_opportunities=cost_opps,
            kpi_scorecard=perf,
        )

    def get_coo_dashboard(self) -> Dict[str, Any]:
        """Single-pane COO dashboard summary."""
        brief = self.generate_operations_brief()
        return {
            "health_score":          brief.kpi_scorecard["overall_health"],
            "total_kpis_monitored":  brief.kpi_scorecard["total_kpis"],
            "critical_alerts":       len(brief.critical_alerts),
            "departments_at_risk":   len([d for d in brief.department_health if d.status != "HEALTHY"]),
            "annual_cost_savings_available": sum(c.annual_savings for c in brief.cost_opportunities),
            "executive_summary":     brief.executive_summary,
        }
