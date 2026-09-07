"""
Phase 15.5 — Digital Twin Organisation
Creates a virtual, real-time simulatable copy of the entire business.
Each department, revenue stream, inventory pool, and growth vector is
modelled as an independent twin that responds to shocks and scenarios.
"""

from __future__ import annotations

import random
import logging
import uuid
from enum import Enum
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field

logger = logging.getLogger("backend.autonomous.digital_twin")


# ---------------------------------------------------------------------------
# Individual Twin Models
# ---------------------------------------------------------------------------

class DepartmentTwin(BaseModel):
    dept_id:            str     = Field(default_factory=lambda: str(uuid.uuid4()))
    name:               str
    headcount:          int
    monthly_budget:     float
    monthly_spend:      float
    revenue_contribution: float     # fraction of total revenue attributable
    efficiency_score:   float       # 0–1
    risk_score:         float       # 0–1 operational risk
    quarter:            int = 1

    def step_quarter(self, growth_rate: float = 0.02, shock: float = 0.0) -> "DepartmentTwin":
        """Advance one quarter; apply growth + optional shock."""
        new_spend = self.monthly_spend * (1 + growth_rate + shock + random.gauss(0, 0.005))
        new_eff   = max(0.0, min(1.0, self.efficiency_score + random.gauss(0, 0.02)))
        return DepartmentTwin(
            dept_id=self.dept_id,
            name=self.name,
            headcount=max(1, int(self.headcount * (1 + growth_rate * 0.3))),
            monthly_budget=self.monthly_budget * 1.05,
            monthly_spend=max(0, new_spend),
            revenue_contribution=max(0.0, self.revenue_contribution + random.gauss(0, 0.005)),
            efficiency_score=new_eff,
            risk_score=max(0.0, min(1.0, self.risk_score + (0.05 if abs(shock) > 0.05 else -0.01))),
            quarter=self.quarter + 1,
        )


class RevenueTwin(BaseModel):
    mrr:          float       # monthly recurring revenue
    arr:          float       # annual recurring revenue
    growth_rate:  float       # MoM growth
    churn_rate:   float       # monthly churn fraction
    expansion:    float       # NRR expansion fraction
    contraction:  float       # NRR contraction fraction

    def step_month(self, market_shock: float = 0.0) -> "RevenueTwin":
        noise      = random.gauss(0, self.mrr * 0.005)
        new_mrr    = (
            self.mrr
            * (1 + self.growth_rate + market_shock)
            * (1 - self.churn_rate)
            * (1 + self.expansion - self.contraction)
            + noise
        )
        new_mrr    = max(0.0, new_mrr)
        return RevenueTwin(
            mrr=round(new_mrr, 2),
            arr=round(new_mrr * 12, 2),
            growth_rate=round(self.growth_rate + random.gauss(0, 0.002), 4),
            churn_rate=max(0.0, round(self.churn_rate + random.gauss(0, 0.001), 4)),
            expansion=self.expansion,
            contraction=self.contraction,
        )


class InventoryTwin(BaseModel):
    sku_id:         str
    units_on_hand:  int
    reorder_point:  int
    monthly_demand: int
    lead_time_days: int
    unit_cost:      float
    stockout_risk:  float = 0.0

    def step_month(self, demand_shock: float = 0.0) -> "InventoryTwin":
        actual_demand  = max(0, int(self.monthly_demand * (1 + demand_shock) + random.gauss(0, self.monthly_demand * 0.05)))
        new_units      = max(0, self.units_on_hand - actual_demand)
        stockout       = max(0.0, min(1.0, (self.reorder_point - new_units) / max(1, self.reorder_point)))
        # Trigger reorder if below point
        if new_units < self.reorder_point:
            new_units += self.monthly_demand * 2      # reorder quantity
        return InventoryTwin(
            sku_id=self.sku_id,
            units_on_hand=new_units,
            reorder_point=self.reorder_point,
            monthly_demand=self.monthly_demand,
            lead_time_days=self.lead_time_days,
            unit_cost=self.unit_cost,
            stockout_risk=round(stockout, 4),
        )


class GrowthTwin(BaseModel):
    """Models growth vectors: new markets, product lines, partnerships."""
    vector_name:    str
    current_tam:    float       # total addressable market
    market_share:   float       # current fraction
    growth_rate:    float       # quarterly growth
    investment:     float       # quarterly investment

    def step_quarter(self) -> "GrowthTwin":
        new_share = min(1.0, self.market_share * (1 + self.growth_rate) + random.gauss(0, 0.002))
        return GrowthTwin(
            vector_name=self.vector_name,
            current_tam=self.current_tam * 1.02,    # market expands
            market_share=round(new_share, 4),
            growth_rate=round(self.growth_rate + random.gauss(0, 0.005), 4),
            investment=self.investment,
        )

    @property
    def revenue_from_vector(self) -> float:
        return round(self.current_tam * self.market_share, 2)


# ---------------------------------------------------------------------------
# Organisation Twin — Master Orchestrator
# ---------------------------------------------------------------------------

class TwinHealthScore(BaseModel):
    overall:        float           # 0–100
    revenue_health: float
    cost_health:    float
    operational:    float
    growth:         float
    risk:           float


class OrganisationTwin:
    """
    Master digital twin that orchestrates all sub-twins and exposes
    high-level simulation APIs.
    """

    def __init__(self) -> None:
        self._departments: Dict[str, DepartmentTwin] = {}
        self._revenue:     Optional[RevenueTwin]     = None
        self._inventories: Dict[str, InventoryTwin]  = {}
        self._growth_vectors: Dict[str, GrowthTwin]  = {}
        self._history:     List[Dict[str, Any]]      = []
        self._initialise_defaults()
        logger.info("OrganisationTwin initialised with default enterprise model.")

    def _initialise_defaults(self) -> None:
        """Seed a representative enterprise with default twin parameters."""
        defaults = [
            DepartmentTwin(name="Sales",      headcount=50,  monthly_budget=500_000, monthly_spend=470_000, revenue_contribution=0.45, efficiency_score=0.78, risk_score=0.20),
            DepartmentTwin(name="Marketing",  headcount=25,  monthly_budget=300_000, monthly_spend=280_000, revenue_contribution=0.15, efficiency_score=0.72, risk_score=0.25),
            DepartmentTwin(name="Engineering",headcount=80,  monthly_budget=700_000, monthly_spend=680_000, revenue_contribution=0.00, efficiency_score=0.85, risk_score=0.15),
            DepartmentTwin(name="Finance",    headcount=15,  monthly_budget=200_000, monthly_spend=190_000, revenue_contribution=0.00, efficiency_score=0.90, risk_score=0.10),
            DepartmentTwin(name="HR",         headcount=10,  monthly_budget=150_000, monthly_spend=145_000, revenue_contribution=0.00, efficiency_score=0.82, risk_score=0.12),
            DepartmentTwin(name="Operations", headcount=30,  monthly_budget=400_000, monthly_spend=390_000, revenue_contribution=0.40, efficiency_score=0.75, risk_score=0.22),
        ]
        for dept in defaults:
            self._departments[dept.name] = dept

        self._revenue = RevenueTwin(
            mrr=1_200_000, arr=14_400_000,
            growth_rate=0.035, churn_rate=0.025,
            expansion=0.15, contraction=0.05,
        )

        self._inventories["SKU-001"] = InventoryTwin(
            sku_id="SKU-001", units_on_hand=5_000,
            reorder_point=1_000, monthly_demand=1_500,
            lead_time_days=14, unit_cost=25.0,
        )

        self._growth_vectors["North America"] = GrowthTwin(
            vector_name="North America",
            current_tam=50_000_000, market_share=0.024,
            growth_rate=0.08, investment=200_000,
        )
        self._growth_vectors["EMEA"] = GrowthTwin(
            vector_name="EMEA",
            current_tam=35_000_000, market_share=0.011,
            growth_rate=0.12, investment=150_000,
        )

    # ------------------------------------------------------------------
    # Simulation Methods
    # ------------------------------------------------------------------

    def apply_market_shock(self, shock_pct: float, description: str = "") -> Dict[str, Any]:
        """Apply an external disruption across the twin (negative = bad)."""
        if self._revenue:
            self._revenue = self._revenue.step_month(market_shock=shock_pct)
        for name, dept in list(self._departments.items()):
            self._departments[name] = dept.step_quarter(shock=shock_pct)
        logger.info("Market shock applied: %.1f%% — %s", shock_pct * 100, description)
        return {
            "shock_applied": shock_pct,
            "description": description or "External market disruption",
            "new_mrr": self._revenue.mrr if self._revenue else None,
            "new_twin_health": self.calculate_health_score().overall,
        }

    def run_growth_simulation(self, quarters: int = 8) -> List[Dict[str, Any]]:
        """Project N-quarter growth trajectory across revenue and growth vectors."""
        trajectory: List[Dict[str, Any]] = []
        rev = self._revenue

        for q in range(1, quarters + 1):
            if rev:
                rev = rev.step_month()
            gv_revenue = sum(v.revenue_from_vector for v in self._growth_vectors.values())
            for key in list(self._growth_vectors.keys()):
                self._growth_vectors[key] = self._growth_vectors[key].step_quarter()
            trajectory.append({
                "quarter": q,
                "mrr":     rev.mrr if rev else 0,
                "arr":     rev.arr if rev else 0,
                "churn":   rev.churn_rate if rev else 0,
                "gv_revenue": round(gv_revenue, 2),
            })

        self._revenue  = rev
        self._history += trajectory
        return trajectory

    def run_risk_simulation(self, scenarios: Optional[List[str]] = None) -> Dict[str, Any]:
        """Stress-test the business against predefined shock scenarios."""
        scenarios = scenarios or ["supply_shock", "demand_drop", "talent_attrition", "market_correction"]
        results: Dict[str, Any] = {}

        for scenario in scenarios:
            shock_map = {
                "supply_shock":       -0.12,
                "demand_drop":        -0.18,
                "talent_attrition":   -0.08,
                "market_correction":  -0.22,
                "regulatory_change":  -0.05,
                "competitor_entry":   -0.10,
            }
            shock = shock_map.get(scenario, -0.10)
            pre_health = self.calculate_health_score().overall

            # Simulate shock on a clone (don't mutate live twin)
            clone = OrganisationTwin()
            clone._revenue = self._revenue
            post = clone.apply_market_shock(shock, description=scenario)
            results[scenario] = {
                "shock_pct":         shock,
                "pre_health_score":  pre_health,
                "post_health_score": post["new_twin_health"],
                "health_delta":      round(post["new_twin_health"] - pre_health, 2),
                "severity":          "CRITICAL" if abs(shock) > 0.15 else "HIGH" if abs(shock) > 0.08 else "MEDIUM",
            }

        return results

    def run_revenue_simulation(self, months: int = 12) -> List[Dict[str, Any]]:
        """Monthly revenue trajectory."""
        trajectory = []
        rev = self._revenue
        for m in range(1, months + 1):
            if rev:
                rev = rev.step_month()
            trajectory.append({
                "month":      m,
                "mrr":        rev.mrr if rev else 0,
                "arr":        rev.arr if rev else 0,
                "churn_rate": rev.churn_rate if rev else 0,
            })
        return trajectory

    def run_inventory_simulation(self, months: int = 6, demand_shock: float = 0.0) -> Dict[str, Any]:
        """Step inventory twins forward and report stockout risks."""
        results: Dict[str, Any] = {}
        for sku, inv in self._inventories.items():
            monthly_states = []
            current = inv
            for m in range(1, months + 1):
                current = current.step_month(demand_shock=demand_shock)
                monthly_states.append({
                    "month": m,
                    "units_on_hand": current.units_on_hand,
                    "stockout_risk": current.stockout_risk,
                })
            results[sku] = {
                "trajectory":   monthly_states,
                "peak_risk":    max(s["stockout_risk"] for s in monthly_states),
                "final_units":  monthly_states[-1]["units_on_hand"],
            }
        return results

    # ------------------------------------------------------------------
    # State & Health
    # ------------------------------------------------------------------

    def get_twin_state(self) -> Dict[str, Any]:
        """Full snapshot of the current virtual organisation."""
        return {
            "revenue": self._revenue.model_dump() if self._revenue else {},
            "departments": {name: d.model_dump() for name, d in self._departments.items()},
            "inventories": {sku: i.model_dump() for sku, i in self._inventories.items()},
            "growth_vectors": {n: g.model_dump() for n, g in self._growth_vectors.items()},
            "health_score": self.calculate_health_score().model_dump(),
            "snapshot_at": datetime.now(timezone.utc).isoformat(),
        }

    def calculate_health_score(self) -> TwinHealthScore:
        """Aggregate 0–100 business health score from all sub-twins."""
        # Revenue health (higher MRR growth + lower churn = better)
        rev = self._revenue
        rev_health = 75.0
        if rev:
            rev_health = min(100, max(0, (rev.growth_rate / 0.05) * 50 + (1 - rev.churn_rate / 0.10) * 50))

        # Cost health (efficiency across departments)
        eff_scores = [d.efficiency_score for d in self._departments.values()]
        cost_health = round((sum(eff_scores) / len(eff_scores)) * 100, 1) if eff_scores else 70.0

        # Risk health (inverse of risk scores)
        risk_scores = [d.risk_score for d in self._departments.values()]
        risk_health = round((1 - sum(risk_scores) / len(risk_scores)) * 100, 1) if risk_scores else 75.0

        # Growth health
        gv_total = sum(v.market_share for v in self._growth_vectors.values())
        growth_health = min(100, gv_total * 2000)   # normalised

        # Operational health — blend
        operational = round((cost_health + risk_health) / 2, 1)
        overall = round((rev_health * 0.35 + cost_health * 0.25 + risk_health * 0.20 + growth_health * 0.20), 1)

        return TwinHealthScore(
            overall=overall,
            revenue_health=round(rev_health, 1),
            cost_health=cost_health,
            operational=operational,
            growth=round(growth_health, 1),
            risk=risk_health,
        )
