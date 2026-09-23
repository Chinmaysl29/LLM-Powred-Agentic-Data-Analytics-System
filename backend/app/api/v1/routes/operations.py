"""REST API Endpoints for Operations & Continuous Improvement (Phase 11)."""

from typing import Any, Dict, Optional
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from backend.operations.ab_testing import ab_testing_platform
from backend.operations.ai_quality_monitor import ai_quality_monitor
from backend.operations.continuous_improvement_orchestrator import (
    continuous_improvement_orchestrator,
)
from backend.operations.continuous_learning import continuous_learning_pipeline
from backend.operations.cost_optimizer import cost_optimization_engine
from backend.operations.feature_flags import feature_flag_system
from backend.operations.feedback_intelligence import feedback_intelligence
from backend.operations.product_analytics import product_analytics
from backend.operations.product_dashboard import product_dashboard

router = APIRouter(prefix="/operations", tags=["Operations & Continuous Improvement"])


# ----------------------------------------------------------------------
# Request / Response Schemas
# ----------------------------------------------------------------------

class FeedbackRequest(BaseModel):
    description: str = Field(..., min_length=2, description="Feedback narrative from the user")
    channel: str = Field(default="dashboard", description="Channel (chat, dashboard, report, feature_request, bug_report)")
    user_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AnalyticsEventRequest(BaseModel):
    event_type: str = Field(..., description="Event type (user_login, dataset_upload, query_executed, forecast_run, etc.)")
    user_id: str = Field(..., min_length=1)
    metadata: Dict[str, Any] = Field(default_factory=dict)


# ----------------------------------------------------------------------
# Phase 11.1 Feedback Intelligence
# ----------------------------------------------------------------------

@router.post("/feedback", status_code=status.HTTP_201_CREATED)
def submit_feedback(payload: FeedbackRequest) -> Dict[str, Any]:
    """Capture and auto-categorize user feedback."""
    try:
        return feedback_intelligence.capture_feedback(
            description=payload.description,
            channel=payload.channel,
            user_id=payload.user_id,
            metadata=payload.metadata,
        )
    except ValueError as ex:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ex))


@router.get("/feedback/analytics")
def get_feedback_analytics() -> Dict[str, Any]:
    """Return aggregated feedback categories, priorities, and top issues."""
    return feedback_intelligence.generate_feedback_analytics()


# ----------------------------------------------------------------------
# Phase 11.2 Product Analytics
# ----------------------------------------------------------------------

@router.post("/analytics/events", status_code=status.HTTP_201_CREATED)
def record_analytics_event(payload: AnalyticsEventRequest) -> Dict[str, Any]:
    """Record platform usage telemetry event."""
    try:
        return product_analytics.record_event(
            event_type=payload.event_type,
            user_id=payload.user_id,
            metadata=payload.metadata,
        )
    except ValueError as ex:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ex))


@router.get("/analytics/metrics")
def get_usage_metrics() -> Dict[str, Any]:
    """Return DAU, WAU, MAU, and feature usage telemetry."""
    return product_analytics.get_metrics()


# ----------------------------------------------------------------------
# Phase 11.4 AI Quality Monitoring
# ----------------------------------------------------------------------

@router.get("/quality/status")
def get_quality_status() -> Dict[str, Any]:
    """Return composite quality score and active SLA defect alerts."""
    return ai_quality_monitor.get_status()


# ----------------------------------------------------------------------
# Phase 11.6 Feature Flags
# ----------------------------------------------------------------------

@router.get("/feature-flags")
def list_feature_flags() -> Dict[str, Any]:
    """List all registered feature flags."""
    return {"flags": feature_flag_system.get_all_flags()}


@router.get("/feature-flags/{flag_name}/evaluate")
def evaluate_feature_flag(
    flag_name: str,
    user_id: Optional[str] = Query(None),
    role: Optional[str] = Query(None),
) -> Dict[str, Any]:
    """Evaluate whether a feature flag is enabled for caller."""
    return feature_flag_system.is_enabled(flag_name, user_id=user_id, role=role)


# ----------------------------------------------------------------------
# Phase 11.7 Cost Optimization
# ----------------------------------------------------------------------

@router.get("/costs")
def get_cost_analysis() -> Dict[str, Any]:
    """Return monthly spend breakdown and optimization recommendations."""
    return cost_optimization_engine.get_cost_analysis()


# ----------------------------------------------------------------------
# Phase 11.9 Product Intelligence Dashboard
# ----------------------------------------------------------------------

@router.get("/dashboard")
def get_product_dashboard() -> Dict[str, Any]:
    """Return unified dashboard aggregating all operational metrics."""
    return product_dashboard.get_dashboard_summary()


# ----------------------------------------------------------------------
# Phase 11.10 Continuous Improvement Orchestrator
# ----------------------------------------------------------------------

@router.get("/orchestrator/status")
def get_orchestration_cycle() -> Dict[str, Any]:
    """Generate and return master continuous improvement cycle and roadmap."""
    return continuous_improvement_orchestrator.generate_orchestration_cycle()
