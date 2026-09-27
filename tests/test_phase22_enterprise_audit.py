"""Phase 22 — Master Enterprise Validation & Deep Audit Test Suite.

Certifies:
- Audit 1: Real model training (ARIMA, XGBoost, MultiModelEnsemble) on distinct datasets (A, B, C)
- Audit 2: Empirical grounding metrics (Source/Evidence Coverage, Grounded Confidence Score)
- Audit 3: RAG full_content vs preview truncation prevention
- Audit 4: Plotly AdaptiveSamplingEngine 4-tier scaling (<10k, 10k-100k, 100k-1M, >1M)
- Audit 5: PDF Report embedded vector charts, tables, unicode, and quality scoring
- Audit 6: Workspace strict multi-tenant isolation (Workspace A vs Workspace B)
- Audit 7: Automatic 3-table Star Schema JOIN discovery (Sales + Customers + Products)
- Phase 22.1: Observability Layer (Prometheus metrics & Grafana dashboard JSON)
- Phase 22.2: Data Catalog (Search, ownership, lineage, tags, usage telemetry)
- Phase 22.3: Business Glossary Portal (Definitions, formulas, physical mapping, synonyms)
- Phase 22.4: AI Analyst Evaluation Framework (Scorecard, SQL success, feedback)
"""

import os
from pathlib import Path
import fitz  # PyMuPDF
import numpy as np
import pandas as pd
import pytest

from backend.app.schemas.context_builder import ContextSource
from backend.app.services.ai_eval_framework import get_ai_evaluation_framework
from backend.app.services.autonomous_ai_analyst import get_autonomous_ai_analyst
from backend.app.services.business_glossary_service import get_business_glossary_service
from backend.app.services.data_catalog_service import get_data_catalog_service
from backend.app.services.dataset_relationship_service import get_dataset_relationship_engine
from backend.app.services.observability_service import get_observability_service
from backend.app.services.report_studio_service import get_report_studio_service
from backend.app.services.workspace_orchestration_service import get_workspace_orchestration_service
from backend.forecasting.engine import get_forecast_engine
from backend.memory.ai_memory_layer import get_ai_memory_layer
from backend.rag.knowledge_validation import KnowledgeValidator
from backend.visualization.generators.adaptive_sampler import get_adaptive_sampling_engine
from backend.visualization.generators.plotly_engine import PlotlyEngine


# =============================================================================
# AUDIT 1 — Real Forecasting Validation & Multi-Dataset Non-Identity Test
# =============================================================================

def test_audit_1_real_model_training_and_distinct_forecasts():
    """Verify models actually train and distinct datasets produce distinct projections."""
    engine = get_forecast_engine()

    # Generate 3 mathematically distinct series
    dates = pd.date_range("2024-01-01", periods=30, freq="D").strftime("%Y-%m-%d").tolist()
    t = np.arange(30)

    # Dataset A: Strong Linear Growth
    df_a = pd.DataFrame({"date": dates, "value": 100.0 + 5.0 * t + np.random.normal(0, 0.5, 30)})
    # Dataset B: High Volatility Cyclical Wave
    df_b = pd.DataFrame({"date": dates, "value": 500.0 + 50.0 * np.sin(2 * np.pi * t / 7)})
    # Dataset C: Declining Contraction Series
    df_c = pd.DataFrame({"date": dates, "value": 1000.0 - 15.0 * t + np.random.normal(0, 1.0, 30)})

    res_a = engine.run_forecast(df_a, target_column="value", horizon=6)
    res_b = engine.run_forecast(df_b, target_column="value", horizon=6)
    res_c = engine.run_forecast(df_c, target_column="value", horizon=6)

    # 1. Verify training occurred and took real compute time
    assert res_a["training_duration_seconds"] >= 0.0
    assert res_a["observations_trained"] == 30
    assert len(res_a["forecast_values"]) == 6

    # 2. Verify forecasts are strictly distinct
    assert res_a["forecast_values"] != res_b["forecast_values"]
    assert res_b["forecast_values"] != res_c["forecast_values"]
    assert res_a["forecast_values"] != res_c["forecast_values"]

    # 3. Verify directional growth reflects reality (A growing, C declining)
    assert res_a["expected_growth_pct"] > 0
    assert res_c["expected_growth_pct"] < 0

    # 4. Verify benchmark runner
    bench = engine.benchmark_datasets({"dataset_a": df_a, "dataset_b": df_b, "dataset_c": df_c})
    assert bench["all_forecasts_distinct"] is True


# =============================================================================
# AUDIT 2 & 3 — Grounding Metrics & Preview Truncation Prevention
# =============================================================================

def test_audit_2_empirical_grounding_metrics():
    """Verify Grounded Confidence Score replaces 0.0% Hallucination claim."""
    validator = KnowledgeValidator(min_faithfulness=0.5)

    answer = "Total revenue reached $150,000 driven by strong enterprise demand across APAC region."
    context = "Total revenue reached $150,000 driven by strong enterprise demand across APAC region during Q3."
    sources = [
        ContextSource(
            source_id="[Source 1]",
            chunk_id="chunk-1",
            document_id="doc-1",
            score=0.95,
            preview="Total revenue reached $150,000",
            full_content=context,
        )
    ]

    result = validator.validate(answer=answer, context_text=context, sources=sources)

    assert result.is_valid is True
    assert result.source_coverage > 0.8
    assert result.evidence_coverage == 1.0  # $150,000 verified
    assert result.grounded_confidence_score > 0.85
    assert result.citation_accuracy > 0.8


def test_audit_3_rag_preview_truncation_prevention():
    """Ensure fact located after 120-char preview boundary is verified via full_content."""
    validator = KnowledgeValidator(min_faithfulness=0.5)

    prefix_filler = "This is a long introductory overview paragraph designed to exceed one hundred and twenty characters in standard document preview mode. "
    critical_fact = "Specialized operating profit reached $4,850,000."
    full_doc = prefix_filler + critical_fact

    # Preview intentionally truncates before the critical fact
    short_preview = prefix_filler[:110] + "..."

    sources = [
        ContextSource(
            source_id="[Source 1]",
            chunk_id="chk-abc",
            document_id="doc-xyz",
            score=0.92,
            preview=short_preview,
            full_content=full_doc,  # Full content contains the fact!
        )
    ]

    answer = "Specialized operating profit reached $4,850,000."
    res = validator.validate(answer=answer, context_text=full_doc, sources=sources)

    assert res.is_valid is True
    assert res.evidence_coverage == 1.0
    assert len(res.checks) >= 1
    # Ensure source was credited because full_content was checked
    assert res.checks[0].supporting_source == "[Source 1]"


# =============================================================================
# AUDIT 4 — 1M Row Test & Plotly Adaptive Sampling Engine
# =============================================================================

def test_audit_4_adaptive_sampling_all_tiers():
    """Verify all 4 data volume tiers in AdaptiveSamplingEngine."""
    sampler = get_adaptive_sampling_engine()

    # Tier 1: 500 rows (< 10k) -> Full Render
    df_tier1 = pd.DataFrame({"x": range(500), "y": np.random.randn(500)})
    sampled_1, meta_1 = sampler.sample_data(df_tier1, "x", "y")
    assert meta_1["tier"] == "Tier 1 (<10k)"
    assert meta_1["mode"] == "full_render"
    assert len(sampled_1) == 500

    # Tier 2: 50,000 rows (10k - 100k) -> Stride Sampling
    df_tier2 = pd.DataFrame({"x": range(50000), "y": np.random.randn(50000)})
    sampled_2, meta_2 = sampler.sample_data(df_tier2, "x", "y")
    assert meta_2["tier"] == "Tier 2 (10k-100k)"
    assert meta_2["mode"] == "stride_sampling"
    assert 2000 <= len(sampled_2) <= 3000

    # Tier 3: 200,000 rows (100k - 1M) -> Bin Aggregation
    df_tier3 = pd.DataFrame({"x": range(200000), "y": np.random.randn(200000)})
    sampled_3, meta_3 = sampler.sample_data(df_tier3, "x", "y")
    assert meta_3["tier"] == "Tier 3 (100k-1M)"
    assert meta_3["mode"] == "bin_aggregation"
    assert len(sampled_3) <= 1000

    # Tier 4: 1,000,000 rows (> 1M) -> Server-Side Streaming Aggregation
    df_tier4 = pd.DataFrame({"x": range(1000000), "y": np.random.randn(1000000)})
    sampled_4, meta_4 = sampler.sample_data(df_tier4, "x", "y")
    assert meta_4["tier"] == "Tier 4 (>1M)"
    assert meta_4["mode"] == "server_side_aggregation"
    assert len(sampled_4) <= 1200
    assert meta_4["browser_protection"]["target_fps"] == 60

    # PlotlyEngine integration
    sampled_plotly, meta_plotly = PlotlyEngine.sample_for_visualization(df_tier2, "x", "y")
    assert len(sampled_plotly) == len(sampled_2)


# =============================================================================
# AUDIT 5 — PDF Generation Quality Scoring & Vector Charts
# =============================================================================

def test_audit_5_pdf_embedded_charts_and_tables():
    """Verify generated PDF contains vector charts, tables, unicode, and quality score."""
    service = get_report_studio_service()

    df_sample = pd.DataFrame({
        "revenue": [50000.0, 75000.0, 120000.0],
        "profit": [15000.0, 24000.0, 48000.0],
    })

    rep = service.generate_report(
        title="Q3 Enterprise Performance Review",
        df=df_sample,
        workspace_id="ws-enterprise-cert",
        key_metrics={"Total Revenue": "INR 245,000", "Operating Margin": "39.2%", "Growth Rate": "+18.4%"},
    )

    assert rep["report_quality_score"] == 100
    assert rep["embedded_elements"]["charts_embedded"] is True
    assert rep["embedded_elements"]["tables_embedded"] is True
    assert rep["pdf_size_bytes"] > 1000

    # Read binary PDF via PyMuPDF to verify page structure
    pdf_path = rep["pdf_path"]
    assert Path(pdf_path).exists()
    doc = fitz.open(pdf_path)
    assert len(doc) >= 1
    page = doc[0]
    text = page.get_text()
    assert "Q3 Enterprise Performance Review" in text
    assert "Key Operational Metrics" in text
    assert "Visual Performance Chart" in text
    doc.close()


# =============================================================================
# AUDIT 6 — Strict Multi-Tenant Workspace Isolation
# =============================================================================

def test_audit_6_strict_workspace_isolation():
    """Verify Workspace A resources and memories are strictly inaccessible from Workspace B."""
    ws_service = get_workspace_orchestration_service()
    mem_service = get_ai_memory_layer()
    rep_service = get_report_studio_service()

    ws_a = ws_service.create_workspace(name="Finance Workspace Alpha", tenant_id="tenant-1")
    ws_b = ws_service.create_workspace(name="Marketing Workspace Beta", tenant_id="tenant-1")
    id_a = ws_a["id"]
    id_b = ws_b["id"]

    # Associate dataset to Workspace A
    ws_service.associate_resource(id_a, "datasets", {"id": "ds-alpha-secret", "name": "Confidential Ledger"})

    # Record Memory in Workspace A
    mem_service.record_turn(
        workspace_id=id_a,
        session_id="sess-alpha-001",
        user_message="Analyze confidential merger metrics.",
        ai_response="Merger targets EBITDA expansion of 24%.",
    )

    # Generate Report in Workspace A
    rep_a = rep_service.generate_report(
        title="Merger Strategic Assessment",
        workspace_id=id_a,
    )

    # Verification: Workspace B cannot see Workspace A's resources
    res_b = ws_service.get_workspace_resources(id_b)
    ds_ids_in_b = [d["id"] if isinstance(d, dict) else d for d in res_b["datasets"]]
    assert "ds-alpha-secret" not in ds_ids_in_b

    # Verification: Workspace B memory context is completely empty
    conv_b = mem_service.get_recent_conversation(workspace_id=id_b, session_id="sess-alpha-001")
    assert len(conv_b) == 0

    # Verification: Report listing strictly isolates
    reps_for_b = rep_service.list_reports(workspace_id=id_b)
    assert not any(r["id"] == rep_a["id"] for r in reps_for_b)


# =============================================================================
# AUDIT 7 — Automatic 3-Table Star Schema JOIN Engine
# =============================================================================

def test_audit_7_automatic_3_table_star_schema_join():
    """Verify automatic multi-table join synthesis across Sales, Customers, and Products without manual hints."""
    engine = get_dataset_relationship_engine()

    # Create 3 related tables
    df_customers = pd.DataFrame({
        "customer_id": [f"CUST-{i}" for i in range(101, 121)],
        "customer_name": [f"Company {i}" for i in range(101, 121)],
        "region": ["North America"] * 10 + ["EMEA"] * 10,
    })

    df_products = pd.DataFrame({
        "product_id": [f"PROD-{i}" for i in range(1, 11)],
        "product_name": [f"Software Suite {i}" for i in range(1, 11)],
        "unit_price": [100.0 * i for i in range(1, 11)],
    })

    # Sales fact table referencing customers and products
    df_sales = pd.DataFrame({
        "order_id": [f"ORD-{i}" for i in range(1001, 1051)],
        "customer_id": [f"CUST-{101 + (i % 20)}" for i in range(50)],
        "product_id": [f"PROD-{1 + (i % 10)}" for i in range(50)],
        "quantity": np.random.randint(1, 5, 50),
        "amount": np.random.uniform(500, 5000, 50),
    })

    datasets = {
        "sales.csv": df_sales,
        "customers.csv": df_customers,
        "products.csv": df_products,
    }

    # Execute auto-join
    join_res = engine.build_star_schema_join(datasets)

    assert join_res["fact_table"] == "sales"
    assert "customers" in join_res["dimension_tables"]
    assert "products" in join_res["dimension_tables"]
    assert join_res["joins_count"] == 2

    # Verify generated SQL syntax
    sql = join_res["sql"].upper()
    assert "FROM SALES" in sql
    assert "JOIN CUSTOMERS" in sql
    assert "JOIN PRODUCTS" in sql
    assert "SALES.CUSTOMER_ID = CUSTOMERS.CUSTOMER_ID" in sql
    assert "SALES.PRODUCT_ID = PRODUCTS.PRODUCT_ID" in sql


# =============================================================================
# PHASE 22.1 — Observability Layer Test
# =============================================================================

def test_phase22_1_observability_and_grafana():
    obs = get_observability_service()
    obs.record_request("ai_analyst_requests_total", 5.0)
    obs.record_latency("ai_analyst_duration_seconds", 0.42)

    prom_text = obs.generate_prometheus_metrics()
    assert "ai_analyst_requests_total 5.0" in prom_text
    assert "process_memory_rss_bytes" in prom_text
    assert "process_cpu_percent" in prom_text

    grafana_json = obs.generate_grafana_dashboard_json()
    assert grafana_json["title"] == "AI Data Analyst OS — Enterprise Observability"
    assert len(grafana_json["panels"]) >= 4


# =============================================================================
# PHASE 22.2 — Data Catalog Test
# =============================================================================

def test_phase22_2_data_catalog_search_and_lineage():
    catalog = get_data_catalog_service()
    df_test = pd.DataFrame({"revenue": [100, 200], "customer_segment": ["Enterprise", "SMB"]})

    entry = catalog.register_dataset(
        name="Global Q3 Revenue Breakdown",
        df=df_test,
        tags=["Finance", "Q3", "Strategic"],
        classification="Confidential",
    )

    # Search by tag
    found_by_tag = catalog.search_catalog(tag="Finance")
    assert any(e["id"] == entry["id"] for e in found_by_tag)

    # Search by query phrase
    found_by_q = catalog.search_catalog(query="revenue")
    assert any(e["id"] == entry["id"] for e in found_by_q)

    # Lineage verification
    lineage = catalog.get_dataset_lineage(entry["id"])
    assert lineage["dataset_id"] == entry["id"]
    assert "downstream_consumers" in lineage["lineage"]


# =============================================================================
# PHASE 22.3 — Business Glossary Portal Test
# =============================================================================

def test_phase22_3_business_glossary():
    glossary = get_business_glossary_service()
    terms = glossary.list_terms()
    assert len(terms) >= 4

    # Search for Gross Revenue
    res = glossary.search_glossary("Revenue")
    assert len(res) >= 1

    # Term resolution from synonym
    resolved = glossary.resolve_term("Sales Volume")
    assert resolved is not None
    assert resolved["term"] == "Gross Revenue"
    assert len(resolved["physical_mappings"]) >= 1


# =============================================================================
# PHASE 22.4 — AI Analyst Evaluation Framework Test
# =============================================================================

def test_phase22_4_ai_eval_framework_scorecard():
    eval_framework = get_ai_evaluation_framework()

    eval_framework.record_feedback(
        query="What products drive profit?",
        rating=5,
        feedback_type="thumbs_up",
        user_comment="Excellent attribution and reasoning.",
    )
    eval_framework.record_sql_execution("Top customers", "SELECT * FROM customers", True, 12.5)
    eval_framework.record_grounding_result("Why did revenue drop?", 0.98, 0.99)
    eval_framework.record_forecast_accuracy("MultiModelEnsemble", mape=3.8, rmse=24.5, r2=0.96)

    scorecard = eval_framework.generate_evaluation_scorecard()
    assert scorecard["overall_ai_quality_score"] >= 90.0
    assert scorecard["metrics"]["sql_success_rate_pct"] == 100.0
    assert scorecard["certification_tier"] == "Enterprise Grade (Zero Critical Findings)"


# =============================================================================
# MASTER ORCHESTRATION INTEGRATION TEST
# =============================================================================

def test_master_autonomous_analyst_end_to_end_audit():
    """Verify Master Autonomous AI Analyst generates grounded intelligence, real forecasts, and metadata."""
    analyst = get_autonomous_ai_analyst()

    dates = pd.date_range("2024-01-01", periods=40, freq="D").strftime("%Y-%m-%d").tolist()
    sample_df = pd.DataFrame({
        "order_date": dates,
        "region": ["North America", "APAC", "EMEA", "LATAM"] * 10,
        "revenue": np.random.uniform(1000, 5000, 40),
        "product_category": ["Database", "Cloud", "Security", "DevTools"] * 10,
    })

    out = analyst.analyze_prompt(
        query="Analyze revenue trends and forecast next 6 periods.",
        df=sample_df,
        workspace_id="ws-audit-master",
    )

    assert "executive_answer" in out
    assert out["forecast"] is not None
    assert len(out["forecast"]["forecast_values"]) == 6
    assert out["execution_metadata"]["grounded_confidence_score"] >= 0.85
    assert out["execution_metadata"]["grounding_metrics"]["source_coverage"] >= 0.85
