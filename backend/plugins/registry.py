"""
Phase 12.10.2 — Plugin Registry
Central metadata catalog managing plugin registrations, version lineages,
author records, and lifecycle statuses.
"""

from typing import Dict, Any, List, Optional
import time
import uuid
import logging
from pydantic import BaseModel, Field

logger = logging.getLogger("backend.plugins.registry")


class PluginRecord(BaseModel):
    plugin_id: str = Field(default_factory=lambda: f"plg-{uuid.uuid4().hex[:8]}")
    plugin_name: str
    plugin_type: str # "agent", "connector", "workflow", "dashboard"
    version: str = "1.0.0"
    author: str = "Enterprise Dev"
    status: str = "active" # "active", "disabled", "deprecated"
    tenant_id: Optional[str] = None
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)


class PluginRegistry:
    """
    Registry for enterprise plugins across tenants and categories.
    """

    def __init__(self):
        self._records: Dict[str, PluginRecord] = {}

    def register_plugin(
        self,
        plugin_name: str,
        plugin_type: str,
        version: str = "1.0.0",
        author: str = "Community",
        plugin_id: Optional[str] = None,
        tenant_id: Optional[str] = None
    ) -> PluginRecord:
        """Register a new plugin into the catalog."""
        pid = plugin_id or f"plg-{uuid.uuid4().hex[:8]}"
        record = PluginRecord(
            plugin_id=pid,
            plugin_name=plugin_name,
            plugin_type=plugin_type,
            version=version,
            author=author,
            tenant_id=tenant_id,
            status="active"
        )
        self._records[pid] = record
        logger.info("Registered plugin %s (%s, v%s)", pid, plugin_name, version)
        return record

    def get_plugin(self, plugin_id: str) -> Optional[PluginRecord]:
        return self._records.get(plugin_id)

    def activate_plugin(self, plugin_id: str) -> bool:
        rec = self._records.get(plugin_id)
        if not rec:
            return False
        rec.status = "active"
        rec.updated_at = time.time()
        return True

    def disable_plugin(self, plugin_id: str) -> bool:
        rec = self._records.get(plugin_id)
        if not rec:
            return False
        rec.status = "disabled"
        rec.updated_at = time.time()
        return True

    def list_plugins(
        self,
        plugin_type: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[PluginRecord]:
        items = list(self._records.values())
        if plugin_type:
            items = [i for i in items if i.plugin_type == plugin_type]
        if status:
            items = [i for i in items if i.status == status]
        return items

    def count(self) -> int:
        return len(self._records)
