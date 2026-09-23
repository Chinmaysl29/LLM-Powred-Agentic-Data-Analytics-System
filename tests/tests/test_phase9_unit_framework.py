"""Tests for Phase 9.1: Unit Testing Framework."""

import pandas as pd
import pytest
from backend.validation.unit_test_runner import UnitTestRunner


@pytest.fixture
def runner():
    return UnitTestRunner(min_coverage_target=80.0)


def test_analytics_layer_profiling(runner):
    """Test Case: Input Dataset -> Expected: Correct Profiling."""
    df = pd.DataFrame({
        "order_id": [1, 2, 3, 4, 5],
        "customer_id": [101, 102, 101, 103, 104],
        "amount": [50.0, 75.5, 120.0, 30.0, 90.0],
    })
    result = runner.verify_analytics_layer(df)
    assert result["status"] == "PASS"
    assert result["row_count"] == 5
    assert result["column_count"] == 3


def test_sql_layer_generation_and_safety(runner):
    """Test Case: Question: Show Revenue -> Expected: Valid SQL."""
    result = runner.verify_sql_layer("Show Revenue")
    assert result["status"] == "PASS"
    assert "SELECT" in result["sql"]
    assert "revenue" in result["sql"].lower()
    assert result["is_safe"] is True


def test_rag_layer_context_retrieval(runner):
    """Test Case: Question: Summarize Report -> Expected: Correct Context Retrieved."""
    doc_text = "Executive Summary: Enterprise Q3 revenue reached $14.2M, representing 18.5% YoY growth."
    result = runner.verify_rag_layer("Summarize Report", sample_text=doc_text)
    assert result["status"] == "PASS"
    assert result["context_retrieved"] is True
    assert result["answer_length"] > 0


def test_all_nine_layers_pass(runner):
    """Verify all 9 platform layers pass their unit validation checks."""
    summary = runner.run_all_layer_tests()
    assert summary["overall_status"] == "PASS"
    assert summary["layers_tested"] == 9
    for layer_name, layer_res in summary["results"].items():
        assert layer_res["status"] == "PASS", f"Layer {layer_name} failed: {layer_res}"


def test_coverage_report_meets_target(runner):
    """Verify coverage report generation meets or exceeds 80% target."""
    cov_rep = runner.generate_coverage_report()
    assert cov_rep["status"] == "PASS"
    assert cov_rep["overall_coverage_pct"] >= 80.0
    assert len(cov_rep["layers"]) == 9
    for layer, stats in cov_rep["layers"].items():
        assert stats["coverage_pct"] >= 80.0
        assert stats["status"] == "PASS"
