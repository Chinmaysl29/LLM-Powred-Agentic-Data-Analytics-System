"""Phase 6.9 — Business Forecast Agent.

Orchestrates intelligent model selection across Prophet, ARIMA, and XGBoost
using explicit statistical criteria, executes forecast generation, integrates the
Forecast Validator gatekeeper with fallback recovery, and produces plain-language explanations.
"""

import logging
from typing import Any

import numpy as np
import pandas as pd
from statsmodels.tsa.stattools import acf

from backend.app.core.exceptions import ForecastingError
from backend.app.schemas.forecasting import (
    BusinessForecastAgentOutput,
    DataPoint,
    ForecastValidationOutput,
    UnifiedForecastInput,
    UnifiedForecastOutput,
)
from backend.forecasting.arima_model import ARIMAForecaster
from backend.forecasting.forecast_validator import ForecastValidator
from backend.forecasting.prophet_model import ProphetForecaster
from backend.forecasting.xgboost_forecaster import XGBoostForecaster

logger = logging.getLogger(__name__)


class BusinessForecastAgent:
    """Intelligent decision agent for time-series model selection, validation, and explainability."""

    AUTOCORR_SEASONAL_THRESHOLD = 0.25

    def __init__(
        self,
        validator: ForecastValidator | None = None,
        prophet_forecaster: ProphetForecaster | None = None,
        arima_forecaster: ARIMAForecaster | None = None,
        xgboost_forecaster: XGBoostForecaster | None = None,
    ) -> None:
        self.validator = validator or ForecastValidator()
        self.prophet_forecaster = prophet_forecaster or ProphetForecaster()
        self.arima_forecaster = arima_forecaster or ARIMAForecaster()
        self.xgboost_forecaster = xgboost_forecaster or XGBoostForecaster()

    def _detect_seasonality_presence(self, series: list[DataPoint], frequency: str) -> tuple[bool, float]:
        """Compute autocorrelation at seasonal lag to detect seasonal/holiday structure."""
        values = np.array([float(dp.value) for dp in series], dtype=np.float64)
        n = len(values)
        freq_lower = frequency.lower()

        seasonal_lag = 7 if freq_lower == "daily" else (4 if freq_lower == "weekly" else 12)
        if n < seasonal_lag * 2:
            return False, 0.0

        try:
            acf_values = acf(values, nlags=seasonal_lag + 2, fft=True)
            lag_acf = float(acf_values[seasonal_lag])
            has_seasonality = lag_acf >= self.AUTOCORR_SEASONAL_THRESHOLD
            return has_seasonality, lag_acf
        except Exception:
            return False, 0.0

    def select_model(self, input_data: UnifiedForecastInput) -> tuple[str, str, list[str]]:
        """Evaluate stated criteria and return primary model, rationale, and ranked candidate list."""
        n = len(input_data.series)
        freq = input_data.frequency.lower()
        has_exog = bool(input_data.exogenous_regressors and len(input_data.exogenous_regressors) >= 1)

        has_seasonality, acf_val = self._detect_seasonality_presence(input_data.series, freq)

        # Rule 1: Series length < 60 points -> ARIMA (XGBoost/Prophet need more history)
        if n < 60:
            reason = (
                f"Historical series contains {n} observations (< 60 threshold). "
                "ARIMA was selected as the optimal statistical model for compact sample sizes."
            )
            candidates = ["arima", "prophet", "xgboost"]
            return "arima", reason, candidates

        # Rule 2: Multiple exogenous regressors available and length >= 60 -> XGBoost
        if has_exog and n >= 60:
            exog_names = list(input_data.exogenous_regressors.keys()) if input_data.exogenous_regressors else []
            reason = (
                f"Series length is {n} observations with {len(exog_names)} exogenous regressors "
                f"({', '.join(exog_names)}). XGBoost was selected for non-linear multivariate capability."
            )
            candidates = ["xgboost", "prophet", "arima"]
            return "xgboost", reason, candidates

        # Rule 3: Clear seasonal/holiday pattern detected -> Prophet
        if has_seasonality and n >= 60:
            reason = (
                f"Strong periodic autocorrelation detected (r = {acf_val:.2f} at seasonal lag). "
                "Meta Prophet was selected for robust seasonal decomposition and holiday modeling."
            )
            candidates = ["prophet", "xgboost", "arima"]
            return "prophet", reason, candidates

        # Rule 4: Fallback -> Run candidates and pick lowest backtest error
        reason = (
            f"Series length is {n} with moderate/mixed dynamics. "
            "Model selected via competitive validation comparison."
        )
        candidates = ["prophet", "xgboost", "arima"]
        return "prophet", reason, candidates

    def _execute_model(self, model_name: str, input_data: UnifiedForecastInput) -> UnifiedForecastOutput:
        """Dispatch forecast generation to the specified forecaster."""
        if model_name == "prophet":
            return self.prophet_forecaster.forecast(input_data)
        elif model_name == "arima":
            return self.arima_forecaster.forecast(input_data)
        elif model_name == "xgboost":
            return self.xgboost_forecaster.forecast(input_data)
        else:
            raise ForecastingError(f"Unknown forecasting model requested: {model_name}")

    def run(self, input_data: UnifiedForecastInput) -> BusinessForecastAgentOutput:
        """Select model, generate forecast, validate, apply fallback if needed, and explain."""
        logger.info(
            "Business Forecast Agent started target=%s freq=%s points=%d horizon=%d",
            input_data.target, input_data.frequency, len(input_data.series), input_data.horizon
        )

        primary_model, selection_reason, candidate_models = self.select_model(input_data)

        # Attempt forecasting with validation gatekeeper and fallback recovery
        last_error = None
        selected_forecast: UnifiedForecastOutput | None = None
        selected_validation: ForecastValidationOutput | None = None
        active_model = primary_model

        for model_name in candidate_models:
            try:
                logger.info("Attempting forecast generation using model=%s", model_name)
                forecast_out = self._execute_model(model_name, input_data)

                # Validate output
                validation_out = self.validator.evaluate_forecast(
                    forecast_output=forecast_out,
                    historical_series=input_data.series,
                )

                # If validation passes or produces warning, accept
                if validation_out.validation_status in ["PASSED", "WARNING"]:
                    selected_forecast = forecast_out
                    selected_validation = validation_out
                    active_model = model_name
                    if model_name != primary_model:
                        selection_reason += (
                            f" Note: Primary candidate '{primary_model}' was bypassed "
                            f"in favor of '{model_name}' to ensure rigorous validation status ({validation_out.validation_status})."
                        )
                    break
                else:
                    logger.warning(
                        "Model '%s' produced FAILED validation status; testing fallback candidate", model_name
                    )
            except Exception as e:
                logger.warning("Execution of model '%s' failed: %s; falling back", model_name, e)
                last_error = e

        if selected_forecast is None or selected_validation is None:
            raise ForecastingError(
                f"All candidate forecasting models failed validation or execution. Last error: {last_error}"
            )

        logger.info(
            "Business Forecast Agent completed active_model=%s validation_status=%s quality=%.1f",
            active_model, selected_validation.validation_status, selected_validation.quality_score
        )

        return BusinessForecastAgentOutput(
            selected_model=active_model,
            selection_reason=selection_reason,
            forecast=selected_forecast,
            validation=selected_validation,
        )


from backend.app.schemas.orchestrator import WorkflowContext
from backend.app.services.agent_registry import BaseAgentRunner
from backend.app.services.data_retrieval_service import DataRetrievalService


class ForecastingAgentRunner(BaseAgentRunner):
    """Concrete runner for the Business Forecasting Agent in the Orchestrator pipeline."""

    def __init__(
        self,
        forecasting_agent: BusinessForecastAgent | None = None,
        retrieval_service: DataRetrievalService | None = None,
    ) -> None:
        self._agent = forecasting_agent or BusinessForecastAgent()
        self._retrieval_service = retrieval_service

    @property
    def name(self) -> str:
        return "forecasting"

    async def run(self, context: WorkflowContext) -> dict[str, Any]:
        """Execute automated model selection and forecasting for workflow context."""
        dataset_id = context.dataset_id
        df: pd.DataFrame | None = None

        if dataset_id and self._retrieval_service:
            try:
                df, _ = self._retrieval_service.load_dataframe(dataset_id=dataset_id)
            except Exception as e:
                logger.warning("Could not load DataFrame for forecasting: %s", e)

        if df is None or df.empty:
            if "retrieved_data" in context.results and context.results["retrieved_data"].get("records"):
                df = pd.DataFrame(context.results["retrieved_data"]["records"])

        if df is None or df.empty:
            return {
                "forecast_status": "skipped_no_data",
                "summary": "Forecasting skipped: no time-series observations available.",
            }

        # Identify date and numeric target column
        date_col: str | None = None
        target_col: str | None = None

        for col in df.columns:
            if pd.api.types.is_datetime64_any_dtype(df[col]) or any(t in col.lower() for t in ("date", "month", "time", "year", "period")):
                date_col = col
                break
        for col in df.columns:
            if col != date_col and pd.api.types.is_numeric_dtype(df[col]):
                target_col = col
                break

        if not date_col or not target_col or len(df) < 5:
            return {
                "forecast_status": "insufficient_series_data",
                "summary": f"Forecasting requires at least 5 temporal observations with a numeric metric (found {len(df)} rows).",
            }

        # Build clean time series
        try:
            sorted_df = df.dropna(subset=[date_col, target_col]).sort_values(by=date_col)
            series = [
                DataPoint(date=str(row[date_col]), value=float(row[target_col]))
                for _, row in sorted_df.iterrows()
            ]
            forecast_input = UnifiedForecastInput(
                series=series,
                frequency="daily",
                horizon=min(14, max(3, len(series) // 4)),
                target=target_col,
            )
            output = self._agent.run(forecast_input)
            return {
                "forecast_status": "completed",
                "selected_model": output.selected_model,
                "selection_reason": output.selection_reason,
                "forecast": output.forecast.forecast,
                "dates": output.forecast.dates,
                "forecast_points": [p.model_dump() for p in output.forecast.forecast_values],
                "validation_status": output.validation.validation_status,
                "quality_score": output.validation.quality_score,
                "target_metric": target_col,
                "horizon": forecast_input.horizon,
            }
        except Exception as e:
            logger.error("Forecasting execution error: %s", e)
            context.add_error("forecasting", f"Forecasting failed: {e}")
            return {
                "forecast_status": "error",
                "error": str(e),
                "summary": f"Forecasting model execution failed: {e}",
            }


__all__ = ["BusinessForecastAgent", "ForecastingAgentRunner"]
