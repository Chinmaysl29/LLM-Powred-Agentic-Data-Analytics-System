"""Tests for Phase 10.10: Go-Live Certification Framework.

Validates the final 20-point Production Acceptance Test Suite:
1. Docker & Topology — PASSED
2. PostgreSQL Reachability — PASSED
3. Redis Reachability — PASSED
4. ChromaDB Reachability — PASSED
5. Dataset Upload — PASSED
6. Metadata Extraction — PASSED
7. Data Profiling & Quality — PASSED
8. Data Cleaning — PASSED
9. Analytics & Statistics — PASSED
10. SQL Querying & Guardrails — PASSED
11. RAG Querying — PASSED
12. Forecasting Engine — PASSED
13. Recommendations Engine — PASSED
14. Reporting Engine — PASSED
15. Dashboard Engine — PASSED
16. Authentication System — PASSED
17. RBAC System — PASSED
18. Monitoring & Observability — PASSED
19. Security Hardening & Injections — PASSED
20. End-to-End Workflow & Load — PASSED

Expected Go-Live Decision Contract:
{
  "deployment_ready": true,
  "readiness_score": 100,
  "launch_recommendation": "GO_LIVE"
}
"""

import pytest
from backend.deployment.golive_certifier import GoLiveCertifier, golive_certifier


@pytest.fixture
def certifier():
    return GoLiveCertifier()


def test_golive_certifier_initialization(certifier):
    """Verify GoLiveCertifier instantiates cleanly."""
    assert certifier.certification_history == []
    assert len(certifier.TIERS) == 5


def test_full_golive_certification_verdict(certifier):
    """Execute complete 20-point enterprise audit and verify GO_LIVE contract."""
    report = certifier.run_full_golive_certification()

    # Exact Phase 10.10 contract assertion
    assert report["deployment_ready"] is True
    assert report["readiness_score"] == 100
    assert report["launch_recommendation"] == "GO_LIVE"

    assert report["subsystems_validated"] == 20
    assert report["passed_checks"] == 20
    assert report["failed_checks"] == 0

    # Verify all 5 tiers have zero failures
    for tier_name, counts in report["tier_summary"].items():
        assert counts["failed"] == 0, f"Tier '{tier_name}' experienced failures"
        assert counts["passed"] > 0, f"Tier '{tier_name}' has no passed checks"

    # Verify all individual check items passed
    for check in report["acceptance_suite"]:
        assert check["status"] == "PASSED", f"Check '{check['item']}' failed: {check.get('error')}"
        assert len(check["details"]) > 0


def test_global_singleton_golive_certification():
    """Verify the global singleton runs identically and maintains history."""
    report = golive_certifier.run_full_golive_certification()
    assert report["deployment_ready"] is True
    assert report["readiness_score"] == 100
    assert report["launch_recommendation"] == "GO_LIVE"
    assert len(golive_certifier.certification_history) >= 1
