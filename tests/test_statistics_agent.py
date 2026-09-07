"""Unit and integration tests for Phase 3.6 Statistics Agent."""

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from backend.agents.statistics_agent import StatisticsAgentRunner
from backend.app.main import create_app
from backend.app.schemas.orchestrator import WorkflowContext
from backend.app.services.statistics_service import StatisticsService


@pytest.fixture
def sales_regression_df() -> pd.DataFrame:
    """Fixture providing a sales dataset where marketing spend strongly drives revenue."""
    np.random.seed(42)
    n = 100
    marketing = np.linspace(1000, 10000, n) + np.random.normal(0, 100, n)
    customers = np.linspace(50, 500, n) + np.random.normal(0, 10, n)
    discount = np.random.uniform(5, 25, n)

    # Revenue strongly determined by marketing (dominant) + customers (secondary)
    revenue = 3.5 * marketing + 15.0 * customers + np.random.normal(0, 500, n)

    # Categorical variables for hypothesis & chi-square tests
    # 2-group category
    segment = np.random.choice(["Enterprise", "SMB"], size=n, p=[0.5, 0.5])
    # Multi-group category with differing means
    region = np.random.choice(["North", "South", "East"], size=n, p=[0.33, 0.33, 0.34])
    # Give South higher revenue
    for i in range(n):
        if region[i] == "South":
            revenue[i] += 5000.0

    # Before vs After metric for paired t-test
    before_score = np.random.normal(70, 10, n)
    after_score = before_score + np.random.normal(12, 3, n)  # Significantly higher

    return pd.DataFrame({
        "revenue": revenue,
        "marketing_spend": marketing,
        "customer_count": customers,
        "discount": discount,
        "segment": segment,
        "region": region,
        "before_score": before_score,
        "after_score": after_score,
    })


@pytest.fixture
def stats_service() -> StatisticsService:
    return StatisticsService()


# -----------------------------------------------------------------------------
# 1. Descriptive Statistics Tests
# -----------------------------------------------------------------------------

def test_descriptive_statistics_quartiles_and_percentiles(stats_service: StatisticsService):
    data = list(range(1, 101))  # 1 to 100
    df = pd.DataFrame({"val": data})
    profiles = stats_service._calculate_descriptive_statistics(df, ["val"])

    assert "val" in profiles
    p = profiles["val"]
    assert p.count == 100
    assert p.mean == 50.5
    assert p.median == 50.5
    assert p.min == 1.0
    assert p.max == 100.0
    assert p.range_val == 99.0

    # Quartiles
    assert p.quartiles.q1 == 25.75
    assert p.quartiles.q3 == 75.25
    assert p.quartiles.iqr == 49.5

    # Percentiles
    assert p.percentiles.p5 < p.percentiles.p10 < p.percentiles.p50 < p.percentiles.p90 < p.percentiles.p95


# -----------------------------------------------------------------------------
# 2. Hypothesis Testing Tests
# -----------------------------------------------------------------------------

def test_hypothesis_testing_two_sample_ttest(stats_service: StatisticsService):
    np.random.seed(42)
    group_a = np.random.normal(100, 5, 50)
    group_b = np.random.normal(130, 5, 50)  # Significant difference

    df = pd.DataFrame({
        "score": np.concatenate([group_a, group_b]),
        "variant": ["A"] * 50 + ["B"] * 50,
    })

    tests = stats_service._perform_hypothesis_tests(df, ["score"], ["variant"])
    assert len(tests["two_sample_ttest"]) >= 1
    t_res = tests["two_sample_ttest"][0]
    assert t_res.p_value < 0.001
    assert t_res.null_hypothesis_rejected is True
    assert t_res.significance_tier == "highly_significant"
    assert "Statistically significant difference" in t_res.interpretation


def test_hypothesis_testing_paired_ttest(stats_service: StatisticsService):
    np.random.seed(42)
    before = np.random.normal(50, 5, 40)
    after = before + 10.0  # Strict paired increase

    df = pd.DataFrame({"before": before, "after": after})
    tests = stats_service._perform_hypothesis_tests(df, ["before", "after"], [])
    assert len(tests["paired_ttest"]) >= 1
    p_res = tests["paired_ttest"][0]
    assert p_res.p_value < 0.001
    assert p_res.null_hypothesis_rejected is True


def test_hypothesis_testing_anova(stats_service: StatisticsService):
    np.random.seed(42)
    g1 = np.random.normal(10, 2, 30)
    g2 = np.random.normal(20, 2, 30)
    g3 = np.random.normal(30, 2, 30)

    df = pd.DataFrame({
        "metric": np.concatenate([g1, g2, g3]),
        "category": ["Low"] * 30 + ["Medium"] * 30 + ["High"] * 30,
    })

    tests = stats_service._perform_hypothesis_tests(df, ["metric"], ["category"])
    assert len(tests["one_way_anova"]) >= 1
    anova_res = tests["one_way_anova"][0]
    assert anova_res.p_value < 0.001
    assert anova_res.null_hypothesis_rejected is True
    assert anova_res.statistic > 50.0


# -----------------------------------------------------------------------------
# 3. Correlation Significance Tests
# -----------------------------------------------------------------------------

def test_correlation_significance(stats_service: StatisticsService):
    np.random.seed(42)
    x = np.linspace(1, 100, 60)
    y_correlated = 3.0 * x + np.random.normal(0, 5, 60)
    z_noise = np.random.normal(0, 100, 60)

    df = pd.DataFrame({"x": x, "y_corr": y_correlated, "z_noise": z_noise})
    corrs, sig_rels = stats_service._analyze_correlation_significance(df, ["x", "y_corr", "z_noise"])

    assert "x:y_corr" in corrs
    assert corrs["x:y_corr"]["p_value"] < 0.001
    assert corrs["x:y_corr"]["significance"] == "highly_significant"

    # Confirmed relationship recorded
    assert any(r.target_variable == "y_corr" or r.source_variable == "y_corr" for r in sig_rels)


# -----------------------------------------------------------------------------
# 4. Regression Analysis & Feature Importance Tests
# -----------------------------------------------------------------------------

def test_regression_analysis_and_drivers(stats_service: StatisticsService, sales_regression_df: pd.DataFrame):
    results = stats_service._perform_regression_analysis(
        sales_regression_df,
        numeric_cols=["revenue", "marketing_spend", "customer_count", "discount"],
        target_column="revenue",
    )

    assert "revenue" in results
    reg = results["revenue"]
    assert reg.r_squared > 0.85  # Strong fit
    assert reg.p_value < 0.001
    assert reg.strongest_driver is not None
    assert reg.strongest_driver in ["marketing_spend", "customer_count"]

    # Ranked drivers
    assert len(reg.drivers) == 3
    driver_features = [d.feature for d in reg.drivers]
    assert "marketing_spend" in driver_features
    assert "customer_count" in driver_features
    assert reg.drivers[0].importance_rank == 1


# -----------------------------------------------------------------------------
# 5. Confidence Intervals Tests
# -----------------------------------------------------------------------------

def test_confidence_intervals_bounds(stats_service: StatisticsService):
    np.random.seed(42)
    sample = np.random.normal(loc=100.0, scale=10.0, size=50)
    df = pd.DataFrame({"metric": sample})

    ci_dict = stats_service._calculate_confidence_intervals(df, ["metric"])
    assert "metric" in ci_dict
    ci95 = ci_dict["metric"]["95%"]
    ci99 = ci_dict["metric"]["99%"]

    # Bounds must bracket the mean
    assert ci95.lower_bound < ci95.mean < ci95.upper_bound
    assert ci99.lower_bound < ci99.mean < ci99.upper_bound

    # 99% CI must be wider than 95% CI
    assert ci99.margin_of_error > ci95.margin_of_error
    assert ci99.lower_bound < ci95.lower_bound
    assert ci99.upper_bound > ci95.upper_bound


# -----------------------------------------------------------------------------
# 6. Chi-Square Tests of Independence Tests
# -----------------------------------------------------------------------------

def test_chi_square_dependent_and_independent(stats_service: StatisticsService):
    # Dependent columns
    seg = ["Enterprise"] * 40 + ["SMB"] * 40
    support = ["Priority"] * 35 + ["Standard"] * 5 + ["Priority"] * 5 + ["Standard"] * 35

    df = pd.DataFrame({"segment": seg, "support": support})
    chi_results = stats_service._perform_chi_square_tests(df, ["segment", "support"])

    assert len(chi_results) >= 1
    c = chi_results[0]
    assert c.is_dependent is True
    assert c.p_value < 0.001
    assert c.significance_tier == "highly_significant"


# -----------------------------------------------------------------------------
# 7. Statistical Significance Classification Tests
# -----------------------------------------------------------------------------

def test_significance_classification():
    assert StatisticsService.classify_significance(0.0001) == "highly_significant"
    assert StatisticsService.classify_significance(0.0099) == "highly_significant"
    assert StatisticsService.classify_significance(0.0100) == "moderately_significant"
    assert StatisticsService.classify_significance(0.0499) == "moderately_significant"
    assert StatisticsService.classify_significance(0.0500) == "not_significant"
    assert StatisticsService.classify_significance(0.5000) == "not_significant"


# -----------------------------------------------------------------------------
# 8. Root Cause Detection Tests
# -----------------------------------------------------------------------------

def test_root_cause_detection(stats_service: StatisticsService, sales_regression_df: pd.DataFrame):
    results = stats_service.analyze_dataframe(sales_regression_df, dataset_id="sales-rc-1")

    assert len(results.root_causes) >= 1
    top_rc = results.root_causes[0]
    assert top_rc.target_metric == "revenue"
    assert top_rc.primary_driver in ["marketing_spend", "customer_count"]
    assert top_rc.variance_explained_pct > 80.0
    assert "positive" in top_rc.direction.lower() or "divergent" in top_rc.direction.lower()


# -----------------------------------------------------------------------------
# 9. Business Insight Generation Tests
# -----------------------------------------------------------------------------

def test_business_insights_generation(stats_service: StatisticsService, sales_regression_df: pd.DataFrame):
    results = stats_service.analyze_dataframe(sales_regression_df, dataset_id="sales-insights-1")

    assert len(results.business_insights) >= 3
    insight_text = " ".join(bi.insight for bi in results.business_insights)

    # Must mention driver variance explanation and confidence
    assert "variance" in insight_text.lower() or "growth factor" in insight_text.lower()
    assert "confidence" in insight_text.lower()


def test_empty_dataframe_returns_clean_fallback(stats_service: StatisticsService):
    df = pd.DataFrame()
    results = stats_service.analyze_dataframe(df, dataset_id="empty")
    assert len(results.descriptive_statistics) == 0
    assert len(results.business_insights) == 1
    assert results.business_insights[0].title == "Empty Dataset"


# -----------------------------------------------------------------------------
# 10. Agent Runner and Orchestrator Integration Tests
# -----------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_statistics_agent_runner_with_context(sales_regression_df: pd.DataFrame):
    class MockRetrieval:
        def load_dataframe(self, dataset_id: str, **kwargs):
            return sales_regression_df, False

    runner = StatisticsAgentRunner(retrieval_service=MockRetrieval())
    context = WorkflowContext(
        request_id="req-stats-1",
        query="Run regression and hypothesis tests on sales",
        intent="eda_analysis",
        dataset_id="sales-ds",
    )

    output = await runner.run(context)
    assert "descriptive_statistics" in output
    assert "regression_results" in output
    assert "confidence_intervals" in output
    assert "business_insights" in output
    assert "revenue" in output["regression_results"]


@pytest.mark.asyncio
async def test_statistics_agent_runner_fallback_without_data():
    runner = StatisticsAgentRunner(retrieval_service=None)
    context = WorkflowContext(
        request_id="req-stats-2",
        query="Statistical summary",
        intent="eda_analysis",
        dataset_id="mock-ds",
        metadata={"row_count": 500},
    )

    output = await runner.run(context)
    assert output["statistical_significance"] == "high"
    assert "confidence_interval" in output


# -----------------------------------------------------------------------------
# 11. API Route Integration Tests
# -----------------------------------------------------------------------------

def test_api_statistics_endpoint(sales_regression_df: pd.DataFrame):
    app = create_app()
    client = TestClient(app)

    from backend.app.api.v1.routes.statistics import get_statistics_service

    class MockStatsService:
        async def analyze_dataset(self, dataset_id: str, **kwargs):
            svc = StatisticsService()
            return svc.analyze_dataframe(sales_regression_df, dataset_id=dataset_id)

    app.dependency_overrides[get_statistics_service] = lambda: MockStatsService()

    response = client.get("/api/v1/statistics/test-sales-101")
    assert response.status_code == 200
    data = response.json()
    assert data["dataset_id"] == "test-sales-101"
    assert data["status"] == "success"
    assert "statistics_results" in data
    assert "revenue" in data["statistics_results"]["regression_results"]
    assert len(data["statistics_results"]["business_insights"]) > 0

    app.dependency_overrides.clear()
