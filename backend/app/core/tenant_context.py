"""Tenant context manager providing ContextVar-based tenant execution scoping."""

from __future__ import annotations

from contextlib import asynccontextmanager, contextmanager
import contextvars
import logging
from typing import AsyncIterator, Iterator

logger = logging.getLogger(__name__)

# Execution context variable tracking active tenant ID across async and sync calls
_TENANT_CONTEXT_VAR: contextvars.ContextVar[str] = contextvars.ContextVar(
    "tenant_context_var",
    default="system",
)


def get_current_tenant() -> str:
    """Retrieve the active tenant ID for the current execution context."""
    return _TENANT_CONTEXT_VAR.get()


def set_current_tenant(tenant_id: str) -> contextvars.Token:
    """Explicitly set the active tenant ID, returning the restore token."""
    logger.debug("Setting active tenant context to: %s", tenant_id)
    return _TENANT_CONTEXT_VAR.set(str(tenant_id))


def clear_current_tenant(token: contextvars.Token) -> None:
    """Reset the tenant context back to its previous state using token."""
    logger.debug("Clearing active tenant context")
    _TENANT_CONTEXT_VAR.reset(token)


@contextmanager
def tenant_scope(tenant_id: str) -> Iterator[str]:
    """Synchronous context manager scoping code execution to a specific tenant ID."""
    token = set_current_tenant(tenant_id)
    try:
        yield tenant_id
    finally:
        clear_current_tenant(token)


@asynccontextmanager
async def async_tenant_scope(tenant_id: str) -> AsyncIterator[str]:
    """Asynchronous context manager scoping code execution to a specific tenant ID."""
    token = set_current_tenant(tenant_id)
    try:
        yield tenant_id
    finally:
        clear_current_tenant(token)
