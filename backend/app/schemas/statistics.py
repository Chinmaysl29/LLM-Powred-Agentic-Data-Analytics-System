"""Pydantic schemas for Phase 3.6 Statistics Agent."""

from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field


SignificanceLevel = Literal["highly_significant", "moderately_significant", "not_significant"]
TestType = Literal["two_sample_ttest", "paired_ttest", "one_way_anova"]


class Quartiles(BaseModel):
    """Quartiles and interquartile range."""

    q1: float = Field(..., description="25th percentile (Q1)")
    q2: float = Field(..., description="50th percentile (Median/Q2)")
    q3: float = Field(..., description="75th percentile (Q3)")
    iqr: float = Field(..., description="Interquartile Range (Q3 - Q1)")


class Percentiles(BaseModel):
    """Detailed percentiles for distribution analysis."""

    p5: float = Field(..., description="5th percentile")
    p10: float = Field(..., description="10th percentile")
    p25: float = Field(..., description="25th percentile")
    p50: float = Field(..., description="50th percentile")
    p75: float = Field(..., description="75th percentile")
    p90: float = Field(..., description="90th percentile")
    p95: float = Field(..., description="95th percentile")


class DescriptiveProfile(BaseModel):
    """Deep statistical profile for a numeric column."""

    count: int = Field(..., description="Count of non-null elements")
    mean: float = Field(..., description="Arithmetic mean")
    median: float = Field(..., description="Median value")
    mode: float | None = Field(None, description="Primary mode value")
    variance: float = Field(..., description="Sample variance (ddof=1)")
    std_dev: float = Field(..., description="Sample standard deviation (ddof=1)")
    range_val: float = Field(..., description="Range (max - min)")
    min: float = Field(..., description="Minimum value")
    max: float = Field(..., description="Maximum value")
    quartiles: Quartiles = Field(..., description="Quartile breakdown")
    percentiles: Percentiles = Field(..., description="Detailed percentiles")


class HypothesisTestResult(BaseModel):
    """Results of a parametric hypothesis test (T-Test, Paired T-Test, or ANOVA)."""

    test_name: str = Field(..., description="Descriptive name of the test")
    test_type: TestType = Field(..., description="Type of test performed")
    variable: str = Field(..., description="Numeric variable tested")
    group_a: str = Field(..., description="First comparison group / condition")
    group_b: str | None = Field(None, description="Second comparison group (if applicable)")
    statistic: float = Field(..., description="Computed test statistic (t or F)")
    p_value: float = Field(..., description="Two-tailed p-value")
    degrees_of_freedom: float | None = Field(None, description="Degrees of freedom")
    significance_tier: SignificanceLevel = Field(..., description="Statistical significance classification")
    null_hypothesis_rejected: bool = Field(..., description="Whether null hypothesis is rejected at alpha=0.05")
    interpretation: str = Field(..., description="Plain-language statistical conclusion")


class RegressionDriver(BaseModel):
    """A predictor variable evaluated in a regression model."""

    feature: str = Field(..., description="Predictor feature name")
    coefficient: float = Field(..., description="Unstandardized regression coefficient (slope)")
    standardized_coefficient: float = Field(..., description="Standardized beta weight representing relative importance")
    t_statistic: float = Field(..., description="t-statistic for the coefficient")
    p_value: float = Field(..., description="Significance p-value for the predictor")
    importance_rank: int = Field(..., description="Relative rank among predictors by absolute beta")
    is_significant: bool = Field(..., description="Whether predictor is statistically significant (p < 0.05)")


class RegressionResult(BaseModel):
    """Results of linear or multiple regression analysis."""

    target_variable: str = Field(..., description="Dependent target variable modeled")
    predictors: list[str] = Field(..., description="List of independent predictor variables")
    r_squared: float = Field(..., description="Coefficient of determination (R²)")
    adjusted_r_squared: float = Field(..., description="Adjusted R² accounting for predictor count")
    f_statistic: float = Field(..., description="Overall model F-statistic")
    p_value: float = Field(..., description="Overall model p-value")
    intercept: float = Field(..., description="Model intercept")
    drivers: list[RegressionDriver] = Field(default_factory=list, description="Ranked drivers with feature importance")
    strongest_driver: str | None = Field(None, description="Most influential predictor feature")
    summary: str = Field(..., description="Concise summary of model performance and drivers")


class ConfidenceInterval(BaseModel):
    """Confidence interval for a population parameter."""

    column: str = Field(..., description="Numeric column name")
    confidence_level: str = Field(..., description="Confidence level (e.g. '95%' or '99%')")
    mean: float = Field(..., description="Sample mean")
    std_error: float = Field(..., description="Standard error of the mean")
    margin_of_error: float = Field(..., description="Margin of error")
    lower_bound: float = Field(..., description="Lower bound of confidence interval")
    upper_bound: float = Field(..., description="Upper bound of confidence interval")


class ChiSquareResult(BaseModel):
    """Results of Chi-Square test of independence between two categorical variables."""

    variable_a: str = Field(..., description="First categorical feature")
    variable_b: str = Field(..., description="Second categorical feature")
    chi2_statistic: float = Field(..., description="Pearson Chi-Square statistic")
    p_value: float = Field(..., description="p-value for independence test")
    degrees_of_freedom: int = Field(..., description="Degrees of freedom")
    is_dependent: bool = Field(..., description="True if variables are statistically dependent (p < 0.05)")
    significance_tier: SignificanceLevel = Field(..., description="Significance tier")
    interpretation: str = Field(..., description="Business conclusion regarding categorical dependency")


class SignificantRelationship(BaseModel):
    """A key statistically verified relationship between two variables."""

    source_variable: str = Field(..., description="Independent or driving variable")
    target_variable: str = Field(..., description="Dependent or associated variable")
    relationship_type: str = Field(..., description="correlation, regression_driver, group_difference, or categorical_dependency")
    metric_value: float = Field(..., description="Quantified strength (e.g. correlation r or regression beta)")
    p_value: float = Field(..., description="Statistical significance p-value")
    significance_tier: SignificanceLevel = Field(..., description="Significance classification")
    insight: str = Field(..., description="Natural language statement of the relationship")


class RootCauseItem(BaseModel):
    """Statistically supported root cause or key outcome driver."""

    target_metric: str = Field(..., description="Metric being explained")
    primary_driver: str = Field(..., description="Statistically verified leading driver")
    variance_explained_pct: float = Field(..., description="Percentage of target variance explained")
    direction: str = Field(..., description="Direction of impact: positive or negative")
    statistical_evidence: str = Field(..., description="Mathematical evidence (R², p-value, beta)")
    business_takeaway: str = Field(..., description="Executive explanation of why the outcome occurred")


class StatisticsBusinessInsight(BaseModel):
    """Actionable business insight derived from inferential statistics."""

    category: str = Field(..., description="Category: driver, hypothesis, dependency, risk, etc.")
    title: str = Field(..., description="Concise insight header")
    insight: str = Field(..., description="Business-readable takeaway")
    impact: str = Field("medium", description="Business impact: low, medium, high")


class StatisticsResults(BaseModel):
    """Standardized output structure for the Statistics Agent."""

    descriptive_statistics: dict[str, DescriptiveProfile] = Field(
        default_factory=dict, description="In-depth statistical profiles for numeric columns"
    )
    hypothesis_tests: dict[str, list[HypothesisTestResult]] = Field(
        default_factory=dict, description="Parametric hypothesis tests grouped by test category"
    )
    regression_results: dict[str, RegressionResult] = Field(
        default_factory=dict, description="Linear and multiple regression models"
    )
    confidence_intervals: dict[str, dict[str, ConfidenceInterval]] = Field(
        default_factory=dict, description="95% and 99% confidence intervals per numeric column"
    )
    chi_square_results: list[ChiSquareResult] = Field(
        default_factory=list, description="Categorical independence test results"
    )
    significant_relationships: list[SignificantRelationship] = Field(
        default_factory=list, description="Verified relationships meeting statistical significance criteria"
    )
    root_causes: list[RootCauseItem] = Field(
        default_factory=list, description="Statistically identified root causes and outcome drivers"
    )
    business_insights: list[StatisticsBusinessInsight] = Field(
        default_factory=list, description="Executive-level actionable takeaways"
    )


class StatisticsResponse(BaseModel):
    """API response envelope for Statistics Agent operations."""

    dataset_id: str = Field(..., description="Dataset ID analyzed")
    status: str = Field("success", description="Execution status")
    execution_time_ms: float = Field(..., description="Execution time in milliseconds")
    statistics_results: StatisticsResults = Field(..., description="Complete statistical inference results")
