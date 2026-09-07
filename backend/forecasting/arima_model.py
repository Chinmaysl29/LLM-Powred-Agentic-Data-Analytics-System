"""Phase 6.4 — ARIMA Forecasting Service.

Implements non-seasonal Auto-ARIMA forecasting for inventory, demand, and revenue,
auto-detecting (p,d,q) orders via pmdarima (ADF stationarity test and AIC minimization).
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

import numpy as np
import pandas as pd
import pmdarima as pm
from statsmodels.tsa.stattools import adfuller

from backend.app.core.exceptions import ForecastingDatasetValidationError, ForecastingError
from backend.app.schemas.forecasting import UnifiedForecastInput, UnifiedForecastOutput

logger = logging.getLogger(__name__)


class ARIMAForecaster:
    """Forecasting service leveraging non-seasonal Auto-ARIMA."""

    SUPPORTED_TARGETS = {"inventory", "demand", "revenue"}
    MIN_OBSERVATIONS = 30

    def __init__(
        self,
        max_p: int = 5,
        max_d: int = 2,
        max_q: int = 5,
        stepwise: bool = True,
    ) -> None:
        self.max_p = max_p
        self.max_d = max_d
        self.max_q = max_q
        self.stepwise = stepwise

    def forecast(self, input_data: UnifiedForecastInput, run_id: str | None = None) -> UnifiedForecastOutput:
        """Fit non-seasonal Auto-ARIMA model and emit UnifiedForecastOutput."""
        run_id = run_id or str(uuid.uuid4())
        target = input_data.target.lower()
        horizon = input_data.horizon
        confidence_level = input_data.confidence_level

        logger.info(
            "ARIMA forecast initiated run_id=%s target=%s frequency=%s horizon=%d confidence=%.2f",
            run_id, target, input_data.frequency, horizon, confidence_level
        )

        # 1. Enforce minimum history (>= 30 points)
        series_len = len(input_data.series)
        if series_len < self.MIN_OBSERVATIONS:
            logger.warning(
                "ARIMA rejected series for insufficient history: run_id=%s found=%d required=%d",
                run_id, series_len, self.MIN_OBSERVATIONS
            )
            raise ForecastingDatasetValidationError(
                f"ARIMA requires at least {self.MIN_OBSERVATIONS} historical data points; found {series_len}."
            )

        # 2. Extract series into ordered numeric array and dates
        sorted_series = sorted(input_data.series, key=lambda x: x.date)
        values = np.array([float(dp.value) for dp in sorted_series], dtype=np.float64)
        last_date = pd.to_datetime(sorted_series[-1].date)

        # 3. Check stationarity via Augmented Dickey-Fuller (ADF) test
        try:
            adf_result = adfuller(values)
            adf_pvalue = float(adf_result[1])
            is_stationary = adf_pvalue < 0.05
        except Exception:
            adf_pvalue = None
            is_stationary = False

        # 4. Fit pmdarima.auto_arima with explicit non-seasonal constraint
        # 4. Fit pmdarima.auto_arima with explicit non-seasonal constraint
        alpha = 1.0 - confidence_level
        try:
            model = pm.auto_arima(
                values,
                start_p=0,
                start_q=0,
                max_p=self.max_p,
                max_d=self.max_d,
                max_q=self.max_q,
                seasonal=False,  # EXPLICITLY NON-SEASONAL as mandated
                test="adf",
                information_criterion="aic",
                stepwise=self.stepwise,
                error_action="ignore",
                suppress_warnings=True,
            )
            forecast_vals, conf_int = model.predict(n_periods=horizon, return_conf_int=True, alpha=alpha)
            p, d, q = model.order
            order_dict = {"p": int(p), "d": int(d), "q": int(q)}
            aic_val = float(model.aic())
            bic_val = float(model.bic())
        except Exception as e:
            logger.warning("pmdarima.auto_arima encountered error (%s); falling back to statsmodels ARIMA", e)
            from statsmodels.tsa.arima.model import ARIMA
            try:
                sm_model = ARIMA(values, order=(1, 1, 0)).fit()
                pred_res = sm_model.get_forecast(steps=horizon)
                forecast_vals = pred_res.predicted_mean
                ci = pred_res.conf_int(alpha=alpha)
                conf_int = ci.values if hasattr(ci, "values") else ci
                order_dict = {"p": 1, "d": 1, "q": 0}
                aic_val = float(sm_model.aic)
                bic_val = float(sm_model.bic)
            except Exception as e2:
                logger.error("ARIMA fitting failed run_id=%s: %s", run_id, e2, exc_info=True)
                raise ForecastingError(f"ARIMA optimization error: {e2}")

        # 5. Generate future dates matching frequency
        freq_lower = input_data.frequency.lower()
        freq_alias = "D" if freq_lower == "daily" else ("W" if freq_lower == "weekly" else "MS")
        future_dates = pd.date_range(start=last_date, periods=horizon + 1, freq=freq_alias)[1:]
        date_strs = [dt.strftime("%Y-%m-%d") for dt in future_dates]

        forecast_list = [float(x) for x in forecast_vals]
        lower_list = [float(x[0]) for x in conf_int]
        upper_list = [float(x[1]) for x in conf_int]

        # Enforce mathematical bound consistency (lower <= forecast <= upper)
        for i in range(len(forecast_list)):
            if lower_list[i] > forecast_list[i]:
                lower_list[i] = forecast_list[i]
            if upper_list[i] < forecast_list[i]:
                upper_list[i] = forecast_list[i]

        # 7. Model diagnostics
        diagnostics = {
            "order": order_dict,
            "seasonal": False,
            "limitation": "Explicitly non-seasonal ARIMA; seasonal decisions belong to Business Forecast Agent",
            "aic": aic_val,
            "bic": bic_val,
            "adf_pvalue": adf_pvalue,
            "is_stationary_prior": is_stationary,
            "observations_fitted": series_len,
        }

        logger.info(
            "ARIMA forecast completed run_id=%s order=%s generated=%d points",
            run_id, order_dict, len(forecast_list)
        )

        return UnifiedForecastOutput(
            model_type="arima",
            target=target,
            frequency=input_data.frequency,
            generated_at=datetime.now(timezone.utc).isoformat(),
            horizon=horizon,
            confidence_level=confidence_level,
            dates=date_strs,
            forecast=forecast_list,
            lower_bound=lower_list,
            upper_bound=upper_list,
            diagnostics=diagnostics,
        )
