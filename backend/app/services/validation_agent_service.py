"""Alias for ValidationService to maintain naming consistency."""

from backend.app.services.validation_service import (
    ValidationService,
    get_validation_service,
)

__all__ = ["ValidationService", "get_validation_service"]
