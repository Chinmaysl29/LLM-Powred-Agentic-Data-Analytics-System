"""Phase 12.4.1 — Connector Registry.

Provides registration, lookup, catalog management, and lifecycle controls
for enterprise connectors across Databases, Cloud Storage, CRMs, ERPs, and Warehouses.
"""

from __future__ import annotations

from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models.connector import (
    ConnectorRecord,
    ConnectorStatus,
    ConnectorType,
)

logger = logging.getLogger(__name__)

SUPPORTED_TYPES = {t.value for t in ConnectorType}


class ConnectorRegistry:
    """Registry managing connector instances with repository pattern."""

    def __init__(self, db: Optional[Session] = None) -> None:
        self.db = db
        # In-memory store fallback for isolated unit testing
        self._memory_store: Dict[uuid.UUID, ConnectorRecord] = {}

    def register_connector(
        self,
        tenant_id: uuid.UUID | str,
        connector_name: str,
        connector_type: ConnectorType | str,
        connector_subtype: str,
        config: Optional[Dict[str, Any]] = None,
        version: str = "1.0.0",
    ) -> ConnectorRecord:
        """Register a new enterprise connector."""
        clean_name = connector_name.strip()
        if not clean_name:
            raise ValueError("connector_name cannot be empty.")

        ctype_str = connector_type.value if isinstance(connector_type, ConnectorType) else str(connector_type).upper()
        if ctype_str not in SUPPORTED_TYPES:
            raise ValueError(f"Invalid connector_type '{connector_type}'. Allowed: {sorted(SUPPORTED_TYPES)}")

        tid = uuid.UUID(str(tenant_id)) if isinstance(tenant_id, str) else tenant_id
        ctype = ConnectorType(ctype_str)

        record = ConnectorRecord(
            tenant_id=tid,
            connector_name=clean_name,
            connector_type=ctype,
            connector_subtype=connector_subtype.lower().strip(),
            config=config or {},
            status=ConnectorStatus.ACTIVE,
            version=version,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        if self.db is not None:
            self.db.add(record)
            self.db.commit()
            self.db.refresh(record)
        else:
            self._memory_store[record.id] = record

        logger.info(
            "Registered connector '%s' [%s:%s] (id=%s, tenant=%s)",
            clean_name,
            ctype.value,
            connector_subtype,
            record.id,
            tid,
        )
        return record

    def get_connector(self, connector_id: uuid.UUID | str) -> Optional[ConnectorRecord]:
        """Retrieve a connector by UUID."""
        cid = uuid.UUID(str(connector_id)) if isinstance(connector_id, str) else connector_id
        if self.db is not None:
            return self.db.get(ConnectorRecord, cid)
        return self._memory_store.get(cid)

    def update_connector(
        self,
        connector_id: uuid.UUID | str,
        connector_name: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
        version: Optional[str] = None,
        status: Optional[ConnectorStatus | str] = None,
    ) -> ConnectorRecord:
        """Update connector details."""
        record = self.get_connector(connector_id)
        if not record:
            raise KeyError(f"Connector with id '{connector_id}' not found.")

        if connector_name:
            clean = connector_name.strip()
            if not clean:
                raise ValueError("connector_name cannot be empty.")
            record.connector_name = clean

        if config is not None:
            record.config = config

        if version:
            record.version = version

        if status:
            cstat = ConnectorStatus(status) if isinstance(status, str) else status
            record.status = cstat

        record.updated_at = datetime.now(timezone.utc)

        if self.db is not None:
            self.db.add(record)
            self.db.commit()
            self.db.refresh(record)
        else:
            self._memory_store[record.id] = record

        logger.info("Updated connector id=%s (status=%s)", record.id, record.status.value)
        return record

    def disable_connector(self, connector_id: uuid.UUID | str) -> ConnectorRecord:
        """Mark a connector as INACTIVE."""
        return self.update_connector(connector_id, status=ConnectorStatus.INACTIVE)

    def enable_connector(self, connector_id: uuid.UUID | str) -> ConnectorRecord:
        """Mark a connector as ACTIVE."""
        return self.update_connector(connector_id, status=ConnectorStatus.ACTIVE)

    def list_connectors(
        self,
        tenant_id: uuid.UUID | str,
        connector_type: Optional[ConnectorType | str] = None,
        status: Optional[ConnectorStatus | str] = None,
    ) -> List[ConnectorRecord]:
        """List connectors for a tenant with optional type and status filtering."""
        tid = uuid.UUID(str(tenant_id)) if isinstance(tenant_id, str) else tenant_id
        ctype = (
            ConnectorType(connector_type)
            if isinstance(connector_type, str)
            else connector_type
        )
        cstat = (
            ConnectorStatus(status)
            if isinstance(status, str)
            else status
        )

        if self.db is not None:
            query = select(ConnectorRecord).where(ConnectorRecord.tenant_id == tid)
            if ctype:
                query = query.where(ConnectorRecord.connector_type == ctype)
            if cstat:
                query = query.where(ConnectorRecord.status == cstat)
            query = query.order_by(ConnectorRecord.created_at.desc())
            return list(self.db.scalars(query).all())

        results = [r for r in self._memory_store.values() if r.tenant_id == tid]
        if ctype:
            results = [r for r in results if r.connector_type == ctype]
        if cstat:
            results = [r for r in results if r.status == cstat]
        results.sort(key=lambda x: x.created_at, reverse=True)
        return results
