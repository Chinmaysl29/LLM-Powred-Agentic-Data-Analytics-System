"""Tenant resolution layer validating tenant identity, existence, and active status."""

from __future__ import annotations

import logging
from typing import Any
import uuid

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from backend.app.core.security import bearer_scheme, verify_token
from backend.app.core.tenant_context import set_current_tenant
from backend.app.database.postgres import get_db_session
from backend.app.models.tenant import Tenant
from backend.app.repositories.tenant_repository import TenantRepository, get_tenant_repository
from backend.app.services.tenant_service import TenantNotFoundException, TenantSuspendedException

logger = logging.getLogger(__name__)


class TenantResolver:
    """Service resolving and verifying tenant status from tokens and request state."""

    def __init__(self, repository: TenantRepository) -> None:
        self.repository = repository

    def resolve_from_identifier(self, identifier: str) -> Tenant:
        """Resolve tenant by UUID string or slug."""
        tenant: Tenant | None = None
        # Try resolving by UUID if valid UUID syntax
        try:
            parsed_uuid = uuid.UUID(identifier)
            tenant = self.repository.get_tenant(parsed_uuid)
        except ValueError:
            pass

        # Try slug resolution
        if not tenant:
            tenant = self.repository.get_by_slug(identifier)

        if not tenant:
            logger.warning("Failed to resolve tenant identifier: %s", identifier)
            raise TenantNotFoundException(f"Tenant '{identifier}' does not exist")

        # Validate lifecycle status
        if tenant.tenant_status == "suspended":
            logger.warning("Access denied: Tenant '%s' is suspended", tenant.tenant_slug)
            raise TenantSuspendedException(
                f"Organization '{tenant.tenant_name}' is currently suspended"
            )
        elif tenant.tenant_status == "archived":
            logger.warning("Access denied: Tenant '%s' is archived", tenant.tenant_slug)
            raise TenantSuspendedException(
                f"Organization '{tenant.tenant_name}' has been archived"
            )

        logger.debug("Successfully resolved active tenant id=%s slug=%s", tenant.id, tenant.tenant_slug)
        return tenant


def get_tenant_resolver(
    repo: TenantRepository = Depends(get_tenant_repository),
) -> TenantResolver:
    """FastAPI dependency providing a configured TenantResolver."""
    return TenantResolver(repository=repo)


async def get_active_tenant(
    request: Request,
    resolver: TenantResolver = Depends(get_tenant_resolver),
) -> Tenant:
    """FastAPI dependency resolving and enforcing the active tenant for a request.

    Extracts tenant from request.state, header, or JWT payload, verifies it exists
    in the database, rejects suspended tenants with 403, and updates ContextVar.
    """
    tenant_id_str = getattr(request.state, "tenant_id", None)
    if not tenant_id_str:
        tenant_id_str = request.headers.get("X-Tenant-ID", "system")

    # If it is the default system tenant and not yet in DB, allow or resolve
    try:
        tenant = resolver.resolve_from_identifier(tenant_id_str)
        # Bind into ContextVar
        set_current_tenant(str(tenant.id))
        return tenant
    except TenantSuspendedException as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    except TenantNotFoundException as exc:
        if tenant_id_str == "system":
            # For system fallback in dev/test, create ephemeral system representation
            system_tenant = Tenant(
                tenant_name="System Default",
                tenant_slug="system",
                tenant_status="active",
            )
            set_current_tenant("system")
            return system_tenant
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
