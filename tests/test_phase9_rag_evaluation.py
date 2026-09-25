"""Tests for Phase 9.6: RAG Evaluation Framework."""

import pytest
from backend.validation.rag_evaluator import RAGEvaluator


@pytest.fixture
def evaluator():
    return RAGEvaluator()


def test_rag_evaluation_from_uploaded_document(evaluator):
    """Test Case: Question from Uploaded Document -> Expected: Correct Context Retrieved."""
    doc_text = """
    Enterprise Annual Financial Report 2026.
    Section 1: Regional Revenue Breakdown.
    North America recorded $18.4 million in annual revenue with 24% YoY growth.
    Europe and Middle East region contributed $12.1 million with EBITDA margin of 32%.
    Section 2: Cost Reduction Initiatives.
    Cloud infrastructure migration achieved $240,000 monthly operational savings.
    Customer support automation reduced resolution times by 45%.
    """

    queries = [
        {
            "query": "What was the revenue and growth rate in North America?",
            "expected_keywords": ["18.4", "million", "North America", "24%"],
        },
        {
            "query": "How much monthly savings did cloud migration achieve?",
            "expected_keywords": ["240,000", "monthly", "cloud"],
        },
    ]

    report = evaluator.evaluate_retrieval(
        document_text=doc_text,
        document_id="doc_annual_report_2026",
        test_queries=queries,
    )

    assert report["status"] == "PASS"
    assert report["context_recall"] >= 0.85
    assert report["precision"] >= 0.80
    assert report["answer_quality"] >= 0.85
    assert report["source_relevance"] >= 0.85
    assert report["rag_score"] >= 80.0
    assert len(report["evaluated_queries"]) == 2
