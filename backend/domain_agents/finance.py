"""Phase 12.5.2 — Finance Agent.

Domain analytics agent specialized in Revenue, Profitability, Cost breakdown,
Cash flow runaways, Budget variance, and financial KPI monitoring.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from backend.domain_agents.base import (
    BaseDomainAgent,
    DomainAnalysisResult,
    DomainInsight,
    DomainRecommendation,
    DomainRisk,
    DomainSeverity,
)

logger = logging.getLogger(__name__)


class FinanceAgent(BaseDomainAgent):
    """Enterprise agent for corporate finance and CFO-level decision intelligence."""

    def __init__(self) -> None:
        super().__init__(name="FinanceAgent", domain="finance")

    def analyze(
        self,
        data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> DomainAnalysisResult:
        start_time = time.time()
        logger.info("[FinanceAgent] Running corporate finance analytics...")

        revenue = float(data.get("revenue", 1_250_000.0))
        cogs = float(data.get("cogs", 450_000.0))
        opex = float(data.get("opex", 520_000.0))
        budget_target = float(data.get("budget_target", 1_100_000.0))
        cash_reserves = float(data.get("cash_reserves", 2_400_000.0))

        gross_profit = revenue - cogs
        net_profit = gross_profit - opex
        gross_margin_pct = round((gross_profit / revenue) * 100, 2) if revenue else 0.0
        net_margin_pct = round((net_profit / revenue) * 100, 2) if revenue else 0.0
        budget_variance_pct = round(((revenue - budget_target) / budget_target) * 100, 2) if budget_target else 0.0
        monthly_burn = max(0.0, opex - (revenue - cogs))
        runway_months = round(cash_reserves / monthly_burn, 1) if monthly_burn > 0 else 36.0

        kpis = {
            "revenue": revenue,
            "gross_profit": gross_profit,
            "net_profit": net_profit,
            "gross_margin_pct": gross_margin_pct,
            "net_margin_pct": net_margin_pct,
            "budget_variance_pct": budget_variance_pct,
            "cash_reserves": cash_reserves,
            "runway_months": runway_months,
        }

        insights = self.generate_insights(kpis)
        risks = self._detect_risks(kpis)
        recommendations = self.generate_recommendations(kpis, insights)
        summary = self.generate_summary(kpis, insights)

        duration = round((time.time() - start_time) * 1000, 2)

        return DomainAnalysisResult(
            agent_name=self.name,
            domain=self.domain,
            summary=summary,
            kpis=kpis,
            insights=insights,
            risks=risks,
            recommendations=recommendations,
            execution_time_ms=duration,
        )

    def generate_insights(self, data: Dict[str, Any]) -> List[DomainInsight]:
        insights: List[DomainInsight] = []

        rev = data.get("revenue", 0.0)
        gm = data.get("gross_margin_pct", 0.0)
        nm = data.get("net_margin_pct", 0.0)
        bvar = data.get("budget_variance_pct", 0.0)

        # Revenue & Budget Performance
        insights.append(
            DomainInsight(
                title="Revenue Over-Performance",
                description=f"Revenue achieved ${rev:,.2f}, beating budget plan by {bvar}%.",
                domain=self.domain,
                severity=DomainSeverity.INFO if bvar >= 0 else DomainSeverity.MEDIUM,
                metrics={"revenue": rev, "variance_pct": bvar},
            )
        )

        # Margin Health
        if gm < 50.0:
            insights.append(
                DomainInsight(
                    title="Margin Compression Warning",
                    description=f"Gross margin stands at {gm}%, below standard enterprise benchmark (50%).",
                    domain=self.domain,
                    severity=DomainSeverity.HIGH,
                    metrics={"gross_margin_pct": gm},
                )
            )
        else:
            insights.append(
                DomainInsight(
                    title="Healthy Margin Profile",
                    description=f"Gross margin sustained at a strong {gm}% with net margin at {nm}%.",
                    domain=self.domain,
                    severity=DomainSeverity.INFO,
                    metrics={"gross_margin_pct": gm, "net_margin_pct": nm},
                )
            )

        return insights

    def _detect_risks(self, data: Dict[str, Any]) -> List[DomainRisk]:
        risks: List[DomainRisk] = []
        runway = data.get("runway_months", 36.0)
        nm = data.get("net_margin_pct", 0.0)

        if runway < 12.0:
            risks.append(
                DomainRisk(
                    category="Liquidity",
                    risk_score=85.0,
                    impact="HIGH",
                    description=f"Cash runway compressed to {runway} months under current operational burn.",
                    mitigation="Implement discretionary spending freezes and accelerate receivable collections.",
                )
            )

        if nm < 10.0:
            risks.append(
                DomainRisk(
                    category="Profitability",
                    risk_score=65.0,
                    impact="MEDIUM",
                    description=f"Net margin of {nm}% leaves narrow buffer against seasonal volatility.",
                    mitigation="Review OPEX allocations and audit cloud infrastructure expenditures.",
                )
            )

        return risks

    def generate_recommendations(
        self,
        data: Dict[str, Any],
        insights: List[DomainInsight],
    ) -> List[DomainRecommendation]:
        recs: List[DomainRecommendation] = []
        gm = data.get("gross_margin_pct", 0.0)

        recs.append(
            DomainRecommendation(
                title="Optimize Tier-1 Vendor Contracts",
                action="Renegotiate wholesale and cloud provider commitments to improve COGS by 3-5%.",
                impact="HIGH",
                effort="MEDIUM",
                expected_outcome="Expands gross profit margin by ~180 bps.",
                priority=1,
            )
        )

        if gm < 60.0:
            recs.append(
                DomainRecommendation(
                    title="Review Pricing Structure",
                    action="Conduct price elasticity study on enterprise tier subscriptions.",
                    impact="HIGH",
                    effort="HIGH",
                    expected_outcome="Increases top-line ARR by 8-12%.",
                    priority=2,
                )
            )

        return recs

    def generate_summary(
        self,
        data: Dict[str, Any],
        insights: List[DomainInsight],
    ) -> str:
        rev = data.get("revenue", 0.0)
        np = data.get("net_profit", 0.0)
        nm = data.get("net_margin_pct", 0.0)
        return (
            f"Financial performance reflects total revenue of ${rev:,.2f} with net profit of ${np:,.2f} "
            f"({nm}% net margin). Overall financial stability remains positive with strong operating cash flow."
        )
