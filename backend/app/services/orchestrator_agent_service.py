"""Checklist alias module providing OrchestratorAgentService pointing to OrchestratorService."""

from backend.app.services.orchestrator_service import (
    OrchestratorService,
    get_orchestrator_service,
)

OrchestratorAgentService = OrchestratorService
get_orchestrator_agent_service = get_orchestrator_service

__all__ = [
    "OrchestratorAgentService",
    "OrchestratorService",
    "get_orchestrator_agent_service",
    "get_orchestrator_service",
]
