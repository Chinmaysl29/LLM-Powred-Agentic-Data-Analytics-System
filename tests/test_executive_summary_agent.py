"""Comprehensive tests for Phase 3.8 Executive Summary Agent.

Verifies:
1. Insight aggregation across EDA, Statistics, Validation, Quality, and Metadata.
2. Key findings generation with primary trends, concentration, and statistical drivers.
3. Opportunity detection (growth, expansion, optimization).
4. Risk detection (business, operational, data risks).
5. Action recommendation layer across immediate, short-term, and long-term horizons.
6. Executive narrative generation translating technical metrics to business language.
7. Multi-level summaries (30-second quick, manager, executive, board).
8. Business health scoring and clamping (0 - 100).
9. Priority engine classification (critical, high, medium, low).
10. Output schema adherence.
11. Concrete Agent Runner (ExecutiveSummaryAgentRunner).
12. FastAPI endpoints (POST /api/v1/summary/generate and GET /api/v1/summary/{dataset_id}).
13. Full Orchestrator end-to-end integration.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.agents.executive_summary_agent import ExecutiveSummaryAgentRunner
from backend.app.database.postgres import get_db_session
from backend.app.models.base import Base
from backend.app.models.dataset import Dataset
from backend.app.models.dataset_metadata import DatasetMetadata
from backend.app.models.dataset_quality import DatasetQuality
from backend.app.schemas.orchestrator import WorkflowContext
from backend.app.services.executive_summary_service import ExecutiveSummaryService
from backend.app.services.orchestrator_service import OrchestratorService
from backend.main import app


# ----------------------------------------------------------------------
# Test Fixtures & Sample Payloads
# ----------------------------------------------------------------------
@pytest.fixture
def summary_service() -> ExecutiveSummaryService:
    return ExecutiveSummaryService()


@pytest.fixture
def rich_agent_results() -> dict:
    """Rich mock of upstream agent outputs mirroring realistic enterprise execution."""
    return {
        "eda": {
            "dataset_summary": {
                "dataset_type": "sales",
                "business_domain": "e-commerce retail",
                "row_count": 15000,
                "column_count": 8,
            },
            "trend_analysis": [
                {
                    "column": "revenue",
                    "direction": "growth",
                    "percentage_change": 14.2,
                }
            ],
            "segments": [
                {
                    "segment_name": "South Region",
                    "share_percentage": 42.0,
                    "metric": "total_sales",
                },
                {
                    "segment_name": "North Region",
                    "share_percentage": 28.0,
                    "metric": "total_sales",
                },
            ],
            "anomalies": [
                {"record_id": 101, "metric": "unit_price", "z_score": 4.2}
            ],
        },
        "statistics": {
            "primary_driver": {
                "feature": "marketing_spend",
                "importance": 0.88,
                "standardized_coefficient": 0.88,
            },
            "regression": {
                "r_squared": 0.83,
                "primary_driver": {"feature": "marketing_spend", "importance": 0.88},
            },
            "significant_correlations": [
                {
                    "variable_1": "marketing_spend",
                    "variable_2": "revenue",
                    "correlation": 0.91,
                    "p_value": 0.0002,
                }
            ],
            "hypothesis_tests": [
                {
                    "test_name": "Region A vs Region B T-Test",
                    "variable": "revenue",
                    "group_a": "South Region",
                    "group_b": "North Region",
                    "statistic": 5.42,
                    "p_value": 0.0001,
                    "null_hypothesis_rejected": True,
                }
            ],
            "root_causes": [
                {
                    "driver": "marketing_spend",
                    "variance_explained": "83%",
                }
            ],
            "business_insights": [
                "Marketing spend explains 83% of revenue variance.",
                "Customer churn observed at 8% in secondary segment.",
            ],
        },
        "validation": {
            "validation_status": "PASSED",
            "confidence_score": 96,
            "warnings": [],
            "errors": [],
        },
        "quality": {
            "quality_score": 95,
            "completeness": 99.1,
            "validity": 98.4,
        },
    }


# ----------------------------------------------------------------------
# 1. Insight Aggregation & Key Findings Tests
# ----------------------------------------------------------------------
def test_insight_aggregation_and_key_findings(summary_service: ExecutiveSummaryService, rich_agent_results: dict):
    summary = summary_service.generate_summary(results=rich_agent_results, query="Analyze Q3 sales performance")

    # Scope and domain extracted
    assert any("15,000 records" in kf for kf in summary.key_findings)
    assert any("e-commerce retail" in kf for kf in summary.key_findings)

    # Primary trend (+14.2%)
    assert any("Revenue" in kf and "+14.2%" in kf for kf in summary.key_findings)

    # Segment concentration (South Region 42%)
    assert any("South Region contributes 42.0%" in kf for kf in summary.key_findings)

    # Primary driver & correlation (Marketing spend)
    assert any("Marketing Spend is the primary outcome driver" in kf for kf in summary.key_findings)
    assert any("correlation" in kf.lower() and "0.91" in kf for kf in summary.key_findings)


# ----------------------------------------------------------------------
# 2. Opportunity Detection Tests
# ----------------------------------------------------------------------
def test_opportunity_detection(summary_service: ExecutiveSummaryService, rich_agent_results: dict):
    summary = summary_service.generate_summary(results=rich_agent_results)

    assert len(summary.opportunities) >= 2
    # Growth opportunity leverages primary driver
    assert any("marketing spend" in opp.lower() and "growth" in opp.lower() for opp in summary.opportunities)

    # Expansion opportunity targets South Region
    assert any("South Region" in opp and "expansion" in opp.lower() for opp in summary.opportunities)


# ----------------------------------------------------------------------
# 3. Risk Detection Tests
# ----------------------------------------------------------------------
def test_risk_detection_declining_and_concentration(summary_service: ExecutiveSummaryService):
    declining_payload = {
        "eda": {
            "dataset_summary": {"dataset_type": "sales", "business_domain": "retail"},
            "trend_analysis": [
                {
                    "column": "sales",
                    "direction": "decline",
                    "percentage_change": -12.5,
                }
            ],
            "segments": [
                {"segment_name": "Key Client", "share_percentage": 55.0, "metric": "revenue"}
            ],
            "anomalies": [{"id": 1}],
        },
        "validation": {
            "validation_status": "WARNING",
            "warnings": ["Potential outlier distortion in key client transactions"],
            "errors": [],
        },
        "quality": {"quality_score": 72},
    }

    summary = summary_service.generate_summary(results=declining_payload)

    # Downward trend risk detected
    assert any("downward trend" in r.lower() and "12.5%" in r for r in summary.risks)

    # High concentration risk detected (55% share)
    assert any("concentration" in r.lower() and "Key Client" in r for r in summary.risks)

    # Quality and validation risks detected
    assert any("Validation warnings present" in r for r in summary.risks)
    assert any("Sub-optimal data quality score" in r for r in summary.risks)


# ----------------------------------------------------------------------
# 4. Action Recommendation Horizons Tests
# ----------------------------------------------------------------------
def test_action_recommendation_horizons(summary_service: ExecutiveSummaryService, rich_agent_results: dict):
    summary = summary_service.generate_summary(results=rich_agent_results)

    assert len(summary.immediate_actions) > 0
    assert len(summary.short_term_actions) > 0
    assert len(summary.long_term_actions) > 0

    # Total actions aggregate all horizons
    assert len(summary.recommended_actions) == (
        len(summary.immediate_actions) + len(summary.short_term_actions) + len(summary.long_term_actions)
    )

    # Short-term reinforces primary driver and South Region
    assert any("marketing spend" in act.lower() or "south region" in act.lower() for act in summary.short_term_actions)


# ----------------------------------------------------------------------
# 5. Executive Narrative & Multi-Level Summaries Tests
# ----------------------------------------------------------------------
def test_multi_level_summaries_and_narrative(summary_service: ExecutiveSummaryService, rich_agent_results: dict):
    summary = summary_service.generate_summary(results=rich_agent_results)

    assert summary.multi_level_summaries is not None
    levels = summary.multi_level_summaries

    # Level 1: Quick 30s elevator pitch
    assert "Business Health Score:" in levels.level_1_quick_summary
    assert "e-commerce retail" in levels.level_1_quick_summary

    # Level 2: Manager Summary
    assert "OPERATIONAL MANAGER BRIEFING:" in levels.level_2_manager_summary
    assert "Key Metric Observations:" in levels.level_2_manager_summary
    assert "Departmental Action Items:" in levels.level_2_manager_summary

    # Level 3: Executive Summary (matches root executive_summary)
    assert summary.executive_summary == levels.level_3_executive_summary
    assert "Executive Recommendation:" in summary.executive_summary
    assert "marketing spend" in summary.executive_summary.lower()

    # Level 4: Board of Directors
    assert "BOARD OF DIRECTORS EXECUTIVE SUMMARY:" in levels.level_4_board_summary
    assert "Strategic Trajectory:" in levels.level_4_board_summary
    assert "Fiduciary Guidance:" in levels.level_4_board_summary


# ----------------------------------------------------------------------
# 6. Business Health Scoring & Clamping Tests
# ----------------------------------------------------------------------
def test_business_health_score_calculation(summary_service: ExecutiveSummaryService, rich_agent_results: dict):
    # Healthy dataset with growth, passed validation, high quality
    healthy_summary = summary_service.generate_summary(results=rich_agent_results)
    assert 85 <= healthy_summary.business_health_score <= 100

    # Unhealthy dataset with decline, failed validation, low quality
    unhealthy_payload = {
        "eda": {
            "trend_analysis": [{"column": "revenue", "direction": "decline", "percentage_change": -35.0}],
            "segments": [{"segment_name": "Sole Distributor", "share_percentage": 75.0}],
        },
        "validation": {
            "validation_status": "FAILED",
            "errors": ["Critical percentage mismatch", "Corrupted calculation"],
        },
        "quality": {"quality_score": 60},
    }
    unhealthy_summary = summary_service.generate_summary(results=unhealthy_payload)
    assert unhealthy_summary.business_health_score < 60
    assert 0 <= unhealthy_summary.business_health_score <= 100


# ----------------------------------------------------------------------
# 7. Priority Engine Tests
# ----------------------------------------------------------------------
def test_priority_engine_classification(summary_service: ExecutiveSummaryService, rich_agent_results: dict):
    summary = summary_service.generate_summary(results=rich_agent_results)

    assert len(summary.priority_items) > 0
    priorities = [item.priority for item in summary.priority_items]

    # Verify priorities are valid levels
    assert all(p in ["critical", "high", "medium", "low"] for p in priorities)

    # Verify sorted: critical before high, high before medium
    p_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    for i in range(len(summary.priority_items) - 1):
        assert p_order[summary.priority_items[i].priority] <= p_order[summary.priority_items[i + 1].priority]


# ----------------------------------------------------------------------
# 8. Strict Output Schema Adherence
# ----------------------------------------------------------------------
def test_output_schema_adherence(summary_service: ExecutiveSummaryService, rich_agent_results: dict):
    summary = summary_service.generate_summary(results=rich_agent_results)
    dumped = summary.model_dump()

    # Exact fields required by Phase 3.8 Master Prompt
    required_keys = [
        "executive_summary",
        "key_findings",
        "opportunities",
        "risks",
        "recommended_actions",
        "business_health_score",
        "priority_items",
    ]
    for key in required_keys:
        assert key in dumped
        assert dumped[key] is not None


# ----------------------------------------------------------------------
# 9. Concrete Agent Runner Tests
# ----------------------------------------------------------------------
@pytest.mark.asyncio
async def test_executive_summary_agent_runner(rich_agent_results: dict):
    runner = ExecutiveSummaryAgentRunner()
    assert runner.name == "summary"

    context = WorkflowContext(
        query="Provide executive readout for Q3",
        intent="report_generation",
        results=rich_agent_results,
    )

    output = await runner.run(context)

    assert "executive_summary" in output
    assert "key_findings" in output
    assert "business_health_score" in output

    # Stored in context under both "summary" and "executive_summary"
    assert "summary" in context.results
    assert "executive_summary" in context.results


# ----------------------------------------------------------------------
# 10. API Endpoints Tests
# ----------------------------------------------------------------------
def test_api_generate_summary_endpoint(rich_agent_results: dict):
    client = TestClient(app)
    response = client.post(
        "/api/v1/summary/generate",
        json={
            "results": rich_agent_results,
            "query": "Synthesize leadership brief",
        },
    )
    assert response.status_code == 200
    data = response.json()

    assert "summary" in data
    summary_obj = data["summary"]
    assert "executive_summary" in summary_obj
    assert "business_health_score" in summary_obj
    assert len(summary_obj["key_findings"]) > 0


def test_api_dataset_summary_endpoint():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db_session] = override_get_db

    # Seed test dataset
    with TestingSession() as db:
        ds = Dataset(
            dataset_id="exec-summary-ds-001",
            dataset_name="Retail Analytics",
            file_name="retail.csv",
            file_type="text/csv",
            file_path="local://retail.csv",
            version=1,
        )
        db.add(ds)
        db.commit()


        meta = DatasetMetadata(
            dataset_id="exec-summary-ds-001",
            row_count=5000,
            column_count=6,
            column_names=["id", "category", "sales", "date"],
            column_types={"id": "integer", "category": "string", "sales": "float", "date": "datetime"},
            columns_metadata=[{"name": "sales", "type": "float"}],
            classifications={"category": "categorical", "sales": "numeric"},
        )
        db.add(meta)


        quality = DatasetQuality(
            dataset_id="exec-summary-ds-001",
            overall_score=88.5,
            completeness_score=98.0,
            validity_score=95.0,
            uniqueness_score=100.0,
            consistency_score=90.0,
            integrity_score=92.0,
            quality_classification="high",
        )
        db.add(quality)
        db.commit()


    client = TestClient(app)
    response = client.get("/api/v1/summary/exec-summary-ds-001")
    assert response.status_code == 200
    data = response.json()
    assert data["dataset_id"] == "exec-summary-ds-001"
    assert "summary" in data
    assert data["summary"]["business_health_score"] > 0

    # Clean up override
    app.dependency_overrides.pop(get_db_session, None)


# ----------------------------------------------------------------------
# 11. Orchestrator End-to-End Pipeline Integration
# ----------------------------------------------------------------------
@pytest.mark.asyncio
async def test_orchestrator_integration_with_summary():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    with TestingSession() as db:
        orchestrator = OrchestratorService(db=db)
        # Verify summary runner is registered
        assert orchestrator.agent_registry.has("summary")
        assert orchestrator.agent_registry.has("executive_summary")

        # Execute query that triggers workflow ending in "summary"
        response = await orchestrator.execute(
            query="Analyze overall sales trend and summarize findings",
            context={"intent": "trend_analysis"},
        )

        assert response.status in ["success", "partial_success"]
        assert "summary" in response.workflow
        assert len(response.summary) > 0
        assert "analysis" in response.results
