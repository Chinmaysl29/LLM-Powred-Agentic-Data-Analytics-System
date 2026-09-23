"""Orchestrator API endpoints for Phase 3.2."""

import logging
from typing import Any
from fastapi import APIRouter, Depends, status

from backend.app.schemas.orchestrator import (
    OrchestratorRequest,
    OrchestratorResponse,
)
from backend.app.services.orchestrator_service import (
    OrchestratorService,
    get_orchestrator_service,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/orchestrator", tags=["Orchestrator Agent"])


@router.post(
    "/execute",
    response_model=OrchestratorResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute query through the sequential agent orchestration pipeline",
)
async def execute_orchestrator(
    request: OrchestratorRequest,
    service: OrchestratorService = Depends(get_orchestrator_service),
) -> OrchestratorResponse:
    """Classify intent, resolve workflow, manage shared context, execute agents, and aggregate results."""
    logger.info("Executing orchestrator query=%s dataset_id=%s", request.query[:50], request.dataset_id)
    return await service.execute(
        query=request.query,
        dataset_id=request.dataset_id,
        context=request.context,
    )


@router.get(
    "/workflows",
    response_model=dict[str, list[str]],
    status_code=status.HTTP_200_OK,
    summary="List all registered intent-to-workflow agent pipelines",
)
async def list_workflows(
    service: OrchestratorService = Depends(get_orchestrator_service),
) -> dict[str, list[str]]:
    """Return all intent-to-agent mappings currently registered in the workflow registry."""
    return service.workflow_registry.list_workflows()
