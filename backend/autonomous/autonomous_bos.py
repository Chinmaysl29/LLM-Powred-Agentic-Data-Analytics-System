"""
Phase 15.10 — Autonomous Business Operating System (BOS)
The final synthesis layer — orchestrates every Phase 15 module into a
unified runtime loop that monitors, understands, predicts, decides, acts,
and learns continuously without human intervention.
"""

from __future__ import annotations

import uuid
import logging
from enum import Enum
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field

from backend.autonomous.knowledge_graph import BusinessKnowledgeGraph, NodeType, EdgeType
from backend.autonomous.enterprise_memory import EnterpriseMemorySystem, MemoryEntry, MemoryTier, ImportanceLevel
from backend.autonomous.self_learning import SelfLearningEngine
from backend.autonomous.decision_engine import AutonomousDecisionEngine
from backend.autonomous.digital_twin import OrganisationTwin
from backend.autonomous.workflow_executor import AutonomousWorkflowExecutor, TriggerType
from backend.autonomous.reasoning_engine import EnterpriseReasoningEngine, ReasoningDepth
from backend.autonomous.ai_coo import AICOO
from backend.autonomous.ai_ceo import AICEO

logger = logging.getLogger("backend.autonomous.autonomous_bos")


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class BOSCyclePhase(str, Enum):
    MONITOR    = "monitor"
    UNDERSTAND = "understand"
    PREDICT    = "predict"
    DECIDE     = "decide"
    ACT        = "act"
    LEARN      = "learn"


class CycleResult(BaseModel):
    cycle_id:        str    = Field(default_factory=lambda: str(uuid.uuid4()))
    cycle_number:    int
    started_at:      str    = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    completed_at:    Optional[str] = None
    phases_completed: List[str] = Field(default_factory=list)
    signals_detected: int   = 0
    decisions_made:   int   = 0
    workflows_triggered: int = 0
    learnings_recorded:  int = 0
    health_score:     float = 0.0
    summary:          str   = ""


class BOSStatus(BaseModel):
    status_id:        str   = Field(default_factory=lambda: str(uuid.uuid4()))
    system_state:     str   # "BOOTING" | "RUNNING" | "PAUSED" | "STOPPED"
    uptime_cycles:    int
    health_score:     float
    active_workflows: int
    memory_entries:   int
    knowledge_nodes:  int
    decisions_pending: int
    last_cycle_at:    Optional[str]
    subsystem_health: Dict[str, bool]


# ---------------------------------------------------------------------------
# Autonomous Business Operating System
# ---------------------------------------------------------------------------

class AutonomousBusinessOS:
    """
    Master autonomous runtime that wires together all Phase 15 subsystems
    into a coherent heartbeat loop:

        Monitor → Understand → Predict → Decide → Act → Learn → (repeat)

    Each cycle ingests business events, reasons across domains, triggers
    workflows, and improves itself.
    """

    def __init__(self) -> None:
        # --- Subsystem initialisation ---
        self._memory    = EnterpriseMemorySystem()
        self._graph     = BusinessKnowledgeGraph()
        self._learner   = SelfLearningEngine(memory=self._memory)
        self._decision  = AutonomousDecisionEngine(memory=self._memory)
        self._twin      = OrganisationTwin()
        self._executor  = AutonomousWorkflowExecutor()
        self._reasoner  = EnterpriseReasoningEngine()
        self._coo       = AICOO()
        self._ceo       = AICEO()

        self._cycle_count: int             = 0
        self._cycle_log:   List[CycleResult] = []
        self._state:       str             = "BOOTING"
        self._event_queue: List[Dict[str, Any]] = []

        logger.info("AutonomousBusinessOS initialising all subsystems…")

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> Dict[str, Any]:
        """Boot all subsystems and build initial knowledge graph."""
        self._graph.build_default_enterprise_graph()
        self._state = "RUNNING"

        # Seed initial business memory
        self._memory.store(MemoryEntry(
            tier=MemoryTier.BUSINESS,
            subject="BOS System Start",
            content="Autonomous Business OS started. All subsystems online.",
            tags=["system", "startup"],
            importance=ImportanceLevel.HIGH,
        ))

        logger.info("AutonomousBusinessOS RUNNING.")
        return {
            "status":         "RUNNING",
            "subsystems":     self._get_subsystem_status(),
            "knowledge_nodes": len(self._graph._nodes),
            "knowledge_edges": len(self._graph._edges),
        }

    def _get_subsystem_status(self) -> Dict[str, bool]:
        return {
            "knowledge_graph":    len(self._graph._nodes) > 0,
            "enterprise_memory":  True,
            "self_learning":      True,
            "decision_engine":    True,
            "digital_twin":       True,
            "workflow_executor":  True,
            "reasoning_engine":   True,
            "ai_coo":             True,
            "ai_ceo":             True,
        }

    # ------------------------------------------------------------------
    # Event ingestion
    # ------------------------------------------------------------------

    def ingest_business_event(self, event: Dict[str, Any]) -> None:
        """Queue any incoming business signal for processing in the next cycle."""
        event.setdefault("event_id", str(uuid.uuid4()))
        event.setdefault("received_at", datetime.now(timezone.utc).isoformat())
        self._event_queue.append(event)

        # Persist to memory
        self._memory.store(MemoryEntry(
            tier=MemoryTier.BUSINESS,
            subject=f"Business Event: {event.get('type', 'unknown')}",
            content=str(event),
            tags=["event", event.get("type", "unknown")],
            importance=ImportanceLevel.MEDIUM,
        ))
        logger.debug("Event ingested: %s", event.get("type", "unknown"))

    # ------------------------------------------------------------------
    # Full BOS cycle
    # ------------------------------------------------------------------

    def run_autonomous_cycle(
        self,
        kpi_snapshot: Optional[Dict[str, float]] = None,
    ) -> CycleResult:
        """
        Execute one full BOS heartbeat:
        Monitor → Understand → Predict → Decide → Act → Learn
        """
        self._cycle_count += 1
        cycle = CycleResult(cycle_number=self._cycle_count)
        kpi_snapshot = kpi_snapshot or self._default_kpi_snapshot()

        logger.info("BOS Cycle #%d starting…", self._cycle_count)

        # ── Phase 1: MONITOR ────────────────────────────────────────────
        ops_brief = self._coo.generate_operations_brief()
        cycle.phases_completed.append(BOSCyclePhase.MONITOR)
        cycle.health_score = ops_brief.kpi_scorecard["overall_health"]

        # ── Phase 2: UNDERSTAND ─────────────────────────────────────────
        self.understand_business()
        cycle.phases_completed.append(BOSCyclePhase.UNDERSTAND)

        # ── Phase 3: PREDICT ────────────────────────────────────────────
        twin_trajectory = self._twin.run_growth_simulation(quarters=4)
        decision_report = self.predict_business(kpi_snapshot)
        cycle.signals_detected = len(decision_report.risks_detected) + len(decision_report.opportunities)
        cycle.phases_completed.append(BOSCyclePhase.PREDICT)

        # ── Phase 4: DECIDE ─────────────────────────────────────────────
        decisions = self.recommend_actions(kpi_snapshot)
        cycle.decisions_made = len(decisions)
        cycle.phases_completed.append(BOSCyclePhase.DECIDE)

        # ── Phase 5: ACT ────────────────────────────────────────────────
        executions = self.execute_workflows(kpi_snapshot, ops_brief)
        cycle.workflows_triggered = len(executions)
        cycle.phases_completed.append(BOSCyclePhase.ACT)

        # ── Phase 6: LEARN ──────────────────────────────────────────────
        learnings = self.learn_continuously(cycle)
        cycle.learnings_recorded = learnings
        cycle.phases_completed.append(BOSCyclePhase.LEARN)

        # Finalise
        cycle.completed_at = datetime.now(timezone.utc).isoformat()
        cycle.summary = (
            f"Cycle #{self._cycle_count}: health={cycle.health_score:.0f}%, "
            f"signals={cycle.signals_detected}, decisions={cycle.decisions_made}, "
            f"workflows={cycle.workflows_triggered}, learnings={cycle.learnings_recorded}."
        )

        self._cycle_log.append(cycle)
        self._event_queue.clear()
        logger.info("BOS Cycle #%d complete: %s", self._cycle_count, cycle.summary)
        return cycle

    # ------------------------------------------------------------------
    # Phase implementations
    # ------------------------------------------------------------------

    def understand_business(self) -> Dict[str, Any]:
        """Build/refresh the knowledge graph from available business data."""
        stats = self._graph.get_stats()
        # Cross-system relationship scan
        cross_links = self._graph.find_cross_system_relationships()
        return {
            "graph_nodes":         stats["total_nodes"],
            "graph_edges":         stats["total_edges"],
            "cross_system_links":  len(cross_links),
            "node_types":          stats["node_type_distribution"],
        }

    def monitor_business(self) -> Dict[str, Any]:
        """Collect all operational metrics."""
        brief = self._coo.generate_operations_brief()
        return {
            "health_score":    brief.kpi_scorecard["overall_health"],
            "kpis_monitored":  brief.kpi_scorecard["total_kpis"],
            "critical_alerts": len(brief.critical_alerts),
            "departments":     len(brief.department_health),
        }

    def predict_business(
        self,
        kpi_snapshot: Optional[Dict[str, float]] = None,
    ):
        """Run forecasts and digital twin simulation."""
        kpi_snapshot = kpi_snapshot or self._default_kpi_snapshot()
        return self._decision.generate_decision_report(kpi_snapshot)

    def recommend_actions(
        self,
        kpi_snapshot: Optional[Dict[str, float]] = None,
    ) -> List[Any]:
        """Surface top decisions from the decision engine."""
        kpi_snapshot = kpi_snapshot or self._default_kpi_snapshot()
        risks  = self._decision.detect_risks(kpi_snapshot)
        opps   = self._decision.detect_opportunities(kpi_snapshot)
        return self._decision.rank_decisions(risks + opps)

    def simulate_outcomes(self, question: str) -> Any:
        """Run scenario planning for top recommendations."""
        return self._reasoner.run_scenario_planning(
            business_goal=question,
            scenarios=["Optimistic Growth", "Base Case", "Downside Scenario"],
        )

    def execute_workflows(
        self,
        kpi_snapshot: Dict[str, float],
        ops_brief: Any,
    ) -> List[Any]:
        """Dispatch autonomous workflows based on current signals."""
        executions = []
        workflows  = self._executor.list_workflows()

        # Always run the daily analytics cycle
        daily_wf = next((w for w in workflows if "Daily" in w.name), None)
        if daily_wf:
            exec_result = self._executor.trigger_workflow(
                daily_wf.workflow_id,
                context={"dataset_name": "enterprise_kpi_stream", "row_count": 50_000},
                trigger_type=TriggerType.SCHEDULED,
            )
            executions.append(exec_result)

        # If there are critical alerts → trigger anomaly workflow
        if ops_brief.critical_alerts:
            anomaly_wf = next((w for w in workflows if "Anomaly" in w.name), None)
            if anomaly_wf:
                exec_result = self._executor.trigger_workflow(
                    anomaly_wf.workflow_id,
                    context={"alert_message": ops_brief.critical_alerts[0]},
                    trigger_type=TriggerType.ANOMALY,
                )
                executions.append(exec_result)

        return executions

    def learn_continuously(self, cycle: CycleResult) -> int:
        """Update self-learning engine from cycle outcomes."""
        learnings = 0

        # Record BOS orchestrator performance
        self._learner.record_outcome(
            agent_name="autonomous_bos",
            task_type="full_cycle",
            accuracy=min(1.0, cycle.health_score / 100),
            latency_ms=500.0,
            user_rating=4.5,
            model_used="ensemble",
            accepted=True,
            notes=cycle.summary,
        )
        learnings += 1

        # Persist cycle to long-term memory
        self._memory.store(MemoryEntry(
            tier=MemoryTier.LONG_TERM,
            subject=f"BOS Cycle #{cycle.cycle_number}",
            content=cycle.summary,
            tags=["bos_cycle", f"cycle_{cycle.cycle_number}"],
            importance=ImportanceLevel.MEDIUM,
        ))
        learnings += 1

        return learnings

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def get_status(self) -> BOSStatus:
        executor_stats = self._executor.get_executor_stats()
        mem_stats      = self._memory.get_memory_stats()
        pending        = len([d for d in self._decision._decision_log if True])  # all recent decisions

        last_cycle_at = (
            self._cycle_log[-1].completed_at if self._cycle_log else None
        )

        return BOSStatus(
            system_state=self._state,
            uptime_cycles=self._cycle_count,
            health_score=self._coo.get_coo_dashboard()["health_score"],
            active_workflows=executor_stats["workflows_registered"],
            memory_entries=mem_stats.total_entries,
            knowledge_nodes=len(self._graph._nodes),
            decisions_pending=min(pending, 10),
            last_cycle_at=last_cycle_at,
            subsystem_health=self._get_subsystem_status(),
        )

    def get_cycle_history(self, limit: int = 20) -> List[CycleResult]:
        return self._cycle_log[-limit:]

    def get_knowledge_graph_schema(self) -> Dict[str, Any]:
        """Return a serialisable graph snapshot for API and dashboard consumers."""
        return self._graph.export_schema()

    def get_queued_event_count(self) -> int:
        """Return the number of events awaiting the next autonomous cycle."""
        return len(self._event_queue)

    # ------------------------------------------------------------------
    # Convenience
    # ------------------------------------------------------------------

    def _default_kpi_snapshot(self) -> Dict[str, float]:
        return {
            "revenue_change_pct":  0.03,
            "churn_rate":          0.027,
            "cost_overrun_pct":    0.08,
            "cac_change_pct":     -0.06,
            "nps_delta":           3.0,
        }

    def get_full_enterprise_intelligence(self) -> Dict[str, Any]:
        """
        Single API call that returns the complete autonomous intelligence
        snapshot — used by front-end executive dashboards.
        """
        ceo_dash   = self._ceo.get_ceo_dashboard()
        coo_dash   = self._coo.get_coo_dashboard()
        twin_state = self._twin.get_twin_state()
        bos_status = self.get_status()

        return {
            "bos_status":         bos_status.model_dump(),
            "ceo_dashboard":      ceo_dash.model_dump(),
            "coo_dashboard":      coo_dash,
            "digital_twin_health": twin_state["health_score"],
            "knowledge_graph":    self._graph.get_stats(),
            "memory_summary":     self._memory.summarize_business_memory(),
            "learning_report":    self._learner.get_learning_report(),
            "generated_at":       datetime.now(timezone.utc).isoformat(),
        }
