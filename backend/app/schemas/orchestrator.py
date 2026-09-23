"""Pydantic schemas and models for Phase 3.2 Orchestrator Agent and Shared Context."""

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class AgentExecutionLog(BaseModel):
    """Execution telemetry for an individual agent in the workflow pipeline."""

    agent_name: str = Field(..., description="Name of the executing agent")
    status: str = Field(..., description="Execution status: success, failed, skipped, recovered")
    duration_ms: float = Field(default=0.0, description="Execution duration in milliseconds")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Timestamp of execution")
    error: str | None = Field(default=None, description="Error message if execution failed")


class WorkflowContext(BaseModel):
    """Centralized shared context object passed through the sequential agent pipeline."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    request_id: str = Field(default_factory=lambda: str(uuid4()), description="Unique request/run identifier")
    dataset_id: str | None = Field(default=None, description="Target dataset UUID if applicable")
    query: str = Field(..., description="Original user natural language query")
    intent: str = Field(default="unknown", description="Classified intent category")
    workflow: list[str] = Field(default_factory=list, description="Ordered sequence of agent names")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Dataset schema and column metadata")
    profile: dict[str, Any] = Field(default_factory=dict, description="Dataset statistical profile and distributions")
    quality: dict[str, Any] = Field(default_factory=dict, description="Dataset quality assessment metrics")
    results: dict[str, Any] = Field(default_factory=dict, description="Aggregated findings written by agents")
    errors: list[dict[str, Any]] = Field(default_factory=list, description="Logged agent errors during workflow execution")
    execution_log: list[AgentExecutionLog] = Field(default_factory=list, description="Step-by-step agent telemetry")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def add_result(self, agent_name: str, result: Any) -> None:
        """Write an agent result to the shared context."""
        self.results[agent_name] = result
        self.updated_at = datetime.now(timezone.utc)

    def get_result(self, agent_name: str, default: Any = None) -> Any:
        """Retrieve an agent result from the shared context."""
        return self.results.get(agent_name, default)

    def add_error(self, agent_name: str, error_message: str, details: Any = None) -> None:
        """Log an error from an agent while keeping pipeline intact."""
        error_entry = {
            "agent_name": agent_name,
            "error": error_message,
            "details": details,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self.errors.append(error_entry)
        self.updated_at = datetime.now(timezone.utc)

    def log_execution(self, agent_name: str, status: str, duration_ms: float, error: str | None = None) -> None:
        """Record step-by-step execution telemetry."""
        log_entry = AgentExecutionLog(
            agent_name=agent_name,
            status=status,
            duration_ms=round(duration_ms, 2),
            error=error,
        )
        self.execution_log.append(log_entry)
        self.updated_at = datetime.now(timezone.utc)


class OrchestratorRequest(BaseModel):
    """Input request for the Orchestrator Agent."""

    query: str = Field(..., min_length=1, max_length=2000, description="Natural language user request")
    dataset_id: str | None = Field(default=None, description="Optional active dataset UUID")
    context: dict[str, Any] | None = Field(default=None, description="Optional user or conversation context")


class OrchestratorResponse(BaseModel):
    """Unified aggregated response returned by the Orchestrator Agent."""

    model_config = ConfigDict(from_attributes=True)

    request_id: str = Field(..., description="Unique run identifier")
    dataset_id: str | None = Field(default=None, description="Active dataset UUID")
    query: str = Field(..., description="User query that was orchestrated")
    intent: str = Field(..., description="Classified intent")
    status: str = Field(..., description="Overall execution status: success, partial_success, failed")
    workflow: list[str] = Field(default_factory=list, description="Target agent sequence")
    executed_agents: list[str] = Field(default_factory=list, description="Agents that were actually executed")
    summary: str = Field(..., description="Synthesized executive summary across all agent outputs")
    results: dict[str, Any] = Field(default_factory=dict, description="Domain-aggregated outputs from all agents")
    errors: list[dict[str, Any]] = Field(default_factory=list, description="Any agent errors encountered during run")
    execution_time_ms: float = Field(default=0.0, description="Total pipeline execution duration in milliseconds")
