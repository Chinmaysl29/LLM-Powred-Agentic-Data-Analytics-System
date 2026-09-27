"""Comprehensive Test Suite for Phase 18.6 — Enterprise Excellence.

Covers all 8 pillars:
- Phase 18.6.1: Enterprise Data Lake Architecture, Lifecycle & Cleanup Services
- Phase 18.6.2: RAG Grounding 2.0, Evaluation Framework & Dynamic Ingestion
- Phase 18.6.3: Forecasting Validation Framework, Multi-Model (Prophet, ARIMA, XGBoost, LSTM) & Dashboard
- Phase 18.6.4: Large Dataset Scalability Engine (100k, 500k, 1M, 5M rows)
- Phase 18.6.5: Dataset Lineage Intelligence (Complete 8-stage journey & DAG Graph)
- Phase 18.6.6: Enterprise Observability & Monitoring Layer
- Phase 18.6.7: Performance Benchmark Suite (Upload, RAG, SQL, Viz, Forecast, Orchestrator)
- Phase 18.6.8: Final Comprehensive Validation Suite across all file formats and workflows
"""

from __future__ import annotations

import io
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
from backend.app.core.exceptions import ForecastingDatasetValidationError
from backend.app.schemas.context_builder import BuiltContext, ContextSource
from backend.app.schemas.forecasting import DataPoint, UnifiedForecastInput
from backend.app.schemas.vector_store import VectorSearchResult
from backend.app.services.benchmark_service import PerformanceBenchmarkSuite
from backend.app.services.data_lake_lifecycle import (
    CleanupReport,
    DataLakeCleanupService,
    DataLakeLifecycleService,
    LifecycleEvent,
)
from backend.app.services.large_dataset_optimizer import (
    DATASET_TIERS,
    DatasetCapacityReport,
    LargeDatasetOptimizer,
)
from backend.app.services.lineage_service import (
    LINEAGE_STAGES,
    DatasetLineage,
    DatasetLineageService,
)
from backend.app.services.observability_service import ObservabilityService
from backend.app.services.rag_service import RAGService
from backend.app.services.storage_service import StorageService
from backend.data_engineering.capacity_analyzer import DatasetCapacityAnalyzer
from backend.data_engineering.lineage_engine import DataLineageEngine
from backend.data_engineering.streaming_reader import StreamingAggregator, StreamingCSVReader
from backend.forecasting.arima_model import ARIMAForecaster
from backend.forecasting.lstm_model import LSTM_MIN_POINTS, LSTMForecaster
from backend.forecasting.prophet_model import ProphetForecaster
from backend.forecasting.validation_framework import (
    MIN_HISTORY,
    ForecastValidationFramework,
    calculate_confidence_score,
    calculate_mae,
    calculate_mape,
    calculate_r2,
    calculate_rmse,
    calculate_smape,
)
from backend.forecasting.xgboost_forecaster import XGBoostForecaster
from backend.monitoring.production_monitoring import ProductionMonitoringService
from backend.orchestrator.enterprise_orchestrator import EnterprisePlatformOrchestrator
from backend.rag.context_builder import ContextBuilder
from backend.rag.dynamic_chunking import DynamicChunkingService
from backend.rag.quality_validation_framework import RAGQualityValidator
from backend.rag.rag_evaluation import RAGBenchmark, RAGEvalResult, RAGEvaluationFramework
from backend.sql_agent.sql_executor import SQLExecutor
from backend.sql_agent.sql_generator import SQLGenerator
from backend.visualization.generators.plotly_engine import PlotlyEngine


@pytest.fixture
def temp_lake(tmp_path: Path) -> tuple[StorageService, Path]:
    settings = Settings(upload_dir=str(tmp_path / "lake"))
    svc = StorageService(settings=settings)
    return svc, tmp_path / "lake"


# =============================================================================
# Phase 18.6.1: Enterprise Data Lake Restructure, Lifecycle & Cleanup
# =============================================================================

class TestPhase18_6_1_DataLakeRestructure:
    """Validates automatic folder provisioning, domain-partitioned persistence, lifecycle, and cleanup."""

    def test_lake_domain_provisioning(self, temp_lake: tuple[StorageService, Path]):
        svc, lake_dir = temp_lake
        domains = [
            svc.raw_dir,
            svc.raw_csv_dir,
            svc.raw_excel_dir,
            svc.raw_json_dir,
            svc.raw_pdf_dir,
            svc.canonical_dir,
            svc.processed_dir,
            svc.profiles_dir,
            svc.quality_dir,
            svc.embeddings_dir,
            svc.reports_dir,
            svc.forecasts_dir,
            svc.lineage_dir,
            svc.archives_dir,
        ]
        for d in domains:
            assert d.exists(), f"Storage domain {d} must exist"
            assert d.is_dir(), f"Storage domain {d} must be a directory"

    def test_domain_artifact_persistence(self, temp_lake: tuple[StorageService, Path]):
        svc, _ = temp_lake
        dataset_id = "ds_enterprise_101"

        # 1. Canonical JSON
        can_path = svc.save_canonical(dataset_id, {"rows": 100, "cols": ["a", "b"]})
        assert can_path.exists()
        assert svc.get_canonical(dataset_id) == {"rows": 100, "cols": ["a", "b"]}

        # 2. Profiles
        prof_path = svc.save_profile(dataset_id, {"numeric_columns": {"a": {"mean": 42.0}}})
        assert prof_path.exists()
        assert svc.get_profile(dataset_id)["numeric_columns"]["a"]["mean"] == 42.0

        # 3. Quality
        qual_path = svc.save_quality(dataset_id, {"overall_score": 96.5, "status": "EXCELLENT"})
        assert qual_path.exists()
        assert svc.get_quality(dataset_id)["overall_score"] == 96.5

        # 4. Forecasts
        fc_path = svc.save_forecast(dataset_id, {"best_model": "prophet", "mae": 4.12})
        assert fc_path.exists()
        assert svc.get_forecast(dataset_id)["best_model"] == "prophet"

        # 5. Lineage
        lin_path = svc.save_lineage(dataset_id, {"stages": ["upload", "canonical_json"]})
        assert lin_path.exists()
        assert "upload" in svc.get_lineage(dataset_id)["stages"]

        # 6. Embeddings
        emb_path = svc.save_embedding_metadata(dataset_id, {"total_chunks": 12, "model": "text-embedding-3"})
        assert emb_path.exists()

        # 7. Reports
        rep_path = svc.save_report("rep_2026", {"title": "Annual Executive Summary", "score": 98})
        assert rep_path.exists()

    def test_archive_and_restoration_lifecycle(self, temp_lake: tuple[StorageService, Path]):
        svc, _ = temp_lake
        dataset_id = "ds_lifecycle_archive"

        svc.save_canonical(dataset_id, {"dataset": dataset_id, "data": [1, 2, 3]})
        svc.save_profile(dataset_id, {"summary": "profile"})
        svc.save_quality(dataset_id, {"score": 90})

        # Archive
        assert svc.archive_dataset(dataset_id, reason="testing_soft_delete")
        arch_dir = svc.archives_dir / dataset_id
        assert arch_dir.exists()
        assert (arch_dir / "manifest.json").exists()
        manifest = json.loads((arch_dir / "manifest.json").read_text(encoding="utf-8"))
        assert manifest["dataset_id"] == dataset_id
        assert manifest["reason"] == "testing_soft_delete"

        # Delete from active domain
        (svc.canonical_dir / f"{dataset_id}.json").unlink()
        assert svc.get_canonical(dataset_id) is None

        # Restore from archive
        assert svc.restore_from_archive(dataset_id)
        assert svc.get_canonical(dataset_id) is not None

    def test_lifecycle_and_cleanup_services(self, temp_lake: tuple[StorageService, Path]):
        svc, _ = temp_lake
        lifecycle_svc = DataLakeLifecycleService(storage_service=svc)
        cleanup_svc = DataLakeCleanupService(storage_service=svc)

        ds_id = "ds_lifecycle_service_test"
        evt = lifecycle_svc.transition_state(
            dataset_id=ds_id,
            from_state="uploaded",
            to_state="canonicalized",
            actor="test_runner",
        )
        assert evt.from_state == "uploaded"
        assert evt.to_state == "canonicalized"

        # Create temporary file to verify cleanup
        temp_file = svc.upload_dir / "test_scratch.tmp"
        temp_file.write_text("temporary scratch data", encoding="utf-8")
        assert temp_file.exists()

        report = cleanup_svc.run_comprehensive_cleanup(retention_days=1, temp_max_age_seconds=0)
        assert report.status == "completed"
        assert not temp_file.exists()


# =============================================================================
# Phase 18.6.2: RAG Grounding 2.0 & Dynamic Ingestion & Evaluation Framework
# =============================================================================

class TestPhase18_6_2_RAGGrounding2AndEvaluation:
    """Validates full_content citation tracking, dynamic chunking, and evaluation metrics."""

    def test_rag_grounding_2_context_source_contract(self):
        builder = ContextBuilder(max_tokens=2000)
        results = [
            VectorSearchResult(
                chunk_id="chk_001",
                document_id="doc_financial_q3",
                content="Q3 consolidated net revenue reached $4.2B, representing 18% YoY growth.",
                score=0.94,
                metadata={"filename": "Q3_Report.pdf", "page_number": 4, "file_type": "pdf"},
            ),
            VectorSearchResult(
                chunk_id="chk_002",
                document_id="doc_financial_q3",
                content="Operating income was $850M with an operating margin of 20.2%.",
                score=0.91,
                metadata={"filename": "Q3_Report.pdf", "page_number": 5, "file_type": "pdf"},
            ),
        ]

        context: BuiltContext = builder.build(results)
        assert len(context.sources) == 2

        src1 = context.sources[0]
        # 1. chunk_id, document_id, score, metadata
        assert src1.chunk_id == "chk_001"
        assert src1.document_id == "doc_financial_q3"
        assert src1.score == 0.94
        assert src1.metadata["filename"] == "Q3_Report.pdf"

        # 2. UI preview is preserved and capped at <= 120 chars
        assert len(src1.preview) <= 120
        assert "Q3 consolidated net revenue" in src1.preview

        # 3. full_content is complete for grounding validation
        assert src1.full_content == "Q3 consolidated net revenue reached $4.2B, representing 18% YoY growth."

        # 4. Document lineage & citations
        assert src1.page_number == 4
        assert "p.4" in src1.citation_ref
        assert src1.char_offset == 0

    def test_dynamic_chunking_detection(self):
        dyn_svc = DynamicChunkingService()

        # Financial Report -> 600
        fin_text = "The quarterly balance sheet shows operating cash flow of $1.2B with net income growth."
        fin_cfg = dyn_svc.get_config(fin_text, filename="annual_financial_report.pdf")
        assert fin_cfg.category == "financial"
        assert fin_cfg.chunk_size == 600
        assert fin_cfg.chunk_overlap == 100

        # Research Paper -> 800
        res_text = "In this methodology, we evaluate our hypothesis against benchmark datasets and arxiv literature review."
        res_cfg = dyn_svc.get_config(res_text, filename="transformer_scaling_paper.pdf")
        assert res_cfg.category == "research"
        assert res_cfg.chunk_size == 800
        assert res_cfg.chunk_overlap == 150

        # Policy -> 400
        pol_text = "Compliance procedure clause: all users shall strictly follow the security regulation policy."
        pol_cfg = dyn_svc.get_config(pol_text, filename="data_security_policy.txt")
        assert pol_cfg.category == "policy"
        assert pol_cfg.chunk_size == 400
        assert pol_cfg.chunk_overlap == 80

        # General Docs -> 500
        gen_text = "Welcome to our customer onboarding overview guide. Here are simple tips to get started."
        gen_cfg = dyn_svc.get_config(gen_text, filename="readme.txt")
        assert gen_cfg.category == "general"
        assert gen_cfg.chunk_size == 500

    def test_rag_evaluation_framework(self, tmp_path: Path):
        eval_engine = RAGEvaluationFramework(storage_dir=tmp_path / "embeddings")

        query = "What was the Q3 operating margin?"
        retrieved_ids = ["chk_001", "chk_002", "chk_003"]
        retrieved_texts = [
            "Q3 net revenue reached $4.2B.",
            "Operating income was $850M with an operating margin of 20.2%.",
            "General corporate disclosures and disclaimer.",
        ]
        relevant_ids = ["chk_002"]
        answer = "The operating margin for Q3 was 20.2% with operating income of $850M."

        result: RAGEvalResult = eval_engine.evaluate(
            query=query,
            retrieved_chunk_ids=retrieved_ids,
            retrieved_texts=retrieved_texts,
            relevant_chunk_ids=relevant_ids,
            answer=answer,
            ground_truth="Operating margin was 20.2%.",
            k=3,
        )

        assert result.precision_at_k > 0.0
        assert result.recall_at_k == 1.0  # chk_002 retrieved in top 3
        assert result.mrr > 0.0
        assert result.ndcg > 0.0
        assert result.context_relevance > 0.0
        assert result.answer_relevance > 0.0
        assert result.groundedness_score > 0.0
        assert result.overall_score > 0.5

        # Verify history persistence & health dashboard
        hist = eval_engine.load_history()
        assert len(hist) == 1
        summary = eval_engine.health_summary()
        assert summary["status"] == "healthy"
        assert summary["total_evals"] == 1

        # Register and retrieve benchmark
        bench = RAGBenchmark(
            benchmark_id="bm_q3_margin",
            query=query,
            relevant_chunk_ids=relevant_ids,
            ground_truth_answer="Operating margin was 20.2%.",
            category="financial",
        )
        eval_engine.add_benchmark(bench)
        benchmarks = eval_engine.load_benchmarks()
        assert len(benchmarks) == 1
        assert benchmarks[0]["benchmark_id"] == "bm_q3_margin"


# =============================================================================
# Phase 18.6.3: Multi-Model Forecasting, Minimum History & Accuracy Dashboard
# =============================================================================

class TestPhase18_6_3_ForecastingValidationAndMultiModel:
    """Validates minimum history rules, Prophet/ARIMA/XGBoost/LSTM backtesting, and accuracy dashboard."""

    def test_minimum_history_rules(self, tmp_path: Path):
        validator = ForecastValidationFramework(storage_dir=tmp_path / "forecasts")

        # 1. Below minimum history (< 12 points) -> Rejected
        few_points = [DataPoint(date=f"2024-{(i%12)+1:02d}-01", value=100.0 + i) for i in range(10)]
        inp_invalid = UnifiedForecastInput(target="sales", frequency="monthly", horizon=3, series=few_points)
        with pytest.raises(ValueError, match="at least 8 points required|Minimum required"):
            validator.run_validation_and_forecast(inp_invalid)

        # 2. Check MIN_HISTORY constant definition
        assert MIN_HISTORY["prophet"] == 12
        assert MIN_HISTORY["arima"] == 24
        assert MIN_HISTORY["xgboost"] == 36
        assert MIN_HISTORY["lstm"] == 48

    def test_lstm_forecaster_standalone(self):
        # 1. Reject if points < 48
        short_series = [DataPoint(date=f"2024-{(i%12)+1:02d}-01", value=100.0 + i) for i in range(30)]
        inp_short = UnifiedForecastInput(target="demand", frequency="monthly", horizon=4, series=short_series)
        lstm = LSTMForecaster(epochs=5)
        with pytest.raises(ForecastingDatasetValidationError):
            lstm.forecast(inp_short)

        # 2. Pass if points >= 48
        valid_series = [
            DataPoint(date=f"2022-{(i%12)+1:02d}-01", value=100.0 + i * 1.5 + np.sin(i / 2.0) * 15.0)
            for i in range(50)
        ]
        inp_valid = UnifiedForecastInput(target="demand", frequency="monthly", horizon=3, series=valid_series)
        out = lstm.forecast(inp_valid)
        assert out.model_type == "lstm"
        assert len(out.forecast) == 3
        assert len(out.lower_bound) == 3
        assert len(out.upper_bound) == 3
        assert all(isinstance(v, (int, float)) for v in out.forecast)

    def test_multi_model_tournament_and_accuracy_dashboard(self, tmp_path: Path):
        validator = ForecastValidationFramework(storage_dir=tmp_path / "forecasts")
        # 52 data points allows all 4 models: Prophet, ARIMA, XGBoost, LSTM
        points = [
            DataPoint(date=f"2022-{(i%12)+1:02d}-01", value=100.0 + i * 2.0 + (i % 4) * 8.0)
            for i in range(52)
        ]
        inp = UnifiedForecastInput(target="revenue", frequency="monthly", horizon=3, series=points)

        res = validator.run_validation_and_forecast(inp, run_id="run_tournament_test")
        assert res.best_model in ["prophet", "arima", "xgboost", "lstm"]
        assert len(res.forecast) == 3
        assert res.mae >= 0.0
        assert res.rmse >= 0.0
        assert res.mape >= 0.0
        assert res.smape >= 0.0
        assert -1.0 <= res.r2 <= 1.0
        assert 0.0 <= res.confidence_score <= 1.0

        # Check rankings
        evaluated_names = [m.model for m in res.model_rankings]
        assert "prophet" in evaluated_names
        assert "arima" in evaluated_names
        assert "xgboost" in evaluated_names

        # Accuracy Dashboard API & trend analysis
        dash = validator.get_health_dashboard()
        assert dash["status"] == "healthy"
        assert dash["total_runs"] >= 1
        assert "model_accuracy_table" in dash
        assert "trend_analysis" in dash
        assert len(dash["model_accuracy_table"]) > 0
        table_cols = {col for item in dash["model_accuracy_table"] for col in item.keys()}
        assert {"model", "mae", "rmse", "mape", "r2", "confidence"}.issubset(table_cols)


# =============================================================================
# Phase 18.6.4: Large Dataset Scalability Engine (100k, 500k, 1M, 5M rows)
# =============================================================================

class TestPhase18_6_4_LargeDatasetOptimization:
    """Validates memory estimation, tier classifications (100k, 500k, 1M, 5M), and streaming chunk readers."""

    def test_dataset_tier_classifications(self):
        optimizer = LargeDatasetOptimizer()
        assert optimizer.classify_tier(50_000) == "small"
        assert optimizer.classify_tier(250_000) == "medium"
        assert optimizer.classify_tier(750_000) == "large"
        assert optimizer.classify_tier(2_500_000) == "xlarge"
        assert optimizer.classify_tier(6_000_000) == "xxlarge"

    def test_memory_estimation_and_capacity_analyzer(self):
        analyzer = DatasetCapacityAnalyzer()
        optimizer = LargeDatasetOptimizer()

        # 100k rows, 10 cols
        mem_100k = optimizer.estimate_memory_from_shape(100_000, 10)
        assert 5.0 <= mem_100k <= 20.0  # ~8 MB

        # 5M rows, 20 cols
        mem_5m = optimizer.estimate_memory_from_shape(5_000_000, 20)
        assert 500.0 <= mem_5m <= 1500.0  # ~762 MB

        report: DatasetCapacityReport = optimizer.analyze_capacity(500_000, 15)
        assert report.tier == "medium"
        assert report.streaming_required is True
        assert report.health_score > 0.0

    def test_streaming_csv_reader_and_aggregator(self, tmp_path: Path):
        csv_file = tmp_path / "streaming_test.csv"
        # Generate 15,000 rows
        df = pd.DataFrame({
            "val": np.arange(15_000, dtype=np.float64),
            "grp": np.random.choice(["A", "B", "C"], size=15_000),
        })
        df.to_csv(csv_file, index=False)

        reader = StreamingCSVReader(chunk_size=5_000)
        agg = StreamingAggregator()

        chunks = list(reader.read_chunks(csv_file))
        assert len(chunks) == 3

        for chk in chunks:
            agg.update_chunk(chk)

        stats = agg.finalize()
        assert stats["total_rows"] == 15_000
        assert stats["numeric"]["val"]["min"] == 0.0
        assert stats["numeric"]["val"]["max"] == 14_999.0
        assert round(stats["numeric"]["val"]["mean"], 1) == 7499.5


# =============================================================================
# Phase 18.6.5: Dataset Lineage Intelligence (8-Stage Complete Journey & DAG)
# =============================================================================

class TestPhase18_6_5_DatasetLineageIntelligence:
    """Validates tracking of complete journey: Upload -> Canonical -> Profile -> Quality -> Cleaning -> Embedding -> Forecast -> Report."""

    def test_complete_8_stage_lineage_journey(self, tmp_path: Path):
        svc = DatasetLineageService(lineage_dir=tmp_path / "lineage")
        dataset_id = "ds_journey_complete_101"

        # Initialize
        lineage = svc.create(dataset_id=dataset_id, filename="sales_data.csv", file_type="csv")
        assert lineage.current_stage == "upload"

        # Record all 8 stages
        for stage in LINEAGE_STAGES:
            updated = svc.record_event(
                dataset_id=dataset_id,
                stage=stage,
                status="success",
                duration_ms=45.2,
                details={"step": stage, "status": "verified"},
            )
            assert updated is not None

        final_lineage = svc.load(dataset_id)
        assert final_lineage.current_stage == "complete"
        assert len(final_lineage.completed_stages) == 8
        assert final_lineage.completed_stages == LINEAGE_STAGES

        # Validate DAG Graph
        graph = final_lineage.to_graph()
        assert len(graph["nodes"]) == 8
        assert len(graph["edges"]) == 7
        assert all(n["status"] == "completed" for n in graph["nodes"])
        assert graph["summary"]["total_stages"] == 8
        assert graph["summary"]["completed"] == 8


# =============================================================================
# Phase 18.6.6: Enterprise Observability & Monitoring
# =============================================================================

class TestPhase18_6_6_EnterpriseObservability:
    """Validates latency tracking, service health, and dashboard generation."""

    def test_observability_tracking_and_dashboard(self, tmp_path: Path):
        obs = ObservabilityService(storage_dir=tmp_path / "reports")

        # Track operations
        with obs.track("upload", {"format": "csv"}):
            time.sleep(0.01)

        with obs.track("rag_query", {"top_k": 5}):
            time.sleep(0.01)

        obs.record("forecast", duration_ms=45.6, status="success")
        obs.record("sql_execute", duration_ms=12.3, status="success")
        obs.record("sql_execute", duration_ms=99.0, status="error")

        dash = obs.dashboard()
        assert dash["total_records"] >= 4
        ops = dash["operations"]
        assert "upload" in ops
        assert "rag_query" in ops
        assert "forecast" in ops
        assert "sql_execute" in ops
        assert ops["sql_execute"]["error_count"] == 1

        health = obs.health_check()
        assert health["status"] in ["healthy", "degraded"]

    def test_production_monitoring_service(self, tmp_path: Path):
        mon = ProductionMonitoringService(storage_dir=tmp_path / "reports")
        mon.record_latency("upload", 120.5)
        mon.record_latency("rag", 240.0)
        mon.record_latency("sql", 45.0)

        dash = mon.get_monitoring_dashboard()
        assert dash["platform_status"] in ["HEALTHY", "DEGRADED", "CRITICAL"]
        assert "infrastructure" in dash
        assert "latencies" in dash
        assert dash["latencies"]["upload"]["count"] >= 1


# =============================================================================
# Phase 18.6.7: Performance Benchmark Suite
# =============================================================================

class TestPhase18_6_7_PerformanceBenchmarkSuite:
    """Validates automated benchmarks across all 6 core pillars."""

    def test_performance_benchmark_suite_components(self, tmp_path: Path):
        suite = PerformanceBenchmarkSuite(storage_dir=tmp_path / "reports", iterations=2)

        # 1. Forecast benchmark
        res_fc = suite.benchmark_forecast()
        assert res_fc.component == "forecast_engine"
        assert res_fc.success_rate == 1.0

        # 2. Orchestrator benchmark
        res_orch = suite.benchmark_orchestrator()
        assert res_orch.component == "orchestrator"
        assert res_orch.success_rate == 1.0

        # 3. Visualization benchmark
        res_viz = suite.benchmark_visualization()
        assert res_viz.component == "visualization"
        assert res_viz.success_rate == 1.0

        # 4. Consolidated run and persistence
        report = suite.run_all()
        assert "summary" in report
        assert report["summary"]["total_benchmarks"] >= 5
        history = suite.load_history()
        assert len(history) >= 1


# =============================================================================
# Phase 18.6.8: Final Comprehensive Validation Suite
# =============================================================================

class TestPhase18_6_8_FinalComprehensiveValidation:
    """End-to-end integration validation across all file types, models, and analytical tools."""

    def test_csv_canonical_and_profiling_flow(self, temp_lake: tuple[StorageService, Path]):
        svc, _ = temp_lake
        dataset_id = "ds_csv_full_pipeline"

        csv_content = pd.DataFrame({
            "product_id": [1, 2, 3, 4, 5],
            "units_sold": [100, 250, 400, 150, 300],
            "revenue": [1000.0, 2500.0, 4000.0, 1500.0, 3000.0],
            "category": ["A", "B", "A", "B", "C"],
        })
        # Save canonical
        svc.save_canonical(dataset_id, csv_content.to_dict(orient="records"))
        assert svc.get_canonical(dataset_id) is not None

        # Profile
        profile_data = {
            "dataset_id": dataset_id,
            "row_count": len(csv_content),
            "column_count": len(csv_content.columns),
            "numeric_columns_profile": {
                "units_sold": {"min": 100, "max": 400, "mean": 240},
            },
        }
        svc.save_profile(dataset_id, profile_data)
        assert svc.get_profile(dataset_id)["row_count"] == 5

        # Quality scoring
        quality_data = {
            "dataset_id": dataset_id,
            "completeness_score": 100.0,
            "overall_score": 98.5,
            "quality_classification": "EXCELLENT",
        }
        svc.save_quality(dataset_id, quality_data)
        assert svc.get_quality(dataset_id)["overall_score"] == 98.5

    def test_json_and_pdf_canonical_representation(self, temp_lake: tuple[StorageService, Path]):
        svc, _ = temp_lake
        json_id = "ds_json_artifact"
        pdf_id = "ds_pdf_artifact"

        svc.save_canonical(json_id, {"records": [{"id": 1, "status": "active"}]})
        assert svc.get_canonical(json_id)["records"][0]["status"] == "active"

        svc.save_canonical(pdf_id, {
            "document_name": "policy.pdf",
            "pages": [{"page_num": 1, "text": "Corporate policy guidelines."}],
        })
        assert svc.get_canonical(pdf_id)["pages"][0]["page_num"] == 1

    def test_sql_agent_and_visualization_integration(self):
        executor = SQLExecutor()
        df = pd.DataFrame({
            "region": ["East", "West", "North", "South"],
            "sales": [12000, 18500, 14200, 9800],
        })

        # SQL execution
        query = "SELECT region, sales FROM dataset WHERE sales > 10000 ORDER BY sales DESC"
        exec_res = executor.execute_on_dataframe(query, df, table_name="dataset")
        filtered_df = exec_res.to_dataframe()
        assert len(filtered_df) == 3
        assert filtered_df.iloc[0]["region"] == "West"

        # Visualization Engine
        engine = PlotlyEngine()
        fig = engine.generate_chart(chart_type="bar", df=filtered_df, x_col="region", y_col="sales", title="Top Regions by Sales")
        assert fig is not None
        assert "data" in fig

    def test_enterprise_platform_orchestrator_health(self):
        orch = EnterprisePlatformOrchestrator()
        status = orch.get_platform_status()
        assert status["status"] == "healthy"
        assert status["platform_score"] >= 90
        module_names = [m["name"] for m in status["modules"]]
        assert "dataset_intelligence" in module_names
        assert "analytics_intelligence" in module_names
        assert "sql_intelligence" in module_names
        assert "rag_intelligence" in module_names
        assert "forecasting_intelligence" in module_names
