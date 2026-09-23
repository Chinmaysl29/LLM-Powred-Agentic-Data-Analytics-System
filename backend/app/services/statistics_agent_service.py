"""Alias for StatisticsService to maintain naming consistency."""

from backend.app.services.statistics_service import (
    StatisticsService,
    get_statistics_service,
)

__all__ = ["StatisticsService", "get_statistics_service"]
