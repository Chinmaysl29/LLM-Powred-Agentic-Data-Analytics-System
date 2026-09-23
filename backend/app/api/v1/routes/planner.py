"""Workflow Planner API endpoints for Phase 3.3."""

import logging
from fastapi import APIRouter, Depends, status

from backend.app.schemas.planner import (
    WorkflowPlan,
    WorkflowPlanningRequest,
)
from backend.app.services.workflow_planner_service import (
    WorkflowPlannerService,
    get_workflow_planner_service,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/planner", tags=["Workflow Planner"])


@router.post(
    "/plan",
    response_model=WorkflowPlan,
    status_code=status.HTTP_200_OK,
    summary="Generate dynamic execution plan based on context, rules, and dependencies",
)
async def generate_workflow_plan(
    request: WorkflowPlanningRequest,
    service: WorkflowPlannerService = Depends(get_workflow_planner_service),
) -> WorkflowPlan:
    """Analyze query and dataset context, evaluate rules, and return optimized workflow plan."""
    logger.info("Generating workflow plan for query: %s", request.query[:50])
    return await service.plan(request)


@router.get(
    "/templates",
    response_model=dict[str, list[str]],
    status_code=status.HTTP_200_OK,
    summary="List baseline workflow templates",
)
async def list_templates(
    service: WorkflowPlannerService = Depends(get_workflow_planner_service),
) -> dict[str, list[str]]:
    """Return all default baseline workflow templates from the registry."""
    return service.workflow_registry.list_workflows()
