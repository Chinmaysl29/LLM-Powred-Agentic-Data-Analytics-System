"""JWT token handling utilities for the security layer.

Wraps the core security module's JWT functions for use by security-domain code.
"""

import logging
from typing import Any

from backend.app.core.config import get_settings
from backend.app.core.security import create_access_token, verify_token

logger = logging.getLogger(__name__)


def issue_token(user_id: str, email: str, role: str) -> str:
    """Issue a JWT token with standard claims for a verified user."""
    settings = get_settings()
    return create_access_token(
        data={"sub": user_id, "email": email, "role": role},
        settings=settings,
    )


def decode_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT token, returning the payload."""
    return verify_token(token, get_settings())


def extract_user_id(token: str) -> str | None:
    """Extract the user ID (sub claim) from a JWT token."""
    payload = decode_token(token)
    return payload.get("sub")
