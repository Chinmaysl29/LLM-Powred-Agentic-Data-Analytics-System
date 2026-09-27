"""Data Governance & Lineage API endpoints (Phase 18.5.7)."""

from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from backend.data_engineering.lineage_engine import (
    DataLineageEngine,
    get_lineage_engine,
)

router = APIRouter(prefix="/lineage", tags=["lineage"])


class RecordTransformationRequest(BaseModel):
    step_name: str = Field(..., description="Name of the transformation step")
    transformation_type: str = Field(..., description="e.g., imputation, outlier_removal, feature_scaling")
    description: str = Field(..., description="Human-readable description")
    operator: str = Field(default="system", description="Author or service applying transformation")
    parameters: dict[str, Any] = Field(default_factory=dict, description="Configuration parameters")


class RecordForecastLineageRequest(BaseModel):
    run_id: str = Field(..., description="Forecast execution ID")
    model_name: str = Field(..., description="Model name (arima, prophet, xgboost)")
    target: str = Field(..., description="Forecasted metric name")
    horizon: int = Field(..., description="Forecast horizon")
    metrics: dict[str, float] = Field(default_factory=dict, description="Validation error metrics (mae, rmse, mape, r2)")


@router.get("/{dataset_id}")
async def get_dataset_lineage(
    dataset_id: str,
    engine: DataLineageEngine = Depends(get_lineage_engine),
) -> dict[str, Any]:
    """Retrieve full provenance and transformation history for a dataset."""
    return engine.load_lineage(dataset_id)


@router.get("/{dataset_id}/graph")
async def get_lineage_graph(
    dataset_id: str,
    engine: DataLineageEngine = Depends(get_lineage_engine),
) -> dict[str, Any]:
    """Retrieve DAG nodes and edges for visualizing dataset evolution."""
    return engine.generate_lineage_graph(dataset_id)


@router.post("/{dataset_id}/transformations")
async def record_transformation(
    dataset_id: str,
    payload: RecordTransformationRequest,
    engine: DataLineageEngine = Depends(get_lineage_engine),
) -> dict[str, Any]:
    """Record an explicit dataset transformation step."""
    return engine.record_transformation(
        dataset_id=dataset_id,
        step_name=payload.step_name,
        transformation_type=payload.transformation_type,
        description=payload.description,
        operator=payload.operator,
        parameters=payload.parameters,
    )


@router.post("/{dataset_id}/forecasts")
async def record_forecast(
    dataset_id: str,
    payload: RecordForecastLineageRequest,
    engine: DataLineageEngine = Depends(get_lineage_engine),
) -> dict[str, Any]:
    """Record downstream forecast execution in dataset lineage."""
    return engine.record_forecast_event(
        dataset_id=dataset_id,
        run_id=payload.run_id,
        model_name=payload.model_name,
        target=payload.target,
        horizon=payload.horizon,
        metrics=payload.metrics,
    )


# -----------------------------------------------------------------------------
# Enterprise Dataset Lifecycle Lineage (Phase 18.6.5)
# -----------------------------------------------------------------------------

class RecordLifecycleEventRequest(BaseModel):
    stage: str = Field(..., description="Stage name (upload, canonical_json, profile, quality, cleaning, embedding, forecast, report)")
    status: str = Field(default="success", description="Event outcome status: success, failed, skipped")
    duration_ms: float = Field(default=0.0, description="Stage duration in milliseconds")
    details: dict[str, Any] = Field(default_factory=dict, description="Stage-specific execution details")
    error: str | None = Field(default=None, description="Error message if failed")


@router.get("/stages/supported", summary="List supported lifecycle stages")
async def list_supported_stages() -> list[str]:
    """List the 8 canonical stages of dataset journey."""
    from backend.app.services.lineage_service import LINEAGE_STAGES
    return LINEAGE_STAGES


@router.post("/{dataset_id}/events", summary="Record a dataset journey stage event (Phase 18.6.5)")
async def record_lineage_event(
    dataset_id: str,
    payload: RecordLifecycleEventRequest,
) -> dict[str, Any]:
    """Track the dataset journey: Upload -> Canonical JSON -> Profile -> Quality -> Cleaning -> Embedding -> Forecast -> Report."""
    from backend.app.services.lineage_service import get_lineage_service
    service = get_lineage_service()
    lineage = service.record_event(
        dataset_id=dataset_id,
        stage=payload.stage,
        status=payload.status,
        duration_ms=payload.duration_ms,
        details=payload.details,
        error=payload.error,
    )
    if lineage is None:
        raise HTTPException(status_code=404, detail=f"Lineage for dataset '{dataset_id}' not found.")
    return lineage.to_dict()


@router.get("/datasets/summary", summary="List lineage summary for all datasets")
async def list_all_lineage_summaries() -> list[dict[str, Any]]:
    """List high-level lifecycle stage status across all datasets."""
    from backend.app.services.lineage_service import get_lineage_service
    service = get_lineage_service()
    return service.list_all()

