"""Production Monitoring API endpoints (Phase 18.5.6)."""

from typing import Any
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from backend.monitoring.production_monitoring import (
    ProductionMonitoringService,
    get_monitoring_service,
)

router = APIRouter(prefix="/monitoring", tags=["monitoring"])


class LatencyRecordRequest(BaseModel):
    operation: str = Field(..., description="Operation name (upload, sql, rag, agent, visualization, forecast)")
    duration_ms: float = Field(..., description="Latency duration in milliseconds")


@router.get("/dashboard")
async def get_dashboard(
    service: ProductionMonitoringService = Depends(get_monitoring_service),
) -> dict[str, Any]:
    """Retrieve real-time production monitoring dashboard."""
    return service.get_monitoring_dashboard()


@router.get("/health")
async def get_health(
    service: ProductionMonitoringService = Depends(get_monitoring_service),
) -> dict[str, Any]:
    """Retrieve real-time infrastructure and service health."""
    dash = service.get_monitoring_dashboard()
    return {
        "platform_status": dash["platform_status"],
        "timestamp": dash["timestamp"],
        "infrastructure": dash["infrastructure"],
    }


@router.get("/summary")
async def get_daily_summary(
    service: ProductionMonitoringService = Depends(get_monitoring_service),
) -> dict[str, Any]:
    """Generate and retrieve daily health summary."""
    return service.generate_daily_health_summary()


@router.post("/record")
async def record_metric(
    payload: LatencyRecordRequest,
    service: ProductionMonitoringService = Depends(get_monitoring_service),
) -> dict[str, Any]:
    """Record operation latency metric."""
    service.record_latency(payload.operation, payload.duration_ms)
    return {"status": "recorded", "operation": payload.operation, "duration_ms": payload.duration_ms}
