"""Unit and integration tests for Phase 3.5 EDA Agent."""

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.agents.eda_agent import EDAAgent, EDAAgentRunner
from backend.app.main import create_app
from backend.app.models.base import Base
from backend.app.models.dataset import Dataset
from backend.app.models.dataset_metadata import DatasetMetadata
from backend.app.models.dataset_version import DatasetVersion
from backend.app.schemas.orchestrator import WorkflowContext
from backend.app.services.data_retrieval_service import DataRetrievalService
from backend.app.services.eda_service import EDAService


@pytest.fixture
def sales_dataframe() -> pd.DataFrame:
    """Fixture providing a standard sales dataset with known metrics."""
    np.random.seed(42)
    dates = pd.date_range("2024-01-01", periods=100, freq="D")
    marketing_spend = np.linspace(1000, 5000, 100) + np.random.normal(0, 50, 100)
    # Strong positive correlation with marketing spend
    revenue = marketing_spend * 2.5 + np.random.normal(0, 100, 100)
    # Add an outlier
    revenue[95] = 25000.0

    regions = ["North", "South", "East", "West"]
    region_col = np.random.choice(regions, size=100, p=[0.2, 0.45, 0.15, 0.2])  # South is dominant

    units = np.random.uniform(10, 50, 100)

    # Some missing values
    units[0] = np.nan
    units[1] = np.nan

    return pd.DataFrame({
        "order_date": dates,
        "revenue": revenue,
        "marketing_spend": marketing_spend,
        "region": region_col,
        "units_sold": units,
    })


@pytest.fixture
def in_memory_db() -> Session:
    """Isolated in-memory SQLite database session."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def eda_service() -> EDAService:
    return EDAService()


# -----------------------------------------------------------------------------
# 1. Dataset Understanding Tests
# -----------------------------------------------------------------------------

def test_detect_dataset_understanding_sales(eda_service: EDAService):
    df = pd.DataFrame({
        "order_id": [1, 2, 3],
        "product_name": ["A", "B", "C"],
        "revenue": [100.0, 200.0, 300.0],
        "discount": [5.0, 10.0, 0.0],
    })
    summary = eda_service._detect_dataset_understanding(df, "ds-1", False, 3)
    assert summary.dataset_type == "sales"
    assert "Sales" in summary.business_domain
    assert "revenue" in summary.numeric_columns
    assert "product_name" in summary.categorical_columns


def test_detect_dataset_understanding_marketing(eda_service: EDAService):
    df = pd.DataFrame({
        "campaign_id": [101, 102],
        "ad_clicks": [500, 1200],
        "impressions": [10000, 25000],
        "spend": [150.0, 320.0],
    })
    summary = eda_service._detect_dataset_understanding(df, "mkt-1", False, 2)
    assert summary.dataset_type == "marketing"
    assert "Marketing" in summary.business_domain


def test_detect_dataset_understanding_customer(eda_service: EDAService):
    df = pd.DataFrame({
        "user_id": [1, 2, 3],
        "churn": [0, 1, 0],
        "tenure": [12, 3, 24],
        "email": ["a@x.com", "b@x.com", "c@x.com"],
    })
    summary = eda_service._detect_dataset_understanding(df, "cust-1", False, 3)
    assert summary.dataset_type == "customer"


def test_detect_dataset_understanding_inventory(eda_service: EDAService):
    df = pd.DataFrame({
        "sku": ["SKU1", "SKU2"],
        "stock_quantity": [50, 120],
        "reorder_level": [20, 30],
        "warehouse": ["WH-North", "WH-East"],
    })
    summary = eda_service._detect_dataset_understanding(df, "inv-1", False, 2)
    assert summary.dataset_type == "inventory"


def test_detect_dataset_understanding_general(eda_service: EDAService):
    df = pd.DataFrame({"alpha": [1, 2], "beta": ["x", "y"]})
    summary = eda_service._detect_dataset_understanding(df, "gen-1", False, 2)
    assert summary.dataset_type == "general"


# -----------------------------------------------------------------------------
# 2. Statistical Summary Tests
# -----------------------------------------------------------------------------

def test_statistical_summary_known_values(eda_service: EDAService):
    df = pd.DataFrame({"val": [10.0, 20.0, 30.0, 40.0, 50.0]})
    stats = eda_service._calculate_statistical_summary(df, ["val"])
    assert "val" in stats
    s = stats["val"]
    assert s.count == 5
    assert s.mean == 30.0
    assert s.median == 30.0
    assert s.min == 10.0
    assert s.max == 50.0
    assert s.variance == 250.0
    assert s.q25 == 20.0
    assert s.q75 == 40.0


# -----------------------------------------------------------------------------
# 3. Missing Value Analysis Tests
# -----------------------------------------------------------------------------

def test_missing_values_analysis(eda_service: EDAService):
    df = pd.DataFrame({
        "a": [1, np.nan, 3, 4],
        "b": [np.nan, np.nan, 3, 4],
        "c": [1, 2, 3, 4],
    })
    missing = eda_service._analyze_missing_values(df)
    assert missing.total_missing_cells == 3
    assert missing.affected_columns_count == 2
    assert "a" in missing.affected_columns
    assert "b" in missing.affected_columns
    assert "c" not in missing.affected_columns
    assert missing.column_details["a"].missing_count == 1
    assert missing.column_details["a"].missing_percentage == 25.0
    assert missing.column_details["b"].missing_count == 2
    assert missing.column_details["b"].missing_percentage == 50.0


# -----------------------------------------------------------------------------
# 4. Distribution Analysis Tests
# -----------------------------------------------------------------------------

def test_distribution_analysis_normal_and_skewed(eda_service: EDAService):
    np.random.seed(42)
    normal_data = np.random.normal(loc=100, scale=15, size=2000)
    skewed_data = np.random.exponential(scale=2.0, size=2000)

    df = pd.DataFrame({"normal_col": normal_data, "skewed_col": skewed_data})
    dists = eda_service._analyze_distributions(df, ["normal_col", "skewed_col"])

    assert dists["normal_col"].distribution_type == "normal"
    assert dists["normal_col"].is_symmetric is True

    assert dists["skewed_col"].distribution_type == "skewed"
    assert dists["skewed_col"].is_symmetric is False


# -----------------------------------------------------------------------------
# 5. Outlier Detection Tests (IQR and Z-score)
# -----------------------------------------------------------------------------

def test_outlier_detection_iqr_and_zscore(eda_service: EDAService):
    data = [10.0] * 50
    data.append(500.0)  # High outlier
    df = pd.DataFrame({"metric": data})

    outliers = eda_service._detect_outliers(df, ["metric"])
    assert "metric" in outliers
    m = outliers["metric"]

    # IQR method should catch the 500
    assert m.iqr.outlier_count >= 1
    assert 500.0 in m.iqr.sample_outliers

    # Z-score method should also flag extreme deviation
    assert m.z_score.outlier_count >= 1


# -----------------------------------------------------------------------------
# 6. Correlation Analysis Tests
# -----------------------------------------------------------------------------

def test_correlation_analysis_strongest_pairs(eda_service: EDAService):
    np.random.seed(42)
    x = np.linspace(1, 100, 50)
    y_pos = 2 * x + np.random.normal(0, 1, 50)  # Strong positive
    y_neg = -3 * x + np.random.normal(0, 1, 50)  # Strong negative
    z_rand = np.random.normal(0, 10, 50)  # No correlation

    df = pd.DataFrame({"x": x, "y_pos": y_pos, "y_neg": y_neg, "z_rand": z_rand})
    corr = eda_service._analyze_correlations(df, ["x", "y_pos", "y_neg", "z_rand"])

    assert len(corr.strongest_correlations) >= 2
    assert corr.top_positive is not None
    assert corr.top_positive.correlation > 0.9
    assert corr.top_negative is not None
    assert corr.top_negative.correlation < -0.9


# -----------------------------------------------------------------------------
# 7. Trend Detection Tests
# -----------------------------------------------------------------------------

def test_trend_detection_growth(eda_service: EDAService):
    dates = pd.date_range("2024-01-01", periods=30, freq="D")
    revenue = np.linspace(100, 300, 30)  # +200% growth
    df = pd.DataFrame({"order_date": dates, "revenue": revenue})

    trends = eda_service._detect_trends(df, ["order_date"], ["revenue"])
    assert trends.has_time_series is True
    assert len(trends.trends) == 1
    t = trends.trends[0]
    assert t.trend_type == "growth"
    assert t.growth_rate_pct > 50.0
    assert "growth" in t.description.lower()


# -----------------------------------------------------------------------------
# 8. Category Analysis Tests
# -----------------------------------------------------------------------------

def test_categorical_analysis(eda_service: EDAService):
    df = pd.DataFrame({
        "status": ["active", "active", "active", "pending", "failed"],
        "region": ["North", "South", "East", "West", "North"],
    })
    cats = eda_service._analyze_categoricals(df, ["status", "region"])
    assert "status" in cats
    assert cats["status"].cardinality_level == "low"
    assert cats["status"].top_categories["active"] == 3
    assert cats["status"].frequency_distribution["active"] == 60.0


# -----------------------------------------------------------------------------
# 9. Business Insight Generation & End-to-End Analysis
# -----------------------------------------------------------------------------

def test_full_eda_analysis_and_business_insights(eda_service: EDAService, sales_dataframe: pd.DataFrame):
    results = eda_service.analyze_dataframe(sales_dataframe, dataset_id="sales-test-1")

    # Output schema compliance
    assert results.dataset_summary.dataset_type == "sales"
    assert results.dataset_summary.row_count == 100
    assert len(results.statistics) >= 3
    assert results.missing_values.total_missing_cells == 2
    assert "revenue" in results.outliers
    assert results.correlations.top_positive is not None
    assert results.trends.has_time_series is True
    assert len(results.business_insights) >= 4

    # Check that business insights translate stats to natural language
    insight_titles = [bi.title for bi in results.business_insights]
    assert any("Profile" in t for t in insight_titles)
    assert any("Correlation" in t or "Co-Movement" in t for t in insight_titles)


def test_empty_dataframe_handling(eda_service: EDAService):
    df = pd.DataFrame()
    results = eda_service.analyze_dataframe(df, dataset_id="empty-ds")
    assert results.dataset_summary.row_count == 0
    assert len(results.business_insights) == 1
    assert results.business_insights[0].title == "Empty Dataset"


def test_sampling_on_large_dataset(eda_service: EDAService):
    df = pd.DataFrame({"val": range(1005)})
    results = eda_service.analyze_dataframe(
        df,
        dataset_id="large-ds",
        max_rows_for_full=1000,
        sample_size_for_large=100,
    )
    assert results.dataset_summary.is_sampled is True
    assert results.dataset_summary.row_count == 1005


# -----------------------------------------------------------------------------
# 10. Agent Runner and Orchestrator Integration Tests
# -----------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_eda_agent_runner_with_context():
    np.random.seed(42)
    df = pd.DataFrame({
        "order_id": [1, 2, 3, 4, 5],
        "revenue": [100.0, 200.0, 150.0, 300.0, 250.0],
        "cost": [50.0, 90.0, 70.0, 140.0, 110.0],
    })

    class MockRetrievalService:
        def load_dataframe(self, dataset_id: str, **kwargs):
            return df, False

    runner = EDAAgentRunner(retrieval_service=MockRetrievalService())
    context = WorkflowContext(
        request_id="req-1",
        query="Analyze revenue and cost",
        intent="eda_analysis",
        dataset_id="test-sales-ds",
    )

    output = await runner.run(context)
    assert "dataset_summary" in output
    assert "statistics" in output
    assert "business_insights" in output
    assert output["dataset_summary"]["dataset_type"] == "sales"
    assert "revenue" in output["statistics"]


@pytest.mark.asyncio
async def test_eda_agent_runner_fallback_without_data():
    runner = EDAAgentRunner(retrieval_service=None)
    context = WorkflowContext(
        request_id="req-2",
        query="Analyze metrics",
        intent="eda_analysis",
        dataset_id="mock-ds",
        metadata={"row_count": 500, "column_count": 10},
    )

    output = await runner.run(context)
    assert output["dataset_shape"]["rows"] == 500
    assert "key_findings" in output


# -----------------------------------------------------------------------------
# 11. API Route Integration Tests
# -----------------------------------------------------------------------------

def test_api_eda_endpoint(sales_dataframe: pd.DataFrame):
    app = create_app()
    client = TestClient(app)

    from backend.app.api.v1.routes.eda import get_eda_service

    class MockService:
        async def analyze_dataset(self, dataset_id: str, **kwargs):
            svc = EDAService()
            return svc.analyze_dataframe(sales_dataframe, dataset_id=dataset_id)

    app.dependency_overrides[get_eda_service] = lambda: MockService()

    response = client.get("/api/v1/eda/test-ds-123")
    assert response.status_code == 200
    data = response.json()
    assert data["dataset_id"] == "test-ds-123"
    assert data["status"] == "success"
    assert "eda_results" in data
    assert data["eda_results"]["dataset_summary"]["dataset_type"] == "sales"
    assert len(data["eda_results"]["business_insights"]) > 0

    app.dependency_overrides.clear()
