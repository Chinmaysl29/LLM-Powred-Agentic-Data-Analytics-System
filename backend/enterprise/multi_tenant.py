"""Phase 12.1 — Multi-Tenant Architecture

Provides enterprise-grade tenant isolation, tenant lifecycle management,
context-variable tracking, quota enforcement, and PostgreSQL Row-Level Security (RLS) helpers.
"""

from __future__ import annotations

import contextvars
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid

# Context variable for holding active request tenant ID
_CURRENT_TENANT_ID: contextvars.ContextVar[str] = contextvars.ContextVar(
    "current_tenant_id", default="system"
)


def get_current_tenant_id() -> str:
    """Return the active tenant ID for the current async execution context."""
    return _CURRENT_TENANT_ID.get()


def set_current_tenant_id(tenant_id: str) -> contextvars.Token:
    """Set the active tenant ID and return reset token."""
    return _CURRENT_TENANT_ID.set(tenant_id)


class tenant_context:
    """Context manager for temporarily scoping execution to a specific tenant."""

    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self._token: Optional[contextvars.Token] = None

    def __enter__(self):
        self._token = set_current_tenant_id(self.tenant_id)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._token is not None:
            _CURRENT_TENANT_ID.reset(self._token)


class TenantTier(str, Enum):
    FREE = "free"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"
    UNLIMITED = "unlimited"


class TenantStatus(str, Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    ARCHIVED = "archived"
    PROVISIONING = "provisioning"


@dataclass
class TenantQuota:
    max_users: int = 10
    max_datasets: int = 25
    max_workspaces: int = 5
    max_storage_mb: int = 5120  # 5 GB
    max_api_calls_per_min: int = 300
    custom_models_allowed: bool = False
    sla_hours: int = 24

    @classmethod
    def default_for_tier(cls, tier: TenantTier) -> TenantQuota:
        if tier == TenantTier.FREE:
            return cls(
                max_users=3,
                max_datasets=5,
                max_workspaces=1,
                max_storage_mb=1024,
                max_api_calls_per_min=60,
                custom_models_allowed=False,
                sla_hours=48,
            )
        elif tier == TenantTier.PROFESSIONAL:
            return cls(
                max_users=25,
                max_datasets=100,
                max_workspaces=10,
                max_storage_mb=51200,  # 50 GB
                max_api_calls_per_min=1000,
                custom_models_allowed=True,
                sla_hours=12,
            )
        elif tier in (TenantTier.ENTERPRISE, TenantTier.UNLIMITED):
            return cls(
                max_users=10000,
                max_datasets=50000,
                max_workspaces=1000,
                max_storage_mb=1048576,  # 1 TB
                max_api_calls_per_min=10000,
                custom_models_allowed=True,
                sla_hours=1,
            )
        return cls()


@dataclass
class TenantUsage:
    user_count: int = 0
    dataset_count: int = 0
    workspace_count: int = 0
    storage_mb_used: float = 0.0
    api_calls_this_minute: int = 0
    total_query_count: int = 0
    last_active: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class Tenant:
    id: str
    name: str
    slug: str
    tier: TenantTier = TenantTier.PROFESSIONAL
    status: TenantStatus = TenantStatus.ACTIVE
    admin_email: str = "admin@example.com"
    quota: TenantQuota = field(default_factory=TenantQuota)
    usage: TenantUsage = field(default_factory=TenantUsage)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "slug": self.slug,
            "tier": self.tier.value,
            "status": self.status.value,
            "admin_email": self.admin_email,
            "quota": {
                "max_users": self.quota.max_users,
                "max_datasets": self.quota.max_datasets,
                "max_workspaces": self.quota.max_workspaces,
                "max_storage_mb": self.quota.max_storage_mb,
                "max_api_calls_per_min": self.quota.max_api_calls_per_min,
                "custom_models_allowed": self.quota.custom_models_allowed,
                "sla_hours": self.quota.sla_hours,
            },
            "usage": {
                "user_count": self.usage.user_count,
                "dataset_count": self.usage.dataset_count,
                "workspace_count": self.usage.workspace_count,
                "storage_mb_used": self.usage.storage_mb_used,
                "api_calls_this_minute": self.usage.api_calls_this_minute,
                "total_query_count": self.usage.total_query_count,
            },
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata,
        }


class TenantManager:
    """Singleton repository and orchestrator for all tenant operations."""

    _instance: Optional[TenantManager] = None

    def __new__(cls) -> TenantManager:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._tenants: Dict[str, Tenant] = {}
            cls._instance._slug_index: Dict[str, str] = {}
            cls._instance._seed_default_tenant()
        return cls._instance

    def _seed_default_tenant(self) -> None:
        """Seed the system default tenant."""
        default_id = "system"
        default_tenant = Tenant(
            id=default_id,
            name="System Default",
            slug="system",
            tier=TenantTier.UNLIMITED,
            status=TenantStatus.ACTIVE,
            admin_email="system@internal",
            quota=TenantQuota.default_for_tier(TenantTier.UNLIMITED),
            metadata={"description": "Built-in root tenant for system accounts and legacy migrations"},
        )
        self._tenants[default_id] = default_tenant
        self._slug_index["system"] = default_id

    def create_tenant(
        self,
        name: str,
        slug: Optional[str] = None,
        tier: TenantTier = TenantTier.PROFESSIONAL,
        admin_email: str = "admin@example.com",
        custom_quota: Optional[TenantQuota] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tenant:
        """Provision a new tenant organization."""
        tenant_id = str(uuid.uuid4())
        normalized_slug = (slug or name.lower().replace(" ", "-")).strip()
        
        if normalized_slug in self._slug_index:
            raise ValueError(f"Tenant with slug '{normalized_slug}' already exists")

        quota = custom_quota or TenantQuota.default_for_tier(tier)
        tenant = Tenant(
            id=tenant_id,
            name=name,
            slug=normalized_slug,
            tier=tier,
            status=TenantStatus.ACTIVE,
            admin_email=admin_email,
            quota=quota,
            metadata=metadata or {},
        )
        self._tenants[tenant_id] = tenant
        self._slug_index[normalized_slug] = tenant_id
        return tenant

    def get_tenant(self, tenant_id: str) -> Optional[Tenant]:
        """Fetch tenant by unique ID."""
        return self._tenants.get(tenant_id)

    def get_tenant_by_slug(self, slug: str) -> Optional[Tenant]:
        """Fetch tenant by unique slug."""
        tenant_id = self._slug_index.get(slug)
        if tenant_id:
            return self._tenants.get(tenant_id)
        return None

    def list_tenants(self, status: Optional[TenantStatus] = None) -> List[Tenant]:
        """List tenants with optional status filtering."""
        tenants = list(self._tenants.values())
        if status is not None:
            tenants = [t for t in tenants if t.status == status]
        return tenants

    def update_tenant_status(self, tenant_id: str, new_status: TenantStatus, reason: str = "") -> Tenant:
        """Transition tenant status (e.g. suspend or archive)."""
        tenant = self.get_tenant(tenant_id)
        if not tenant:
            raise KeyError(f"Tenant {tenant_id} not found")
        tenant.status = new_status
        tenant.metadata["status_reason"] = reason
        tenant.metadata["status_changed_at"] = datetime.now(timezone.utc).isoformat()
        return tenant

    def check_quota(self, tenant_id: str, resource: str, requested: int = 1) -> Dict[str, Any]:
        """Verify whether tenant is permitted to allocate additional resources."""
        tenant = self.get_tenant(tenant_id)
        if not tenant:
            return {"allowed": False, "reason": f"Unknown tenant {tenant_id}"}

        if tenant.status != TenantStatus.ACTIVE:
            return {"allowed": False, "reason": f"Tenant is {tenant.status.value}"}

        quota = tenant.quota
        usage = tenant.usage

        limit_map = {
            "users": (usage.user_count, quota.max_users),
            "datasets": (usage.dataset_count, quota.max_datasets),
            "workspaces": (usage.workspace_count, quota.max_workspaces),
            "storage_mb": (usage.storage_mb_used, quota.max_storage_mb),
            "api_calls": (usage.api_calls_this_minute, quota.max_api_calls_per_min),
        }

        if resource not in limit_map:
            return {"allowed": True, "resource": resource}

        current, maximum = limit_map[resource]
        if current + requested > maximum:
            return {
                "allowed": False,
                "resource": resource,
                "current": current,
                "limit": maximum,
                "requested": requested,
                "reason": f"Quota exceeded for {resource}: current={current}, limit={maximum}",
            }

        return {
            "allowed": True,
            "resource": resource,
            "current": current,
            "limit": maximum,
            "remaining": maximum - (current + requested),
        }

    def record_usage(self, tenant_id: str, resource: str, delta: int | float = 1) -> None:
        """Increment usage metric for a tenant."""
        tenant = self.get_tenant(tenant_id)
        if not tenant:
            return
        usage = tenant.usage
        usage.last_active = datetime.now(timezone.utc)

        if resource == "users":
            usage.user_count = max(0, usage.user_count + int(delta))
        elif resource == "datasets":
            usage.dataset_count = max(0, usage.dataset_count + int(delta))
        elif resource == "workspaces":
            usage.workspace_count = max(0, usage.workspace_count + int(delta))
        elif resource == "storage_mb":
            usage.storage_mb_used = max(0.0, usage.storage_mb_used + float(delta))
        elif resource == "api_calls":
            usage.api_calls_this_minute += int(delta)
        elif resource == "queries":
            usage.total_query_count += int(delta)

    def get_tenant_stats(self, tenant_id: str) -> Dict[str, Any]:
        """Aggregate high-level usage and health statistics."""
        tenant = self.get_tenant(tenant_id)
        if not tenant:
            raise KeyError(f"Tenant {tenant_id} not found")

        quota = tenant.quota
        usage = tenant.usage
        storage_pct = round((usage.storage_mb_used / max(1, quota.max_storage_mb)) * 100, 2)
        dataset_pct = round((usage.dataset_count / max(1, quota.max_datasets)) * 100, 2)

        return {
            "tenant_id": tenant.id,
            "name": tenant.name,
            "tier": tenant.tier.value,
            "status": tenant.status.value,
            "storage_utilization_pct": min(100.0, storage_pct),
            "dataset_utilization_pct": min(100.0, dataset_pct),
            "active_users": usage.user_count,
            "total_queries_executed": usage.total_query_count,
            "sla_hours": quota.sla_hours,
        }

    def reset(self) -> None:
        """Reset state for testing."""
        self._tenants.clear()
        self._slug_index.clear()
        self._seed_default_tenant()


# =====================================================================
# Database Row-Level Security (RLS) & Query Filter Helpers
# =====================================================================

def generate_rls_sql_policies(table_name: str, tenant_col: str = "tenant_id") -> List[str]:
    """Generate production-ready PostgreSQL Row-Level Security DDL commands.

    Enforces PostgreSQL database-level isolation so no tenant can ever see
    rows belonging to another tenant even under direct SQL queries.
    """
    safe_table = table_name.replace("'", "").replace(";", "")
    safe_col = tenant_col.replace("'", "").replace(";", "")

    return [
        f"ALTER TABLE {safe_table} ADD COLUMN IF NOT EXISTS {safe_col} VARCHAR(64) DEFAULT 'system' NOT NULL;",
        f"CREATE INDEX IF NOT EXISTS idx_{safe_table}_{safe_col} ON {safe_table}({safe_col});",
        f"ALTER TABLE {safe_table} ENABLE ROW LEVEL SECURITY;",
        f"DROP POLICY IF EXISTS {safe_table}_tenant_isolation_policy ON {safe_table};",
        (
            f"CREATE POLICY {safe_table}_tenant_isolation_policy ON {safe_table} "
            f"FOR ALL USING ({safe_col} = NULLIF(current_setting('app.current_tenant_id', true), '')) "
            f"WITH CHECK ({safe_col} = NULLIF(current_setting('app.current_tenant_id', true), ''));"
        ),
    ]


def verify_tenant_access(requester_tenant_id: str, resource_tenant_id: str) -> bool:
    """Validate that the requesting tenant has permission to access the resource."""
    # System tenant has administrative super-access across all partitions
    if requester_tenant_id == "system":
        return True
    return requester_tenant_id == resource_tenant_id


def apply_tenant_filter(query: Any, model: Any, tenant_id: Optional[str] = None) -> Any:
    """Scope an ORM or SQL query to a specific tenant ID."""
    tid = tenant_id or get_current_tenant_id()
    if hasattr(model, "tenant_id"):
        return query.filter(model.tenant_id == tid)
    return query

