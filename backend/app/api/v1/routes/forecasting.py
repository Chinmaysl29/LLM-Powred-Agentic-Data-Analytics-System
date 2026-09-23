"""API routes for Phase 6 Forecasting and Predictive Intelligence."""

import logging
from typing import Any

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.agents.forecasting_agent import BusinessForecastAgent
from backend.app.database.postgres import get_db_session
from backend.app.models.forecast_run import ForecastRun
from backend.app.repositories.forecast_run_repository import ForecastRunRepository
from backend.app.schemas.forecasting import (
    BusinessForecastAgentOutput,
    DataPoint,
    ForecastPipelineOutput,
    ForecastValidationOutput,
    ForecastingFoundationConfig,
    ForecastingFoundationResponse,
    FrequencyType,
    PrepareDataRecordsRequest,
    ScenarioEngineOutput,
    UnifiedForecastInput,
    UnifiedForecastOutput,
    ValidateDatasetRequest,
    ValidationReport,
    WhatIfAnalysisInput,
    WhatIfAnalysisOutput,
)
from backend.app.services.forecasting_foundation_service import (
    ForecastingFoundationService,
    get_forecasting_foundation_service,
)
from backend.forecasting.arima_model import ARIMAForecaster
from backend.forecasting.forecast_pipeline import ForecastPipeline
from backend.forecasting.forecast_validator import ForecastValidator
from backend.forecasting.prophet_model import ProphetForecaster
from backend.forecasting.scenario_engine import ScenarioEngine
from backend.forecasting.what_if_engine import WhatIfAnalysisEngine
from backend.forecasting.xgboost_forecaster import XGBoostForecaster

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/forecasting", tags=["Forecasting"])


# -----------------------------------------------------------------------------
# 1. Foundation & Validation Routes (Phase 6.1)
# -----------------------------------------------------------------------------

@router.get(
    "/prepare/{dataset_id}",
    response_model=ForecastingFoundationResponse,
    summary="Validate and Prepare Forecasting Dataset",
)
async def prepare_stored_dataset(
    dataset_id: str,
    version: int | None = Query(None, description="Dataset version to analyze"),
    time_column: str | None = Query(None, description="Explicit date/time column"),
    target_column: str | None = Query(None, description="Explicit target metric column"),
    frequency: FrequencyType | None = Query(None, description="Explicit frequency cadence"),
    sample_size: int | None = Query(None, description="Max rows to retrieve"),
    foundation_service: ForecastingFoundationService = Depends(get_forecasting_foundation_service),
) -> ForecastingFoundationResponse:
    """Retrieve a stored dataset and run time-series validation, preparation, and feature engineering."""
    config = ForecastingFoundationConfig(
        time_column=time_column,
        target_column=target_column,
        frequency=frequency,
    )
    return await foundation_service.prepare_dataset(
        dataset_id=dataset_id,
        version_number=version,
        config=config,
        sample_size=sample_size,
    )


@router.post(
    "/prepare-data",
    response_model=ForecastingFoundationResponse,
    summary="Prepare In-Memory Time Series Records",
)
async def prepare_data_records(
    request: PrepareDataRecordsRequest,
    foundation_service: ForecastingFoundationService = Depends(get_forecasting_foundation_service),
) -> ForecastingFoundationResponse:
    """Validate, regularize, and engineer features on raw in-memory time-series records."""
    if not request.records:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The 'records' array cannot be empty.",
        )
    df = pd.DataFrame(request.records)
    return foundation_service.prepare_dataframe(df, config=request.config)


@router.post(
    "/validate",
    response_model=ValidationReport,
    summary="Validate Forecasting Time Series Criteria",
)
async def validate_forecasting_dataset(
    request: ValidateDatasetRequest,
    foundation_service: ForecastingFoundationService = Depends(get_forecasting_foundation_service),
) -> ValidationReport:
    """Evaluate whether data satisfies date, target, history, and completeness checks."""
    if request.records:
        df = pd.DataFrame(request.records)
    elif request.dataset_id:
        df_resp = await foundation_service.prepare_dataset(
            dataset_id=request.dataset_id,
            version_number=request.version_number,
        )
        return df_resp.validation_report
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either 'records' or 'dataset_id' must be provided for validation.",
        )

    freq_val = request.frequency.value if request.frequency else "monthly"
    return foundation_service.validate_dataframe(
        df=df,
        time_col=request.time_column,
        target_col=request.target_column,
        frequency=freq_val,
    )


# -----------------------------------------------------------------------------
# 2. Model Specific Forecast Routes (Phases 6.3 - 6.5)
# -----------------------------------------------------------------------------

@router.post(
    "/prophet",
    response_model=UnifiedForecastOutput,
    summary="Generate Meta Prophet Forecast (Phase 6.3)",
)
async def run_prophet_forecast(
    input_data: UnifiedForecastInput,
) -> UnifiedForecastOutput:
    """Execute Prophet model with NSE/BSE holiday calendar and weekly/yearly seasonality."""
    forecaster = ProphetForecaster(use_nse_holidays=True)
    return forecaster.forecast(input_data)


@router.post(
    "/arima",
    response_model=UnifiedForecastOutput,
    summary="Generate Auto-ARIMA Forecast (Phase 6.4)",
)
async def run_arima_forecast(
    input_data: UnifiedForecastInput,
) -> UnifiedForecastOutput:
    """Execute non-seasonal Auto-ARIMA model with automated (p,d,q) detection."""
    forecaster = ARIMAForecaster()
    return forecaster.forecast(input_data)


@router.post(
    "/xgboost",
    response_model=UnifiedForecastOutput,
    summary="Generate XGBoost Forecast (Phase 6.5)",
)
async def run_xgboost_forecast(
    input_data: UnifiedForecastInput,
) -> UnifiedForecastOutput:
    """Execute non-linear XGBoost model with walk-forward validation and derived prediction bounds."""
    forecaster = XGBoostForecaster()
    return forecaster.forecast(input_data)


# -----------------------------------------------------------------------------
# 3. Forecast Validation Route (Phase 6.6)
# -----------------------------------------------------------------------------

class ValidateForecastPayload(UnifiedForecastInput):
    """Payload containing forecast output and historical series for validation."""

    forecast_output: UnifiedForecastOutput


@router.post(
    "/validate-forecast",
    response_model=ForecastValidationOutput,
    summary="Audit Forecast with Backtesting and Anomaly Detection (Phase 6.6)",
)
async def audit_forecast_output(
    payload: ValidateForecastPayload,
) -> ForecastValidationOutput:
    """Evaluate MAE/RMSE/MAPE, detect unrealistic growth or spikes, and compute quality/confidence scores."""
    validator = ForecastValidator()
    return validator.evaluate_forecast(
        forecast_output=payload.forecast_output,
        historical_series=payload.series,
    )


# -----------------------------------------------------------------------------
# 4. Scenario Engine Route (Phase 6.7)
# -----------------------------------------------------------------------------

class ScenarioRequestPayload(UnifiedForecastInput):
    """Payload for generating scenario presets."""

    base_forecast: UnifiedForecastOutput
    optimistic_assumptions: dict[str, float] | None = None
    pessimistic_assumptions: dict[str, float] | None = None


@router.post(
    "/scenarios",
    response_model=ScenarioEngineOutput,
    summary="Generate Baseline, Optimistic, and Pessimistic Scenarios (Phase 6.7)",
)
async def generate_scenarios(
    payload: ScenarioRequestPayload,
) -> ScenarioEngineOutput:
    """Construct preset futures with period-by-period delta comparisons."""
    engine = ScenarioEngine()
    return engine.generate_scenarios(
        base_forecast=payload.base_forecast,
        optimistic_assumptions=payload.optimistic_assumptions,
        pessimistic_assumptions=payload.pessimistic_assumptions,
    )


# -----------------------------------------------------------------------------
# 5. What-If Analysis Route (Phase 6.8)
# -----------------------------------------------------------------------------

@router.post(
    "/what-if",
    response_model=WhatIfAnalysisOutput,
    summary="Evaluate Single Ad-Hoc Business Change (Phase 6.8)",
)
async def analyze_what_if(
    payload: WhatIfAnalysisInput,
) -> WhatIfAnalysisOutput:
    """Predict revenue outcome, growth, and interval-derived risk from a single ad-hoc change."""
    engine = WhatIfAnalysisEngine()
    return engine.analyze(payload)


# -----------------------------------------------------------------------------
# 6. Business Forecast Agent Route (Phase 6.9)
# -----------------------------------------------------------------------------

@router.post(
    "/agent-select",
    response_model=BusinessForecastAgentOutput,
    summary="Intelligent Model Selection and Validation (Phase 6.9)",
)
async def run_business_forecast_agent(
    input_data: UnifiedForecastInput,
) -> BusinessForecastAgentOutput:
    """Automatically select best model using stated criteria, validate, and explain."""
    agent = BusinessForecastAgent()
    return agent.run(input_data)


# -----------------------------------------------------------------------------
# 7. End-to-End Forecast Pipeline Route (Phase 6.10)
# -----------------------------------------------------------------------------

class PipelineRequestPayload(UnifiedForecastInput):
    """Payload for executing the full end-to-end pipeline."""

    what_if_query: str = "marketing +15%"
    optimistic_assumptions: dict[str, float] | None = None
    pessimistic_assumptions: dict[str, float] | None = None


@router.post(
    "/pipeline",
    response_model=ForecastPipelineOutput,
    summary="Execute Full Predictive Intelligence Pipeline (Phase 6.10)",
)
async def run_full_forecast_pipeline(
    payload: PipelineRequestPayload,
    db: Session = Depends(get_db_session),
) -> ForecastPipelineOutput:
    """Orchestrate Model Selection -> Generation -> Validation -> Scenarios -> What-If -> Summary."""
    repo = ForecastRunRepository(db=db)
    pipeline = ForecastPipeline(run_repository=repo)

    return pipeline.run(
        input_data=payload,
        what_if_query=payload.what_if_query,
        optimistic_assumptions=payload.optimistic_assumptions,
        pessimistic_assumptions=payload.pessimistic_assumptions,
    )


@router.get(
    "/runs/{run_id}",
    summary="Retrieve Persisted Forecast Run Outcome",
)
async def get_persisted_forecast_run(
    run_id: str,
    db: Session = Depends(get_db_session),
) -> dict[str, Any]:
    """Fetch past forecast run details from PostgreSQL database."""
    repo = ForecastRunRepository(db=db)
    run = repo.get_run(run_id)
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Forecast run with ID '{run_id}' not found.",
        )
    return {
        "run_id": run.run_id,
        "model_type": run.model_type,
        "target": run.target,
        "params": run.params,
        "output": run.output,
        "created_at": run.created_at.isoformat() if run.created_at else None,
    }
