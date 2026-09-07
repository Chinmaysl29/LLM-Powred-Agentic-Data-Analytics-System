"""Pydantic schemas for Phase 6.1 Forecasting Foundation.

Defines schemas for time-series validation, frequency detection,
data preparation, feature engineering, and foundation responses.
"""

from enum import Enum
from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class FrequencyType(str, Enum):
    """Standardized forecasting frequencies supported across all models."""

    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


class TargetDomain(str, Enum):
    """Business domain classification for the target variable."""

    REVENUE = "revenue"
    SALES = "sales"
    DEMAND = "demand"
    INVENTORY = "inventory"
    GENERIC = "generic"


class ValidationCheckStatus(str, Enum):
    """Status of an individual dataset validation check."""

    PASSED = "PASSED"
    FAILED = "FAILED"
    WARNING = "WARNING"


class ValidationCheckItem(BaseModel):
    """Details of a single validation check."""

    check_name: str = Field(..., description="Name of the validation check")
    status: ValidationCheckStatus = Field(..., description="Check status")
    message: str = Field(..., description="Human-readable outcome message")
    details: dict[str, Any] | None = Field(default=None, description="Diagnostic metadata")


class ValidationReport(BaseModel):
    """Comprehensive validation outcome for time-series forecasting."""

    status: str = Field(..., description="'PASSED', 'WARNING', or 'REJECTED'")
    is_valid: bool = Field(..., description="True if dataset satisfies all core forecasting criteria")
    total_rows: int = Field(default=0, description="Total input rows before cleaning")
    valid_observations: int = Field(default=0, description="Usable consecutive or aggregated observations")
    min_date: str | None = Field(default=None, description="Earliest timestamp in dataset")
    max_date: str | None = Field(default=None, description="Latest timestamp in dataset")
    missing_dates_count: int = Field(default=0, description="Number of timestamp gaps detected on the regular grid")
    missing_target_count: int = Field(default=0, description="Number of missing or null target values")
    checks: list[ValidationCheckItem] = Field(default_factory=list, description="Audit of all individual checks")
    rejection_reasons: list[str] = Field(default_factory=list, description="Reasons if dataset is not ready")


class FeatureSummary(BaseModel):
    """Breakdown of generated features for downstream machine learning."""

    trend_features: list[str] = Field(default_factory=list, description="Trend indicator columns")
    seasonal_features: list[str] = Field(default_factory=list, description="Calendar and cyclical trigonometric columns")
    lag_features: list[str] = Field(default_factory=list, description="Shifted historical lag columns")
    rolling_features: list[str] = Field(default_factory=list, description="Rolling window statistics columns")
    total_features: int = Field(default=0, description="Total count of engineered features")


class ForecastingFoundationConfig(BaseModel):
    """Configuration options for forecasting dataset preparation and feature engineering."""

    time_column: str | None = Field(default=None, description="Explicit date/time column; auto-detected if None")
    target_column: str | None = Field(default=None, description="Explicit target column; auto-detected if None")
    frequency: FrequencyType | None = Field(default=None, description="Explicit frequency; auto-detected if None")
    aggregation_func: str = Field(default="sum", description="Aggregation function for duplicates/sub-intervals ('sum', 'mean')")
    fill_missing_method: str = Field(default="interpolate", description="Gap handling method ('interpolate', 'ffill', 'bfill', 'zero')")
    min_history_records: int | None = Field(default=None, description="Custom minimum observations required (overrides defaults)")
    generate_features: bool = Field(default=True, description="Whether to compute trend, seasonal, lag, and rolling features")
    lags: list[int] | None = Field(default=None, description="Custom lag shifts (auto-selected based on frequency if None)")
    rolling_windows: list[int] | None = Field(default=None, description="Custom rolling window sizes (auto-selected if None)")


class ForecastingFoundationResponse(BaseModel):
    """Standardized response from Phase 6.1 Forecasting Foundation."""

    model_config = ConfigDict(from_attributes=True)

    dataset_ready: bool = Field(..., description="True if dataset passes all validation and is ready for forecasting")
    frequency: str = Field(..., description="Detected or specified frequency ('daily', 'weekly', 'monthly', 'quarterly', 'yearly')")
    target_column: str = Field(..., description="Detected or specified forecasting target column")
    time_column: str = Field(default="", description="Detected or specified time/date column")
    data_domain: str = Field(default=TargetDomain.GENERIC.value, description="Business domain classification of target variable")
    total_records: int = Field(default=0, description="Total prepared time-series records")
    validation_report: ValidationReport = Field(..., description="Detailed validation breakdown")
    feature_summary: FeatureSummary | None = Field(default=None, description="Summary of generated features")
    feature_names: list[str] = Field(default_factory=list, description="List of all column names in the prepared dataset")
    prepared_data_preview: list[dict[str, Any]] | None = Field(default=None, description="Sample preview of prepared records")
    execution_time_ms: float = Field(default=0.0, description="Pipeline execution duration in milliseconds")


class PrepareDataRecordsRequest(BaseModel):
    """Request payload to prepare time-series directly from JSON records."""

    records: list[dict[str, Any]] = Field(..., description="List of dictionary records")
    config: ForecastingFoundationConfig = Field(default_factory=ForecastingFoundationConfig, description="Foundation options")


class ValidateDatasetRequest(BaseModel):
    """Request payload for validation-only check on records or dataset."""

    records: list[dict[str, Any]] | None = Field(default=None, description="Optional raw records")
    dataset_id: str | None = Field(default=None, description="Optional dataset ID from storage")
    version_number: int | None = Field(default=None, description="Optional dataset version")
    time_column: str | None = Field(default=None, description="Explicit date column")
    target_column: str | None = Field(default=None, description="Explicit target column")
    frequency: FrequencyType | None = Field(default=None, description="Explicit frequency")


# =============================================================================
# SHARED CONTRACTS (PHASES 6.3 - 6.10)
# =============================================================================

class DataPoint(BaseModel):
    """Single time-series observation."""

    date: str = Field(..., description="Timestamp in ISO or YYYY-MM-DD format")
    value: float = Field(..., description="Observed metric value")


class UnifiedForecastInput(BaseModel):
    """Standardized input contract accepted by Prophet, ARIMA, and XGBoost."""

    series: list[DataPoint] = Field(..., description="Array of {date, value} objects")
    frequency: str = Field(default="daily", description="Cadence: 'daily', 'weekly', or 'monthly'")
    horizon: int = Field(default=30, ge=1, description="Periods into the future to forecast")
    confidence_level: float = Field(default=0.95, gt=0.0, lt=1.0, description="Prediction interval width")
    target: str = Field(default="sales", description="Target metric name ('sales', 'revenue', 'demand', 'inventory')")
    exogenous_regressors: dict[str, list[float]] | None = Field(
        default=None, description="Optional named historical regressors"
    )
    future_exogenous: dict[str, list[float]] | None = Field(
        default=None, description="Optional future values for exogenous regressors across the horizon"
    )


class BoundFloat(float):
    """Float wrapper that exposes .value property for test assertion compatibility."""
    @property
    def value(self) -> float:
        return float(self)


class UnifiedForecastOutput(BaseModel):
    """Unified forecast output contract emitted by all forecasting models."""

    model_config = ConfigDict(from_attributes=True, arbitrary_types_allowed=True)

    model_type: str = Field(..., description="'prophet', 'arima', or 'xgboost'")
    target: str = Field(..., description="'sales', 'revenue', 'demand', or 'inventory'")
    frequency: str = Field(..., description="'daily', 'weekly', or 'monthly'")
    generated_at: str = Field(..., description="ISO-8601 generation timestamp")
    horizon: int = Field(..., description="Forecast horizon length")
    confidence_level: float = Field(default=0.95, description="Confidence interval coverage")
    dates: list[str] = Field(..., description="Projected future date strings")
    forecast: list[float] = Field(..., description="Point forecasts")
    lower_bound: list[Any] = Field(..., description="Lower prediction bounds")
    upper_bound: list[Any] = Field(..., description="Upper prediction bounds")
    diagnostics: dict[str, Any] = Field(default_factory=dict, description="Model-specific extra diagnostics")

    def model_post_init(self, __context: Any) -> None:
        if self.lower_bound and not isinstance(self.lower_bound[0], BoundFloat):
            self.lower_bound = [BoundFloat(x) for x in self.lower_bound]
        if self.upper_bound and not isinstance(self.upper_bound[0], BoundFloat):
            self.upper_bound = [BoundFloat(x) for x in self.upper_bound]

    @property
    def forecast_id(self) -> str:
        return str(self.diagnostics.get("run_id") or "forecast-run")

    @property
    def model_name(self) -> str:
        return self.model_type

    @property
    def forecast_values(self) -> list[DataPoint]:
        dates = self.dates if len(self.dates) == len(self.forecast) else ["" for _ in self.forecast]
        return [DataPoint(date=d, value=float(v)) for d, v in zip(dates, self.forecast)]


class ForecastValidationOutput(BaseModel):
    """Validation output from Phase 6.6 Forecast Validator."""

    run_id: str = Field(default="", description="Identifier of the validated run")
    model_type: str = Field(..., description="Model tested ('prophet', 'arima', 'xgboost')")
    validation_status: str = Field(..., description="'PASSED', 'WARNING', or 'FAILED'")
    mae: float = Field(default=0.0, description="Mean Absolute Error from backtest")
    rmse: float = Field(default=0.0, description="Root Mean Squared Error from backtest")
    mape: float = Field(default=0.0, description="Mean Absolute Percentage Error (0-1.0)")
    r2: float = Field(default=0.0, description="Coefficient of determination")
    anomalies_detected: list[dict[str, Any]] = Field(default_factory=list, description="Detected forecast anomalies")
    quality_score: float = Field(default=0.0, description="Composite model quality score (0-100)")
    confidence_score: float = Field(default=0.0, description="Composite prediction confidence score (0-100)")


class ScenarioEngineOutput(BaseModel):
    """Preset scenarios output from Phase 6.7 Scenario Engine."""

    baseline: dict[str, Any] = Field(..., description="Baseline forecast output")
    optimistic: dict[str, Any] = Field(..., description="Optimistic scenario forecast")
    pessimistic: dict[str, Any] = Field(..., description="Pessimistic scenario forecast")
    comparison: dict[str, Any] = Field(..., description="Delta metrics compared to baseline")


class WhatIfAnalysisInput(BaseModel):
    """Request payload for Phase 6.8 What-If Analysis Engine."""

    model_config = ConfigDict(extra="allow")

    input_change: str = Field(default="", description="Ad-hoc business change (e.g. 'marketing +20%', 'price -5%')")
    what_if_query: str | None = Field(default=None, description="Query alias for input_change")
    target_metric: str | None = Field(default="revenue", description="Target metric name")
    target: str | None = Field(default=None, description="Target alias")
    base_forecast: UnifiedForecastOutput | None = Field(default=None, description="Optional baseline forecast")
    historical_series: list[DataPoint] | None = Field(default=None, description="Optional historical data")
    series: list[DataPoint] | None = Field(default=None, description="Series alias")
    horizon: int = Field(default=30, description="Forecast horizon")
    frequency: Any = Field(default="daily", description="Cadence")


class WhatIfAnalysisOutput(BaseModel):
    """Output from Phase 6.8 What-If Analysis Engine."""

    input_change: str = Field(..., description="The evaluated change string")
    predicted_revenue: float = Field(..., description="Predicted total or terminal value under change")
    predicted_growth: float = Field(..., description="Predicted percentage growth vs baseline")
    predicted_risk: float = Field(..., description="Stated risk derived from interval expansion")

    @property
    def projected_value(self) -> float:
        return self.predicted_revenue

    @property
    def scenario_forecast(self) -> float:
        return self.predicted_revenue


class BusinessForecastAgentOutput(BaseModel):
    """Output from Phase 6.9 Business Forecast Agent."""

    selected_model: str = Field(..., description="Chosen model name ('prophet', 'arima', 'xgboost')")
    selection_reason: str = Field(..., description="Explicit criteria and rationale for selection")
    forecast: UnifiedForecastOutput = Field(..., description="Forecast generated by selected model")
    validation: ForecastValidationOutput = Field(..., description="Validation audit from Forecast Validator")

    @property
    def explanation(self) -> str:
        return self.selection_reason

    @property
    def selection_explanation(self) -> str:
        return self.selection_reason

    @property
    def model_selection_reason(self) -> str:
        return self.selection_reason



class RecommendationItem(BaseModel):
    """Structured recommendation item produced by Forecast Pipeline."""

    action: str = Field(..., description="Recommended business decision")
    rationale: str = Field(..., description="Analytical backing from forecast/scenario analysis")
    expected_impact: str = Field(..., description="Estimated revenue/inventory/demand outcome")
    confidence: float = Field(..., description="Confidence level (0.0 - 1.0)")


class ForecastPipelineOutput(BaseModel):
    """End-to-end output from Phase 6.10 Forecast Pipeline."""

    run_id: str = Field(..., description="Unique execution UUID")
    forecast: UnifiedForecastOutput = Field(..., description="Validated forecast output")
    validation: ForecastValidationOutput = Field(..., description="Validator scoring")
    scenarios: ScenarioEngineOutput = Field(..., description="Scenario presets")
    what_if: WhatIfAnalysisOutput = Field(..., description="Exploratory what-if analysis outcome")
    recommendations: list[RecommendationItem] = Field(default_factory=list, description="Structured actions")
    business_summary: str = Field(..., description="Deterministic templated executive summary")

