"""Phase 20 — Enterprise AI Analytics Operating System Verification Suite.

Comprehensive tests covering all 10 productization pillars:
- 20.1 Workspace Management System
- 20.2 AI Memory Layer & Coreference Resolution
- 20.3 Natural Language Dashboard Builder
- 20.4 Executive Report Studio (Markdown, Slides, PDF)
- 20.5 Data Storytelling Engine
- 20.6 Dashboard Templates Marketplace & Auto-Mapping
- 20.7 Dataset Relationship Engine & Join Graph
- 20.8 Enterprise Semantic Business Layer
- 20.9 KPI Knowledge Engine & Live Computation
- 20.10 Autonomous AI Analyst Mode (Universal Orchestration)
- REST API Integration Gateway Verification
"""

from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path
from typing import Any
import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from backend.app.main import create_app
from backend.app.services.autonomous_ai_analyst import AutonomousAIAnalyst
from backend.app.services.dashboard_builder_service import DashboardBuilderService
from backend.app.services.dashboard_marketplace_service import DashboardMarketplaceService
from backend.app.services.dataset_relationship_service import DatasetRelationshipEngine
from backend.app.services.data_storytelling_service import DataStorytellingEngine
from backend.app.services.kpi_knowledge_engine import KPIKnowledgeEngine
from backend.app.services.report_studio_service import ReportStudioService, ReportType
from backend.app.services.semantic_layer_service import SemanticBusinessLayer
from backend.app.services.workspace_orchestration_service import (
    WorkspaceOrchestrationService,
    WorkspaceMemberRole,
    WorkspaceStatus,
)
from backend.memory.ai_memory_layer import AIMemoryLayer


@pytest.fixture
def temp_storage():
    """Create a temporary directory for isolated file persistence during tests."""
    temp_dir = tempfile.mkdtemp(prefix="phase20_test_")
    yield Path(temp_dir)
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def sample_sales_df() -> pd.DataFrame:
    """Authentic commercial sales dataframe."""
    np.random.seed(42)
    dates = pd.date_range("2024-01-01", periods=36, freq="ME").strftime("%Y-%m-%d")
    return pd.DataFrame({
        "order_id": [f"ORD-{i:04d}" for i in range(1, 37)],
        "order_date": dates,
        "revenue": [12000 + i * 850 + np.random.randint(-500, 500) for i in range(36)],
        "cogs": [4500 + i * 320 + np.random.randint(-200, 200) for i in range(36)],
        "category": (["Enterprise", "SMB", "Mid-Market"] * 12),
        "customer_id": [f"CUST-{100 + (i % 10)}" for i in range(36)],
        "quantity": np.random.randint(1, 20, size=36),
    })


@pytest.fixture
def sample_customers_df() -> pd.DataFrame:
    """Authentic customer entity dataframe for join tests."""
    return pd.DataFrame({
        "customer_id": [f"CUST-{100 + i}" for i in range(10)],
        "customer_name": [f"Acme Corp {i}" for i in range(10)],
        "region": ["North America", "EMEA", "APAC", "North America", "LATAM"] * 2,
        "segment": ["Enterprise", "Mid-Market"] * 5,
    })


# =============================================================================
# 1. Workspace Management Tests (Phase 20.1)
# =============================================================================

class TestPhase20_1_WorkspaceManagement:
    def test_workspace_lifecycle_and_resource_scoping(self, temp_storage: Path):
        svc = WorkspaceOrchestrationService(storage_dir=temp_storage)

        # 1. Create Workspaces
        ws_sales = svc.create_workspace("Sales Analytics", description="Sales & Revenue Hub")
        ws_finance = svc.create_workspace("Finance Analytics", description="FP&A and Treasury")

        assert ws_sales["name"] == "Sales Analytics"
        assert ws_sales["status"] == WorkspaceStatus.ACTIVE
        assert len(ws_sales["members"]) == 1
        assert ws_sales["members"][0]["role"] == WorkspaceMemberRole.OWNER

        # 2. Add Members
        svc.add_member(ws_sales["id"], user_id="analyst-1", email="analyst@enterprise.ai", role=WorkspaceMemberRole.ANALYST)
        svc.add_member(ws_sales["id"], user_id="viewer-1", email="viewer@enterprise.ai", role=WorkspaceMemberRole.VIEWER)

        updated_ws = svc.get_workspace(ws_sales["id"])
        assert len(updated_ws["members"]) == 3

        # 3. Associate Scoped Resources
        svc.associate_resource(ws_sales["id"], "datasets", {"id": "ds-101", "name": "Q3_Sales.csv"})
        svc.associate_resource(ws_sales["id"], "dashboards", {"id": "dash-01", "title": "Sales Executive View"})
        svc.associate_resource(ws_sales["id"], "reports", {"id": "rep-01", "title": "Q3 Board Deck"})
        svc.associate_resource(ws_sales["id"], "forecasts", {"id": "fc-01", "target": "revenue"})
        svc.associate_resource(ws_sales["id"], "insights", {"id": "ins-01", "summary": "Growth +14%"})

        res = svc.get_workspace_resources(ws_sales["id"])
        assert len(res["datasets"]) == 1
        assert len(res["dashboards"]) == 1
        assert len(res["reports"]) == 1
        assert len(res["forecasts"]) == 1
        assert len(res["insights"]) == 1

        # 4. Archive & Delete
        svc.archive_workspace(ws_finance["id"])
        assert svc.get_workspace(ws_finance["id"])["status"] == WorkspaceStatus.ARCHIVED

        assert svc.delete_workspace(ws_finance["id"]) is True
        assert len(svc.list_workspaces()) == 1


# =============================================================================
# 2. AI Memory Layer Tests (Phase 20.2)
# =============================================================================

class TestPhase20_2_AIMemoryLayer:
    def test_multi_tier_memory_and_coreference_resolution(self, temp_storage: Path):
        mem = AIMemoryLayer(storage_dir=temp_storage)
        ws_id = "ws-test"
        sess_id = "sess-001"

        # Turn 1: User asks to analyze revenue
        turn1 = mem.record_turn(ws_id, sess_id, "Analyze revenue.", "Revenue is $1.2M, up 14% YoY.")
        mem.record_analytics_execution(
            ws_id, sess_id,
            question="Analyze revenue",
            sql_query="SELECT SUM(revenue) FROM sales;",
            key_metrics={"total_revenue": 1_200_000, "growth_pct": 14.2},
        )

        # Turn 2: User runs a forecast
        mem.record_forecast(
            ws_id, sess_id,
            target_column="revenue",
            model_name="Prophet_Ensemble",
            horizon_periods=6,
            historical_summary={"mean": 100_000},
            forecast_values=[110_000.0, 115_000.0, 118_000.0],
            metrics={"MAPE": 3.8},
        )

        # Turn 3: User asks "Compare with last forecast."
        res1 = mem.resolve_contextual_query("Compare with last forecast.", ws_id, sess_id)
        assert res1["has_memory_dependency"] is True
        assert res1["referenced_forecast"] is not None
        assert "Prophet_Ensemble" in res1["context_augmented_prompt"]

        # Turn 4: User asks "Why is it lower?"
        res2 = mem.resolve_contextual_query("Why is it lower?", ws_id, sess_id)
        assert res2["has_memory_dependency"] is True
        assert res2["referenced_analytics"] is not None
        assert "total_revenue" in res2["context_augmented_prompt"]


# =============================================================================
# 3. Dashboard Builder Tests (Phase 20.3)
# =============================================================================

class TestPhase20_3_DashboardBuilder:
    def test_natural_language_dashboard_creation(self, temp_storage: Path, sample_sales_df: pd.DataFrame):
        builder = DashboardBuilderService(storage_dir=temp_storage)

        dash = builder.create_dashboard_from_prompt(
            prompt="Create Executive Sales Dashboard",
            df=sample_sales_df,
            workspace_id="ws-sales",
        )

        assert dash["id"].startswith("dash-")
        assert len(dash["kpis"]) >= 3
        assert any("Revenue" in k["label"] for k in dash["kpis"])
        assert len(dash["charts"]) >= 2
        assert any(c["type"] == "line" for c in dash["charts"])
        assert any(c["type"] == "donut" for c in dash["charts"])
        assert len(dash["layout"]) == len(dash["charts"])
        assert len(dash["insights"]) >= 3


# =============================================================================
# 4. Executive Report Studio Tests (Phase 20.4)
# =============================================================================

class TestPhase20_4_ReportStudio:
    def test_multi_format_report_generation(self, temp_storage: Path, sample_sales_df: pd.DataFrame):
        studio = ReportStudioService(storage_dir=temp_storage)

        rep = studio.generate_report(
            title="Q3 Board of Directors Performance Dossier",
            report_type=ReportType.BOARD,
            df=sample_sales_df,
            workspace_id="ws-corp",
        )

        assert rep["id"].startswith("rep-")
        assert "Executive Summary" in rep["markdown"]
        assert len(rep["slides"]) == 4
        assert rep["pdf_size_bytes"] > 1000
        assert os.path.exists(rep["pdf_path"])

        # Test Scheduling
        sched = studio.schedule_report(
            title="Automated Weekly Sales Audit",
            report_type=ReportType.WEEKLY_OPS,
            frequency="weekly",
        )
        assert sched["status"] == "active"
        assert len(studio.list_reports("ws-corp")) == 1


# =============================================================================
# 5. Data Storytelling Engine Tests (Phase 20.5)
# =============================================================================

class TestPhase20_5_DataStorytelling:
    def test_narrative_generation_and_confidence(self, sample_sales_df: pd.DataFrame):
        engine = DataStorytellingEngine()

        story = engine.generate_story(
            query="Analyze commercial revenue growth drivers",
            df=sample_sales_df,
            forecast_data={"expected_growth_pct": 12.5},
        )

        assert any(seg in story["executive_summary"] for seg in ["Enterprise", "Mid-Market", "SMB"])

        assert len(story["key_findings"]) >= 3
        assert len(story["risks"]) >= 1
        assert len(story["opportunities"]) >= 1
        assert len(story["recommendations"]) >= 3
        assert 0.80 <= story["confidence_score"] <= 1.0
        assert story["evidence_chain"]["grounded"] is True


# =============================================================================
# 6. Dashboard Templates Marketplace Tests (Phase 20.6)
# =============================================================================

class TestPhase20_6_DashboardMarketplace:
    def test_template_catalog_and_auto_mapping(self, sample_sales_df: pd.DataFrame):
        market = DashboardMarketplaceService()

        templates = market.get_templates()
        assert len(templates) == 5
        template_ids = [t["id"] for t in templates]
        assert "tpl-sales" in template_ids
        assert "tpl-finance" in template_ids

        # Test auto-mapping against sales df
        mapping = market.map_dataset_to_template("tpl-sales", sample_sales_df)
        assert mapping["overall_match_pct"] >= 70.0
        assert mapping["slot_mapping"]["value"] == "revenue"
        assert mapping["slot_mapping"]["date"] == "order_date"

        # Apply template
        dash = market.apply_template_to_dataset("tpl-sales", sample_sales_df)
        assert dash["marketplace_metadata"]["template_id"] == "tpl-sales"
        assert len(dash["kpis"]) >= 3


# =============================================================================
# 7. Dataset Relationship Engine Tests (Phase 20.7)
# =============================================================================

class TestPhase20_7_RelationshipEngine:
    def test_pk_fk_discovery_and_sql_join(self, sample_sales_df: pd.DataFrame, sample_customers_df: pd.DataFrame):
        engine = DatasetRelationshipEngine()

        # 1. Primary Key Detection
        pks_cust = engine.detect_candidate_pks(sample_customers_df)
        assert len(pks_cust) >= 1
        assert pks_cust[0]["column"] == "customer_id"

        # 2. Join Relationship Discovery
        datasets = {
            "sales.csv": sample_sales_df,
            "customers.csv": sample_customers_df,
        }
        joins = engine.detect_relationships(datasets)
        assert len(joins) >= 1
        rel = joins[0]
        assert rel["source_column"] == "customer_id" or rel["target_column"] == "customer_id"
        assert rel["relationship_type"] in ["1:N", "N:1", "1:1"]
        assert rel["confidence"] >= 0.70

        # 3. Schema Graph & SQL Generation
        graph = engine.generate_schema_graph(datasets)
        assert graph["total_datasets"] == 2
        assert graph["total_relationships"] >= 1

        sql = engine.generate_multi_table_sql("sales.csv", "customers.csv", rel)
        assert "JOIN" in sql
        assert "ON" in sql


# =============================================================================
# 8. Enterprise Semantic Business Layer Tests (Phase 20.8)
# =============================================================================

class TestPhase20_8_SemanticBusinessLayer:
    def test_glossary_synonyms_and_translation(self):
        semantic = SemanticBusinessLayer()

        # 1. Cryptic column resolution
        concept_rev = semantic.resolve_column_to_concept("rev_amt")
        assert concept_rev is not None
        assert concept_rev["canonical_key"] == "revenue"
        assert concept_rev["business_name"] == "Gross Revenue"

        concept_cust = semantic.resolve_column_to_concept("cust_id")
        assert concept_cust is not None
        assert concept_cust["canonical_key"] == "customer_id"

        concept_qty = semantic.resolve_column_to_concept("qty_sold")
        assert concept_qty is not None
        assert concept_qty["canonical_key"] == "quantity"

        # 2. Query Term Translation
        cols = ["rev_amt", "cust_id", "order_date"]
        mapped = semantic.translate_query_terms_to_columns("Show total sales by customer", cols)
        assert "sales" in mapped
        assert mapped["sales"] == "rev_amt"


# =============================================================================
# 9. KPI Knowledge Engine Tests (Phase 20.9)
# =============================================================================

class TestPhase20_9_KPIKnowledgeEngine:
    def test_kpi_detection_and_live_calculation(self, sample_sales_df: pd.DataFrame):
        engine = KPIKnowledgeEngine()

        catalog = engine.get_kpi_catalog()
        assert len(catalog) >= 8

        computable = engine.detect_computable_kpis(sample_sales_df)
        assert len(computable) >= 4
        comp_ids = [c["id"] for c in computable]
        assert "gross_margin" in comp_ids
        assert "aov" in comp_ids

        results = engine.calculate_kpis(sample_sales_df)
        assert len(results) >= 4
        gm = next(r for r in results if r["id"] == "gross_margin")
        assert "%" in gm["formatted"]
        assert gm["status"] in ["healthy", "warning"]

        aov = next(r for r in results if r["id"] == "aov")
        assert "$" in aov["formatted"]
        assert aov["value"] > 0


# =============================================================================
# 10. Autonomous AI Analyst Mode Tests (Phase 20.10)
# =============================================================================

class TestPhase20_10_AutonomousAIAnalyst:
    def test_universal_orchestrator_multi_agent_execution(self, sample_sales_df: pd.DataFrame):
        analyst = AutonomousAIAnalyst()

        query = "How is our quarterly revenue performing, forecast upcoming trend, and what are the strategic risks?"
        result = analyst.execute(
            query=query,
            df=sample_sales_df,
            workspace_id="ws-enterprise",
            session_id="sess-analyst-01",
        )

        assert "executive_answer" in result
        assert len(result["kpis"]) >= 3
        assert len(result["visualizations"]) >= 1
        assert result["forecast"] is not None
        assert len(result["forecast"]["forecast_values"]) == 6
        assert len(result["story"]["key_findings"]) >= 3
        assert len(result["story"]["risks"]) >= 1
        assert len(result["story"]["recommendations"]) >= 3
        assert result["execution_metadata"]["rows_analyzed"] == len(sample_sales_df)
        assert result["execution_metadata"]["confidence_score"] >= 0.85

        # Check that turn was recorded in AI Memory Layer
        mem = analyst.memory
        hist = mem.get_conversation_history("ws-enterprise", "sess-analyst-01")
        assert len(hist) >= 1
        assert hist[-1]["user_message"] == query


# =============================================================================
# 11. REST API Integration Gateway Verification
# =============================================================================

class TestPhase20_RESTAPIGateway:
    def test_all_phase20_endpoints(self):
        app = create_app()
        client = TestClient(app)

        # 1. Workspaces
        res_ws = client.post("/api/v1/os/workspaces", json={"name": "Live Executive Space", "description": "Testing WS"})
        assert res_ws.status_code == 200
        ws_id = res_ws.json()["id"]

        res_list = client.get("/api/v1/os/workspaces")
        assert res_list.status_code == 200
        assert any(w["id"] == ws_id for w in res_list.json())

        # 2. Memory Resolve
        res_mem = client.post("/api/v1/os/memory/resolve", json={"query": "Compare with last forecast", "workspace_id": ws_id})
        assert res_mem.status_code == 200

        # 3. Dashboard Builder
        res_dash = client.post("/api/v1/os/dashboards/generate", json={"prompt": "Executive Revenue Overview", "workspace_id": ws_id})
        assert res_dash.status_code == 200
        assert "kpis" in res_dash.json()

        # 4. Report Studio
        res_rep = client.post("/api/v1/os/reports/studio/generate", json={"title": "Q3 Executive Dossier", "workspace_id": ws_id})
        assert res_rep.status_code == 200
        assert "markdown" in res_rep.json()

        # 5. Data Storytelling
        res_story = client.post("/api/v1/os/storytelling/generate", json={"query": "Show revenue drivers"})
        assert res_story.status_code == 200
        assert "key_findings" in res_story.json()

        # 6. Marketplace
        res_tpl = client.get("/api/v1/os/marketplace/templates")
        assert res_tpl.status_code == 200
        assert len(res_tpl.json()) == 5

        # 7. Semantic Glossary
        res_sem = client.get("/api/v1/os/semantic/glossary")
        assert res_sem.status_code == 200
        assert "revenue" in res_sem.json()

        # 8. KPI Catalog
        res_kpi = client.get("/api/v1/os/kpis/catalog")
        assert res_kpi.status_code == 200
        assert len(res_kpi.json()) >= 8

        # 9. Autonomous AI Analyst
        res_analyst = client.post("/api/v1/os/analyst/execute", json={"query": "Analyze top revenue trends and risks", "workspace_id": ws_id})
        assert res_analyst.status_code == 200
        data = res_analyst.json()
        assert "executive_answer" in data
        assert "forecast" in data
        assert "story" in data
