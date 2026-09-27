"""Comprehensive Test Suite for Phase 18.5 — Production Hardening & Enterprise Readiness.

Covers all 7 pillars:
- Phase 18.5.1: Enterprise Data Lake Architecture
- Phase 18.5.2: Large Dataset Scalability Engine
- Phase 18.5.3: RAG Quality Validation Framework
- Phase 18.5.4: Forecast Validation Framework
- Phase 18.5.5: End-to-End User Journeys (Upload -> Viz, Chat -> SQL -> Insights, Forecast -> Viz)
- Phase 18.5.6: Production Monitoring System
- Phase 18.5.7: Data Governance & Lineage Engine
"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
import time
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from backend.app.core.config import Settings, get_settings
from backend.app.schemas.forecasting import DataPoint, UnifiedForecastInput
from backend.app.services.storage_service import StorageService
from backend.data_engineering.benchmark_suite import DatasetBenchmarkSuite
from backend.data_engineering.capacity_analyzer import CapacityLimits, DatasetCapacityAnalyzer
from backend.data_engineering.lineage_engine import DataLineageEngine
from backend.data_engineering.streaming_reader import StreamingAggregator, StreamingCSVReader
from backend.forecasting.validation_framework import (
    ForecastValidationFramework,
    calculate_mae,
    calculate_mape,
    calculate_r2,
    calculate_rmse,
)
from backend.monitoring.production_monitoring import ProductionMonitoringService
from backend.rag.quality_validation_framework import (
    RAGQualityValidator,
    calculate_context_relevance,
    calculate_precision_at_k,
    calculate_recall_at_k,
    calculate_reciprocal_rank,
)
from backend.sql_agent.sql_executor import SQLExecutor
from backend.sql_agent.sql_generator import SQLGenerator
from backend.visualization.chart_selector import ChartSelector
from backend.visualization.generators.plotly_engine import PlotlyEngine


# =============================================================================
# Phase 18.5.1 — Enterprise Data Lake Architecture Tests
# =============================================================================

class TestPhase18_5_1_DataLakeArchitecture:
    """Validates multi-domain data lake structure, health checks, and lifecycle."""

    @pytest.fixture
    def test_lake(self, tmp_path: Path):
        test_settings = Settings(upload_dir=str(tmp_path / "storage"))
        storage = StorageService(test_settings)
        return storage, tmp_path

    def test_domain_folder_creation(self, test_lake):
        storage, _ = test_lake
        domains = [
            storage.raw_dir,
            storage.raw_csv_dir,
            storage.raw_excel_dir,
            storage.raw_json_dir,
            storage.raw_pdf_dir,
            storage.raw_parquet_dir,
            storage.canonical_dir,
            storage.processed_dir,
            storage.profiles_dir,
            storage.quality_dir,
            storage.embeddings_dir,
            storage.reports_dir,
            storage.forecasts_dir,
            storage.lineage_dir,
        ]
        for d in domains:
            assert d.exists(), f"Domain folder missing: {d}"
            assert d.is_dir()

    def test_lake_storage_persistence(self, test_lake):
        storage, _ = test_lake
        dataset_id = "test_dataset_42"

        # 1. Canonical artifact
        can_path = storage.save_canonical(dataset_id, [{"col_a": 1, "col_b": "val"}])
        assert Path(can_path).exists()
        assert storage.get_canonical(dataset_id) == [{"col_a": 1, "col_b": "val"}]

        # 2. Processed artifact
        proc_path = storage.save_processed(dataset_id, [{"col_a": 1, "cleaned": True}])
        assert Path(proc_path).exists()

        # 3. Profile artifact
        prof_path = storage.save_profile(dataset_id, {"row_count": 100, "duplicate_rows": 0})
        assert Path(prof_path).exists()

        # 4. Quality artifact
        qual_path = storage.save_quality(dataset_id, {"overall_score": 98.5, "status": "passed"})
        assert Path(qual_path).exists()

        # 5. Forecast artifact
        fc_path = storage.save_forecast(dataset_id, {"forecast": [10.5, 12.0], "mae": 1.2})
        assert Path(fc_path).exists()

        # 6. Lineage artifact
        lin_path = storage.save_lineage(dataset_id, {"nodes": [], "edges": []})
        assert Path(lin_path).exists()

    def test_storage_health_validation(self, test_lake):
        storage, _ = test_lake
        health = storage.validate_storage_health()
        assert health["status"] == "healthy"
        assert health["writable"] is True
        assert health["total_domains"] >= 9
        assert "domains" in health

    def test_file_checksum_and_lifecycle_delete(self, test_lake):
        storage, tmp_path = test_lake
        sample_file = tmp_path / "sample.csv"
        sample_file.write_text("a,b\n1,2\n3,4", encoding="utf-8")

        chk = storage.calculate_checksum(sample_file)
        assert len(chk) == 64  # SHA-256

        # Populate domains for a dataset
        d_id = "delete_target_99"
        storage.save_canonical(d_id, {"data": 1})
        storage.save_profile(d_id, {"eda": True})
        storage.save_quality(d_id, {"score": 90})

        deleted = storage.delete_dataset(d_id)
        assert deleted is True
        assert storage.get_canonical(d_id) is None


# =============================================================================
# Phase 18.5.2 — Large Dataset Scalability Engine Tests
# =============================================================================

class TestPhase18_5_2_LargeDatasetScalability:
    """Validates streaming reader, chunk processing, capacity analysis, and benchmarks."""

    @pytest.fixture
    def test_csv_file(self, tmp_path: Path):
        file_path = tmp_path / "sales_large.csv"
        df = pd.DataFrame({
            "id": range(10_000),
            "revenue": np.random.uniform(10.0, 500.0, size=10_000),
            "units": np.random.randint(1, 50, size=10_000),
            "category": np.random.choice(["Hardware", "Software", "Cloud"], size=10_000),
        })
        df.to_csv(file_path, index=False)
        return file_path

    def test_streaming_csv_reader_chunks(self, test_csv_file):
        reader = StreamingCSVReader(chunk_size=2_000)
        chunks = list(reader.read_csv_chunks(test_csv_file))
        assert len(chunks) == 5
        assert sum(len(c) for c in chunks) == 10_000

    def test_streaming_aggregations_welford(self, test_csv_file):
        reader = StreamingCSVReader(chunk_size=2_500)
        stats = reader.compute_streaming_aggregations(test_csv_file)

        assert stats["total_rows"] == 10_000
        assert stats["chunks_processed"] == 4
        assert "revenue" in stats["numeric_aggregations"]

        rev_stats = stats["numeric_aggregations"]["revenue"]
        assert rev_stats["count"] == 10_000
        assert rev_stats["mean"] > 10.0
        assert rev_stats["variance"] > 0.0

    def test_dataset_capacity_analyzer(self, test_csv_file):
        analyzer = DatasetCapacityAnalyzer()
        report = analyzer.analyze(test_csv_file, file_type="csv")

        assert report.estimated_rows >= 10_000
        assert report.column_count == 4
        assert "revenue" in report.column_names
        assert report.estimated_memory_mb > 0.0
        assert report.processing_cost in ["low", "medium", "high", "excessive"]
        assert report.is_within_limits is True

    def test_dataset_capacity_analyzer_warnings(self, tmp_path: Path):
        # Create tiny custom limits to trigger warnings
        strict_limits = CapacityLimits(
            max_recommended_rows=500,
            hard_limit_rows=1_000,
            max_recommended_cols=2,
            hard_limit_cols=5,
        )
        analyzer = DatasetCapacityAnalyzer(limits=strict_limits)

        test_file = tmp_path / "warning_test.csv"
        df = pd.DataFrame({"col1": range(1500), "col2": range(1500), "col3": range(1500)})
        df.to_csv(test_file, index=False)

        report = analyzer.analyze(test_file, file_type="csv")
        assert len(report.warnings) > 0
        assert report.is_within_limits is False

    def test_scalability_benchmark_suite(self, tmp_path: Path):
        suite = DatasetBenchmarkSuite(work_dir=tmp_path / "benchmarks")
        report = suite.run_benchmark(row_counts=[5_000, 10_000], max_allowed_peak_mb=300.0)

        assert report.all_passed is True
        assert len(report.benchmarks) == 2
        for b in report.benchmarks:
            assert b.passed is True
            assert b.actual_rows == b.target_rows
            assert b.peak_memory_mb < 300.0


# =============================================================================
# Phase 18.5.3 — RAG Quality Validation Framework Tests
# =============================================================================

class TestPhase18_5_3_RAGQualityValidation:
    """Validates Precision@K, Recall@K, MRR, Context Relevance, and RAG Health scoring."""

    def test_precision_at_k(self):
        retrieved = ["doc_1", "doc_2", "doc_3", "doc_4", "doc_5"]
        relevant = {"doc_1", "doc_3", "doc_7"}
        # Top 3: doc_1, doc_2, doc_3 -> 2 matches / 3 = 0.6667
        p3 = calculate_precision_at_k(retrieved, relevant, k=3)
        assert abs(p3 - 0.6667) < 0.01

    def test_recall_at_k(self):
        retrieved = ["doc_1", "doc_2", "doc_3"]
        relevant = {"doc_1", "doc_3"}
        # Both relevant docs are in top 3 -> 2/2 = 1.0
        r3 = calculate_recall_at_k(retrieved, relevant, k=3)
        assert r3 == 1.0

    def test_reciprocal_rank(self):
        retrieved = ["doc_x", "doc_y", "doc_target"]
        relevant = {"doc_target"}
        # doc_target is at position 3 -> 1/3 = 0.3333
        rr = calculate_reciprocal_rank(retrieved, relevant)
        assert abs(rr - 0.3333) < 0.01

    def test_context_relevance(self):
        chunks = [
            "Q4 net revenue grew by 24% with an operating margin of 18.5%.",
            "Customer churn decreased significantly in the enterprise segment.",
        ]
        score = calculate_context_relevance(chunks, "What was the revenue growth and margin?", ["revenue", "margin", "q4"])
        assert score > 0.5

    def test_rag_quality_validator_end_to_end(self, tmp_path: Path):
        validator = RAGQualityValidator(storage_dir=tmp_path / "embeddings")
        report = validator.evaluate_retrieval(k=5)

        assert report.total_queries >= 6
        assert report.mean_precision_at_k > 0.0
        assert report.mean_recall_at_k >= 0.5
        assert report.mrr >= 0.5
        assert report.rag_health_score >= 70.0
        assert report.health_status in ["EXCELLENT", "HEALTHY"]

        # Check persistence
        assert Path(report.history_file_path).exists()
        summary = validator.get_dashboard_summary()
        assert summary["historical_evaluations_count"] >= 1


# =============================================================================
# Phase 18.5.4 — Forecast Validation Framework Tests
# =============================================================================

class TestPhase18_5_4_ForecastValidation:
    """Validates MAE, RMSE, MAPE, R², multi-model ranking, and confidence scores."""

    def test_error_metrics(self):
        actuals = np.array([100.0, 110.0, 120.0, 130.0])
        preds = np.array([102.0, 108.0, 122.0, 128.0])

        mae = calculate_mae(actuals, preds)
        rmse = calculate_rmse(actuals, preds)
        mape = calculate_mape(actuals, preds)
        r2 = calculate_r2(actuals, preds)

        assert mae == 2.0
        assert rmse == 2.0
        assert round(mape, 2) > 0.0
        assert r2 > 0.90

    def test_multi_model_ranking_and_selection(self, tmp_path: Path):
        framework = ForecastValidationFramework(storage_dir=tmp_path / "forecasts")

        # 36 months of predictable upward series
        series = [
            DataPoint(date=f"2023-{(i%12)+1:02d}-01", value=100.0 + (i * 4.0) + (np.sin(i) * 5.0))
            for i in range(36)
        ]
        inp = UnifiedForecastInput(
            target="sales",
            horizon=6,
            frequency="monthly",
            series=series,
        )

        result = framework.run_validation_and_forecast(inp, run_id="fc_validation_test")

        assert len(result.forecast) == 6
        assert result.mae > 0.0
        assert result.rmse > 0.0
        assert result.mape > 0.0
        assert result.best_model in ["prophet", "arima", "xgboost"]
        assert result.confidence_score > 0.0
        assert len(result.model_rankings) == 3

        # Check best model is rank 1
        best_rank = [m for m in result.model_rankings if m.is_best][0]
        assert best_rank.rank == 1

        # Check persistence
        saved_file = tmp_path / "forecasts" / "fc_validation_test_validation.json"
        assert saved_file.exists()


# =============================================================================
# Phase 18.5.5 — End-to-End User Journeys Tests
# =============================================================================

class TestPhase18_5_5_EndToEndUserJourneys:
    """Validates the 3 end-to-end user journeys."""

    def test_journey_1_dataset_to_visualization(self, tmp_path: Path):
        """Journey 1: Ingest -> Profiling & Stats -> Visualization Chart Generation."""
        # 1. Dataset payload
        records = [
            {"product": "Apples", "revenue": 1200.0, "region": "North"},
            {"product": "Bananas", "revenue": 850.0, "region": "South"},
            {"product": "Cherries", "revenue": 2100.0, "region": "North"},
            {"product": "Dates", "revenue": 1450.0, "region": "West"},
        ]
        df = pd.DataFrame(records)
        csv_path = tmp_path / "products.csv"
        df.to_csv(csv_path, index=False)

        # 2. Analyze via Capacity Analyzer & Streaming Aggregator
        analyzer = DatasetCapacityAnalyzer()
        cap_report = analyzer.analyze(csv_path)
        assert cap_report.column_count == 3
        assert cap_report.is_within_limits is True

        reader = StreamingCSVReader()
        stats = reader.compute_streaming_aggregations(csv_path)
        assert stats["total_rows"] == 4

        # 3. Visualization generation
        selector = ChartSelector()
        recommendation = selector.select_chart(
            columns=["product", "revenue"],
            data=records,
            user_intent="Show revenue comparison by product",
        )
        assert recommendation.chart_type in ["bar_chart", "treemap", "line_chart", "bar"]

        engine = PlotlyEngine()
        spec = engine.generate_spec(
            chart_type="bar",
            data=records,
            x="product",
            y="revenue",
            title="Product Revenue Breakdown",
        )
        assert spec["data"][0]["type"] == "bar"
        assert len(spec["data"][0]["x"]) == 4

    def test_journey_2_chat_sql_to_chart_insights(self):
        """Journey 2: Ask Question -> SQL Agent -> Chart -> Insights."""
        schema = {
            "tables": {
                "sales": {
                    "columns": ["id", "category", "amount", "sale_date"],
                    "primary_key": "id",
                }
            }
        }

        # 1. Ask question & generate SQL
        generator = SQLGenerator(schema_context=schema)
        sql = generator.generate_sql("Show total sales amount grouped by category")
        assert "SELECT" in sql.upper()
        assert "CATEGORY" in sql.upper()
        assert "GROUP BY" in sql.upper()

        # 2. Execute query (simulated SQLite/PostgreSQL)
        simulated_results = [
            {"category": "Electronics", "total_amount": 45000.0},
            {"category": "Apparel", "total_amount": 28000.0},
            {"category": "Home", "total_amount": 19500.0},
        ]

        # 3. Select chart and render Plotly spec
        engine = PlotlyEngine()
        spec = engine.generate_spec(
            chart_type="bar",
            data=simulated_results,
            x="category",
            y="total_amount",
            title="Category Sales Performance",
        )
        assert spec["layout"]["title"]["text"] == "Category Sales Performance"

    def test_journey_3_forecast_engine_to_visualization(self, tmp_path: Path):
        """Journey 3: Forecast Request -> Forecast Validation Engine -> Plotly Visualization."""
        series = [
            DataPoint(date=f"2024-{(i%12)+1:02d}-01", value=50.0 + (i * 3.0))
            for i in range(24)
        ]
        inp = UnifiedForecastInput(target="demand", horizon=6, frequency="monthly", series=series)

        framework = ForecastValidationFramework(storage_dir=tmp_path / "forecasts")
        validated = framework.run_validation_and_forecast(inp)

        assert len(validated.forecast) == 6
        assert validated.best_model != ""

        # Render forecast chart specification
        engine = PlotlyEngine()
        forecast_plot_data = [
            {"period": f"Period +{p['period']}", "forecast": p["predicted_value"]}
            for p in validated.forecast_points
        ]
        spec = engine.generate_spec(
            chart_type="line",
            data=forecast_plot_data,
            x="period",
            y="forecast",
            title=f"Validated Forecast ({validated.best_model.upper()})",
        )
        assert spec["data"][0]["type"] == "scatter"


# =============================================================================
# Phase 18.5.6 — Production Monitoring System Tests
# =============================================================================

class TestPhase18_5_6_ProductionMonitoring:
    """Validates telemetry tracking, latency timers, alert rules, and daily health summaries."""

    @pytest.fixture
    def monitor(self, tmp_path: Path):
        return ProductionMonitoringService(storage_dir=tmp_path / "reports")

    def test_latency_recording_and_stats(self, monitor):
        for lat in [120.0, 150.0, 180.0, 210.0, 300.0]:
            monitor.record_latency("sql", lat)

        stats = monitor.get_latency_stats()
        sql_stat = stats["sql"]
        assert sql_stat.count == 5
        assert sql_stat.avg_ms == 192.0
        assert sql_stat.min_ms == 120.0
        assert sql_stat.max_ms == 300.0

    def test_timer_context_manager(self, monitor):
        with monitor.time_operation("upload"):
            time.sleep(0.02)  # 20ms

        stats = monitor.get_latency_stats()
        assert stats["upload"].count == 1
        assert stats["upload"].avg_ms >= 15.0

    def test_alert_threshold_breach(self, monitor):
        # Default critical for upload is 10000ms
        monitor.record_latency("upload", 12500.0)
        dash = monitor.get_monitoring_dashboard()
        assert dash["active_alerts_count"] >= 1
        latest_alert = dash["recent_alerts"][-1]
        assert latest_alert["severity"] == "critical"
        assert latest_alert["metric"] == "upload"

    def test_daily_health_summary_generation(self, monitor, tmp_path: Path):
        summary = monitor.generate_daily_health_summary()
        assert "platform_status" in summary
        assert "infrastructure_status" in summary
        assert "p95_latencies_ms" in summary
        assert summary["sla_percentage"] >= 98.0


# =============================================================================
# Phase 18.5.7 — Data Governance & Lineage Engine Tests
# =============================================================================

class TestPhase18_5_7_DataGovernanceLineage:
    """Validates dataset provenance tracking, transformation audit, and DAG graphs."""

    @pytest.fixture
    def lineage_engine(self, tmp_path: Path):
        return DataLineageEngine(storage_dir=tmp_path / "lineage")

    def test_initialize_lineage_dag(self, lineage_engine):
        rec = lineage_engine.initialize_lineage(
            dataset_id="ds_lineage_01",
            dataset_name="Quarterly Financials",
            file_name="q4_sales.csv",
            file_type="csv",
            file_size_bytes=45000,
            content_hash="abc123hash",
        )
        assert rec["dataset_id"] == "ds_lineage_01"
        assert len(rec["graph"]["nodes"]) == 2  # raw + canonical
        assert len(rec["graph"]["edges"]) == 1

    def test_record_transformations_and_events(self, lineage_engine):
        ds_id = "ds_lineage_02"
        lineage_engine.initialize_lineage(
            dataset_id=ds_id,
            dataset_name="Customer Analytics",
            file_name="customers.csv",
            file_type="csv",
            file_size_bytes=12000,
        )

        # 1. Record transformation
        lineage_engine.record_transformation(
            dataset_id=ds_id,
            step_name="outlier_capping",
            transformation_type="imputation",
            description="Capped extreme revenue values above 99th percentile",
            parameters={"upper_percentile": 0.99},
        )

        # 2. Record profile event
        lineage_engine.record_profile_event(
            dataset_id=ds_id,
            profile_summary={"duplicate_rows": 0, "numeric_columns_profile": {"revenue": {}}},
        )

        # 3. Record quality event
        lineage_engine.record_quality_event(
            dataset_id=ds_id,
            quality_summary={"overall_score": 96.2, "quality_classification": "High"},
        )

        # 4. Record forecast event
        lineage_engine.record_forecast_event(
            dataset_id=ds_id,
            run_id="run_fc_887",
            model_name="prophet",
            target="revenue",
            horizon=12,
            metrics={"mae": 4.2, "rmse": 6.8, "mape": 3.1},
        )

        # Verify DAG structure
        graph = lineage_engine.generate_lineage_graph(ds_id)
        assert len(graph["nodes"]) >= 6
        assert len(graph["edges"]) >= 5
        assert graph["total_transformations"] >= 1
        assert graph["total_forecasts"] == 1

        # Check node types
        types = {n["type"] for n in graph["nodes"]}
        assert "source" in types
        assert "canonical" in types
        assert "cleaned" in types
        assert "profile" in types
        assert "quality" in types
        assert "forecast" in types
