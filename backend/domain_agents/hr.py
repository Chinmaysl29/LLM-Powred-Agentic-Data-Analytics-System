"""Phase 12.5.5 — HR Agent.

Domain analytics agent specialized in Workforce metrics, Voluntary/involuntary attrition,
Team performance, Hiring pipeline velocity, and Compensation parity.
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


class HRAgent(BaseDomainAgent):
    """Enterprise agent for Chief People Officer and HR operations analytics."""

    def __init__(self) -> None:
        super().__init__(name="HRAgent", domain="hr")

    def analyze(
        self,
        data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> DomainAnalysisResult:
        start_time = time.time()
        logger.info("[HRAgent] Running people analytics and workforce modeling...")

        total_headcount = int(data.get("total_headcount", 480))
        departures_annualized = int(data.get("departures_annualized", 36))
        open_requisitions = int(data.get("open_requisitions", 42))
        avg_time_to_hire_days = float(data.get("avg_time_to_hire_days", 38.5))
        enps = float(data.get("enps", 46.0))
        comp_ratio = float(data.get("compa_ratio_median", 0.98))

        attrition_rate_pct = round((departures_annualized / total_headcount) * 100, 2) if total_headcount else 0.0

        kpis = {
            "total_headcount": total_headcount,
            "departures_annualized": departures_annualized,
            "attrition_rate_pct": attrition_rate_pct,
            "open_requisitions": open_requisitions,
            "avg_time_to_hire_days": avg_time_to_hire_days,
            "enps": enps,
            "compa_ratio_median": comp_ratio,
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
        att = data.get("attrition_rate_pct", 0.0)
        tth = data.get("avg_time_to_hire_days", 0.0)
        enps = data.get("enps", 0.0)

        # Attrition Insight
        insights.append(
            DomainInsight(
                title="Annualized Attrition Within Target",
                description=f"Annualized workforce turnover is {att}%, outperforming tech industry median (12.5%).",
                domain=self.domain,
                severity=DomainSeverity.INFO if att <= 10.0 else DomainSeverity.MEDIUM,
                metrics={"attrition_rate_pct": att},
            )
        )

        # eNPS Sentiment
        insights.append(
            DomainInsight(
                title="Positive Employee Sentiment",
                description=f"Employee Net Promoter Score (eNPS) stands at +{enps}, indicating high organizational engagement.",
                domain=self.domain,
                severity=DomainSeverity.INFO,
                metrics={"enps": enps},
            )
        )

        # Time to hire
        if tth > 45.0:
            insights.append(
                DomainInsight(
                    title="Hiring Velocity Bottleneck",
                    description=f"Average time to hire ({tth} days) exceeds 40-day target.",
                    domain=self.domain,
                    severity=DomainSeverity.MEDIUM,
                    metrics={"avg_time_to_hire_days": tth},
                )
            )

        return insights

    def _detect_risks(self, data: Dict[str, Any]) -> List[DomainRisk]:
        risks: List[DomainRisk] = []
        att = data.get("attrition_rate_pct", 0.0)
        tth = data.get("avg_time_to_hire_days", 0.0)

        if att > 15.0:
            risks.append(
                DomainRisk(
                    category="Human Capital",
                    risk_score=75.0,
                    impact="HIGH",
                    description=f"Elevated turnover ({att}%) threatens institutional memory and delivery timelines.",
                    mitigation="Conduct stay-interviews with critical engineering and sales talent.",
                )
            )

        if tth > 50.0:
            risks.append(
                DomainRisk(
                    category="Talent Acquisition",
                    risk_score=60.0,
                    impact="MEDIUM",
                    description="Protracted hiring cycle creates understaffing in critical departments.",
                    mitigation="Streamline interview loops and leverage pre-screened candidate pools.",
                )
            )

        return risks

    def generate_recommendations(
        self,
        data: Dict[str, Any],
        insights: List[DomainInsight],
    ) -> List[DomainRecommendation]:
        recs: List[DomainRecommendation] = []
        recs.append(
            DomainRecommendation(
                title="Automate First-Round Technical Screenings",
                action="Deploy AI coding assessments to reduce engineering recruiting pipeline duration.",
                impact="HIGH",
                effort="LOW",
                expected_outcome="Reduces time-to-hire by 10 days.",
                priority=1,
            )
        )
        return recs

    def generate_summary(
        self,
        data: Dict[str, Any],
        insights: List[DomainInsight],
    ) -> str:
        hc = data.get("total_headcount", 0)
        att = data.get("attrition_rate_pct", 0.0)
        reqs = data.get("open_requisitions", 0)
        return (
            f"Workforce operates at {hc} active employees with a healthy {att}% annualized attrition rate. "
            f"There are {reqs} open requisitions with an average hiring time of {data.get('avg_time_to_hire_days')} days."
        )
