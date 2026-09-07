"""Phase 6.6 — Forecast Validator Service.

Implements rigorous evaluation of forecasting models via walk-forward backtesting
(MAE, RMSE, MAPE, R²), algorithmic anomaly detection (unrealistic growth, abnormal spikes,
invalid seasonal amplitude), and composite quality and confidence scoring.
"""

import logging
import uuid
from typing import Any

import numpy as np
import pandas as pd

from backend.app.schemas.forecasting import (
    DataPoint,
    ForecastValidationOutput,
    UnifiedForecastInput,
    UnifiedForecastOutput,
)

logger = logging.getLogger(__name__)


class ForecastValidator:
    """Enterprise validation gatekeeper for time-series forecasting outputs."""

    DEFAULT_SPIKE_Z_THRESHOLD = 3.0
    DEFAULT_GROWTH_MULTIPLIER_THRESHOLD = 3.0
    DEFAULT_SEASONAL_AMPLITUDE_TOLERANCE = 2.5

    def __init__(
        self,
        spike_z_threshold: float = DEFAULT_SPIKE_Z_THRESHOLD,
        growth_multiplier_threshold: float = DEFAULT_GROWTH_MULTIPLIER_THRESHOLD,
        seasonal_amplitude_tolerance: float = DEFAULT_SEASONAL_AMPLITUDE_TOLERANCE,
    ) -> None:
        self.spike_z_threshold = spike_z_threshold
        self.growth_multiplier_threshold = growth_multiplier_threshold
        self.seasonal_amplitude_tolerance = seasonal_amplitude_tolerance

    def evaluate_forecast(
        self,
        forecast_output: UnifiedForecastOutput,
        historical_series: list[DataPoint],
        backtest_actuals: list[float] | None = None,
        run_id: str | None = None,
    ) -> ForecastValidationOutput:
        """Run complete backtest scoring and anomaly detection suite on a forecast."""
        run_id = run_id or str(uuid.uuid4())
        model_type = forecast_output.model_type
        target = forecast_output.target
        forecast_pts = np.array(forecast_output.forecast, dtype=np.float64)

        logger.info(
            "Forecast validation initiated run_id=%s model=%s target=%s forecast_len=%d",
            run_id, model_type, target, len(forecast_pts)
        )

        hist_values = np.array([float(dp.value) for dp in historical_series], dtype=np.float64)

        # 1. Walk-forward backtest error metrics
        if backtest_actuals is not None and len(backtest_actuals) > 0:
            actuals_arr = np.array(backtest_actuals, dtype=np.float64)
            n_eval = min(len(forecast_pts), len(actuals_arr))
            f_eval = forecast_pts[:n_eval]
            a_eval = actuals_arr[:n_eval]
        else:
            # When full future actuals are not yet observed, evaluate on the tail of history (pseudo-holdout)
            tail_size = min(len(forecast_pts), max(5, int(len(hist_values) * 0.15)))
            a_eval = hist_values[-tail_size:]
            # Compare tail actuals against forecast terminal levels or historical step
            f_eval = forecast_pts[:tail_size]

        errors = a_eval - f_eval
        mae = float(np.mean(np.abs(errors)))
        rmse = float(np.sqrt(np.mean(errors ** 2)))
        denom = np.abs(a_eval) + 1e-8
        mape = float(np.mean(np.abs(errors) / denom))

        ss_tot = float(np.sum((a_eval - np.mean(a_eval)) ** 2))
        ss_res = float(np.sum(errors ** 2))
        r2 = float(1.0 - (ss_res / (ss_tot + 1e-8)))
        r2 = float(np.clip(r2, -1.0, 1.0))

        # 2. Algorithmic Anomaly Detection
        anomalies: list[dict[str, Any]] = []

        # 2A. Unrealistic Growth Check:
        # Period-over-period delta > growth_multiplier_threshold * historical max observed change
        if len(hist_values) > 1:
            hist_diffs = np.abs(np.diff(hist_values))
            max_hist_change = float(np.max(hist_diffs)) if len(hist_diffs) > 0 else 1.0
            max_allowed_change = max(max_hist_change * self.growth_multiplier_threshold, 1e-4)

            # Check initial transition from history to forecast
            first_step_change = abs(forecast_pts[0] - hist_values[-1])
            if first_step_change > max_allowed_change:
                anomalies.append({
                    "type": "unrealistic_growth",
                    "period_index": 0,
                    "date": forecast_output.dates[0] if forecast_output.dates else "",
                    "observed_change": float(first_step_change),
                    "threshold": float(max_allowed_change),
                    "description": f"Initial forecast step jumps by {first_step_change:.2f}, exceeding {self.growth_multiplier_threshold}x historical maximum ({max_allowed_change:.2f}).",
                })

            # Check consecutive forecast step changes
            if len(forecast_pts) > 1:
                fcast_diffs = np.abs(np.diff(forecast_pts))
                for step_idx, delta in enumerate(fcast_diffs):
                    if delta > max_allowed_change:
                        date_str = forecast_output.dates[step_idx + 1] if len(forecast_output.dates) > step_idx + 1 else ""
                        anomalies.append({
                            "type": "unrealistic_growth",
                            "period_index": step_idx + 1,
                            "date": date_str,
                            "observed_change": float(delta),
                            "threshold": float(max_allowed_change),
                            "description": f"Forecast period {step_idx + 1} growth delta {delta:.2f} exceeds allowable threshold {max_allowed_change:.2f}.",
                        })

        # 2B. Abnormal Spikes Check (Rolling Z-score > spike_z_threshold)
        # Combined tail of history + forecast to establish local rolling envelope
        window_size = min(7, len(hist_values))
        combined_series = np.concatenate([hist_values[-window_size:], forecast_pts])
        for i, val in enumerate(forecast_pts):
            local_window = combined_series[max(0, window_size + i - window_size) : window_size + i]
            local_mean = float(np.mean(local_window))
            local_std = float(np.std(local_window)) + 1e-8
            z_score = abs(val - local_mean) / local_std

            if z_score > self.spike_z_threshold:
                date_str = forecast_output.dates[i] if len(forecast_output.dates) > i else ""
                anomalies.append({
                    "type": "abnormal_spike",
                    "period_index": i,
                    "date": date_str,
                    "value": float(val),
                    "local_mean": local_mean,
                    "z_score": round(float(z_score), 2),
                    "threshold": self.spike_z_threshold,
                    "description": f"Forecast point at step {i} has z-score {z_score:.2f} > {self.spike_z_threshold} vs local mean {local_mean:.2f}.",
                })

        # 2C. Invalid Seasonality Amplitude Check
        if len(hist_values) >= 14 and len(forecast_pts) >= 7:
            hist_seasonal_amp = float(np.percentile(hist_values, 90) - np.percentile(hist_values, 10))
            fcast_seasonal_amp = float(np.percentile(forecast_pts, 90) - np.percentile(forecast_pts, 10))
            if hist_seasonal_amp > 1e-4:
                ratio = fcast_seasonal_amp / hist_seasonal_amp
                if ratio > self.seasonal_amplitude_tolerance:
                    anomalies.append({
                        "type": "invalid_seasonality",
                        "amplitude_ratio": round(ratio, 2),
                        "tolerance": self.seasonal_amplitude_tolerance,
                        "description": f"Forecast seasonal amplitude is {ratio:.2f}x historical amplitude, exceeding tolerance of {self.seasonal_amplitude_tolerance}x.",
                    })

        # 3. Quality Score & Confidence Score (0 - 100 Scale)
        # Accurate models with low MAPE (<5%) should naturally score 90-100
        mape_score = max(0.0, 100.0 - (mape * 150.0))
        r2_bonus = max(0.0, r2 * 10.0) if r2 > 0 else 0.0
        anomaly_penalty = min(50.0, len(anomalies) * 20.0)

        quality_score = float(np.clip(mape_score + r2_bonus - anomaly_penalty, 0.0, 100.0))
        confidence_score = float(np.clip(100.0 - (mape * 100.0) - (len(anomalies) * 25.0), 0.0, 100.0))

        # 4. Status Determination
        if len(anomalies) == 0 and mape <= 0.20:
            status = "PASSED"
        elif len(anomalies) <= 1 and mape <= 0.45:
            status = "WARNING"
        else:
            status = "FAILED"

        logger.info(
            "Forecast validation completed run_id=%s status=%s quality=%.1f confidence=%.1f anomalies=%d",
            run_id, status, quality_score, confidence_score, len(anomalies)
        )

        return ForecastValidationOutput(
            run_id=run_id,
            model_type=model_type,
            validation_status=status,
            mae=round(mae, 4),
            rmse=round(rmse, 4),
            mape=round(mape, 4),
            r2=round(r2, 4),
            anomalies_detected=anomalies,
            quality_score=round(quality_score, 1),
            confidence_score=round(confidence_score, 1),
        )
