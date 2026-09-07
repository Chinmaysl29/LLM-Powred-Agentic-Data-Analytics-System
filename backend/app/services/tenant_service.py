"""Tenant business service layer managing organization lifecycle and validation."""

from __future__ import annotations

import logging
import re
from typing import Any
import uuid

from backend.app.models.tenant import Tenant
from backend.app.repositories.tenant_repository import TenantRepository

logger = logging.getLogger(__name__)


# ----------------------------------------------------------------------
# Domain Exceptions
# ----------------------------------------------------------------------

class TenantException(Exception):
    """Base exception for tenant domain errors."""
    pass


class TenantNotFoundException(TenantException):
    """Raised when a requested tenant does not exist."""
    pass


class DuplicateTenantException(TenantException):
    """Raised when a tenant slug or unique attribute already exists."""
    pass


class TenantSuspendedException(TenantException):
    """Raised when access is attempted on a suspended tenant."""
    pass


class TenantValidationException(TenantException):
    """Raised when input parameters fail tenant validation rules."""
    pass


# ----------------------------------------------------------------------
# Tenant Business Service
# ----------------------------------------------------------------------

class TenantService:
    """Service encapsulating tenant lifecycle, slug generation, and validation."""

    def __init__(self, repository: TenantRepository) -> None:
        self.repository = repository

    @staticmethod
    def generate_slug(name: str) -> str:
        """Derive a clean, URL-friendly slug from an organization name."""
        if not name or not name.strip():
            raise TenantValidationException("Cannot generate slug from empty organization name")
        # Lowercase and replace non-alphanumeric characters with hyphens
        slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
        if not slug:
            slug = f"tenant-{uuid.uuid4().hex[:8]}"
        return slug

    def validate_tenant_data(self, name: str, slug: str | None = None) -> str:
        """Validate organization name and slug parameters."""
        clean_name = name.strip()
        if len(clean_name) < 2:
            raise TenantValidationException("Tenant name must be at least 2 characters long")
        if len(clean_name) > 255:
            raise TenantValidationException("Tenant name cannot exceed 255 characters")

        final_slug = (slug or self.generate_slug(clean_name)).strip().lower()
        if not re.match(r"^[a-z0-9]+(-[a-z0-9]+)*$", final_slug):
            raise TenantValidationException(
                f"Invalid tenant slug format '{final_slug}': must be lowercase alphanumeric with single hyphens"
            )
        if len(final_slug) > 100:
            raise TenantValidationException("Tenant slug cannot exceed 100 characters")

        return final_slug

    def create_tenant(
        self,
        tenant_name: str,
        tenant_slug: str | None = None,
        tenant_status: str = "active",
    ) -> Tenant:
        """Provision a new tenant organization with duplicate checks."""
        resolved_slug = self.validate_tenant_data(tenant_name, tenant_slug)

        # Duplicate slug check
        existing = self.repository.get_by_slug(resolved_slug)
        if existing:
            logger.warning("Duplicate tenant slug rejected: %s", resolved_slug)
            raise DuplicateTenantException(f"Tenant with slug '{resolved_slug}' already exists")

        tenant = Tenant(
            tenant_name=tenant_name.strip(),
            tenant_slug=resolved_slug,
            tenant_status=tenant_status,
        )
        created = self.repository.create_tenant(tenant)
        logger.info("Successfully provisioned tenant id=%s slug=%s", created.id, created.tenant_slug)
        return created

    def get_tenant(self, tenant_id: uuid.UUID | str) -> Tenant:
        """Retrieve tenant or raise TenantNotFoundException."""
        tenant = self.repository.get_tenant(tenant_id)
        if not tenant:
            raise TenantNotFoundException(f"Tenant with id '{tenant_id}' not found")
        return tenant

    def get_by_slug(self, slug: str) -> Tenant:
        """Retrieve tenant by slug or raise TenantNotFoundException."""
        tenant = self.repository.get_by_slug(slug)
        if not tenant:
            raise TenantNotFoundException(f"Tenant with slug '{slug}' not found")
        return tenant

    def list_tenants(
        self,
        skip: int = 0,
        limit: int = 100,
        status: str | None = None,
    ) -> list[Tenant]:
        """List tenants with pagination and optional status filter."""
        return self.repository.list_tenants(skip=skip, limit=limit, status=status)

    def activate_tenant(self, tenant_id: uuid.UUID | str) -> Tenant:
        """Transition tenant status to active."""
        tenant = self.get_tenant(tenant_id)
        updated = self.repository.update_tenant(tenant.id, tenant_status="active")
        if not updated:
            raise TenantNotFoundException(f"Tenant '{tenant_id}' not found")
        logger.info("Activated tenant id=%s slug=%s", updated.id, updated.tenant_slug)
        return updated

    def suspend_tenant(self, tenant_id: uuid.UUID | str, reason: str = "") -> Tenant:
        """Suspend an organization's access to the platform."""
        tenant = self.get_tenant(tenant_id)
        updated = self.repository.update_tenant(tenant.id, tenant_status="suspended")
        if not updated:
            raise TenantNotFoundException(f"Tenant '{tenant_id}' not found")
        logger.warning("Suspended tenant id=%s slug=%s reason=%s", updated.id, updated.tenant_slug, reason)
        return updated

    def archive_tenant(self, tenant_id: uuid.UUID | str) -> Tenant:
        """Archive an organization upon offboarding."""
        tenant = self.get_tenant(tenant_id)
        updated = self.repository.update_tenant(tenant.id, tenant_status="archived")
        if not updated:
            raise TenantNotFoundException(f"Tenant '{tenant_id}' not found")
        logger.info("Archived tenant id=%s slug=%s", updated.id, updated.tenant_slug)
        return updated
