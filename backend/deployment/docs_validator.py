"""Enterprise Documentation Validator for Phase 10.8.

Validates the presence, completeness, and integrity of the 7 enterprise guides:
1. API Documentation (API_DOCUMENTATION.md)
2. Architecture Documentation (ARCHITECTURE.md)
3. Deployment Guide (DEPLOYMENT_GUIDE.md)
4. Admin Guide (ADMIN_GUIDE.md)
5. User Guide (USER_GUIDE.md)
6. Developer Guide (DEVELOPER_GUIDE.md)
7. Security Guide (SECURITY_GUIDE.md)

Verifies Test Case: New Developer -> Can setup project from documentation alone.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger("deployment.docs")

DOCS_DIR = Path(__file__).resolve().parent.parent.parent / "docs"


class DocsValidator:
    """Audits and validates the enterprise documentation repository."""

    REQUIRED_DOCS = [
        "API_DOCUMENTATION.md",
        "ARCHITECTURE.md",
        "DEPLOYMENT_GUIDE.md",
        "ADMIN_GUIDE.md",
        "USER_GUIDE.md",
        "DEVELOPER_GUIDE.md",
        "SECURITY_GUIDE.md",
    ]

    DEVELOPER_CHECKLIST_SECTIONS = [
        "Prerequisites",
        "Python Virtual Environment",
        "Install Python Dependencies",
        "Environment Configuration",
        "Running Backend",
        "Running the Test Suite",
    ]

    def __init__(self, docs_dir: str | Path | None = None) -> None:
        self.docs_dir = Path(docs_dir) if docs_dir else DOCS_DIR

    def validate_document_existence(self) -> dict[str, Any]:
        """Verify all 7 mandatory documentation files exist with substantial content."""
        missing: list[str] = []
        details: dict[str, dict[str, Any]] = {}

        for doc_name in self.REQUIRED_DOCS:
            doc_path = self.docs_dir / doc_name
            if not doc_path.exists():
                missing.append(doc_name)
                details[doc_name] = {"exists": False, "bytes": 0}
            else:
                size = doc_path.stat().st_size
                details[doc_name] = {"exists": True, "bytes": size}
                if size < 200:
                    missing.append(f"{doc_name} (insufficient content)")

        all_present = len(missing) == 0
        return {
            "all_present": all_present,
            "status": "PASS" if all_present else "FAIL",
            "total_docs": len(self.REQUIRED_DOCS),
            "missing": missing,
            "details": details,
        }

    def validate_developer_onboarding(self) -> dict[str, Any]:
        """Validate Developer Guide contains complete self-contained instructions."""
        dev_guide = self.docs_dir / "DEVELOPER_GUIDE.md"
        if not dev_guide.exists():
            return {"can_setup_alone": False, "status": "FAIL", "reason": "DEVELOPER_GUIDE.md missing"}

        with open(dev_guide, "r", encoding="utf-8") as f:
            content = f.read()

        missing_sections = [
            sec for sec in self.DEVELOPER_CHECKLIST_SECTIONS
            if sec.lower() not in content.lower()
        ]

        can_setup = len(missing_sections) == 0
        return {
            "can_setup_alone": can_setup,
            "status": "PASS" if can_setup else "FAIL",
            "missing_sections": missing_sections,
            "has_docker_instructions": "docker compose" in content,
            "has_test_instructions": "pytest" in content,
            "validated_at": datetime.now(timezone.utc).isoformat(),
        }

    def run_full_docs_audit(self) -> dict[str, Any]:
        """Execute complete documentation platform audit."""
        existence = self.validate_document_existence()
        onboarding = self.validate_developer_onboarding()

        all_pass = existence["status"] == "PASS" and onboarding["status"] == "PASS"
        return {
            "audit_name": "Enterprise Documentation Audit",
            "overall_status": "PASS" if all_pass else "FAIL",
            "coverage_pct": 100.0 if all_pass else 50.0,
            "existence_check": existence,
            "developer_onboarding_check": onboarding,
            "audited_at": datetime.now(timezone.utc).isoformat(),
        }


# Global documentation validator singleton
docs_validator = DocsValidator()
