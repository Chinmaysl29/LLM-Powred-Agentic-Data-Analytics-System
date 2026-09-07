"""Operator API for the Phase 15 autonomous intelligence runtime.

The runtime deliberately stays in decision-support mode: a cycle can analyse,
rank, and queue workflow results, but it does not make external changes to a
customer's systems from this API.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, status
from pydantic import BaseModel, Field

from backend.autonomous.autonomous_bos import AutonomousBusinessOS


router = APIRouter(prefix="/autonomous", tags=["Autonomous Business OS"])


class BusinessEventRequest(BaseModel):
    """A business event to be incorporated during the next autonomous cycle."""

    event: Dict[str, Any] = Field(..., min_length=1)


class CycleRequest(BaseModel):
    """Optional current KPI values; omitted values use the BOS baseline."""

    kpi_snapshot: Optional[Dict[str, float]] = None


class SimulationRequest(BaseModel):
    goal: str = Field(..., min_length=3, max_length=500)


_bos = AutonomousBusinessOS()


def _runtime() -> AutonomousBusinessOS:
    """Return one process-local runtime, booting it exactly once."""
    if _bos.get_status().system_state == "BOOTING":
        _bos.start()
    return _bos


@router.post("/start")
def start_runtime() -> Dict[str, Any]:
    """Start the autonomous runtime, or return its current state if running."""
    runtime = _runtime()
    return runtime.get_status().model_dump(mode="json")


@router.get("/status")
def get_status() -> Dict[str, Any]:
    return _runtime().get_status().model_dump(mode="json")


@router.get("/intelligence")
def get_enterprise_intelligence() -> Dict[str, Any]:
    """Return the consolidated CEO, COO, graph, memory, and learning snapshot."""
    return _runtime().get_full_enterprise_intelligence()


@router.get("/knowledge-graph")
def get_knowledge_graph() -> Dict[str, Any]:
    """Expose the graph schema for dashboard visualisation and traceability."""
    return _runtime().get_knowledge_graph_schema()


@router.post("/events", status_code=status.HTTP_202_ACCEPTED)
def ingest_business_event(payload: BusinessEventRequest) -> Dict[str, Any]:
    runtime = _runtime()
    runtime.ingest_business_event(payload.event)
    return {
        "status": "QUEUED",
        "event_id": payload.event["event_id"],
        "queued_events": runtime.get_queued_event_count(),
    }


@router.post("/cycles")
def run_cycle(payload: CycleRequest) -> Dict[str, Any]:
    """Run one monitor → understand → predict → decide → act → learn cycle."""
    cycle = _runtime().run_autonomous_cycle(payload.kpi_snapshot)
    return cycle.model_dump(mode="json")


@router.get("/cycles")
def get_cycle_history(limit: int = 20) -> List[Dict[str, Any]]:
    bounded_limit = max(1, min(limit, 100))
    return [
        cycle.model_dump(mode="json")
        for cycle in _runtime().get_cycle_history(bounded_limit)
    ]


@router.post("/simulate")
def simulate_outcomes(payload: SimulationRequest) -> List[Dict[str, Any]]:
    """Run planning scenarios without changing the live organisation state."""
    return [scenario.model_dump(mode="json") for scenario in _runtime().simulate_outcomes(payload.goal)]
