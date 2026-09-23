"""Forecasting Foundation Engine for Phase 6.1.

Provides standardized time-series validation, frequency detection,
data regularization, and leakage-free feature engineering for all
predictive intelligence models (Prophet, ARIMA, XGBoost, Scenarios).
"""

import logging
import re
import time
from typing import Any

import numpy as np
import pandas as pd

from backend.app.schemas.forecasting import (
    FeatureSummary,
    ForecastingFoundationConfig,
    ForecastingFoundationResponse,
    FrequencyType,
    TargetDomain,
    ValidationCheckItem,
    ValidationCheckStatus,
    ValidationReport,
)

logger = logging.getLogger(__name__)

# Minimum required observations per frequency to establish trend/seasonality
MIN_OBSERVATIONS_PER_FREQ: dict[str, int] = {
    FrequencyType.DAILY.value: 14,
    FrequencyType.WEEKLY.value: 8,
    FrequencyType.MONTHLY.value: 6,
    FrequencyType.QUARTERLY.value: 4,
    FrequencyType.YEARLY.value: 3,
}

# Pandas frequency aliases for resample / date_range
PANDAS_FREQ_MAP: dict[str, str] = {
    FrequencyType.DAILY.value: "D",
    FrequencyType.WEEKLY.value: "W",
    FrequencyType.MONTHLY.value: "MS",
    FrequencyType.QUARTERLY.value: "QS",
    FrequencyType.YEARLY.value: "YS",
}

# Domain keyword matchers for target detection
DOMAIN_KEYWORDS: dict[TargetDomain, list[str]] = {
    TargetDomain.REVENUE: [
        "revenue", "rev", "gross_revenue", "net_revenue", "total_revenue",
        "turnover", "mrr", "arr", "income"
    ],
    TargetDomain.SALES: [
        "sales", "total_sales", "net_sales", "gross_sales", "sales_amount",
        "amount", "gmv"
    ],
    TargetDomain.DEMAND: [
        "demand", "orders", "units_sold", "order_quantity", "volume",
        "bookings", "requests", "transactions", "usage"
    ],
    TargetDomain.INVENTORY: [
        "inventory", "stock", "stock_level", "units_in_stock", "qty_on_hand",
        "quantity", "inventory_count"
    ],
}


class TimeSeriesDetector:
    """Automatic detection of time column, target column, domain, and frequency."""

    TIME_COLUMN_CANDIDATES = [
        "date", "datetime", "timestamp", "ds", "time", "period", "day",
        "transaction_date", "order_date", "invoice_date", "sale_date",
        "created_at", "recorded_at", "month", "year_month", "quarter"
    ]

    @classmethod
    def detect_time_column(cls, df: pd.DataFrame, explicit_column: str | None = None) -> str | None:
        """Detect the time-series timestamp column."""
        if explicit_column:
            if explicit_column in df.columns:
                return explicit_column
            logger.warning("Explicit time column '%s' not found in dataframe columns: %s", explicit_column, list(df.columns))
            return None

        # 1. Exact or lowercase substring match on candidate names
        col_lower_map = {str(c).lower().strip(): c for c in df.columns}
        for candidate in cls.TIME_COLUMN_CANDIDATES:
            if candidate in col_lower_map:
                return col_lower_map[candidate]

        # 2. Check for already datetime dtype columns
        for col in df.columns:
            if pd.api.types.is_datetime64_any_dtype(df[col]):
                return col

        # 3. Sample check: try parsing object/string columns
        for col in df.columns:
            if df[col].dtype == object or pd.api.types.is_string_dtype(df[col]):
                sample = df[col].dropna().head(10)
                if len(sample) >= 3:
                    try:
                        parsed = pd.to_datetime(sample, errors="coerce")
                        if parsed.notna().sum() >= len(sample) * 0.8:
                            return col
                    except Exception:
                        continue

        return None

    @classmethod
    def detect_target_column(cls, df: pd.DataFrame, explicit_column: str | None = None, exclude_column: str | None = None) -> tuple[str | None, TargetDomain]:
        """Detect the forecasting target metric column and its business domain."""
        if explicit_column:
            if explicit_column in df.columns:
                domain = cls._classify_domain(explicit_column)
                return explicit_column, domain
            logger.warning("Explicit target column '%s' not found in columns", explicit_column)
            return None, TargetDomain.GENERIC

        numeric_cols = [c for c in df.select_dtypes(include=[np.number]).columns if c != exclude_column]

        # Exclude obvious ID / index columns from being target
        filtered_numeric = [
            c for c in numeric_cols
            if not re.search(r"(^id$|_id$|^index$|^row_num$|^year$|^year_num$)", str(c).lower())
        ]
        candidate_cols = filtered_numeric if filtered_numeric else numeric_cols

        if not candidate_cols:
            return None, TargetDomain.GENERIC

        # 1. Domain keyword check in prioritized order: Revenue -> Sales -> Demand -> Inventory
        for domain, keywords in DOMAIN_KEYWORDS.items():
            for kw in keywords:
                for col in candidate_cols:
                    col_clean = str(col).lower().replace(" ", "_")
                    if col_clean == kw or kw in col_clean:
                        return col, domain

        # 2. Check other common business metric keywords
        other_keywords = ["profit", "cost", "churn", "customers", "users", "units", "value", "target", "y"]
        for kw in other_keywords:
            for col in candidate_cols:
                if kw in str(col).lower():
                    return col, TargetDomain.GENERIC

        # 3. Fallback: first numeric column
        return candidate_cols[0], TargetDomain.GENERIC

    @classmethod
    def _classify_domain(cls, col_name: str) -> TargetDomain:
        """Classify a given column name into a TargetDomain."""
        name_clean = str(col_name).lower().replace(" ", "_")
        for domain, keywords in DOMAIN_KEYWORDS.items():
            for kw in keywords:
                if name_clean == kw or kw in name_clean:
                    return domain
        return TargetDomain.GENERIC

    @classmethod
    def detect_frequency(cls, dates: pd.Series, explicit_frequency: FrequencyType | None = None) -> str:
        """Detect frequency from a timestamp series (daily, weekly, monthly, quarterly, yearly)."""
        if explicit_frequency:
            return explicit_frequency.value

        clean_dates = pd.to_datetime(dates, errors="coerce").dropna().drop_duplicates().sort_values()
        if len(clean_dates) < 2:
            return FrequencyType.MONTHLY.value  # default fallback

        # 1. Attempt pandas infer_freq
        try:
            inferred = pd.infer_freq(clean_dates)
            if inferred:
                inferred_upper = inferred.upper()
                if inferred_upper.startswith("D") or inferred_upper.startswith("B"):
                    return FrequencyType.DAILY.value
                if inferred_upper.startswith("W"):
                    return FrequencyType.WEEKLY.value
                if inferred_upper.startswith("M"):
                    return FrequencyType.MONTHLY.value
                if inferred_upper.startswith("Q"):
                    return FrequencyType.QUARTERLY.value
                if inferred_upper.startswith("Y") or inferred_upper.startswith("A"):
                    return FrequencyType.YEARLY.value
        except Exception:
            pass

        # 2. Robust median delta calculation
        deltas = clean_dates.diff().dropna()
        median_seconds = deltas.dt.total_seconds().median()
        median_days = median_seconds / 86400.0

        if median_days <= 1.8:
            return FrequencyType.DAILY.value
        elif 4.0 <= median_days <= 11.0:
            return FrequencyType.WEEKLY.value
        elif 20.0 <= median_days <= 45.0:
            return FrequencyType.MONTHLY.value
        elif 60.0 <= median_days <= 125.0:
            return FrequencyType.QUARTERLY.value
        elif median_days >= 250.0:
            return FrequencyType.YEARLY.value
        else:
            # Boundary fallbacks based on nearest threshold
            if median_days < 3.0:
                return FrequencyType.DAILY.value
            elif median_days < 18.0:
                return FrequencyType.WEEKLY.value
            elif median_days < 55.0:
                return FrequencyType.MONTHLY.value
            elif median_days < 200.0:
                return FrequencyType.QUARTERLY.value
            return FrequencyType.YEARLY.value


class TimeSeriesValidator:
    """Validates whether a dataset satisfies time-series forecasting criteria."""

    @classmethod
    def validate(
        cls,
        df: pd.DataFrame,
        time_col: str | None,
        target_col: str | None,
        frequency: str,
        custom_min_history: int | None = None,
    ) -> ValidationReport:
        """Run comprehensive time-series checks and compile a ValidationReport."""
        checks: list[ValidationCheckItem] = []
        reasons: list[str] = []
        is_valid = True

        total_rows = len(df)
        if total_rows == 0:
            return ValidationReport(
                status="REJECTED",
                is_valid=False,
                total_rows=0,
                valid_observations=0,
                checks=[
                    ValidationCheckItem(
                        check_name="empty_dataset_check",
                        status=ValidationCheckStatus.FAILED,
                        message="Dataset contains 0 rows.",
                    )
                ],
                rejection_reasons=["The provided dataset is empty."],
            )

        # 1. Date Column Check
        if not time_col or time_col not in df.columns:
            checks.append(
                ValidationCheckItem(
                    check_name="date_column_check",
                    status=ValidationCheckStatus.FAILED,
                    message="No valid date or timestamp column detected or specified.",
                )
            )
            reasons.append("Missing required date/time column.")
            is_valid = False
            parsed_dates = None
        else:
            try:
                parsed_dates = pd.to_datetime(df[time_col], errors="coerce")
                valid_dates_count = int(parsed_dates.notna().sum())
                if valid_dates_count == 0:
                    checks.append(
                        ValidationCheckItem(
                            check_name="date_column_check",
                            status=ValidationCheckStatus.FAILED,
                            message=f"Date column '{time_col}' could not be parsed to datetime.",
                        )
                    )
                    reasons.append(f"Date column '{time_col}' contains unparseable dates.")
                    is_valid = False
                else:
                    checks.append(
                        ValidationCheckItem(
                            check_name="date_column_check",
                            status=ValidationCheckStatus.PASSED,
                            message=f"Date column '{time_col}' successfully validated with {valid_dates_count} timestamps.",
                            details={"parsed_dates": valid_dates_count, "total_rows": total_rows},
                        )
                    )
            except Exception as e:
                checks.append(
                    ValidationCheckItem(
                        check_name="date_column_check",
                        status=ValidationCheckStatus.FAILED,
                        message=f"Error parsing date column '{time_col}': {e}",
                    )
                )
                reasons.append(f"Failed to process date column '{time_col}'.")
                is_valid = False
                parsed_dates = None

        # 2. Target Column Check
        if not target_col or target_col not in df.columns:
            checks.append(
                ValidationCheckItem(
                    check_name="target_column_check",
                    status=ValidationCheckStatus.FAILED,
                    message="No valid target metric column detected or specified.",
                )
            )
            reasons.append("Missing required numeric target column for forecasting.")
            is_valid = False
            numeric_target = None
        else:
            if not pd.api.types.is_numeric_dtype(df[target_col]):
                # Try coerce
                numeric_target = pd.to_numeric(df[target_col], errors="coerce")
                if numeric_target.notna().sum() == 0:
                    checks.append(
                        ValidationCheckItem(
                            check_name="target_column_check",
                            status=ValidationCheckStatus.FAILED,
                            message=f"Target column '{target_col}' is non-numeric.",
                        )
                    )
                    reasons.append(f"Target column '{target_col}' must be numeric.")
                    is_valid = False
                else:
                    checks.append(
                        ValidationCheckItem(
                            check_name="target_column_check",
                            status=ValidationCheckStatus.WARNING,
                            message=f"Target column '{target_col}' coerced to numeric.",
                        )
                    )
            else:
                numeric_target = df[target_col]
                checks.append(
                    ValidationCheckItem(
                        check_name="target_column_check",
                        status=ValidationCheckStatus.PASSED,
                        message=f"Target column '{target_col}' confirmed numeric.",
                    )
                )

        # 3. Missing Values Check
        missing_target_count = 0
        if numeric_target is not None:
            missing_target_count = int(numeric_target.isna().sum())
            if missing_target_count > 0:
                missing_pct = (missing_target_count / total_rows) * 100
                if missing_pct > 50.0:
                    checks.append(
                        ValidationCheckItem(
                            check_name="missing_values_check",
                            status=ValidationCheckStatus.FAILED,
                            message=f"Target column has {missing_target_count} missing values ({missing_pct:.1f}% > 50%).",
                            details={"missing_count": missing_target_count, "percentage": round(missing_pct, 2)},
                        )
                    )
                    reasons.append(f"Target column exceeds 50% missing data ({missing_pct:.1f}%).")
                    is_valid = False
                else:
                    checks.append(
                        ValidationCheckItem(
                            check_name="missing_values_check",
                            status=ValidationCheckStatus.WARNING,
                            message=f"Target column has {missing_target_count} missing values ({missing_pct:.1f}%), will be imputed.",
                            details={"missing_count": missing_target_count, "percentage": round(missing_pct, 2)},
                        )
                    )
            else:
                checks.append(
                    ValidationCheckItem(
                        check_name="missing_values_check",
                        status=ValidationCheckStatus.PASSED,
                        message="Zero missing values in target column.",
                    )
                )

        # 4. History Sufficiency Check
        min_required = custom_min_history or MIN_OBSERVATIONS_PER_FREQ.get(frequency, 6)
        valid_obs = 0
        min_date_str: str | None = None
        max_date_str: str | None = None
        missing_dates_count = 0

        if parsed_dates is not None and is_valid:
            valid_mask = parsed_dates.notna()
            valid_obs = int(valid_mask.sum())
            if valid_obs > 0:
                min_dt = parsed_dates[valid_mask].min()
                max_dt = parsed_dates[valid_mask].max()
                min_date_str = min_dt.isoformat()
                max_date_str = max_dt.isoformat()

                # Calculate approximate expected points for frequency
                freq_alias = PANDAS_FREQ_MAP.get(frequency, "MS")
                try:
                    expected_range = pd.date_range(start=min_dt, end=max_dt, freq=freq_alias)
                    missing_dates_count = max(0, len(expected_range) - valid_obs)
                except Exception:
                    missing_dates_count = 0

            if valid_obs < min_required:
                checks.append(
                    ValidationCheckItem(
                        check_name="history_sufficiency_check",
                        status=ValidationCheckStatus.FAILED,
                        message=(
                            f"Insufficient historical data: found {valid_obs} observations, "
                            f"but {frequency} forecasting requires at least {min_required}."
                        ),
                        details={"found": valid_obs, "required": min_required, "frequency": frequency},
                    )
                )
                reasons.append(
                    f"Insufficient historical records: {valid_obs} found, {min_required} required for {frequency} cadence."
                )
                is_valid = False
            else:
                checks.append(
                    ValidationCheckItem(
                        check_name="history_sufficiency_check",
                        status=ValidationCheckStatus.PASSED,
                        message=f"Sufficient historical data: {valid_obs} observations >= {min_required} required.",
                        details={"found": valid_obs, "required": min_required, "frequency": frequency},
                    )
                )

        # 5. Target Variance / Uniformity Check
        if numeric_target is not None and is_valid:
            clean_series = numeric_target.dropna()
            if len(clean_series) > 1 and clean_series.nunique() == 1:
                checks.append(
                    ValidationCheckItem(
                        check_name="target_variance_check",
                        status=ValidationCheckStatus.WARNING,
                        message="Target variable is completely constant; forecasts will project flat line.",
                    )
                )

        status_str = "PASSED" if is_valid and not any(c.status == ValidationCheckStatus.WARNING for c in checks) else (
            "WARNING" if is_valid else "REJECTED"
        )

        return ValidationReport(
            status=status_str,
            is_valid=is_valid,
            total_rows=total_rows,
            valid_observations=valid_obs,
            min_date=min_date_str,
            max_date=max_date_str,
            missing_dates_count=missing_dates_count,
            missing_target_count=missing_target_count,
            checks=checks,
            rejection_reasons=reasons,
        )


class TimeSeriesPreparer:
    """Prepares and regularizes time series on a continuous grid with gap imputation."""

    @classmethod
    def prepare(
        cls,
        df: pd.DataFrame,
        time_col: str,
        target_col: str,
        frequency: str,
        aggregation_func: str = "sum",
        fill_method: str = "interpolate",
    ) -> pd.DataFrame:
        """Aggregate, sort, reindex to regular continuous date range, and impute gaps."""
        work_df = df.copy()

        # 1. Parse and standardize time and target
        work_df["ds"] = pd.to_datetime(work_df[time_col], errors="coerce")
        work_df["y"] = pd.to_numeric(work_df[target_col], errors="coerce")
        work_df = work_df.dropna(subset=["ds"]).sort_values("ds")

        freq_alias = PANDAS_FREQ_MAP.get(frequency, "MS")

        # 2. Resample / Aggregate duplicate timestamps or sub-period observations
        if aggregation_func.lower() in ["sum", "total"]:
            resampled = work_df.set_index("ds")[["y"]].resample(freq_alias).sum(min_count=1)
        else:
            resampled = work_df.set_index("ds")[["y"]].resample(freq_alias).mean()

        # 3. Create full continuous grid between min and max
        full_index = pd.date_range(start=resampled.index.min(), end=resampled.index.max(), freq=freq_alias)
        regular_df = resampled.reindex(full_index)
        regular_df.index.name = "ds"

        # 4. Impute missing values on the regular grid
        if fill_method == "zero":
            regular_df["y"] = regular_df["y"].fillna(0.0)
        elif fill_method == "ffill":
            regular_df["y"] = regular_df["y"].ffill().bfill().fillna(0.0)
        elif fill_method == "bfill":
            regular_df["y"] = regular_df["y"].bfill().ffill().fillna(0.0)
        else:  # interpolate (default)
            regular_df["y"] = regular_df["y"].interpolate(method="linear").bfill().ffill().fillna(0.0)

        # Reset index to have 'ds' as column
        prepared = regular_df.reset_index()

        # Preserve original column name as an alias for interoperability
        if target_col != "y":
            prepared[target_col] = prepared["y"]
        if time_col != "ds":
            prepared[time_col] = prepared["ds"]

        return prepared


class FeatureEngineer:
    """Generates leakage-free trend, seasonality, lag, and rolling statistics features."""

    # Default frequency-aware lag structures
    FREQUENCY_LAGS: dict[str, list[int]] = {
        FrequencyType.DAILY.value: [1, 2, 3, 7, 14, 28],
        FrequencyType.WEEKLY.value: [1, 2, 4, 8, 12],
        FrequencyType.MONTHLY.value: [1, 2, 3, 6, 12],
        FrequencyType.QUARTERLY.value: [1, 2, 4],
        FrequencyType.YEARLY.value: [1, 2],
    }

    # Default frequency-aware rolling window sizes
    FREQUENCY_ROLLING: dict[str, list[int]] = {
        FrequencyType.DAILY.value: [3, 7, 14],
        FrequencyType.WEEKLY.value: [2, 4, 8],
        FrequencyType.MONTHLY.value: [2, 3, 6],
        FrequencyType.QUARTERLY.value: [2, 4],
        FrequencyType.YEARLY.value: [2],
    }

    @classmethod
    def generate_features(
        cls,
        df: pd.DataFrame,
        frequency: str,
        custom_lags: list[int] | None = None,
        custom_rolling: list[int] | None = None,
    ) -> tuple[pd.DataFrame, FeatureSummary]:
        """Generate trend, calendar, cyclical, lag, and rolling features on prepared time series."""
        out_df = df.copy()
        n = len(out_df)

        trend_cols: list[str] = []
        seasonal_cols: list[str] = []
        lag_cols: list[str] = []
        rolling_cols: list[str] = []

        # -----------------------------------------------------------------
        # 1. Trend Features
        # -----------------------------------------------------------------
        t_seq = np.arange(n, dtype=np.float64)
        out_df["trend_step"] = t_seq
        out_df["log_trend"] = np.log1p(t_seq)
        out_df["trend_squared"] = t_seq ** 2

        trend_cols.extend(["trend_step", "log_trend", "trend_squared"])

        # -----------------------------------------------------------------
        # 2. Seasonality & Calendar Features
        # -----------------------------------------------------------------
        ds = out_df["ds"]

        out_df["year"] = ds.dt.year
        out_df["quarter"] = ds.dt.quarter
        out_df["month"] = ds.dt.month
        out_df["day"] = ds.dt.day
        out_df["day_of_week"] = ds.dt.dayofweek
        out_df["day_of_year"] = ds.dt.dayofyear
        out_df["week_of_year"] = ds.dt.isocalendar().week.astype(int)
        out_df["is_weekend"] = (ds.dt.dayofweek >= 5).astype(int)
        out_df["is_month_start"] = ds.dt.is_month_start.astype(int)
        out_df["is_month_end"] = ds.dt.is_month_end.astype(int)
        out_df["is_quarter_start"] = ds.dt.is_quarter_start.astype(int)
        out_df["is_quarter_end"] = ds.dt.is_quarter_end.astype(int)

        seasonal_cols.extend([
            "year", "quarter", "month", "day", "day_of_week",
            "day_of_year", "week_of_year", "is_weekend",
            "is_month_start", "is_month_end", "is_quarter_start", "is_quarter_end"
        ])

        # Cyclical trigonometric transforms (sin / cos)
        out_df["sin_month"] = np.sin(2.0 * np.pi * out_df["month"] / 12.0)
        out_df["cos_month"] = np.cos(2.0 * np.pi * out_df["month"] / 12.0)
        out_df["sin_quarter"] = np.sin(2.0 * np.pi * out_df["quarter"] / 4.0)
        out_df["cos_quarter"] = np.cos(2.0 * np.pi * out_df["quarter"] / 4.0)
        out_df["sin_dow"] = np.sin(2.0 * np.pi * out_df["day_of_week"] / 7.0)
        out_df["cos_dow"] = np.cos(2.0 * np.pi * out_df["day_of_week"] / 7.0)
        out_df["sin_doy"] = np.sin(2.0 * np.pi * out_df["day_of_year"] / 365.25)
        out_df["cos_doy"] = np.cos(2.0 * np.pi * out_df["day_of_year"] / 365.25)

        seasonal_cols.extend([
            "sin_month", "cos_month", "sin_quarter", "cos_quarter",
            "sin_dow", "cos_dow", "sin_doy", "cos_doy"
        ])

        # -----------------------------------------------------------------
        # 3. Lag Features (Shifted by 1+ to strictly prevent lookahead leakage)
        # -----------------------------------------------------------------
        target_series = out_df["y"]
        lags_to_use = custom_lags if custom_lags is not None else cls.FREQUENCY_LAGS.get(frequency, [1, 2, 3])

        # Filter out lags that exceed dataset size
        effective_lags = [k for k in lags_to_use if k < n and k > 0]
        if not effective_lags:
            effective_lags = [1] if n > 1 else []

        for k in effective_lags:
            col_name = f"lag_{k}"
            # shift(k) means lag_k at time t uses observation at t-k
            out_df[col_name] = target_series.shift(k).bfill().fillna(target_series.iloc[0] if len(target_series) > 0 else 0.0)
            lag_cols.append(col_name)

        # -----------------------------------------------------------------
        # 4. Rolling Statistics (Applied to shifted target to prevent lookahead leakage)
        # -----------------------------------------------------------------
        # IMPORTANT: Always compute rolling statistics on shifted series y.shift(1)
        # so time t only incorporates past information up to t-1!
        y_shifted = target_series.shift(1).bfill().fillna(target_series.iloc[0] if len(target_series) > 0 else 0.0)

        windows_to_use = custom_rolling if custom_rolling is not None else cls.FREQUENCY_ROLLING.get(frequency, [2, 3])
        effective_windows = [w for w in windows_to_use if w <= n and w > 1]
        if not effective_windows and n >= 2:
            effective_windows = [2]

        for w in effective_windows:
            mean_col = f"rolling_mean_{w}"
            std_col = f"rolling_std_{w}"
            min_col = f"rolling_min_{w}"
            max_col = f"rolling_max_{w}"

            out_df[mean_col] = y_shifted.rolling(window=w, min_periods=1).mean().bfill()
            out_df[std_col] = y_shifted.rolling(window=w, min_periods=1).std().fillna(0.0)
            out_df[min_col] = y_shifted.rolling(window=w, min_periods=1).min().bfill()
            out_df[max_col] = y_shifted.rolling(window=w, min_periods=1).max().bfill()

            rolling_cols.extend([mean_col, std_col, min_col, max_col])

        # EWMA (Exponentially Weighted Moving Average on shifted series)
        ewma_span = 3 if n >= 3 else 2
        out_df[f"ewma_{ewma_span}"] = y_shifted.ewm(span=ewma_span, min_periods=1).mean().bfill()
        rolling_cols.append(f"ewma_{ewma_span}")

        total_features = len(trend_cols) + len(seasonal_cols) + len(lag_cols) + len(rolling_cols)
        summary = FeatureSummary(
            trend_features=trend_cols,
            seasonal_features=seasonal_cols,
            lag_features=lag_cols,
            rolling_features=rolling_cols,
            total_features=total_features,
        )

        return out_df, summary


class ForecastingFoundation:
    """Unified Facade for Phase 6.1 Forecasting Foundation.

    Combines TimeSeriesDetector, TimeSeriesValidator, TimeSeriesPreparer,
    and FeatureEngineer into a single high-performance pipeline.
    """

    @classmethod
    def process_dataframe(
        cls,
        df: pd.DataFrame,
        config: ForecastingFoundationConfig | None = None,
    ) -> tuple[pd.DataFrame, ForecastingFoundationResponse]:
        """Execute complete forecasting foundation pipeline on a DataFrame."""
        start_time = time.perf_counter()
        cfg = config or ForecastingFoundationConfig()

        logger.info("Starting Forecasting Foundation processing shape=%s", df.shape)

        # 1. Detection Phase
        time_col = TimeSeriesDetector.detect_time_column(df, explicit_column=cfg.time_column)
        target_col, data_domain = TimeSeriesDetector.detect_target_column(
            df, explicit_column=cfg.target_column, exclude_column=time_col
        )

        # Detect frequency if time column is available
        if time_col and time_col in df.columns:
            detected_frequency = TimeSeriesDetector.detect_frequency(
                df[time_col], explicit_frequency=cfg.frequency
            )
        else:
            detected_frequency = cfg.frequency.value if cfg.frequency else FrequencyType.MONTHLY.value

        target_col_name = target_col or "target"
        time_col_name = time_col or "date"

        # 2. Validation Phase
        validation_report = TimeSeriesValidator.validate(
            df=df,
            time_col=time_col,
            target_col=target_col,
            frequency=detected_frequency,
            custom_min_history=cfg.min_history_records,
        )

        # If dataset is NOT ready / rejected, return early with structured report
        if not validation_report.is_valid:
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            logger.warning(
                "Dataset rejected by Forecasting Foundation: reasons=%s",
                validation_report.rejection_reasons
            )
            response = ForecastingFoundationResponse(
                dataset_ready=False,
                frequency=detected_frequency,
                target_column=target_col_name,
                time_column=time_col_name,
                data_domain=data_domain.value,
                total_records=len(df),
                validation_report=validation_report,
                feature_summary=None,
                feature_names=[],
                prepared_data_preview=None,
                execution_time_ms=round(duration_ms, 2),
            )
            return pd.DataFrame(), response

        # 3. Preparation & Regularization Phase
        prepared_df = TimeSeriesPreparer.prepare(
            df=df,
            time_col=time_col_name,
            target_col=target_col_name,
            frequency=detected_frequency,
            aggregation_func=cfg.aggregation_func,
            fill_method=cfg.fill_missing_method,
        )

        # 4. Feature Engineering Phase
        feature_summary: FeatureSummary | None = None
        if cfg.generate_features:
            prepared_df, feature_summary = FeatureEngineer.generate_features(
                df=prepared_df,
                frequency=detected_frequency,
                custom_lags=cfg.lags,
                custom_rolling=cfg.rolling_windows,
            )

        duration_ms = (time.perf_counter() - start_time) * 1000.0

        # Build preview records (first 5 and last 5)
        preview_records: list[dict[str, Any]] = []
        if not prepared_df.empty:
            preview_subset = pd.concat([prepared_df.head(5), prepared_df.tail(5)]).drop_duplicates()
            # Convert timestamps to string for JSON serialization
            preview_dict = preview_subset.copy()
            for col in preview_dict.columns:
                if pd.api.types.is_datetime64_any_dtype(preview_dict[col]):
                    preview_dict[col] = preview_dict[col].dt.strftime("%Y-%m-%d %H:%M:%S")
                elif pd.api.types.is_float_dtype(preview_dict[col]):
                    preview_dict[col] = preview_dict[col].round(4)
            preview_records = preview_dict.to_dict(orient="records")

        logger.info(
            "Forecasting Foundation completed successfully: target=%s, freq=%s, total_points=%d, duration=%.2fms",
            target_col_name, detected_frequency, len(prepared_df), duration_ms
        )

        response = ForecastingFoundationResponse(
            dataset_ready=True,
            frequency=detected_frequency,
            target_column=target_col_name,
            time_column=time_col_name,
            data_domain=data_domain.value,
            total_records=len(prepared_df),
            validation_report=validation_report,
            feature_summary=feature_summary,
            feature_names=list(prepared_df.columns),
            prepared_data_preview=preview_records,
            execution_time_ms=round(duration_ms, 2),
        )

        return prepared_df, response
