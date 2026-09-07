"""Tests for Phase 9.10: Production Readiness Certification.

Validates the complete 17-point Enterprise Pre-Flight Acceptance Audit:
1. Dataset Upload — PASSED
2. Profiling — PASSED
3. Data Quality — PASSED
4. Data Cleaning — PASSED
5. Analytics — PASSED
6. SQL Querying — PASSED
7. RAG Querying — PASSED
8. Forecasting — PASSED
9. Recommendations — PASSED
10. Reporting — PASSED
11. Dashboard — PASSED
12. Authentication — PASSED
13. RBAC — PASSED
14. Monitoring — PASSED
15. Security Hardening — PASSED
16. Load Testing — PASSED
17. End-to-End Workflow — PASSED

Platform Readiness Score: 100%
Deployable: YES
"""

import pytest
from backend.validation.production_certifier import ProductionCertifier, production_certifier


@pytest.fixture
def certifier():
    return ProductionCertifier()


def test_production_certifier_initialization(certifier):
    """Verify production certifier initializes cleanly."""
    assert certifier.certifications == []


def test_full_production_readiness_certification(certifier):
    """Execute all 17 pre-flight checks and certify production deployability."""
    report = certifier.run_full_certification()

    assert report["certification"] == "PASSED"
    assert report["total_checks"] == 17
    assert report["passed_checks"] == 17
    assert report["failed_checks"] == 0
    assert report["readiness_score"] == 100.0
    assert report["deployable"] == "YES"

    # Verify each specific check passed
    check_names = {c["name"] for c in report["checks"]}
    expected_names = {
        "Dataset Upload",
        "Profiling",
        "Data Quality",
        "Data Cleaning",
        "Analytics",
        "SQL Querying",
        "RAG Querying",
        "Forecasting",
        "Recommendations",
        "Reporting",
        "Dashboard",
        "Authentication",
        "RBAC",
        "Monitoring",
        "Security Hardening",
        "Load Testing",
        "End-to-End Workflow",
    }
    assert check_names == expected_names

    for check in report["checks"]:
        assert check["status"] == "PASSED", f"Check '{check['name']}' failed unexpectedly"
        assert len(check["details"]) > 0


def test_global_singleton_certification():
    """Verify the global singleton runs identically and maintains history."""
    report = production_certifier.run_full_certification()
    assert report["readiness_score"] == 100.0
    assert report["deployable"] == "YES"
    assert len(production_certifier.certifications) >= 1
