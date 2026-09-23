"""Executive Summary Agent Service module facade.

Provides dependency injection providers and aliases for ExecutiveSummaryService.
"""

from backend.app.services.executive_summary_service import ExecutiveSummaryService


def get_executive_summary_service() -> ExecutiveSummaryService:
    """Dependency injection provider for ExecutiveSummaryService."""
    return ExecutiveSummaryService()
