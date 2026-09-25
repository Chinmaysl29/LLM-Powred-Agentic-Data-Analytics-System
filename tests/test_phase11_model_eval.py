"""Unit tests for Phase 11.3: Model Evaluation Framework."""

import pytest
from backend.operations.model_evaluation import (
    EvaluatedAgent,
    ModelEvaluationFramework,
)


@pytest.fixture
def eval_framework():
    return ModelEvaluationFramework()


def test_100_sql_questions_evaluation(eval_framework):
    """Test Case: 100 SQL Questions -> Expected: Accuracy Calculated & Latency Reported."""
    # Build 100 benchmark test cases (92 correct, 8 incorrect)
    test_cases = []
    for i in range(100):
        expected_sql = f"SELECT region, SUM(sales) FROM sales_table WHERE year = {2020 + (i % 4)} GROUP BY region;"
        if i < 92:
            actual_sql = expected_sql
            latency = 150.0 + (i * 1.2)
            error = None
        else:
            actual_sql = "SELECT region FROM invalid_table;"
            latency = 300.0
            error = "Table not found" if i >= 96 else None

        test_cases.append({
            "query": f"What are the regional sales for {2020 + (i % 4)}?",
            "expected": expected_sql,
            "actual": actual_sql,
            "latency_ms": latency,
            "error": error,
        })

    report = eval_framework.evaluate_batch(
        model=EvaluatedAgent.SQL_AGENT,
        test_cases=test_cases,
    )

    assert report["model"] == "sql_agent"
    assert report["total_evaluations"] == 100
    assert report["accuracy"] == 0.92
    assert report["success_rate"] == 0.96
    assert report["failure_rate"] == 0.04
    assert report["avg_latency_ms"] > 100.0
    assert report["p50_latency_ms"] > 0.0
    assert report["p95_latency_ms"] >= report["p50_latency_ms"]


def test_predict_fn_execution(eval_framework):
    """Verify evaluation framework executes prediction functions with latency measurement."""
    def mock_predict(query: str) -> str:
        if "fail" in query:
            raise RuntimeError("Inference failed")
        return "Insight: Sales grew 10%"

    test_cases = [
        {"query": "Analyze Q1", "expected": "Insight: Sales grew 10%"},
        {"query": "Analyze Q2", "expected": "Insight: Sales grew 10%"},
        {"query": "fail this", "expected": "Insight: Sales grew 10%"},
    ]

    report = eval_framework.evaluate_batch(
        model=EvaluatedAgent.RECOMMENDATION_AGENT,
        test_cases=test_cases,
        predict_fn=mock_predict,
    )

    assert report["total_evaluations"] == 3
    assert report["accuracy"] == round(2 / 3, 4)
    assert report["failure_rate"] == round(1 / 3, 4)
    assert report["avg_latency_ms"] >= 0.0


def test_empty_test_cases(eval_framework):
    """Verify empty case list produces a zeroed report without exception."""
    report = eval_framework.evaluate_batch(
        model=EvaluatedAgent.RAG_AGENT,
        test_cases=[],
    )
    assert report["total_evaluations"] == 0
    assert report["accuracy"] == 0.0
