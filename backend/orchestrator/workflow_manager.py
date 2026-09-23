"""Workflow manager component for orchestrator pipelines."""

from backend.app.services.workflow_registry import WorkflowRegistry

WorkflowManager = WorkflowRegistry

__all__ = ["WorkflowManager", "WorkflowRegistry"]
