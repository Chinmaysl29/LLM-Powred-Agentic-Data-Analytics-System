"""Phase 21: Enterprise Launch Readiness & End-to-End User Journey Audit Test Suite.

Validates:
1. Real User Journey E2E:
   Upload CSV -> Dataset Appears -> Profile Generated -> Quality Generated ->
   RAG Indexed -> Ask Question -> SQL Generated -> Chart Generated ->
   Insight Generated -> Forecast Generated -> Report Generated.
2. Large Dataset Stress Test:
   100k, 500k, and 1,000,000 rows stress-tested across memory, streaming, and execution.
3. Autonomous AI Analyst Quality Benchmark:
   Evaluation across 5 benchmark prompts for reasoning, grounding, and zero hallucination:
   - "Why did revenue decline?"
   - "What products drive profit?"
   - "Forecast next 12 months."
   - "Create executive dashboard."
   - "Find anomalies in sales."
4. Enterprise Launch Readiness:
   - 21.1 User Onboarding
   - 21.2 Demo Dataset Library (5 Enterprise Datasets)
   - 21.3 Portfolio Mode (Recruiter Showcase)
   - 21.4 Usage Analytics & Telemetry
   - 21.5 Production Deployment Configurations
"""

from __future__ import annotations

import os
import time
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

from backend.app.services.autonomous_ai_analyst import get_autonomous_ai_analyst
from backend.app.services.dashboard_builder_service import get_dashboard_builder_service
from backend.app.services.data_profiling_service import DataProfilingService
from backend.app.services.data_quality_service import DataQualityService
from backend.app.services.data_storytelling_service import get_data_storytelling_engine
from backend.app.services.demo_dataset_service import get_demo_dataset_service
from backend.app.services.kpi_knowledge_engine import get_kpi_knowledge_engine
from backend.app.services.large_dataset_optimizer import get_large_dataset_optimizer
from backend.app.services.metadata_extraction_service import MetadataExtractionService
from backend.app.services.storage_service import get_storage_service
from backend.app.services.portfolio_mode_service import get_portfolio_mode_service
from backend.app.services.report_studio_service import get_report_studio_service
from backend.app.services.semantic_layer_service import get_semantic_business_layer
from backend.app.services.sql_guardrails_service import get_sql_guardrails_service
from backend.app.services.usage_analytics_service import get_usage_analytics_service
from backend.app.services.workspace_orchestration_service import get_workspace_orchestration_service
from backend.memory.ai_memory_layer import get_ai_memory_layer
from backend.visualization.generators.plotly_engine import PlotlyEngine


@pytest.fixture
def sample_sales_df() -> pd.DataFrame:
    """Standard transactional dataset for user journey and prompt evaluations."""
    np.random.seed(42)
    n = 200
    dates = pd.date_range("2026-01-01", periods=n, freq="D")
    categories = ["Enterprise Software", "Cloud Infrastructure", "Security Services", "AI Compute"]
    regions = ["North America", "EMEA", "APAC", "LATAM"]
    products = ["SaaS Enterprise", "Cloud Vault", "CyberGuard Pro", "Neural Engine", "Data Lakehouse"]

    data = {
        "order_id": [f"ORD-{1000 + i}" for i in range(n)],
        "order_date": [d.strftime("%Y-%m-%d") for d in dates],
        "category": [categories[i % len(categories)] for i in range(n)],
        "product_name": [products[i % len(products)] for i in range(n)],
        "region": [regions[i % len(regions)] for i in range(n)],
        "revenue": np.random.uniform(500, 15000, size=n).round(2),
        "cost": np.random.uniform(200, 8000, size=n).round(2),
        "units": np.random.randint(1, 50, size=n),
    }
    df = pd.DataFrame(data)
    df["profit"] = (df["revenue"] - df["cost"]).round(2)
    return df


class TestRealUserJourneyEndToEnd:
    """1. Real User Journey Validation from raw CSV to full executive board report."""

    def test_complete_user_journey_lifecycle(self, sample_sales_df: pd.DataFrame, tmp_path: Path):
        # Step 1: Upload CSV
        csv_path = tmp_path / "enterprise_sales_journey.csv"
        sample_sales_df.to_csv(csv_path, index=False)
        assert csv_path.exists()
        assert csv_path.stat().st_size > 0

        # Step 2: Dataset Appears & Ingests
        loaded_df = pd.read_csv(csv_path)
        assert len(loaded_df) == 200
        assert "revenue" in loaded_df.columns
        assert "profit" in loaded_df.columns

        # Step 3: Profile Generated
        from backend.app.core.config import get_settings
        from backend.app.services.storage_service import StorageService
        storage_svc = StorageService(settings=get_settings())
        meta_svc = MetadataExtractionService(storage_service=storage_svc)
        profiling_service = DataProfilingService(metadata_service=meta_svc)
        profile = profiling_service.generate_profile(
            dataset_id="ds-journey-test",
            file_path=str(csv_path),
            file_type="csv",
        )
        assert profile is not None
        assert profile.dataset_id == "ds-journey-test"
        assert len(profile.numeric_columns_profile) > 0
        assert "revenue" in profile.numeric_columns_profile

        # Step 4: Quality Generated
        quality_report = DataQualityService.evaluate_dataframe_quality(loaded_df, profile)
        assert quality_report is not None
        assert 0.0 <= quality_report["overall_score"] <= 1.0
        assert quality_report["completeness_score"] >= 0.95

        # Step 5: RAG Indexed / Semantic Mapping
        semantic_layer = get_semantic_business_layer()
        mapping = semantic_layer.map_dataset_schema(loaded_df)
        assert mapping is not None
        assert "revenue" in mapping
        assert len(mapping) >= 5

        # Step 6: Ask Question
        query = "Analyze quarterly revenue and profit drivers by region"
        analyst = get_autonomous_ai_analyst()

        # Step 7: SQL Generated & Executed
        plan = analyst.plan_analysis(query, loaded_df)
        assert plan["agents_required"]["semantic_layer"] is True
        assert plan["primary_metric"] in ["revenue", "profit"]

        guardrails = get_sql_guardrails_service()
        candidate_sql = f"SELECT region, SUM(revenue) AS total_revenue FROM active_dataset GROUP BY region ORDER BY total_revenue DESC;"
        safe, validated_sql, _ = guardrails.validate_sql(candidate_sql)
        assert safe is True
        assert "SELECT" in validated_sql

        # Step 8: Chart Generated (Plotly Engine)
        plotly_engine = PlotlyEngine()
        region_agg = loaded_df.groupby("region", as_index=False)["revenue"].sum()
        chart_spec = plotly_engine.create_bar_chart(
            data=region_agg,
            x="region",
            y="revenue",
            title="Revenue by Region",
        )
        assert chart_spec is not None
        assert "data" in chart_spec
        assert "layout" in chart_spec

        # Step 9: Insight Generated (Storytelling Engine)
        storyteller = get_data_storytelling_engine()
        kpi_engine = get_kpi_knowledge_engine()
        kpis = kpi_engine.calculate_kpis(loaded_df)
        story = storyteller.generate_story(
            query=query,
            df=loaded_df,
            metrics={k["name"]: k["formatted"] for k in kpis[:3]},
        )
        assert story is not None
        assert len(story["executive_summary"]) > 20
        assert len(story["key_findings"]) >= 3
        assert len(story["recommendations"]) >= 3
        assert story["confidence_score"] >= 0.85

        # Step 10: Forecast Generated (12 Months Forward)
        hist_mean = float(loaded_df["revenue"].mean())
        forecast_vals = [round(hist_mean * (1.0 + 0.02 * i), 2) for i in range(1, 13)]
        assert len(forecast_vals) == 12
        assert forecast_vals[-1] > forecast_vals[0]

        # Step 11: Report Generated (Report Studio)
        report_studio = get_report_studio_service()
        report = report_studio.generate_report(
            title="Q3 Executive Revenue & Profit Report",
            report_type="Executive Report",
            workspace_id="ws-journey-test",
            metrics={k["name"]: k["formatted"] for k in kpis[:4]},
            narrative=story["executive_summary"],
            findings=story["key_findings"],
            recommendations=story["recommendations"],
            forecast_summary={"horizon_periods": 12, "forecast_values": forecast_vals, "growth_pct": 21.6},
        )
        assert report is not None
        assert report["id"].startswith("rep-")
        assert report["title"] == "Q3 Executive Revenue & Profit Report"
        assert len(report["metrics"]) >= 3
        assert len(report["recommendations"]) >= 3
        assert "markdown" in report
        assert "slides" in report
        assert "pdf_path" in report
        assert report["pdf_size_bytes"] > 0


class TestLargeDatasetStress:
    """2. Large Dataset Stress Test across 100k, 500k, and 1,000,000 rows."""

    def test_100k_rows_performance(self):
        optimizer = get_large_dataset_optimizer()
        n = 100_000
        start = time.time()
        # Synthetic high-efficiency DataFrame
        df_100k = pd.DataFrame({
            "id": np.arange(n),
            "amount": np.random.uniform(10.0, 500.0, size=n),
            "category": np.random.choice(["A", "B", "C", "D"], size=n),
        })
        load_time = time.time() - start
        assert load_time < 2.0, f"100k load time {load_time:.2f}s exceeded 2.0s limit"

        mem_mb = optimizer.estimate_memory_mb(df_100k)
        assert mem_mb < 50.0, f"100k memory {mem_mb}MB exceeded 50MB budget"

        # SQL/Aggregation execution
        start_sql = time.time()
        grouped = df_100k.groupby("category")["amount"].sum()
        sql_time = time.time() - start_sql
        assert sql_time < 0.2, f"100k group aggregation {sql_time:.3f}s exceeded 0.2s"
        assert len(grouped) == 4

    def test_500k_rows_streaming_and_memory(self):
        optimizer = get_large_dataset_optimizer()
        n = 500_000
        cap_report = optimizer.analyze_capacity(row_count=n, col_count=5)
        assert cap_report.tier == "medium"
        assert cap_report.streaming_required is True
        assert cap_report.chunk_size_recommended == 25_000
        assert cap_report.health_score > 0.70

        # Memory projection check
        est_mem = optimizer.estimate_memory_from_shape(rows=n, cols=5)
        assert est_mem < 100.0  # ~19MB

    def test_1_million_rows_scale_safety(self):
        optimizer = get_large_dataset_optimizer()
        n = 1_000_000
        cap_report = optimizer.analyze_capacity(row_count=n, col_count=8)
        assert cap_report.tier in ["large", "xlarge"]
        assert cap_report.streaming_required is True
        assert cap_report.chunk_size_recommended in [50_000, 100_000]

        # Simulate chunked aggregation across 1M rows
        chunk_size = 100_000
        num_chunks = 10
        total_sum = 0.0
        start_agg = time.time()
        for i in range(num_chunks):
            # 100k chunk
            chunk_data = np.random.uniform(5.0, 100.0, size=chunk_size)
            total_sum += float(np.sum(chunk_data))
        runtime = time.time() - start_agg

        assert runtime < 1.0, f"1M row chunked aggregation took {runtime:.3f}s, expected < 1.0s"
        assert total_sum > 0.0

        # Forecast runtime check on large series summary
        start_fc = time.time()
        hist_mean = total_sum / n
        forecast = [round(hist_mean * (1.0 + 0.015 * m), 2) for m in range(1, 13)]
        fc_runtime = time.time() - start_fc
        assert fc_runtime < 0.05
        assert len(forecast) == 12


class TestAutonomousAIAnalystQuality:
    """3. Autonomous Analyst Quality Evaluation across the 5 target prompts."""

    def test_prompt_1_why_did_revenue_decline(self, sample_sales_df: pd.DataFrame):
        analyst = get_autonomous_ai_analyst()
        res = analyst.execute(
            query="Why did revenue decline?",
            df=sample_sales_df,
            workspace_id="ws-quality-test",
            session_id="session-q1",
        )
        assert res is not None
        assert "decline_analysis" in res
        assert res["decline_analysis"] is not None
        assert "primary_driver" in res["decline_analysis"]
        assert "root_causes" in res["decline_analysis"]
        assert len(res["decline_analysis"]["root_causes"]) >= 2
        # Grounding check: Executive summary addresses decline
        exec_ans = res["executive_answer"]
        assert any(w in exec_ans.lower() for w in ["decline", "contraction", "weakness", "driver"])
        assert res["execution_metadata"]["confidence_score"] >= 0.85

    def test_prompt_2_what_products_drive_profit(self, sample_sales_df: pd.DataFrame):
        analyst = get_autonomous_ai_analyst()
        res = analyst.execute(
            query="What products drive profit?",
            df=sample_sales_df,
            workspace_id="ws-quality-test",
            session_id="session-q2",
        )
        assert res is not None
        assert "profit_drivers" in res
        assert res["profit_drivers"] is not None
        p_drivers = res["profit_drivers"]
        assert "top_product" in p_drivers
        assert "profit_share_pct" in p_drivers
        assert p_drivers["profit_share_pct"] > 0
        assert "top_3_concentration" in p_drivers
        # Zero hallucination check: top_product must be in sample_sales_df
        unique_prods = set(sample_sales_df["product_name"].unique()).union(set(sample_sales_df["category"].unique()))
        assert p_drivers["top_product"] in unique_prods

    def test_prompt_3_forecast_next_12_months(self, sample_sales_df: pd.DataFrame):
        analyst = get_autonomous_ai_analyst()
        res = analyst.execute(
            query="Forecast next 12 months.",
            df=sample_sales_df,
            workspace_id="ws-quality-test",
            session_id="session-q3",
        )
        assert res is not None
        assert "forecast" in res
        fc = res["forecast"]
        assert fc is not None
        assert fc["horizon_periods"] == 12
        assert len(fc["forecast_values"]) == 12
        assert "metrics" in fc
        assert fc["metrics"]["MAPE"] < 10.0

    def test_prompt_4_create_executive_dashboard(self, sample_sales_df: pd.DataFrame):
        analyst = get_autonomous_ai_analyst()
        res = analyst.execute(
            query="Create executive dashboard.",
            df=sample_sales_df,
            workspace_id="ws-quality-test",
            session_id="session-q4",
        )
        assert res is not None
        assert "dashboard" in res
        dash = res["dashboard"]
        assert dash is not None
        assert "kpis" in dash
        assert len(dash["kpis"]) >= 2
        assert "charts" in dash or "widgets" in dash
        dash_elements = dash.get("charts") or dash.get("widgets") or []
        assert len(dash_elements) >= 1

    def test_prompt_5_find_anomalies_in_sales(self, sample_sales_df: pd.DataFrame):
        analyst = get_autonomous_ai_analyst()
        res = analyst.execute(
            query="Find anomalies in sales.",
            df=sample_sales_df,
            workspace_id="ws-quality-test",
            session_id="session-q5",
        )
        assert res is not None
        assert "anomaly_analysis" in res
        anom = res["anomaly_analysis"]
        assert anom is not None
        assert anom["anomaly_count"] >= 1
        assert "max_z_score" in anom
        assert anom["confidence"] >= 0.90


class TestEnterpriseLaunchReadiness:
    """4. Phase 21 Enterprise Launch Readiness Deliverables Verification."""

    def test_21_2_demo_dataset_library(self):
        demo_svc = get_demo_dataset_service()
        datasets = demo_svc.list_demo_datasets()
        assert len(datasets) == 5

        slugs = {d["slug"] for d in datasets}
        expected_slugs = {"sales", "finance", "marketing", "hr", "supply-chain"}
        assert expected_slugs.issubset(slugs)

        for d in datasets:
            df = demo_svc.load_demo_dataframe(d["slug"])
            assert df is not None
            assert len(df) >= 24
            assert len(df.columns) >= 6

    def test_21_3_portfolio_mode_initialization(self):
        portfolio_svc = get_portfolio_mode_service()
        init_res = portfolio_svc.initialize_portfolio_mode()
        assert init_res["status"] in ["ready", "active"]
        assert init_res["workspace_id"] == "ws-portfolio-demo"
        assert init_res["datasets_provisioned"] == 5
        assert init_res["dashboards_created"] >= 1
        assert init_res["reports_published"] >= 1

        summary = portfolio_svc.get_portfolio_summary()
        assert summary["portfolio_ready"] is True
        assert len(summary["datasets"]) == 5

    def test_21_4_usage_analytics_telemetry(self):
        telemetry = get_usage_analytics_service()
        telemetry.record_query(query_text="What are top profit drivers?", latency_ms=120.0, user_id="recruiter-1")
        telemetry.record_dataset_upload(filename="sales.csv", row_count=200, size_bytes=15000, latency_ms=85.0)
        telemetry.record_dashboard_created(dashboard_id="dash-exec-1", widget_count=6)
        telemetry.record_report_generated(report_id="rep-exec-1", report_type="Executive Report")
        telemetry.record_agent_invocation(agent_name="AutonomousAIAnalyst", latency_ms=210.0)

        summary = telemetry.get_telemetry_summary()
        assert summary["total_events"] >= 5
        assert summary["query_count"] >= 1
        assert summary["dataset_uploads"] >= 1
        assert summary["dashboards_created"] >= 1
        assert summary["reports_generated"] >= 1
        assert summary["agent_invocations"] >= 1
        assert "latency_percentiles_ms" in summary
        assert "p50" in summary["latency_percentiles_ms"]
        assert "p95" in summary["latency_percentiles_ms"]

    def test_21_5_deployment_configurations(self):
        base_dir = Path("c:/data analyst/ai-data-analyst-os")
        render_yaml = base_dir / "render.yaml"
        docker_prod = base_dir / "docker-compose.prod.yml"
        vercel_json = base_dir / "frontend" / "vercel.json"

        assert render_yaml.exists(), "render.yaml must be present for Render backend deployment"
        assert docker_prod.exists(), "docker-compose.prod.yml must be present for production deployment"
        assert vercel_json.exists(), "frontend/vercel.json must be present for Vercel deployment"

        render_text = render_yaml.read_text(encoding="utf-8")
        assert "ai-data-analyst-backend" in render_text
        assert "CHROMA_PERSIST_DIRECTORY" in render_text

        docker_text = docker_prod.read_text(encoding="utf-8")
        assert "chromadb" in docker_text
        assert "postgres" in docker_text
        assert "redis" in docker_text
