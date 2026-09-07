"""Tests for Phase 9.4: AI Agent Validation Suite."""

import pytest
from backend.validation.agent_benchmark_suite import (
    BENCHMARK_100_QUESTIONS,
    AgentBenchmarkSuite,
)


@pytest.fixture
def suite():
    return AgentBenchmarkSuite()


def test_100_questions_benchmark_accuracy(suite):
    """Test Case: 100 Sample Questions -> Expected: >90% Correct Routing."""
    results = suite.evaluate_100_questions()

    assert results["total_questions"] == 100
    assert results["accuracy_pct"] >= 90.0, f"Accuracy was {results['accuracy_pct']}%, expected >= 90%"
    assert results["status"] == "PASS"

    # Verify each agent's individual accuracy is at least 85%
    for agent_name, stats in results["agent_breakdowns"].items():
        assert stats["total"] == 20
        assert stats["accuracy"] >= 85.0, f"{agent_name} accuracy below threshold: {stats}"


def test_hallucination_and_consistency_thresholds(suite):
    """Verify hallucination rate < 10% and consistency > 95%."""
    results = suite.evaluate_100_questions()

    assert results["hallucination_rate_pct"] <= 10.0
    assert results["consistency_pct"] >= 95.0
    assert results["response_quality_score"] >= 90.0


def test_all_100_questions_properly_structured():
    """Verify that benchmark questions set has 100 distinct non-empty questions."""
    assert len(BENCHMARK_100_QUESTIONS) == 100
    queries = [q["q"] for q in BENCHMARK_100_QUESTIONS]
    assert len(set(queries)) == 100
    for item in BENCHMARK_100_QUESTIONS:
        assert len(item["q"]) > 10
        assert item["expected"] in {
            "eda_agent",
            "sql_agent",
            "forecast_agent",
            "recommendation_agent",
            "executive_summary_agent",
        }
