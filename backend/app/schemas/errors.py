"""Standardized API error payloads."""

from typing import Any

from pydantic import BaseModel


class ErrorResponse(BaseModel):
    """Public error response returned by global exception handlers."""

    success: bool = False
    message: str
    error_code: str
    request_id: str | None = None
    details: Any | None = None
