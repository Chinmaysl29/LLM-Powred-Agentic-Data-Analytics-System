"""Phase 12.4.1 — Connector Metadata Model.

SQLAlchemy model representing an enterprise data connector instance.
"""

from __future__ import annotations

from datetime import datetime, timezone
import enum
from typing import Any, Dict, Optional
import uuid

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    JSON,
    String,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, TimestampMixin


class ConnectorType(str, enum.Enum):
    DATABASE = "DATABASE"
    STORAGE = "STORAGE"
    CRM = "CRM"
    ERP = "ERP"
    WAREHOUSE = "WAREHOUSE"


class ConnectorStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    ERROR = "ERROR"
    SYNCING = "SYNCING"


class ConnectorRecord(Base, TimestampMixin):
    """Registered connector instance within a tenant workspace."""

    __tablename__ = "connectors"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    connector_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    connector_type: Mapped[ConnectorType] = mapped_column(
        SAEnum(ConnectorType),
        nullable=False,
        index=True,
    )
    connector_subtype: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,  # e.g., "postgresql", "s3", "salesforce", "snowflake"
    )
    status: Mapped[ConnectorStatus] = mapped_column(
        SAEnum(ConnectorStatus),
        default=ConnectorStatus.ACTIVE,
        nullable=False,
        index=True,
    )
    version: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="1.0.0",
    )
    config: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )

    __table_args__ = (
        Index("ix_connectors_tenant_type", "tenant_id", "connector_type"),
    )

    def __init__(self, **kwargs: Any) -> None:
        kwargs.setdefault("id", uuid.uuid4())
        kwargs.setdefault("status", ConnectorStatus.ACTIVE)
        kwargs.setdefault("version", "1.0.0")
        kwargs.setdefault("config", {})
        kwargs.setdefault("created_at", datetime.now(timezone.utc))
        kwargs.setdefault("updated_at", datetime.now(timezone.utc))
        super().__init__(**kwargs)
