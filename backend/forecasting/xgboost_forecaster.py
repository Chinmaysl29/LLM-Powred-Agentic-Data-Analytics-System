"""Phase 6.5 — XGBoost Forecasting Service.

Implements non-linear gradient-boosted time-series forecasting with lag,
rolling, trend, and calendar feature engineering, walk-forward validation splits,
multivariate exogenous regressors, residual-based prediction intervals, and feature importance.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

import numpy as np
import pandas as pd
from xgboost import XGBRegressor

from backend.app.core.exceptions import ForecastingDatasetValidationError, ForecastingError
from backend.app.schemas.forecasting import UnifiedForecastInput, UnifiedForecastOutput

logger = logging.getLogger(__name__)


class XGBoostForecaster:
    """Forecasting service leveraging XGBoost for non-linear time-series projection."""

    SUPPORTED_TARGETS = {"sales", "revenue", "demand", "inventory"}
    MIN_OBSERVATIONS = 60

    def __init__(
        self,
        n_estimators: int = 150,
        max_depth: int = 5,
        learning_rate: float = 0.05,
        n_splits: int = 3,
        custom_lags: list[int] | None = None,
        custom_windows: list[int] | None = None,
    ) -> None:
        self.n_estimators = n_estimators
        self.max_depth = max_depth
        self.learning_rate = learning_rate
        self.n_splits = n_splits
        self.custom_lags = custom_lags
        self.custom_windows = custom_windows

    def _build_feature_matrix(
        self,
        df: pd.DataFrame,
        frequency: str,
        exog_cols: list[str],
    ) -> tuple[pd.DataFrame, list[str]]:
        """Engineer lag, rolling, trend, calendar, and exogenous features."""
        feat_df = df.copy()
        target = feat_df["y"]
        freq_lower = frequency.lower()

        # 1. Trend feature (linear index)
        feat_df["trend_step"] = np.arange(len(feat_df), dtype=np.float64)

        # 2. Calendar features
        ds = feat_df["ds"]
        feat_df["month"] = ds.dt.month
        feat_df["day_of_week"] = ds.dt.dayofweek
        feat_df["quarter"] = ds.dt.quarter

        # 3. Lags (frequency-aware)
        if self.custom_lags:
            lags = self.custom_lags
        else:
            lags = [1, 2, 3, 7, 14, 30] if freq_lower == "daily" else ([1, 2, 4, 8] if freq_lower == "weekly" else [1, 2, 3, 6])

        for lag in lags:
            if lag < len(feat_df):
                feat_df[f"lag_{lag}"] = target.shift(lag)

        # 4. Rolling statistics (computed on shifted target to prevent lookahead leakage)
        if self.custom_windows:
            windows = self.custom_windows
        else:
            windows = [7, 14, 30] if freq_lower == "daily" else ([2, 4, 8] if freq_lower == "weekly" else [2, 3, 6])

        y_shifted = target.shift(1)
        for w in windows:
            if w < len(feat_df):
                feat_df[f"rolling_mean_{w}"] = y_shifted.rolling(window=w, min_periods=1).mean()
                feat_df[f"rolling_std_{w}"] = y_shifted.rolling(window=w, min_periods=1).std().fillna(0.0)

        # Drop initial rows with NaNs resulting from maximum lag
        feature_cols = [c for c in feat_df.columns if c not in ["ds", "y"]]
        # Fill remaining lag NaNs with backward fill so training retains points
        feat_df[feature_cols] = feat_df[feature_cols].bfill().fillna(0.0)

        return feat_df, feature_cols

    def forecast(self, input_data: UnifiedForecastInput, run_id: str | None = None) -> UnifiedForecastOutput:
        """Execute walk-forward split, train XGBoost, extrapolate horizon, and compute intervals."""
        run_id = run_id or str(uuid.uuid4())
        target_name = input_data.target.lower()
        horizon = input_data.horizon
        confidence_level = input_data.confidence_level

        logger.info(
            "XGBoost forecast initiated run_id=%s target=%s frequency=%s horizon=%d confidence=%.2f",
            run_id, target_name, input_data.frequency, horizon, confidence_level
        )

        # 1. Enforce minimum history (>= 60 points for daily/weekly, >= 24 points for monthly)
        series_len = len(input_data.series)
        min_required = 24 if input_data.frequency.lower() == "monthly" else self.MIN_OBSERVATIONS
        if series_len < min_required:
            logger.warning(
                "XGBoost rejected series for insufficient history: run_id=%s found=%d required=%d",
                run_id, series_len, min_required
            )
            raise ForecastingDatasetValidationError(
                f"XGBoost requires at least {min_required} historical data points; found {series_len}."
            )


        # 2. Build base DataFrame
        sorted_series = sorted(input_data.series, key=lambda x: x.date)
        df = pd.DataFrame([{"ds": pd.to_datetime(dp.date), "y": float(dp.value)} for dp in sorted_series])
        df = df.dropna().sort_values("ds").reset_index(drop=True)

        exog_cols: list[str] = []
        if input_data.exogenous_regressors:
            for exog_name, exog_vals in input_data.exogenous_regressors.items():
                if len(exog_vals) == len(df):
                    df[exog_name] = [float(v) for v in exog_vals]
                    exog_cols.append(exog_name)

        # 3. Engineer features
        feat_df, feature_cols = self._build_feature_matrix(df, input_data.frequency, exog_cols)

        # 4. Walk-forward validation split (hold out last fold for residual estimation)
        # Hold out a test window equal to min(horizon, 15% of series)
        val_size = max(5, min(horizon, int(len(feat_df) * 0.2)))
        train_df = feat_df.iloc[:-val_size]
        val_df = feat_df.iloc[-val_size:]

        X_train, y_train = train_df[feature_cols], train_df["y"]
        X_val, y_val = val_df[feature_cols], val_df["y"]

        # Train model on walk-forward training fold
        model = XGBRegressor(
            n_estimators=self.n_estimators,
            max_depth=self.max_depth,
            learning_rate=self.learning_rate,
            random_state=42,
            objective="reg:squarederror",
            verbosity=0,
        )

        try:
            model.fit(X_train, y_train)
        except Exception as e:
            logger.error("XGBoost training failed run_id=%s: %s", run_id, e, exc_info=True)
            raise ForecastingError(f"XGBoost training error: {e}")

        # Compute validation residuals to derive prediction intervals
        val_preds = model.predict(X_val)
        residuals = y_val.values - val_preds
        residual_std = float(np.std(residuals)) if len(residuals) > 1 else 1.0

        # Refit model on full dataset for final projection
        X_full, y_full = feat_df[feature_cols], feat_df["y"]
        model.fit(X_full, y_full)

        # 5. Autoregressive recursive multi-step forecasting across horizon
        freq_lower = input_data.frequency.lower()
        freq_alias = "D" if freq_lower == "daily" else ("W" if freq_lower == "weekly" else "MS")
        last_dt = df["ds"].iloc[-1]
        future_dates = pd.date_range(start=last_dt, periods=horizon + 1, freq=freq_alias)[1:]
        date_strs = [dt.strftime("%Y-%m-%d") for dt in future_dates]

        history_y = list(df["y"].values)
        forecast_vals: list[float] = []

        # Recursive stepping: at each step, predict next value and append to history to update lags
        sim_df = feat_df.copy()
        for step_idx, future_dt in enumerate(future_dates):
            current_t = len(sim_df)
            row_dict: dict[str, Any] = {
                "ds": future_dt,
                "y": np.nan,
                "trend_step": float(current_t),
                "month": future_dt.month,
                "day_of_week": future_dt.dayofweek,
                "quarter": future_dt.quarter,
            }

            # Lags from history_y
            for col in feature_cols:
                if col.startswith("lag_"):
                    lag_num = int(col.split("_")[1])
                    if lag_num <= len(history_y):
                        row_dict[col] = history_y[-lag_num]
                    else:
                        row_dict[col] = history_y[0]
                elif col.startswith("rolling_mean_"):
                    w = int(col.split("_")[2])
                    slice_w = history_y[-w:] if len(history_y) >= w else history_y
                    row_dict[col] = float(np.mean(slice_w))
                elif col.startswith("rolling_std_"):
                    w = int(col.split("_")[2])
                    slice_w = history_y[-w:] if len(history_y) >= w else history_y
                    row_dict[col] = float(np.std(slice_w)) if len(slice_w) > 1 else 0.0
                elif col in exog_cols:
                    if input_data.future_exogenous and col in input_data.future_exogenous:
                        row_dict[col] = float(input_data.future_exogenous[col][step_idx])
                    else:
                        row_dict[col] = float(df[col].iloc[-1])

            step_row = pd.DataFrame([row_dict])[feature_cols]
            next_pred = float(model.predict(step_row)[0])
            forecast_vals.append(next_pred)
            history_y.append(next_pred)

        # 6. Derive Prediction Intervals using residual bootstrapping / z-score
        # For confidence level C (e.g. 0.95 -> z ~ 1.96)
        from scipy.stats import norm
        z_score = float(norm.ppf(0.5 + confidence_level / 2.0))

        lower_vals: list[float] = []
        upper_vals: list[float] = []

        # Uncertainty widens proportionally with forecast step (sqrt(step + 1))
        for step_i, pred in enumerate(forecast_vals):
            step_expansion = np.sqrt(step_i + 1.0)
            margin = z_score * residual_std * step_expansion
            low = pred - margin
            up = pred + margin
            # Enforce mathematical bound consistency (lower <= forecast <= upper)
            if low > pred:
                low = pred
            if up < pred:
                up = pred
            lower_vals.append(float(low))
            upper_vals.append(float(up))

        # 7. Diagnostics: feature importances
        importance_map = {
            col: float(score)
            for col, score in zip(feature_cols, model.feature_importances_)
        }
        # Sort descending
        sorted_importance = dict(sorted(importance_map.items(), key=lambda x: x[1], reverse=True))

        diagnostics = {
            "feature_importance": sorted_importance,
            "top_features": list(sorted_importance.keys())[:5],
            "walk_forward_val_size": val_size,
            "residual_std": residual_std,
            "exogenous_regressors": exog_cols,
        }

        logger.info(
            "XGBoost forecast completed run_id=%s target=%s generated=%d points",
            run_id, target_name, len(forecast_vals)
        )

        return UnifiedForecastOutput(
            model_type="xgboost",
            target=target_name,
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
