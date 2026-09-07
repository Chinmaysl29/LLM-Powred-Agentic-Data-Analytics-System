"""Tests for Phase 9.5: SQL Safety Validation."""

import pytest
from backend.validation.sql_safety_certifier import SQLSafetyCertifier


@pytest.fixture
def certifier():
    return SQLSafetyCertifier()


def test_block_drop_table(certifier):
    """Verify DROP TABLE / DATABASE is strictly blocked."""
    res1 = certifier.test_query_safety("DROP TABLE customers;")
    assert res1["blocked"] is True

    res2 = certifier.test_query_safety("DROP DATABASE production_db;")
    assert res2["blocked"] is True


def test_block_delete_all(certifier):
    """Verify DELETE / DELETE * is strictly blocked."""
    res1 = certifier.test_query_safety("DELETE FROM orders WHERE 1=1;")
    assert res1["blocked"] is True

    res2 = certifier.test_query_safety("DELETE * FROM audit_logs;")
    assert res2["blocked"] is True


def test_block_truncate(certifier):
    """Verify TRUNCATE TABLE is strictly blocked."""
    res = certifier.test_query_safety("TRUNCATE TABLE transactions;")
    assert res["blocked"] is True


def test_block_alter_table(certifier):
    """Verify ALTER TABLE is strictly blocked."""
    res = certifier.test_query_safety("ALTER TABLE employees DROP COLUMN salary;")
    assert res["blocked"] is True


def test_legitimate_select_allowed(certifier):
    """Verify legitimate analytical SELECT query is allowed."""
    res = certifier.test_query_safety("SELECT department, AVG(salary) FROM employees GROUP BY department")
    assert res["blocked"] is False
    assert res["is_safe"] is True


def test_full_corpus_100_percent_blocked(certifier):
    """Test Case: All destructive vectors must achieve 100% blocked safety score."""
    summary = certifier.certify_all_vectors()
    assert summary["status"] == "PASS"
    assert summary["safety_score"] == 100.0
    assert summary["blocked"] == summary["total_tested"]
    assert summary["passed"] == 0

    # Ensure all four specific requirement categories are blocked
    categories = summary["category_summary"]
    assert categories["DROP"]["blocked"] == categories["DROP"]["total"]
    assert categories["DELETE"]["blocked"] == categories["DELETE"]["total"]
    assert categories["TRUNCATE"]["blocked"] == categories["TRUNCATE"]["total"]
    assert categories["ALTER"]["blocked"] == categories["ALTER"]["total"]
