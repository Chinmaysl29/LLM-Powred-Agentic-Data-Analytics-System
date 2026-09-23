"""Pydantic schemas and models for Phase 3.3 Workflow Planner."""

from typing import Any
from uuid import uuid4
from pydantic import BaseModel, ConfigDict, Field


class PlanDependency(BaseModel):
    """Prerequisite agent dependency declaration for a workflow step."""

    step: str = Field(..., description="Target agent step")
    requires: list[str] = Field(default_factory=list, description="Prerequisite agent steps that must execute before this step")


class WorkflowPlan(BaseModel):
    """Dynamic execution plan produced by the Workflow Planner."""

    model_config = ConfigDict(from_attributes=True)

    workflow_id: str = Field(default_factory=lambda: f"wf_{uuid4().hex[:8]}", description="Unique workflow plan identifier")
    intent: str = Field(..., description="Primary user intent")
    workflow_type: str = Field(default="dynamic", description="Type of plan: dynamic, template, optimized")
    steps: list[str] = Field(default_factory=list, description="Ordered sequence of agents to execute")
    dependencies: list[PlanDependency] = Field(default_factory=list, description="Inter-agent dependency graph")
    estimated_execution_time: float = Field(default=0.0, description="Estimated total execution duration in seconds")
    optimizations_applied: list[str] = Field(default_factory=list, description="List of performance optimizations applied")
    rules_triggered: list[str] = Field(default_factory=list, description="List of dynamic rules triggered by context")
    use_sampling: bool = Field(default=False, description="Whether data sampling should be enabled for massive datasets")

    @property
    def workflow(self) -> list[str]:
        """Convenience alias returning steps list matching success criteria."""
        return self.steps


class WorkflowPlanningRequest(BaseModel):
    """Input payload to generate a dynamic execution plan."""

    query: str = Field(..., min_length=1, max_length=2000, description="Natural language user request")
    intent: str | None = Field(default=None, description="Pre-classified intent or None for automatic intent detection")
    dataset_id: str | None = Field(default=None, description="Optional active dataset UUID")
    metadata: dict[str, Any] | None = Field(default=None, description="Dataset column and schema metadata")
    profile: dict[str, Any] | None = Field(default=None, description="Dataset statistical profile and distribution")
    quality: dict[str, Any] | None = Field(default=None, description="Dataset quality assessment metrics")
    dataset_type: str | None = Field(default=None, description="Domain type: sales, churn, inventory, etc.")
