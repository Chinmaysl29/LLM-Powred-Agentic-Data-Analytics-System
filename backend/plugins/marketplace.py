"""
Phase 12.10.7 — Marketplace Engine
Central enterprise app store allowing developers to publish, rate,
discover, install, and upgrade verified platform plugins.
"""

from typing import Dict, Any, List, Optional
import time
import logging
from pydantic import BaseModel, Field

logger = logging.getLogger("backend.plugins.marketplace")


class MarketplaceItem(BaseModel):
    item_id: str
    name: str
    category: str # "agents", "connectors", "workflows", "dashboards"
    latest_version: str
    author: str
    description: str
    ratings: List[float] = Field(default_factory=list)
    downloads_count: int = 0
    is_verified: bool = True
    published_at: float = Field(default_factory=time.time)

    @property
    def average_rating(self) -> float:
        return round(sum(self.ratings) / len(self.ratings), 1) if self.ratings else 5.0


class MarketplaceEngine:
    """
    Public and private marketplace managing plugin listings, installation,
    version upgrades, and community ratings.
    """

    def __init__(self):
        self._catalog: Dict[str, MarketplaceItem] = {}
        self._installed: Dict[str, Dict[str, str]] = {} # tenant_id -> {item_id: installed_version}
        self._init_default_listings()

    def _init_default_listings(self):
        default_items = [
            MarketplaceItem(
                item_id="plg-sap-erp",
                name="SAP S/4HANA Enterprise Connector",
                category="connectors",
                latest_version="2.1.0",
                author="SAP Partner Network",
                description="Direct OData integration into SAP financial tables.",
                ratings=[5.0, 4.8, 4.9]
            ),
            MarketplaceItem(
                item_id="plg-fraud-agent",
                name="Autonomous Payment Fraud Detection Agent",
                category="agents",
                latest_version="1.4.2",
                author="FinTech Security Labs",
                description="Detects anomalous wire transactions in real-time.",
                ratings=[5.0, 4.9]
            ),
            MarketplaceItem(
                item_id="plg-sankey-viz",
                name="Revenue Flow Sankey Diagram Widget",
                category="dashboards",
                latest_version="1.0.1",
                author="VizDesign Co",
                description="Multi-tier interactive revenue cashflow visualizer.",
                ratings=[4.7, 4.8]
            )
        ]
        for it in default_items:
            self._catalog[it.item_id] = it

    def publish_plugin(
        self,
        item_id: str,
        name: str,
        category: str,
        version: str,
        author: str,
        description: str = ""
    ) -> MarketplaceItem:
        """Publish a new plugin or update version in marketplace."""
        existing = self._catalog.get(item_id)
        if existing:
            existing.latest_version = version
            existing.description = description or existing.description
            logger.info("Updated plugin %s to version %s", item_id, version)
            return existing

        item = MarketplaceItem(
            item_id=item_id,
            name=name,
            category=category,
            latest_version=version,
            author=author,
            description=description
        )
        self._catalog[item_id] = item
        logger.info("Published new marketplace plugin: %s (%s)", item_id, name)
        return item

    def search_plugins(self, query: str = "", category: Optional[str] = None) -> List[MarketplaceItem]:
        """Discover marketplace plugins by name, keyword, or category."""
        results = list(self._catalog.values())
        if category:
            results = [r for r in results if r.category == category]
        if query:
            q = query.lower()
            results = [r for r in results if q in r.name.lower() or q in r.description.lower()]
        return results

    def install_plugin(self, tenant_id: str, item_id: str) -> Dict[str, Any]:
        """Install a marketplace plugin for an enterprise tenant."""
        item = self._catalog.get(item_id)
        if not item:
            return {"success": False, "error": "Plugin not found in marketplace"}

        tenant_installs = self._installed.setdefault(tenant_id, {})
        tenant_installs[item_id] = item.latest_version
        item.downloads_count += 1

        logger.info("Installed plugin %s v%s for tenant %s", item_id, item.latest_version, tenant_id)
        return {
            "success": True,
            "tenant_id": tenant_id,
            "item_id": item_id,
            "installed_version": item.latest_version
        }

    def upgrade_plugin(self, tenant_id: str, item_id: str) -> Dict[str, Any]:
        """Upgrade installed plugin to latest published version."""
        item = self._catalog.get(item_id)
        if not item:
            return {"success": False, "error": "Plugin not found"}

        tenant_installs = self._installed.get(tenant_id, {})
        if item_id not in tenant_installs:
            return {"success": False, "error": "Plugin not installed"}

        old_v = tenant_installs[item_id]
        tenant_installs[item_id] = item.latest_version
        return {
            "success": True,
            "item_id": item_id,
            "old_version": old_v,
            "new_version": item.latest_version
        }

    def add_rating(self, item_id: str, rating: float) -> bool:
        """Submit user review / star rating (1.0 to 5.0)."""
        item = self._catalog.get(item_id)
        if not item or rating < 1.0 or rating > 5.0:
            return False
        item.ratings.append(rating)
        return True
