"""Forecast Validation and Multi-Model Ranking Framework (Phase 18.6.3).

Evaluates forecasting models (ARIMA, Prophet, XGBoost, LSTM) via empirical backtesting:
- Calculates MAE, RMSE, MAPE, SMAPE, R²
- Enforces minimum history requirements per model
- Multi-model evaluation and ranking
- Automatic selection of the best-performing model
- Forecast confidence score calculation
- Historical persistence in storage/forecasts/
- Forecast health dashboard generation
"""

from __future__ import annotations

import json
import logging
import math
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from backend.app.schemas.forecasting import (
    DataPoint,
    UnifiedForecastInput,
    UnifiedForecastOutput,
)
from backend.forecasting.arima_model import ARIMAForecaster
from backend.forecasting.prophet_model import ProphetForecaster
from backend.forecasting.xgboost_forecaster import XGBoostForecaster

logger = logging.getLogger(__name__)


@dataclass
class ModelMetricResult:
    model: str
    rank: int
    mae: float
    rmse: float
    mape: float
    smape: float
    r2: float
    confidence_score: float
    holdout_predictions: list[float]
    is_best: bool = False
    error_message: str | None = None


@dataclass
class ValidatedForecastResult:
    forecast: list[float]
    mae: float
    rmse: float
    mape: float
    smape: float
    r2: float
    confidence_score: float
    best_model: str
    target: str
    horizon: int
    frequency: str
    model_rankings: list[ModelMetricResult]
    models_skipped: list[str] = field(default_factory=list)
    forecast_points: list[dict[str, Any]] = field(default_factory=list)
    run_id: str = ""
    timestamp: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "forecast": [round(float(v), 2) for v in self.forecast],
            "mae": round(self.mae, 2),
            "rmse": round(self.rmse, 2),
            "mape": round(self.mape, 2),
            "smape": round(self.smape, 2),
            "r2": round(self.r2, 4),
            "confidence_score": round(self.confidence_score, 4),
            "best_model": self.best_model,
            "target": self.target,
            "horizon": self.horizon,
            "frequency": self.frequency,
            "model_rankings": [asdict(m) for m in self.model_rankings],
            "models_skipped": self.models_skipped,
            "forecast_points": self.forecast_points,
            "run_id": self.run_id,
            "timestamp": self.timestamp,
        }


def calculate_mae(actuals: np.ndarray, predictions: np.ndarray) -> float:
    return float(np.mean(np.abs(actuals - predictions)))


def calculate_rmse(actuals: np.ndarray, predictions: np.ndarray) -> float:
    return float(np.sqrt(np.mean((actuals - predictions) ** 2)))


def calculate_mape(actuals: np.ndarray, predictions: np.ndarray) -> float:
    denom = np.abs(actuals) + 1e-8
    return float(np.mean(np.abs((actuals - predictions) / denom)) * 100.0)


def calculate_smape(actuals: np.ndarray, predictions: np.ndarray) -> float:
    """Symmetric Mean Absolute Percentage Error — bounded [0, 200]."""
    denom = (np.abs(actuals) + np.abs(predictions)) / 2.0 + 1e-8
    return float(np.mean(np.abs(actuals - predictions) / denom) * 100.0)


def calculate_r2(actuals: np.ndarray, predictions: np.ndarray) -> float:
    ss_tot = float(np.sum((actuals - np.mean(actuals)) ** 2))
    ss_res = float(np.sum((actuals - predictions) ** 2))
    if ss_tot <= 1e-8:
        return 1.0 if ss_res <= 1e-8 else 0.0
    r2 = 1.0 - (ss_res / ss_tot)
    return float(np.clip(r2, -1.0, 1.0))


def calculate_confidence_score(mape: float, r2: float) -> float:
    """Calculate confidence score [0.0, 1.0] from MAPE and R²."""
    mape_score = max(0.0, min(1.0, 1.0 - (mape / 100.0)))
    r2_score = max(0.0, min(1.0, (r2 + 1.0) / 2.0))
    confidence = (mape_score * 0.6) + (r2_score * 0.4)
    return round(float(np.clip(confidence, 0.05, 0.99)), 4)


# Minimum history requirements per model (Phase 18.6.3)
MIN_HISTORY: dict[str, int] = {
    "prophet": 12,
    "arima": 24,
    "xgboost": 36,
    "lstm": 48,
}


class ForecastValidationFramework:
    """Multi-model empirical backtesting, validation, ranking, and persistence engine.

    Phase 18.6.3 upgrades:
    - Enforces minimum history per model (Prophet=12, ARIMA=24, XGBoost=36, LSTM=48)
    - SMAPE metric added
    - LSTM model support (requires 48+ points)
    - Forecast health dashboard generation
    - models_skipped tracking
    """

    def __init__(self, storage_dir: str | Path = "storage/forecasts") -> None:
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.arima = ARIMAForecaster()
        self.prophet = ProphetForecaster()
        self.xgboost = XGBoostForecaster()
        try:
            from backend.forecasting.lstm_model import LSTMForecaster
            self.lstm = LSTMForecaster()
        except Exception:
            self.lstm = None

    def run_validation_and_forecast(
        self,
        input_data: UnifiedForecastInput,
        run_id: str | None = None,
        holdout_ratio: float = 0.2,
    ) -> ValidatedForecastResult:
        """Backtest eligible models, rank them, select the best, and generate forecast."""
        import time

        run_id = run_id or str(uuid.uuid4())
        series = input_data.series
        n = len(series)

        if n < 8:
            raise ValueError(f"Series has {n} points; at least 8 points required for backtest validation.")

        # Determine holdout split size
        holdout_len = max(2, min(input_data.horizon, int(n * holdout_ratio)))
        train_series = series[:-holdout_len]
        test_series = series[-holdout_len:]
        actual_test_vals = np.array([float(dp.value) for dp in test_series], dtype=np.float64)

        train_input = UnifiedForecastInput(
            target=input_data.target,
            horizon=holdout_len,
            frequency=input_data.frequency,
            series=train_series,
            exogenous_regressors=input_data.exogenous_regressors,
        )

        # Models eligible based on minimum history (Phase 18.6.3)
        candidate_models = [m for m in ["arima", "prophet", "xgboost", "lstm"] if n >= MIN_HISTORY[m]]
        skipped_models = [m for m in ["arima", "prophet", "xgboost", "lstm"] if n < MIN_HISTORY[m]]
        if skipped_models:
            logger.info("Skipping models due to insufficient history (n=%d): %s", n, skipped_models)

        if not candidate_models:
            raise ValueError(
                f"Series has only {n} points. Minimum required: Prophet={MIN_HISTORY['prophet']}, "
                f"ARIMA={MIN_HISTORY['arima']}, XGBoost={MIN_HISTORY['xgboost']}, LSTM={MIN_HISTORY['lstm']}."
            )

        evaluated_metrics: list[ModelMetricResult] = []

        # Backtest each eligible candidate model
        for model_name in candidate_models:
            try:
                preds = self._predict_candidate(model_name, train_input, holdout_len)
                preds_arr = np.array(preds, dtype=np.float64)

                mae = calculate_mae(actual_test_vals, preds_arr)
                rmse = calculate_rmse(actual_test_vals, preds_arr)
                mape = calculate_mape(actual_test_vals, preds_arr)
                smape = calculate_smape(actual_test_vals, preds_arr)
                r2 = calculate_r2(actual_test_vals, preds_arr)
                conf = calculate_confidence_score(mape, r2)

                evaluated_metrics.append(ModelMetricResult(
                    model=model_name, rank=0,
                    mae=round(mae, 4), rmse=round(rmse, 4),
                    mape=round(mape, 4), smape=round(smape, 4),
                    r2=round(r2, 4), confidence_score=conf,
                    holdout_predictions=[round(float(v), 2) for v in preds_arr],
                ))
            except Exception as exc:
                logger.warning("Model %s backtest failed: %s", model_name, exc)
                evaluated_metrics.append(ModelMetricResult(
                    model=model_name, rank=99,
                    mae=9999.0, rmse=9999.0, mape=999.0, smape=200.0,
                    r2=-1.0, confidence_score=0.1,
                    holdout_predictions=[], error_message=str(exc),
                ))

        # Rank candidates: sort by MAPE, then RMSE, then -R²
        evaluated_metrics.sort(key=lambda m: (m.mape, m.rmse, -m.r2))
        for idx, item in enumerate(evaluated_metrics, start=1):
            item.rank = idx

        best_candidate = evaluated_metrics[0]
        best_candidate.is_best = True
        best_model_name = best_candidate.model

        # Generate production forecast using best model
        full_forecast_output = self._predict_candidate(best_model_name, input_data, input_data.horizon)

        forecast_points: list[dict[str, Any]] = [
            {"period": i, "predicted_value": round(float(val), 2), "model": best_model_name}
            for i, val in enumerate(full_forecast_output, start=1)
        ]

        timestamp_str = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        result = ValidatedForecastResult(
            forecast=[round(float(v), 2) for v in full_forecast_output],
            mae=round(best_candidate.mae, 2),
            rmse=round(best_candidate.rmse, 2),
            mape=round(best_candidate.mape, 2),
            smape=round(best_candidate.smape, 2),
            r2=round(best_candidate.r2, 4),
            confidence_score=round(best_candidate.confidence_score, 4),
            best_model=best_model_name,
            target=input_data.target,
            horizon=input_data.horizon,
            frequency=input_data.frequency,
            model_rankings=evaluated_metrics,
            models_skipped=skipped_models,
            forecast_points=forecast_points,
            run_id=run_id,
            timestamp=timestamp_str,
        )

        # Persist validation results
        output_path = self.storage_dir / f"{run_id}_validation.json"
        output_path.write_text(json.dumps(result.to_dict(), indent=2), encoding="utf-8")

        # Update forecast health dashboard
        self._update_health_dashboard(result)

        return result

    def _predict_candidate(
        self,
        model_name: str,
        input_data: UnifiedForecastInput,
        horizon: int,
    ) -> list[float]:
        """Execute specific forecaster candidate."""
        if model_name == "arima":
            out = self.arima.forecast(input_data)
            return out.forecast[:horizon]
        elif model_name == "prophet":
            out = self.prophet.forecast(input_data)
            return out.forecast[:horizon]
        elif model_name == "xgboost":
            out = self.xgboost.forecast(input_data)
            return out.forecast[:horizon]
        elif model_name == "lstm":
            if self.lstm is not None:
                out = self.lstm.forecast(input_data)
                return out.forecast[:horizon]
            from backend.forecasting.lstm_model import LSTMForecaster
            lstm = LSTMForecaster()
            out = lstm.forecast(input_data)
            return out.forecast[:horizon]
        else:
            raise ValueError(f"Unknown forecast model candidate: {model_name}")

    def _update_health_dashboard(self, result: ValidatedForecastResult) -> None:
        """Append result to forecast health dashboard history with ranking history."""
        dashboard_path = self.storage_dir / "forecast_health_dashboard.json"
        history: list[dict[str, Any]] = []
        if dashboard_path.exists():
            try:
                history = json.loads(dashboard_path.read_text(encoding="utf-8"))
            except Exception:
                history = []

        history.append({
            "run_id": result.run_id,
            "timestamp": result.timestamp,
            "best_model": result.best_model,
            "target": result.target,
            "horizon": result.horizon,
            "frequency": result.frequency,
            "mae": result.mae,
            "rmse": result.rmse,
            "mape": result.mape,
            "smape": result.smape,
            "r2": result.r2,
            "confidence_score": result.confidence_score,
            "models_evaluated": [m.model for m in result.model_rankings if m.error_message is None],
            "models_skipped": result.models_skipped,
            "model_metrics": [
                {
                    "model": m.model,
                    "rank": m.rank,
                    "mae": m.mae,
                    "rmse": m.rmse,
                    "mape": m.mape,
                    "smape": m.smape,
                    "r2": m.r2,
                    "confidence": m.confidence_score,
                    "is_best": m.is_best,
                }
                for m in result.model_rankings
            ],
        })
        dashboard_path.write_text(json.dumps(history, indent=2), encoding="utf-8")

    def get_health_dashboard(self) -> dict[str, Any]:
        """Return forecast accuracy dashboard, per-model breakdowns, ranking history, and trend analysis."""
        dashboard_path = self.storage_dir / "forecast_health_dashboard.json"
        if not dashboard_path.exists():
            return {
                "status": "no_runs",
                "total_runs": 0,
                "model_accuracy_table": [],
                "trend_analysis": {"trend_direction": "neutral", "recent_vs_all_mae_delta": 0.0},
                "ranking_history": [],
            }
        try:
            history: list[dict] = json.loads(dashboard_path.read_text(encoding="utf-8"))
        except Exception:
            return {"status": "error", "total_runs": 0, "model_accuracy_table": [], "trend_analysis": {}}

        if not history:
            return {"status": "no_runs", "total_runs": 0, "model_accuracy_table": [], "trend_analysis": {}}

        def avg(key: str, data: list[dict]) -> float:
            vals = [h[key] for h in data if key in h and isinstance(h[key], (int, float))]
            return round(sum(vals) / len(vals), 4) if vals else 0.0

        model_counts: dict[str, int] = {}
        for h in history:
            m = h.get("best_model", "unknown")
            model_counts[m] = model_counts.get(m, 0) + 1
        best_model = max(model_counts, key=lambda k: model_counts[k]) if model_counts else "N/A"

        # Model accuracy breakdown table (Model, MAE, RMSE, MAPE, R², Confidence)
        model_accum: dict[str, dict[str, list[float]]] = {}
        for h in history:
            for mm in h.get("model_metrics", []):
                m_name = mm.get("model")
                if not m_name or mm.get("mae", 9999) >= 9999:
                    continue
                if m_name not in model_accum:
                    model_accum[m_name] = {"mae": [], "rmse": [], "mape": [], "r2": [], "confidence": []}
                for k in ["mae", "rmse", "mape", "r2", "confidence"]:
                    if k in mm and isinstance(mm[k], (int, float)):
                        model_accum[m_name][k].append(float(mm[k]))

        accuracy_table = []
        for m_name, metrics in sorted(model_accum.items()):
            accuracy_table.append({
                "model": m_name,
                "mae": round(sum(metrics["mae"]) / max(len(metrics["mae"]), 1), 2),
                "rmse": round(sum(metrics["rmse"]) / max(len(metrics["rmse"]), 1), 2),
                "mape": round(sum(metrics["mape"]) / max(len(metrics["mape"]), 1), 2),
                "r2": round(sum(metrics["r2"]) / max(len(metrics["r2"]), 1), 4),
                "confidence": round(sum(metrics["confidence"]) / max(len(metrics["confidence"]), 1), 4),
                "total_evaluations": len(metrics["mae"]),
            })

        # Trend analysis (comparing recent 5 runs vs all historical)
        recent_window = history[-5:]
        all_mae = avg("mae", history)
        recent_mae = avg("mae", recent_window)
        mae_delta = round(recent_mae - all_mae, 4)

        if len(history) < 2:
            trend_dir = "insufficient_data"
        elif mae_delta < -0.05:
            trend_dir = "improving"
        elif mae_delta > 0.05:
            trend_dir = "degrading"
        else:
            trend_dir = "stable"

        trend_analysis = {
            "trend_direction": trend_dir,
            "overall_avg_mae": all_mae,
            "recent_avg_mae": recent_mae,
            "mae_delta": mae_delta,
            "recent_runs_count": len(recent_window),
        }

        return {
            "status": "healthy",
            "total_runs": len(history),
            "avg_mae": avg("mae", history),
            "avg_rmse": avg("rmse", history),
            "avg_mape": avg("mape", history),
            "avg_smape": avg("smape", history),
            "avg_r2": avg("r2", history),
            "avg_confidence": avg("confidence_score", history),
            "most_selected_model": best_model,
            "model_accuracy_table": accuracy_table,
            "trend_analysis": trend_analysis,
            "ranking_history": [
                {
                    "run_id": h.get("run_id"),
                    "timestamp": h.get("timestamp"),
                    "best_model": h.get("best_model"),
                    "rankings": h.get("model_metrics", []),
                }
                for h in history[-20:]
            ],
            "latest_run": history[-1] if history else None,
        }
