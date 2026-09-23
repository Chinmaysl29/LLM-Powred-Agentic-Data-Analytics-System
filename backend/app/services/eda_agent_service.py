"""Alias for EDAService to maintain naming consistency."""

from backend.app.services.eda_service import (
    EDAService,
    get_eda_service,
)

__all__ = ["EDAService", "get_eda_service"]
