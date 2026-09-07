"""Tests for Phase 5.10 — Knowledge Validation."""

import pytest
from backend.app.schemas.context_builder import ContextSource
from backend.rag.knowledge_validation import KnowledgeValidator


def _make_source(source_id, chunk_id, doc_id, preview, score=0.9):
    return ContextSource(
        source_id=source_id,
        chunk_id=chunk_id,
        document_id=doc_id,
        filename="q3_report.pdf",
        file_type="pdf",
        score=score,
        preview=preview,
    )


CONTEXT_TEXT = """
[Source 1]
Total revenue for Q3 2026 reached $4.2M, representing a 14% increase year-over-year.
The North region contributed $1.8M which is 42% of total revenue.
Operating costs were $2.8M with EBITDA margin of 33%.

[Source 2]
Customer churn decreased by 8% after implementing machine learning retention models.
"""

GOOD_ANSWER = (
    "Revenue for Q3 2026 was $4.2M representing a 14% increase year-over-year. "
    "North region contributed $1.8M. Customer churn decreased by 8%."
)

HALLUCINATED_ANSWER = (
    "Revenue reached $99M representing 200% growth. The West region contributed "
    "72% of total revenue with an EBITDA margin of 95%."
)


def test_validator_grounded_answer():
    validator = KnowledgeValidator(min_faithfulness=0.4)
    sources = [
        _make_source("[Source 1]", "c1", "d1", "Total revenue for Q3 2026 reached $4.2M"),
    ]
    result = validator.validate(GOOD_ANSWER, CONTEXT_TEXT, sources)
    assert result.faithfulness_score >= 0.4
    assert result.answer_has_sources is True


def test_validator_hallucinated_answer():
    validator = KnowledgeValidator(min_faithfulness=0.5)
    sources = [
        _make_source("[Source 1]", "c1", "d1", "Total revenue for Q3 2026 reached $4.2M"),
    ]
    result = validator.validate(HALLUCINATED_ANSWER, CONTEXT_TEXT, sources)
    # Numbers $99M and 200% don't appear in context — should detect hallucination
    assert result.hallucinations_detected is True or result.faithfulness_score < 1.0


def test_validator_empty_answer():
    validator = KnowledgeValidator()
    result = validator.validate("", CONTEXT_TEXT, [])
    assert result.is_valid is False
    assert result.hallucinations_detected is True
    assert len(result.warnings) > 0


def test_validator_no_context():
    validator = KnowledgeValidator()
    result = validator.validate(GOOD_ANSWER, "", [])
    assert result.is_valid is False
    assert result.faithfulness_score == 0.0


def test_validator_no_sources():
    validator = KnowledgeValidator(min_faithfulness=0.3)
    result = validator.validate(GOOD_ANSWER, CONTEXT_TEXT, [])
    assert result.answer_has_sources is False
    assert not result.is_valid  # Missing sources means not fully valid


def test_validator_checks_structure():
    validator = KnowledgeValidator(min_faithfulness=0.3)
    sources = [_make_source("[Source 1]", "c1", "d1", "Revenue $4.2M Q3 2026")]
    result = validator.validate(GOOD_ANSWER, CONTEXT_TEXT, sources)
    assert len(result.checks) > 0
    for check in result.checks:
        assert 0.0 <= check.confidence <= 1.0
        assert isinstance(check.is_grounded, bool)
        assert len(check.claim) > 0
