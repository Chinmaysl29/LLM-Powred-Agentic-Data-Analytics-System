"""Unit & Integration Tests for Phase 10.8: Documentation Platform.

Validates:
- Presence of all 7 enterprise guides (API, Architecture, Deployment, Admin, User, Developer, Security)
- Test Case: New Developer -> Expected: Can setup project from documentation alone
- Non-empty content and key instruction blocks
"""

import pytest
from backend.deployment.docs_validator import DocsValidator, docs_validator


@pytest.fixture
def validator():
    return DocsValidator()


def test_all_seven_documents_exist(validator):
    """Verify all 7 required enterprise documentation files are present."""
    res = validator.validate_document_existence()
    assert res["status"] == "PASS"
    assert res["all_present"] is True
    assert len(res["missing"]) == 0
    assert res["total_docs"] == 7


def test_developer_guide_can_setup_alone(validator):
    """Test Case: New Developer -> Expected: Can setup project from documentation alone."""
    res = validator.validate_developer_onboarding()
    assert res["status"] == "PASS"
    assert res["can_setup_alone"] is True
    assert len(res["missing_sections"]) == 0
    assert res["has_docker_instructions"] is True
    assert res["has_test_instructions"] is True


def test_full_documentation_audit(validator):
    """Verify comprehensive documentation audit achieves 100% coverage."""
    audit = validator.run_full_docs_audit()
    assert audit["overall_status"] == "PASS"
    assert audit["coverage_pct"] == 100.0
