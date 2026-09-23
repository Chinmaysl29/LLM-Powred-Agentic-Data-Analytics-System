"""Phase 6.3 — Prophet Forecasting Service.

Implements Meta Prophet forecasting for sales, revenue, and demand metrics,
configured with weekly/yearly seasonality, Indian NSE/BSE trading holiday calendars,
confidence interval widths, and changepoint diagnostics.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

import numpy as np
import pandas as pd
from prophet import Prophet

from backend.app.core.exceptions import ForecastingDatasetValidationError, ForecastingError
from backend.app.schemas.forecasting import UnifiedForecastInput, UnifiedForecastOutput

logger = logging.getLogger(__name__)


class NSETradingCalendar:
    """Trading holiday calendar for the National Stock Exchange (NSE) and Bombay Stock Exchange (BSE)."""

    # Static fixed-date Indian market holidays
    FIXED_HOLIDAYS = [
        ("01-26", "Republic Day"),
        ("04-14", "Dr. Ambedkar Jayanti"),
        ("05-01", "Maharashtra Day"),
        ("08-15", "Independence Day"),
        ("10-02", "Mahatma Gandhi Jayanti"),
        ("12-25", "Christmas"),
    ]

    # Major variable holidays for Indian financial markets across recent and future years
    VARIABLE_HOLIDAYS: dict[int, list[tuple[str, str]]] = {
        2023: [
            ("03-07", "Holi"),
            ("03-30", "Ram Navami"),
            ("04-04", "Mahavir Jayanti"),
            ("04-07", "Good Friday"),
            ("04-22", "Eid-ul-Fitr"),
            ("06-29", "Bakri Id"),
            ("09-19", "Ganesh Chaturthi"),
            ("10-24", "Dussehra"),
            ("11-14", "Diwali Balipratipada"),
            ("11-27", "Gurunanak Jayanti"),
        ],
        2024: [
            ("01-22", "Special Holiday"),
            ("03-08", "Mahashivratri"),
            ("03-25", "Holi"),
            ("03-29", "Good Friday"),
            ("04-11", "Eid-ul-Fitr"),
            ("04-17", "Ram Navami"),
            ("06-17", "Bakri Id"),
            ("07-17", "Muharram"),
            ("11-01", "Diwali Laxmi Pujan"),
            ("11-15", "Gurunanak Jayanti"),
        ],
        2025: [
            ("02-26", "Mahashivratri"),
            ("03-14", "Holi"),
            ("03-31", "Eid-ul-Fitr"),
            ("04-18", "Good Friday"),
            ("06-07", "Bakri Id"),
            ("07-06", "Muharram"),
            ("08-27", "Ganesh Chaturthi"),
            ("10-02", "Dussehra"),
            ("10-21", "Diwali Laxmi Pujan"),
            ("11-05", "Gurunanak Jayanti"),
        ],
        2026: [
            ("02-15", "Mahashivratri"),
            ("03-04", "Holi"),
            ("03-20", "Eid-ul-Fitr"),
            ("04-03", "Good Friday"),
            ("05-27", "Bakri Id"),
            ("06-26", "Muharram"),
            ("09-15", "Ganesh Chaturthi"),
            ("10-20", "Dussehra"),
            ("11-08", "Diwali Laxmi Pujan"),
            ("11-24", "Gurunanak Jayanti"),
        ],
    }

    @classmethod
    def get_holiday_dataframe(cls, start_year: int = 2020, end_year: int = 2030) -> pd.DataFrame:
        """Construct Prophet-compliant holiday DataFrame for NSE/BSE trading holidays."""
        records: list[dict[str, str]] = []

        for yr in range(start_year, end_year + 1):
            # Fixed annual holidays
            for mm_dd, name in cls.FIXED_HOLIDAYS:
                records.append({
                    "holiday": f"NSE_{name.replace(' ', '_')}",
                    "ds": f"{yr}-{mm_dd}",
                    "lower_window": 0,
                    "upper_window": 0,
                })

            # Variable holidays
            if yr in cls.VARIABLE_HOLIDAYS:
                for mm_dd, name in cls.VARIABLE_HOLIDAYS[yr]:
                    records.append({
                        "holiday": f"NSE_{name.replace(' ', '_')}",
                        "ds": f"{yr}-{mm_dd}",
                        "lower_window": 0,
                        "upper_window": 0,
                    })

        df = pd.DataFrame(records)
        df["ds"] = pd.to_datetime(df["ds"])
        return df.drop_duplicates(subset=["holiday", "ds"]).sort_values("ds").reset_index(drop=True)


class ProphetForecaster:
    """Forecasting service leveraging Meta Prophet for business metric projection."""

    SUPPORTED_TARGETS = {"sales", "revenue", "demand"}

    def __init__(
        self,
        weekly_seasonality: bool | str = True,
        yearly_seasonality: bool | str = True,
        daily_seasonality: bool | str = False,
        use_nse_holidays: bool = True,
    ) -> None:
        self.weekly_seasonality = weekly_seasonality
        self.yearly_seasonality = yearly_seasonality
        self.daily_seasonality = daily_seasonality
        self.use_nse_holidays = use_nse_holidays

    def forecast(self, input_data: UnifiedForecastInput, run_id: str | None = None) -> UnifiedForecastOutput:
        """Fit Prophet model and emit UnifiedForecastOutput."""
        run_id = run_id or str(uuid.uuid4())
        target = input_data.target.lower()
        horizon = input_data.horizon
        confidence_level = input_data.confidence_level

        logger.info(
            "Prophet forecast initiated run_id=%s target=%s frequency=%s horizon=%d confidence=%.2f",
            run_id, target, input_data.frequency, horizon, confidence_level
        )

        # 1. Minimum historical length enforcement (>= 2 full seasonal cycles)
        series_len = len(input_data.series)
        freq_lower = input_data.frequency.lower()

        min_required = 14 if freq_lower == "daily" else (8 if freq_lower == "weekly" else 6)
        if series_len < min_required:
            logger.warning(
                "Prophet rejected series for insufficient history: run_id=%s found=%d required=%d",
                run_id, series_len, min_required
            )
            raise ForecastingDatasetValidationError(
                f"Prophet requires at least 2 full seasonal cycles ({min_required} points for {input_data.frequency}); found {series_len}."
            )

        # 2. Build training DataFrame (ds, y)
        df = pd.DataFrame([{"ds": pd.to_datetime(dp.date), "y": float(dp.value)} for dp in input_data.series])
        df = df.dropna().sort_values("ds").reset_index(drop=True)

        if df["y"].nunique() <= 1 and len(df) > 3:
            logger.warning("Prophet target series is flat: run_id=%s", run_id)

        # 3. Add exogenous regressors if provided
        exog_cols: list[str] = []
        if input_data.exogenous_regressors:
            for exog_name, exog_vals in input_data.exogenous_regressors.items():
                if len(exog_vals) == len(df):
                    df[exog_name] = exog_vals
                    exog_cols.append(exog_name)

        # 4. Prepare NSE/BSE Holidays
        holidays_df = None
        if self.use_nse_holidays:
            min_yr = df["ds"].dt.year.min() - 1
            max_yr = df["ds"].dt.year.max() + 3
            holidays_df = NSETradingCalendar.get_holiday_dataframe(min_yr, max_yr)

        # 5. Initialize and fit Prophet
        # Map frequency to seasonality defaults
        is_daily = freq_lower == "daily"
        weekly_s = self.weekly_seasonality if is_daily else False
        yearly_s = self.yearly_seasonality if len(df) >= (60 if is_daily else 12) else False

        model = Prophet(
            interval_width=confidence_level,
            weekly_seasonality=weekly_s,
            yearly_seasonality=yearly_s,
            daily_seasonality=self.daily_seasonality,
            holidays=holidays_df,
        )

        for col in exog_cols:
            model.add_regressor(col)

        try:
            model.fit(df)
        except Exception as e:
            logger.error("Prophet fitting failed run_id=%s: %s", run_id, e, exc_info=True)
            raise ForecastingError(f"Prophet fitting error: {e}")

        # 6. Construct future dataframe
        freq_alias = "D" if freq_lower == "daily" else ("W" if freq_lower == "weekly" else "MS")
        future = model.make_future_dataframe(periods=horizon, freq=freq_alias, include_history=False)

        # Supply future exogenous regressors if present
        if exog_cols:
            for col in exog_cols:
                if input_data.future_exogenous and col in input_data.future_exogenous:
                    future[col] = input_data.future_exogenous[col][:len(future)]
                else:
                    # Forward-fill latest historical value as baseline assumption
                    future[col] = df[col].iloc[-1]

        # 7. Predict
        forecast_df = model.predict(future)

        forecast_vals = [float(x) for x in forecast_df["yhat"].tolist()]
        lower_vals = [float(x) for x in forecast_df["yhat_lower"].tolist()]
        upper_vals = [float(x) for x in forecast_df["yhat_upper"].tolist()]
        date_strs = [dt.strftime("%Y-%m-%d") for dt in forecast_df["ds"]]

        # Enforce mathematical bound consistency (lower <= forecast <= upper)
        for i in range(len(forecast_vals)):
            if lower_vals[i] > forecast_vals[i]:
                lower_vals[i] = forecast_vals[i]
            if upper_vals[i] < forecast_vals[i]:
                upper_vals[i] = forecast_vals[i]

        # 8. Diagnostics
        changepoints = [cp.strftime("%Y-%m-%d") for cp in model.changepoints] if hasattr(model, "changepoints") else []
        diagnostics = {
            "changepoints": changepoints,
            "changepoint_count": len(changepoints),
            "weekly_seasonality": bool(weekly_s),
            "yearly_seasonality": bool(yearly_s),
            "nse_holidays_applied": self.use_nse_holidays,
            "exogenous_regressors": exog_cols,
        }

        logger.info(
            "Prophet forecast completed run_id=%s target=%s generated=%d points",
            run_id, target, len(forecast_vals)
        )

        return UnifiedForecastOutput(
            model_type="prophet",
            target=target,
            frequency=input_data.frequency,
            generated_at=datetime.now(timezone.utc).isoformat(),
            horizon=horizon,
            confidence_level=confidence_level,
            dates=date_strs,
            forecast=forecast_vals,
            lower_bound=lower_vals,
            upper_bound=upper_vals,
            diagnostics=diagnostics,
        )
