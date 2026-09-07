"""
Phase 12.10.5 — Workflow Plugin SDK
Interfaces for custom LangGraph state machines, multi-agent chaining pipelines,
and bespoke enterprise automation flows.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import time
from pydantic import BaseModel, Field


class WorkflowExecutionResult(BaseModel):
    workflow_id: str
    status: str # "COMPLETED", "FAILED"
    output_state: Dict[str, Any]
    steps_executed: List[str]
    execution_time_sec: float
    completed_at: float = Field(default_factory=time.time)


class BaseWorkflowPlugin(ABC):
    """
    Abstract Base Class for custom LangGraph and multi-agent workflow extensions.
    """

    def __init__(self, workflow_id: str, name: str):
        self.workflow_id = workflow_id
        self.name = name
        self.steps: List[str] = []

    @abstractmethod
    def run(self, initial_state: Dict[str, Any]) -> WorkflowExecutionResult:
        """Execute the workflow state graph."""
        pass

    def validate_workflow(self) -> bool:
        """Ensure workflow has valid step definitions."""
        return len(self.steps) > 0
