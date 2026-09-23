"""
Phase 15.6 — Autonomous Workflow Execution Engine
Eliminates manual work through end-to-end automated business workflows:
auto-analysis, auto-forecasting, auto-reporting, auto-alerting,
auto-escalation, and auto-recommendations.
"""

from __future__ import annotations

import uuid
import logging
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field

logger = logging.getLogger("backend.autonomous.workflow_executor")


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class StepType(str, Enum):
    ANALYSE     = "analyse"
    FORECAST    = "forecast"
    REPORT      = "report"
    ALERT       = "alert"
    ESCALATE    = "escalate"
    RECOMMEND   = "recommend"
    CUSTOM      = "custom"


class TriggerType(str, Enum):
    MANUAL      = "manual"
    SCHEDULED   = "scheduled"
    THRESHOLD   = "threshold"
    EVENT       = "event"
    ANOMALY     = "anomaly"


class StepStatus(str, Enum):
    PENDING     = "pending"
    RUNNING     = "running"
    COMPLETED   = "completed"
    FAILED      = "failed"
    SKIPPED     = "skipped"


class ExecutionStatus(str, Enum):
    QUEUED      = "queued"
    RUNNING     = "running"
    COMPLETED   = "completed"
    FAILED      = "failed"
    CANCELLED   = "cancelled"


class WorkflowStep(BaseModel):
    step_id:     str       = Field(default_factory=lambda: str(uuid.uuid4()))
    name:        str
    step_type:   StepType
    agent:       str       = "orchestrator"
    config:      Dict[str, Any] = Field(default_factory=dict)
    depends_on:  List[str] = Field(default_factory=list)   # step_ids
    timeout_s:   int       = 300


class WorkflowDefinition(BaseModel):
    workflow_id:   str           = Field(default_factory=lambda: str(uuid.uuid4()))
    name:          str
    description:   str           = ""
    trigger_type:  TriggerType   = TriggerType.MANUAL
    trigger_config: Dict[str, Any] = Field(default_factory=dict)
    steps:         List[WorkflowStep] = Field(default_factory=list)
    enabled:       bool          = True
    created_at:    str           = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class StepResult(BaseModel):
    step_id:     str
    step_name:   str
    status:      StepStatus
    output:      Dict[str, Any] = Field(default_factory=dict)
    error:       Optional[str]  = None
    duration_ms: float          = 0.0
    completed_at: str           = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class WorkflowExecution(BaseModel):
    execution_id:  str              = Field(default_factory=lambda: str(uuid.uuid4()))
    workflow_id:   str
    workflow_name: str
    trigger_type:  TriggerType
    status:        ExecutionStatus  = ExecutionStatus.QUEUED
    step_results:  List[StepResult] = Field(default_factory=list)
    triggered_at:  str              = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    completed_at:  Optional[str]    = None
    duration_ms:   float            = 0.0
    context:       Dict[str, Any]   = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Built-in step handlers
# ---------------------------------------------------------------------------

def _handle_analyse(step: WorkflowStep, ctx: Dict[str, Any]) -> Dict[str, Any]:
    dataset = ctx.get("dataset_name", "default_dataset")
    return {
        "action": "auto_analysis",
        "dataset": dataset,
        "rows_analysed": ctx.get("row_count", 10_000),
        "insights_found": 7,
        "kpis_extracted": ["Revenue", "Churn", "CAC", "LTV", "NPS"],
        "anomalies_detected": 2,
        "status": "COMPLETED",
    }


def _handle_forecast(step: WorkflowStep, ctx: Dict[str, Any]) -> Dict[str, Any]:
    metric = step.config.get("target_metric", "Revenue")
    horizon = step.config.get("horizon_months", 6)
    return {
        "action": "auto_forecast",
        "target_metric": metric,
        "horizon_months": horizon,
        "model_used": "XGBoost",
        "mape": 0.043,
        "forecast_generated": True,
        "status": "COMPLETED",
    }


def _handle_report(step: WorkflowStep, ctx: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "action": "auto_report",
        "report_type": step.config.get("report_type", "executive_summary"),
        "pages": 5,
        "distributed_to": step.config.get("recipients", ["ceo@company.com"]),
        "format": "PDF",
        "status": "SENT",
    }


def _handle_alert(step: WorkflowStep, ctx: Dict[str, Any]) -> Dict[str, Any]:
    channels = step.config.get("channels", ["slack", "email"])
    return {
        "action": "auto_alert",
        "alert_type": step.config.get("alert_type", "threshold_breach"),
        "message": ctx.get("alert_message", "KPI threshold exceeded."),
        "channels_notified": channels,
        "status": "DELIVERED",
    }


def _handle_escalate(step: WorkflowStep, ctx: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "action": "auto_escalation",
        "escalated_to": step.config.get("escalate_to", "manager@company.com"),
        "priority": step.config.get("priority", "HIGH"),
        "jira_ticket_created": True,
        "ticket_id": f"AUTO-{uuid.uuid4().hex[:6].upper()}",
        "status": "ESCALATED",
    }


def _handle_recommend(step: WorkflowStep, ctx: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "action": "auto_recommend",
        "recommendations_generated": 3,
        "top_recommendation": "Increase sales team outreach in underperforming regions.",
        "expected_impact": "8.5% revenue uplift over 90 days",
        "status": "COMPLETED",
    }


_STEP_HANDLERS: Dict[StepType, Callable] = {
    StepType.ANALYSE:   _handle_analyse,
    StepType.FORECAST:  _handle_forecast,
    StepType.REPORT:    _handle_report,
    StepType.ALERT:     _handle_alert,
    StepType.ESCALATE:  _handle_escalate,
    StepType.RECOMMEND: _handle_recommend,
}


# ---------------------------------------------------------------------------
# Autonomous Workflow Executor
# ---------------------------------------------------------------------------

class AutonomousWorkflowExecutor:
    """
    Registers, triggers, and executes enterprise workflows end-to-end.
    Each step is dispatched to the appropriate handler (simulated).
    Supports sequential step ordering with dependency resolution.
    """

    # -- Built-in canonical workflows --
    _CANONICAL_WORKFLOWS = [
        WorkflowDefinition(
            name="Daily Analytics Cycle",
            description="Automatically analyse new data, forecast KPIs, and send executive summary.",
            trigger_type=TriggerType.SCHEDULED,
            trigger_config={"cron": "0 7 * * *"},
            steps=[
                WorkflowStep(name="Auto Analysis",      step_type=StepType.ANALYSE,   agent="eda_agent"),
                WorkflowStep(name="Auto Forecast",       step_type=StepType.FORECAST,  agent="forecast_agent",  config={"target_metric": "Revenue", "horizon_months": 3}),
                WorkflowStep(name="Generate Report",     step_type=StepType.REPORT,    agent="report_agent",    config={"report_type": "executive_summary"}),
                WorkflowStep(name="Distribute Report",   step_type=StepType.ALERT,     agent="notification",    config={"channels": ["slack", "email"]}),
            ],
        ),
        WorkflowDefinition(
            name="Anomaly Alert Workflow",
            description="Detect anomalies, alert stakeholders, and escalate if critical.",
            trigger_type=TriggerType.ANOMALY,
            steps=[
                WorkflowStep(name="Detect Anomaly",     step_type=StepType.ANALYSE,   agent="eda_agent"),
                WorkflowStep(name="Send Alert",          step_type=StepType.ALERT,     config={"channels": ["slack"]}),
                WorkflowStep(name="Escalate Critical",   step_type=StepType.ESCALATE,  config={"priority": "HIGH"}),
            ],
        ),
        WorkflowDefinition(
            name="Opportunity Capture Workflow",
            description="Identify business opportunities and recommend actions.",
            trigger_type=TriggerType.EVENT,
            steps=[
                WorkflowStep(name="Analyse Context",    step_type=StepType.ANALYSE),
                WorkflowStep(name="Generate Recommendations", step_type=StepType.RECOMMEND, agent="recommendation_agent"),
                WorkflowStep(name="Create Board Report", step_type=StepType.REPORT,   config={"report_type": "opportunity_brief"}),
            ],
        ),
    ]

    def __init__(self) -> None:
        self._registry:   Dict[str, WorkflowDefinition] = {}
        self._executions: Dict[str, WorkflowExecution]  = {}

        # Register built-in workflows
        for wf in self._CANONICAL_WORKFLOWS:
            self._registry[wf.workflow_id] = wf

        logger.info(
            "AutonomousWorkflowExecutor initialised with %d built-in workflows.",
            len(self._registry),
        )

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register_workflow(self, workflow: WorkflowDefinition) -> WorkflowDefinition:
        self._registry[workflow.workflow_id] = workflow
        logger.info("Workflow registered: %s", workflow.name)
        return workflow

    def list_workflows(self) -> List[WorkflowDefinition]:
        return list(self._registry.values())

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def trigger_workflow(
        self,
        workflow_id:  str,
        context:      Optional[Dict[str, Any]] = None,
        trigger_type: TriggerType = TriggerType.MANUAL,
    ) -> WorkflowExecution:
        wf = self._registry.get(workflow_id)
        if not wf:
            raise ValueError(f"Workflow not found: {workflow_id}")

        execution = WorkflowExecution(
            workflow_id=workflow_id,
            workflow_name=wf.name,
            trigger_type=trigger_type,
            status=ExecutionStatus.RUNNING,
            context=context or {},
        )
        self._executions[execution.execution_id] = execution

        start_ms = _now_ms()
        try:
            for step in wf.steps:
                result = self.execute_step(step, execution.context)
                execution.step_results.append(result)
                if result.status == StepStatus.FAILED:
                    execution.status = ExecutionStatus.FAILED
                    break
            else:
                execution.status = ExecutionStatus.COMPLETED

        except Exception as exc:
            execution.status = ExecutionStatus.FAILED
            logger.exception("Workflow %s failed: %s", wf.name, exc)

        execution.duration_ms  = round(_now_ms() - start_ms, 2)
        execution.completed_at = datetime.now(timezone.utc).isoformat()

        logger.info(
            "Workflow '%s' %s in %.0f ms.",
            wf.name, execution.status, execution.duration_ms,
        )
        return execution

    def execute_step(self, step: WorkflowStep, ctx: Dict[str, Any]) -> StepResult:
        import time
        t0 = time.perf_counter()
        handler = _STEP_HANDLERS.get(step.step_type)
        try:
            output = handler(step, ctx) if handler else {"status": "NO_HANDLER"}
            status = StepStatus.COMPLETED
            error  = None
        except Exception as exc:
            output = {}
            status = StepStatus.FAILED
            error  = str(exc)
            logger.warning("Step '%s' failed: %s", step.name, exc)

        duration_ms = round((time.perf_counter() - t0) * 1000, 2)
        return StepResult(
            step_id=step.step_id,
            step_name=step.name,
            status=status,
            output=output,
            error=error,
            duration_ms=duration_ms,
        )

    # ------------------------------------------------------------------
    # Convenience shortcuts
    # ------------------------------------------------------------------

    def auto_analyse(self, dataset_name: str, row_count: int = 10_000) -> Dict[str, Any]:
        """Trigger just the analysis step with minimal context."""
        step = WorkflowStep(name="Auto Analysis", step_type=StepType.ANALYSE, agent="eda_agent")
        result = self.execute_step(step, {"dataset_name": dataset_name, "row_count": row_count})
        return result.output

    def auto_forecast(self, target_metric: str, horizon_months: int = 6) -> Dict[str, Any]:
        step = WorkflowStep(
            name="Auto Forecast", step_type=StepType.FORECAST,
            config={"target_metric": target_metric, "horizon_months": horizon_months},
        )
        return self.execute_step(step, {}).output

    def auto_report(self, report_type: str = "executive_summary", recipients: Optional[List[str]] = None) -> Dict[str, Any]:
        step = WorkflowStep(
            name="Auto Report", step_type=StepType.REPORT,
            config={"report_type": report_type, "recipients": recipients or ["leadership@company.com"]},
        )
        return self.execute_step(step, {}).output

    def auto_alert(self, message: str, channels: Optional[List[str]] = None) -> Dict[str, Any]:
        step = WorkflowStep(
            name="Auto Alert", step_type=StepType.ALERT,
            config={"channels": channels or ["slack", "email"], "alert_type": "autonomous"},
        )
        return self.execute_step(step, {"alert_message": message}).output

    def auto_escalate(self, issue: str, priority: str = "HIGH") -> Dict[str, Any]:
        step = WorkflowStep(
            name="Auto Escalate", step_type=StepType.ESCALATE,
            config={"priority": priority},
        )
        return self.execute_step(step, {"issue": issue}).output

    def auto_recommend(self, context: Dict[str, Any]) -> Dict[str, Any]:
        step = WorkflowStep(name="Auto Recommend", step_type=StepType.RECOMMEND)
        return self.execute_step(step, context).output

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def get_execution_status(self, execution_id: str) -> Optional[WorkflowExecution]:
        return self._executions.get(execution_id)

    def get_execution_history(self, limit: int = 50) -> List[WorkflowExecution]:
        history = list(self._executions.values())
        return sorted(history, key=lambda e: e.triggered_at, reverse=True)[:limit]

    def get_executor_stats(self) -> Dict[str, Any]:
        executions = list(self._executions.values())
        completed  = sum(1 for e in executions if e.status == ExecutionStatus.COMPLETED)
        failed     = sum(1 for e in executions if e.status == ExecutionStatus.FAILED)
        return {
            "workflows_registered": len(self._registry),
            "total_executions":     len(executions),
            "completed":            completed,
            "failed":               failed,
            "success_rate":         round(completed / len(executions), 4) if executions else 1.0,
        }


def _now_ms() -> float:
    import time
    return time.perf_counter() * 1000
