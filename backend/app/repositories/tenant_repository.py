"""Tenant repository providing CRUD database operations for the Tenant model."""

from __future__ import annotations

import logging
from typing import Any
import uuid

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.database.postgres import get_db_session
from backend.app.models.tenant import Tenant

logger = logging.getLogger(__name__)


class TenantRepository:
    """Repository handling database persistence and retrieval of Tenant entities."""

    def __init__(self, db: Session) -> None:
        self.db = db

    @property
    def session(self) -> Session:
        """Backward-compatible alias for the database session."""
        return self.db

    def create_tenant(self, tenant: Tenant) -> Tenant:
        """Persist a new Tenant record to the database."""
        self.db.add(tenant)
        self.db.commit()
        self.db.refresh(tenant)
        logger.info(
            "Created tenant record id=%s name=%s slug=%s status=%s",
            tenant.id,
            tenant.tenant_name,
            tenant.tenant_slug,
            tenant.tenant_status,
        )
        return tenant

    def get_tenant(self, tenant_id: uuid.UUID | str) -> Tenant | None:
        """Retrieve a single Tenant record by its unique id."""
        parsed_id = uuid.UUID(str(tenant_id)) if isinstance(tenant_id, str) else tenant_id
        stmt = select(Tenant).where(Tenant.id == parsed_id)
        tenant = self.db.scalars(stmt).first()
        if tenant:
            logger.debug("Retrieved tenant record id=%s", tenant_id)
        else:
            logger.warning("Tenant record not found id=%s", tenant_id)
        return tenant

    def get_by_slug(self, slug: str) -> Tenant | None:
        """Retrieve a Tenant record by its unique URL-friendly slug."""
        normalized_slug = slug.strip().lower()
        stmt = select(Tenant).where(Tenant.tenant_slug == normalized_slug)
        tenant = self.db.scalars(stmt).first()
        if tenant:
            logger.debug("Retrieved tenant record by slug=%s", normalized_slug)
        else:
            logger.warning("Tenant record not found by slug=%s", normalized_slug)
        return tenant

    def list_tenants(
        self,
        skip: int = 0,
        limit: int = 100,
        status: str | None = None,
    ) -> list[Tenant]:
        """List Tenant records with optional status filtering and pagination."""
        stmt = select(Tenant).order_by(Tenant.created_at.desc())
        if status:
            stmt = stmt.where(Tenant.tenant_status == status)
        stmt = stmt.offset(skip).limit(limit)

        results = list(self.db.scalars(stmt).all())
        logger.debug(
            "Listed tenants count=%d skip=%d limit=%d status=%s",
            len(results),
            skip,
            limit,
            status,
        )
        return results

    def update_tenant(
        self,
        tenant_id: uuid.UUID | str,
        **updates: Any,
    ) -> Tenant | None:
        """Update fields of an existing Tenant entity."""
        tenant = self.get_tenant(tenant_id)
        if not tenant:
            return None

        allowed_fields = {"tenant_name", "tenant_slug", "tenant_status"}
        applied_changes = {}

        for key, value in updates.items():
            if key in allowed_fields and value is not None:
                setattr(tenant, key, value)
                applied_changes[key] = value

        if applied_changes:
            self.db.commit()
            self.db.refresh(tenant)
            logger.info("Updated tenant id=%s fields=%s", tenant_id, list(applied_changes.keys()))

        return tenant

    def delete_tenant(self, tenant_id: uuid.UUID | str) -> bool:
        """Delete a Tenant record from the database."""
        tenant = self.get_tenant(tenant_id)
        if not tenant:
            return False

        self.db.delete(tenant)
        self.db.commit()
        logger.info("Deleted tenant record id=%s", tenant_id)
        return True


def get_tenant_repository(db: Session = Depends(get_db_session)) -> TenantRepository:
    """FastAPI dependency yielding a TenantRepository instance."""
    return TenantRepository(db=db)
