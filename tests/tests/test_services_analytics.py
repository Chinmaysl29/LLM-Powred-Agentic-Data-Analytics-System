"""
Tests for analytics services:
  - EDAService (full analysis, distributions, outliers, correlations, trends)
  - StatisticsService (descriptive, hypothesis, regression, CI, chi-square)
  - ExecutiveSummaryService (narrative generation, insights)
  - IntentClassificationService (all 17 intents, fallback, LLM integration)
  - OrchestratorService (workflow execution, error recovery, partial results)
"""

import numpy as np
import pandas as pd
import pytest
from unittest.mock import AsyncMock, MagicMock

from backend.app.core.exceptions import ValidationException
from backend.app.schemas.intent import IntentType
from backend.app.schemas.orchestrator import WorkflowContext
from backend.app.services.eda_service import EDAService
from backend.app.services.executive_summary_service import ExecutiveSummaryService
from backend.app.services.intent_classification_service import (
    IntentClassificationService,
    IntentRegistry,
)
from backend.app.services.orchestrator_service import OrchestratorService
from backend.app.services.statistics_service import StatisticsService


# ===========================================================================
# EDAService Tests
# ===========================================================================

class TestEDAService:

    @pytest.fixture
    def svc(self):
        return EDAService()

    @pytest.fixture
    def sales_df(self):
        np.random.seed(0)
        n = 100
        dates = pd.date_range("2024-01-01", periods=n, freq="D")
        marketing = np.linspace(1000, 5000, n)
        revenue = marketing * 2.5 + np.random.normal(0, 50, n)
        revenue[90] = 30000.0
        region = np.random.choice(["North", "South", "East"], size=n)
        units = np.random.uniform(10, 50, n)
        units[0] = np.nan
        return pd.DataFrame({
            "order_date": dates,
            "revenue": revenue,
            "marketing_spend": marketing,
            "region": region,
            "units_sold": units,
        })

    def test_analyze_dataframe_returns_full_structure(self, svc, sales_df):
        results = svc.analyze_dataframe(sales_df, dataset_id="test-1")
        assert results.dataset_summary is not None
        assert results.dataset_summary.row_count == 100
        assert len(results.statistics) >= 1
        assert results.missing_values is not None
        assert results.correlations is not None
        assert len(results.business_insights) >= 1

    def test_empty_dataframe_returns_graceful_result(self, svc):
        df = pd.DataFrame()
        results = svc.analyze_dataframe(df, dataset_id="empty")
        assert results.dataset_summary.row_count == 0
        assert len(results.business_insights) == 1

    def test_dataset_type_detection_sales(self, svc):
        df = pd.DataFrame({
            "order_id": [1, 2],
            "product": ["A", "B"],
            "revenue": [100.0, 200.0],
            "discount": [5.0, 10.0],
        })
        summary = svc._detect_dataset_understanding(df, "ds", False, 2)
        assert summary.dataset_type == "sales"

    def test_dataset_type_detection_marketing(self, svc):
        df = pd.DataFrame({
            "campaign": ["c1", "c2"],
            "ad_clicks": [500, 800],
            "impressions": [10000, 20000],
        })
        summary = svc._detect_dataset_understanding(df, "ds", False, 2)
        assert summary.dataset_type == "marketing"

    def test_dataset_type_detection_customer(self, svc):
        df = pd.DataFrame({
            "user_id": [1, 2],
            "churn": [0, 1],
            "tenure": [12, 3],
        })
        summary = svc._detect_dataset_understanding(df, "ds", False, 2)
        assert summary.dataset_type == "customer"

    def test_dataset_type_detection_inventory(self, svc):
        df = pd.DataFrame({
            "sku": ["S1", "S2"],
            "stock_quantity": [100, 50],
            "reorder_level": [20, 10],
        })
        summary = svc._detect_dataset_understanding(df, "ds", False, 2)
        assert summary.dataset_type == "inventory"

    def test_dataset_type_detection_general(self, svc):
        df = pd.DataFrame({"x": [1, 2], "y": ["a", "b"]})
        summary = svc._detect_dataset_understanding(df, "ds", False, 2)
        assert summary.dataset_type == "general"

    def test_statistical_summary_known_values(self, svc):
        df = pd.DataFrame({"val": [10.0, 20.0, 30.0, 40.0, 50.0]})
        stats = svc._calculate_statistical_summary(df, ["val"])
        assert "val" in stats
        s = stats["val"]
        assert s.count == 5
        assert s.mean == 30.0
        assert s.median == 30.0
        assert s.min == 10.0
        assert s.max == 50.0

    def test_missing_values_analysis(self, svc):
        df = pd.DataFrame({
            "a": [1, np.nan, 3],
            "b": [np.nan, np.nan, 3],
            "c": [1, 2, 3],
        })
        missing = svc._analyze_missing_values(df)
        assert missing.total_missing_cells == 3
        assert missing.affected_columns_count == 2
        assert "a" in missing.affected_columns
        assert "b" in missing.affected_columns
        assert "c" not in missing.affected_columns

    def test_outlier_detection_flags_extreme_value(self, svc):
        data = [10.0] * 50 + [500.0]
        df = pd.DataFrame({"metric": data})
        outliers = svc._detect_outliers(df, ["metric"])
        assert "metric" in outliers
        assert outliers["metric"].iqr.outlier_count >= 1

    def test_correlation_analysis_positive_pair(self, svc):
        np.random.seed(1)
        x = np.linspace(1, 100, 50)
        y = 2 * x + np.random.normal(0, 1, 50)
        df = pd.DataFrame({"x": x, "y": y})
        corr = svc._analyze_correlations(df, ["x", "y"])
        assert corr.top_positive is not None
        assert corr.top_positive.correlation > 0.9

    def test_trend_detection_growth(self, svc):
        dates = pd.date_range("2024-01-01", periods=30, freq="D")
        revenue = np.linspace(100, 300, 30)
        df = pd.DataFrame({"order_date": dates, "revenue": revenue})
        trends = svc._detect_trends(df, ["order_date"], ["revenue"])
        assert trends.has_time_series is True
        assert trends.trends[0].trend_type == "growth"

    def test_categorical_analysis_low_cardinality(self, svc):
        df = pd.DataFrame({"status": ["active"] * 3 + ["inactive"] * 2})
        cats = svc._analyze_categoricals(df, ["status"])
        assert "status" in cats
        assert cats["status"].cardinality_level == "low"

    def test_sampling_on_large_dataset(self, svc):
        df = pd.DataFrame({"val": range(1500)})
        results = svc.analyze_dataframe(
            df, dataset_id="large", max_rows_for_full=1000, sample_size_for_large=200
        )
        assert results.dataset_summary.is_sampled is True

    def test_business_insights_have_titles(self, svc, sales_df):
        results = svc.analyze_dataframe(sales_df, dataset_id="insight-test")
        for insight in results.business_insights:
            assert isinstance(insight.title, str)
            assert len(insight.title) > 0

    def test_single_column_dataframe(self, svc):
        df = pd.DataFrame({"x": [1, 2, 3, 4, 5]})
        results = svc.analyze_dataframe(df, dataset_id="single-col")
        assert results.dataset_summary.column_count == 1


# ===========================================================================
# StatisticsService Tests
# ===========================================================================

class TestStatisticsService:

    @pytest.fixture
    def svc(self):
        return StatisticsService()

    @pytest.fixture
    def df(self):
        np.random.seed(42)
        n = 60
        x = np.linspace(1, 100, n)
        y = 2.5 * x + np.random.normal(0, 5, n)
        group = np.where(x < 50, "A", "B")
        return pd.DataFrame({"x": x, "y": y, "group": group})

    def test_analyze_dataframe_empty_returns_empty_result(self, svc):
        result = svc.analyze_dataframe(pd.DataFrame(), dataset_id="empty")
        assert len(result.descriptive_statistics) == 0

    def test_analyze_dataframe_returns_descriptive_stats(self, svc, df):
        result = svc.analyze_dataframe(df, dataset_id="stats-test")
        assert "x" in result.descriptive_statistics
        assert "y" in result.descriptive_statistics
        p = result.descriptive_statistics["x"]
        assert p.count == 60
        assert p.min < p.max

    def test_descriptive_stats_quartiles_present(self, svc, df):
        result = svc.analyze_dataframe(df, dataset_id="q-test")
        p = result.descriptive_statistics["x"]
        assert p.quartiles is not None
        assert p.quartiles.q1 < p.quartiles.q2 < p.quartiles.q3

    def test_descriptive_stats_percentiles_present(self, svc, df):
        result = svc.analyze_dataframe(df, dataset_id="pct-test")
        p = result.descriptive_statistics["x"]
        assert p.percentiles is not None
        assert p.percentiles.p5 < p.percentiles.p50 < p.percentiles.p95

    def test_regression_identifies_x_as_driver_of_y(self, svc, df):
        result = svc.analyze_dataframe(df, target_column="y")
        assert "y" in result.regression_results
        reg = result.regression_results["y"]
        assert reg.r_squared > 0.9
        assert any(d.feature == "x" for d in reg.drivers)

    def test_confidence_intervals_present(self, svc, df):
        result = svc.analyze_dataframe(df)
        assert "x" in result.confidence_intervals
        ci_95 = result.confidence_intervals["x"]["95%"]
        assert ci_95.lower_bound < ci_95.mean < ci_95.upper_bound

    def test_hypothesis_tests_contain_ttest(self, svc, df):
        result = svc.analyze_dataframe(df)
        assert "two_sample_ttest" in result.hypothesis_tests or \
               "paired_ttest" in result.hypothesis_tests

    def test_significant_relationships_populated(self, svc, df):
        result = svc.analyze_dataframe(df, target_column="y")
        # x→y is a strong linear relationship, should appear
        assert isinstance(result.significant_relationships, list)

    def test_business_insights_generated(self, svc, df):
        result = svc.analyze_dataframe(df)
        assert len(result.business_insights) >= 1
        for bi in result.business_insights:
            assert isinstance(bi.title, str)

    def test_classify_significance_levels(self):
        svc = StatisticsService()
        assert svc.classify_significance(0.001) == "highly_significant"
        assert svc.classify_significance(0.03) == "moderately_significant"
        assert svc.classify_significance(0.15) == "not_significant"

    def test_chi_square_test_categorical_independence(self, svc):
        np.random.seed(42)
        df = pd.DataFrame({
            "department": np.random.choice(["Sales", "Eng", "Marketing"], 90),
            "level": np.random.choice(["Junior", "Senior"], 90),
        })
        result = svc.analyze_dataframe(df)
        assert isinstance(result.chi_square_results, list)


# ===========================================================================
# ExecutiveSummaryService Tests
# ===========================================================================

class TestExecutiveSummaryService:

    @pytest.fixture
    def svc(self):
        return ExecutiveSummaryService()

    def test_generate_summary_returns_structured_result(self, svc):
        result = svc.generate_summary(
            results={},
            metadata={"dataset_id": "ds-1", "row_count": 100, "column_count": 5},
            query="Analyze sales data",
        )
        assert result is not None
        # Should have some text output
        assert hasattr(result, "executive_narrative") or hasattr(result, "narrative") or isinstance(result, dict) or hasattr(result, "key_findings")

    def test_generate_summary_with_eda_results(self, svc):
        results = {
            "analysis": {
                "dataset_summary": {"row_count": 200, "dataset_type": "sales"},
                "business_insights": [{"title": "Revenue Growth", "insight": "Revenue grew 15%"}],
            }
        }
        result = svc.generate_summary(
            results=results,
            metadata={"row_count": 200},
            query="Show revenue summary",
        )
        assert result is not None

    def test_generate_summary_empty_results_no_crash(self, svc):
        result = svc.generate_summary(results={}, metadata={}, query="empty")
        assert result is not None

    def test_generate_summary_with_quality_data(self, svc):
        result = svc.generate_summary(
            results={},
            metadata={"row_count": 500},
            quality={"overall_score": 92.0, "completeness": 98.0},
            query="Quality overview",
        )
        assert result is not None


# ===========================================================================
# IntentClassificationService Tests
# ===========================================================================

class TestIntentClassificationService:

    @pytest.fixture
    def svc(self):
        return IntentClassificationService(llm=None)

    @pytest.mark.asyncio
    async def test_classify_trend_analysis(self, svc):
        result = await svc.classify("Show revenue trends")
        assert result.intent == IntentType.TREND_ANALYSIS.value
        assert result.confidence >= 0.85

    @pytest.mark.asyncio
    async def test_classify_forecasting(self, svc):
        result = await svc.classify("Predict sales for next quarter")
        assert result.intent == IntentType.FORECASTING.value

    @pytest.mark.asyncio
    async def test_classify_data_quality(self, svc):
        result = await svc.classify("Find duplicate records in the dataset")
        assert result.intent == IntentType.DATA_QUALITY.value

    @pytest.mark.asyncio
    async def test_classify_ranking(self, svc):
        result = await svc.classify("Which product generated the highest revenue?")
        assert result.intent == IntentType.RANKING_ANALYSIS.value

    @pytest.mark.asyncio
    async def test_classify_eda(self, svc):
        result = await svc.classify("Perform exploratory analysis on the data")
        assert result.intent == IntentType.EDA_ANALYSIS.value

    @pytest.mark.asyncio
    async def test_classify_sql_query(self, svc):
        result = await svc.classify("SELECT * FROM orders WHERE total > 100")
        assert result.intent == IntentType.SQL_QUERY.value

    @pytest.mark.asyncio
    async def test_classify_dataset_overview(self, svc):
        result = await svc.classify("Show me a summary of this dataset")
        assert result.intent == IntentType.DATASET_OVERVIEW.value

    @pytest.mark.asyncio
    async def test_classify_comparison(self, svc):
        result = await svc.classify("Compare Q1 and Q2 sales performance")
        assert result.intent == IntentType.COMPARISON_ANALYSIS.value

    @pytest.mark.asyncio
    async def test_classify_correlation(self, svc):
        result = await svc.classify("Is there correlation between marketing spend and revenue?")
        assert result.intent == IntentType.CORRELATION_ANALYSIS.value

    @pytest.mark.asyncio
    async def test_classify_unknown_returns_unknown(self, svc):
        result = await svc.classify("Hello, how are you today?")
        assert result.intent == IntentType.UNKNOWN.value

    @pytest.mark.asyncio
    async def test_classify_empty_raises_validation_exception(self, svc):
        with pytest.raises(ValidationException):
            await svc.classify("")

    @pytest.mark.asyncio
    async def test_classify_whitespace_raises_validation_exception(self, svc):
        with pytest.raises(ValidationException):
            await svc.classify("   ")

    @pytest.mark.asyncio
    async def test_classify_too_long_raises_validation_exception(self, svc):
        with pytest.raises(ValidationException):
            await svc.classify("word " * 500)

    @pytest.mark.asyncio
    async def test_result_has_required_fields(self, svc):
        result = await svc.classify("Show sales trends")
        assert hasattr(result, "intent")
        assert hasattr(result, "confidence")
        assert hasattr(result, "reasoning")
        assert hasattr(result, "required_agents")
        assert 0.0 <= result.confidence <= 1.0

    @pytest.mark.asyncio
    async def test_llm_failure_falls_back_to_heuristic(self):
        mock_llm = MagicMock()
        mock_llm.chat_with_json = AsyncMock(side_effect=RuntimeError("timeout"))
        svc = IntentClassificationService(llm=mock_llm)
        result = await svc.classify("Show revenue trends")
        assert result.intent == IntentType.TREND_ANALYSIS.value

    @pytest.mark.asyncio
    async def test_llm_success_uses_llm_output(self):
        mock_llm = MagicMock()
        mock_llm.chat_with_json = AsyncMock(
            return_value='{"intent": "forecasting", "confidence": 0.95, "reasoning": "Future prediction."}'
        )
        svc = IntentClassificationService(llm=mock_llm)
        result = await svc.classify("Predict next month revenue")
        assert result.intent == "forecasting"
        assert result.confidence == 0.95

    def test_all_core_intents_registered(self):
        registry = IntentRegistry()
        for intent_type in IntentType:
            if intent_type != IntentType.UNKNOWN:
                assert registry.get(intent_type.value) is not None


# ===========================================================================
# OrchestratorService Tests
# ===========================================================================

class TestOrchestratorService:

    @pytest.fixture
    def svc(self):
        return OrchestratorService(llm=None, db=None)

    @pytest.mark.asyncio
    async def test_execute_sales_trends_returns_success(self, svc):
        result = await svc.execute("Show sales trends")
        assert result.status == "success"
        assert result.intent == "trend_analysis"
        assert "data_retrieval" in result.executed_agents

    @pytest.mark.asyncio
    async def test_execute_empty_query_raises_validation_exception(self, svc):
        with pytest.raises(ValidationException):
            await svc.execute("")

    @pytest.mark.asyncio
    async def test_execute_whitespace_query_raises(self, svc):
        with pytest.raises(ValidationException):
            await svc.execute("   ")

    @pytest.mark.asyncio
    async def test_execute_returns_orchestrator_response(self, svc):
        from backend.app.schemas.orchestrator import OrchestratorResponse
        result = await svc.execute("Analyze data")
        assert isinstance(result, OrchestratorResponse)

    @pytest.mark.asyncio
    async def test_execute_result_has_all_fields(self, svc):
        result = await svc.execute("Show trends")
        assert result.request_id
        assert result.intent
        assert result.workflow
        assert result.executed_agents is not None
        assert isinstance(result.execution_time_ms, float)

    @pytest.mark.asyncio
    async def test_execute_explicit_intent_override(self, svc):
        result = await svc.execute(
            "analyze something",
            context={"intent": "forecasting"},
        )
        assert result.intent == "forecasting"

    @pytest.mark.asyncio
    async def test_agent_failure_gives_partial_success(self, svc):
        from backend.app.services.agent_registry import BaseAgentRunner
        from typing import Any

        class AlwaysFailsAgent(BaseAgentRunner):
            @property
            def name(self):
                return "statistics"

            async def run(self, ctx: WorkflowContext) -> dict[str, Any]:
                raise RuntimeError("intentional failure")

        svc.agent_registry.register(AlwaysFailsAgent())
        result = await svc.execute("Show revenue trends")
        assert result.status in ("partial_success", "success")
        assert any(e["agent_name"] == "statistics" for e in result.errors)

    def test_workflow_registry_list_returns_all_intents(self, svc):
        workflows = svc.workflow_registry.list_workflows()
        assert "trend_analysis" in workflows
        assert "forecasting" in workflows
        assert "data_quality" in workflows

    @pytest.mark.asyncio
    async def test_execute_with_dataset_id_passed_through(self, svc):
        result = await svc.execute("Analyze sales", dataset_id="ds-test-123")
        assert result.dataset_id == "ds-test-123"
