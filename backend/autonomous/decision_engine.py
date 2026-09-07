"""
Phase 15.4 — Autonomous Decision Engine
Moves the platform from analytics to decision intelligence.
Detects business risks and opportunities, ranks potential actions by
expected value, runs Monte Carlo impact simulations, and produces
executive-ready decision briefings.
"""

from __future__ import annotations

import uuid
import random
import logging
from enum import Enum
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field

from backend.autonomous.enterprise_memory import (
    EnterpriseMemorySystem,
    MemoryEntry,
    MemoryTier,
    ImportanceLevel,
)

logger = logging.getLogger("backend.autonomous.decision_engine")


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class SignalType(str, Enum):
    RISK        = "risk"
    OPPORTUNITY = "opportunity"
    ANOMALY     = "anomaly"
    TREND       = "trend"


class RiskLevel(str, Enum):
    CRITICAL = "critical"
    HIGH     = "high"
    MEDIUM   = "medium"
    LOW      = "low"


class BusinessSignal(BaseModel):
    signal_id:      str         = Field(default_factory=lambda: str(uuid.uuid4()))
    signal_type:    SignalType
    title:          str
    description:    str
    magnitude:      float       # 0–1 normalised severity/opportunity score
    confidence:     float       # 0–1 model confidence
    affected_kpis:  List[str]   = Field(default_factory=list)
    risk_level:     RiskLevel   = RiskLevel.MEDIUM
    source:         str         = "decision_engine"
    detected_at:    str         = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class DecisionScenario(BaseModel):
    label:       str        # "pessimistic" | "base" | "optimistic"
    probability: float
    impact:      float      # % change in target metric
    description: str


class Decision(BaseModel):
    decision_id:    str         = Field(default_factory=lambda: str(uuid.uuid4()))
    title:          str
    description:    str
    priority:       int         # 1 = highest
    expected_roi:   float       # % expected return
    confidence:     float
    risk_level:     RiskLevel
    rationale:      str
    scenarios:      List[DecisionScenario] = Field(default_factory=list)
    related_kpis:   List[str]              = Field(default_factory=list)
    created_at:     str         = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class SimulationResult(BaseModel):
    months_simulated: int
    final_revenue:    float
    final_costs:      float
    net_outcome:      float
    scenario_label:   str
    trajectory:       List[Dict[str, float]]


class DecisionReport(BaseModel):
    report_id:         str               = Field(default_factory=lambda: str(uuid.uuid4()))
    generated_at:      str               = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    risks_detected:    List[BusinessSignal]
    opportunities:     List[BusinessSignal]
    top_decisions:     List[Decision]
    executive_summary: str


# ---------------------------------------------------------------------------
# Autonomous Decision Engine
# ---------------------------------------------------------------------------

class AutonomousDecisionEngine:
    """
    Continuously scans business metrics for risk and opportunity signals,
    ranks actions by expected value, and simulates outcomes through
    probabilistic Monte Carlo modelling.
    """

    _RISK_THRESHOLDS = {
        "revenue_decline_pct":  -0.05,
        "churn_rate_pct":        0.08,
        "cost_overrun_pct":      0.10,
        "margin_compression":   -0.03,
        "inventory_stockout":    0.15,
    }

    _OPPORTUNITY_SIGNALS = {
        "revenue_growth_pct":   0.15,
        "market_share_gain":    0.05,
        "cost_reduction_pct":  -0.08,
        "nps_improvement":      10.0,
        "cac_reduction_pct":   -0.10,
    }

    def __init__(self, memory: Optional[EnterpriseMemorySystem] = None) -> None:
        self._memory    = memory or EnterpriseMemorySystem()
        self._signal_log: List[BusinessSignal] = []
        self._decision_log: List[Decision]     = []
        logger.info("AutonomousDecisionEngine initialised.")

    # ------------------------------------------------------------------
    # Detection
    # ------------------------------------------------------------------

    def detect_risks(self, kpi_snapshot: Dict[str, float]) -> List[BusinessSignal]:
        """Scan a KPI snapshot dict and surface threshold-breaching risks."""
        signals: List[BusinessSignal] = []

        revenue_chg = kpi_snapshot.get("revenue_change_pct", 0.0)
        if revenue_chg < self._RISK_THRESHOLDS["revenue_decline_pct"]:
            signals.append(BusinessSignal(
                signal_type=SignalType.RISK,
                title="Revenue Declining",
                description=f"Revenue fell {abs(revenue_chg):.1%} vs prior period, exceeding the {abs(self._RISK_THRESHOLDS['revenue_decline_pct']):.0%} risk threshold.",
                magnitude=min(abs(revenue_chg) / 0.20, 1.0),
                confidence=0.88,
                affected_kpis=["Revenue", "EBITDA", "Cash Flow"],
                risk_level=RiskLevel.HIGH if revenue_chg < -0.10 else RiskLevel.MEDIUM,
            ))

        churn = kpi_snapshot.get("churn_rate", 0.0)
        if churn > self._RISK_THRESHOLDS["churn_rate_pct"]:
            signals.append(BusinessSignal(
                signal_type=SignalType.RISK,
                title="Customer Churn Elevated",
                description=f"Churn rate {churn:.1%} exceeds acceptable {self._RISK_THRESHOLDS['churn_rate_pct']:.0%} ceiling.",
                magnitude=min(churn / 0.25, 1.0),
                confidence=0.92,
                affected_kpis=["Churn Rate", "ARR", "NRR"],
                risk_level=RiskLevel.HIGH,
            ))

        cost_overrun = kpi_snapshot.get("cost_overrun_pct", 0.0)
        if cost_overrun > self._RISK_THRESHOLDS["cost_overrun_pct"]:
            signals.append(BusinessSignal(
                signal_type=SignalType.RISK,
                title="Cost Overrun Detected",
                description=f"Operating costs {cost_overrun:.1%} over budget.",
                magnitude=min(cost_overrun / 0.30, 1.0),
                confidence=0.85,
                affected_kpis=["OpEx", "EBITDA", "Burn Rate"],
                risk_level=RiskLevel.MEDIUM,
            ))

        self._signal_log.extend(signals)
        logger.info("detect_risks: %d signals found.", len(signals))
        return signals

    def detect_opportunities(self, kpi_snapshot: Dict[str, float]) -> List[BusinessSignal]:
        """Surface positive business signals from a KPI snapshot."""
        signals: List[BusinessSignal] = []

        rev_growth = kpi_snapshot.get("revenue_change_pct", 0.0)
        if rev_growth >= self._OPPORTUNITY_SIGNALS["revenue_growth_pct"]:
            signals.append(BusinessSignal(
                signal_type=SignalType.OPPORTUNITY,
                title="Revenue Growth Momentum",
                description=f"Revenue grew {rev_growth:.1%} — consider reinvesting in top-of-funnel acceleration.",
                magnitude=min(rev_growth / 0.40, 1.0),
                confidence=0.87,
                affected_kpis=["Revenue", "ARR", "NRR"],
                risk_level=RiskLevel.LOW,
            ))

        cac_reduction = kpi_snapshot.get("cac_change_pct", 0.0)
        if cac_reduction < self._OPPORTUNITY_SIGNALS["cac_reduction_pct"]:
            signals.append(BusinessSignal(
                signal_type=SignalType.OPPORTUNITY,
                title="CAC Efficiency Gain",
                description=f"Customer acquisition cost dropped {abs(cac_reduction):.1%} — marketing efficiency improving.",
                magnitude=min(abs(cac_reduction) / 0.25, 1.0),
                confidence=0.82,
                affected_kpis=["CAC", "LTV:CAC", "Marketing ROI"],
                risk_level=RiskLevel.LOW,
            ))

        self._signal_log.extend(signals)
        logger.info("detect_opportunities: %d signals found.", len(signals))
        return signals

    # ------------------------------------------------------------------
    # Decision ranking
    # ------------------------------------------------------------------

    def rank_decisions(self, signals: List[BusinessSignal]) -> List[Decision]:
        """Convert signals into ranked, actionable decisions."""
        decisions: List[Decision] = []

        for i, signal in enumerate(sorted(signals, key=lambda s: -s.magnitude)):
            roi = round(signal.magnitude * signal.confidence * 35, 1)  # % expected return
            risk = signal.risk_level
            decision = Decision(
                title=f"Action: Address — {signal.title}",
                description=signal.description,
                priority=i + 1,
                expected_roi=roi,
                confidence=signal.confidence,
                risk_level=risk,
                rationale=(
                    f"Signal magnitude {signal.magnitude:.2f} × confidence {signal.confidence:.2f} "
                    f"yields expected value score {signal.magnitude * signal.confidence:.3f}."
                ),
                scenarios=self._build_scenarios(signal.magnitude),
                related_kpis=signal.affected_kpis,
            )
            decisions.append(decision)

        self._decision_log.extend(decisions)
        self._persist_decisions(decisions)
        return decisions

    def _build_scenarios(self, magnitude: float) -> List[DecisionScenario]:
        return [
            DecisionScenario(
                label="pessimistic",
                probability=0.20,
                impact=round(-magnitude * 0.10, 3),
                description="Action taken but headwinds persist; partial improvement.",
            ),
            DecisionScenario(
                label="base",
                probability=0.60,
                impact=round(magnitude * 0.20, 3),
                description="Action resolves root cause; KPIs recover to target.",
            ),
            DecisionScenario(
                label="optimistic",
                probability=0.20,
                impact=round(magnitude * 0.45, 3),
                description="Action triggers compounding positive flywheel effect.",
            ),
        ]

    def _persist_decisions(self, decisions: List[Decision]) -> None:
        for d in decisions:
            self._memory.store(MemoryEntry(
                tier=MemoryTier.DECISION,
                subject=d.title,
                content=f"priority={d.priority}, roi={d.expected_roi}%, {d.rationale}",
                tags=["autonomous_decision"] + d.related_kpis,
                importance=ImportanceLevel.HIGH if d.priority <= 3 else ImportanceLevel.MEDIUM,
            ))

    # ------------------------------------------------------------------
    # Simulation
    # ------------------------------------------------------------------

    def simulate_decision_impact(
        self,
        decision:    Decision,
        n_simulations: int = 200,
    ) -> Dict[str, Any]:
        """Monte Carlo impact simulation for a given decision."""
        outcomes = []
        for _ in range(n_simulations):
            r = random.random()
            cumulative = 0.0
            for scenario in decision.scenarios:
                cumulative += scenario.probability
                if r <= cumulative:
                    noise  = random.gauss(0, scenario.impact * 0.10)
                    impact = scenario.impact + noise
                    outcomes.append(impact)
                    break

        avg_impact   = round(sum(outcomes) / len(outcomes), 4) if outcomes else 0.0
        p10          = round(sorted(outcomes)[int(len(outcomes) * 0.10)], 4)
        p90          = round(sorted(outcomes)[int(len(outcomes) * 0.90)], 4)

        return {
            "decision_title":    decision.title,
            "n_simulations":     n_simulations,
            "avg_impact":        avg_impact,
            "p10_impact":        p10,
            "p90_impact":        p90,
            "confidence":        decision.confidence,
            "recommendation":    "PROCEED" if avg_impact > 0.05 else "REVIEW",
        }

    def run_business_simulation(
        self,
        initial_revenue: float = 1_000_000,
        monthly_growth:  float = 0.03,
        monthly_costs:   float = 750_000,
        months:          int   = 12,
        scenario:        str   = "base",
    ) -> SimulationResult:
        """Step through N months of projected business financials."""
        growth_multiplier = {"pessimistic": 0.50, "base": 1.00, "optimistic": 1.50}.get(scenario, 1.00)
        revenue = initial_revenue
        trajectory: List[Dict[str, float]] = []

        for m in range(1, months + 1):
            noise   = random.gauss(0, revenue * 0.01)
            revenue = revenue * (1 + monthly_growth * growth_multiplier) + noise
            costs   = monthly_costs * (1 + 0.005 * m)        # slight cost creep
            trajectory.append({
                "month":   m,
                "revenue": round(revenue, 2),
                "costs":   round(costs, 2),
                "profit":  round(revenue - costs, 2),
            })

        final = trajectory[-1]
        return SimulationResult(
            months_simulated=months,
            final_revenue=final["revenue"],
            final_costs=final["costs"],
            net_outcome=final["profit"],
            scenario_label=scenario,
            trajectory=trajectory,
        )

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------

    def generate_decision_report(
        self,
        kpi_snapshot: Dict[str, float],
    ) -> DecisionReport:
        """End-to-end: detect → rank → summarise into an executive report."""
        risks         = self.detect_risks(kpi_snapshot)
        opportunities = self.detect_opportunities(kpi_snapshot)
        all_signals   = risks + opportunities
        decisions     = self.rank_decisions(all_signals)

        n_risks = len(risks)
        n_opps  = len(opportunities)
        top     = decisions[:3]

        summary = (
            f"Autonomous scan detected {n_risks} risk signal(s) and {n_opps} opportunity signal(s). "
            f"Top priority action: '{top[0].title}' (expected ROI {top[0].expected_roi:.1f}%). "
            if top else
            "No significant signals detected in current KPI snapshot. Business is on-track."
        )

        return DecisionReport(
            risks_detected=risks,
            opportunities=opportunities,
            top_decisions=decisions[:5],
            executive_summary=summary,
        )
