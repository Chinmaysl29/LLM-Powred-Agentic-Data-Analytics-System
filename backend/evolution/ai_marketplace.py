"""
Phase 14.5 — AI Marketplace
Enterprise store providing curated, verified AI assets across 6 specialized departments:
Agents, Workflows, Prompts, Forecasting Models, Connectors, and Dashboards.
"""

from typing import Dict, Any, List, Optional
import time
import logging
from enum import Enum
from pydantic import BaseModel, Field

logger = logging.getLogger("backend.evolution.ai_marketplace")


class StoreDepartment(str, Enum):
    AGENTS = "agents"
    WORKFLOWS = "workflows"
    PROMPTS = "prompts"
    FORECAST_MODELS = "forecast_models"
    CONNECTORS = "connectors"
    DASHBOARDS = "dashboards"


class AIAsset(BaseModel):
    asset_id: str
    name: str
    department: StoreDepartment
    version: str
    author: str
    price_credits: int = 0 # 0 for free / community
    rating: float = 5.0
    downloads: int = 0
    description: str = ""


class AIMarketplaceStore:
    """
    Unified marketplace serving all 6 asset stores for enterprise platform extension.
    """

    def __init__(self):
        self._assets: Dict[str, AIAsset] = {}
        self._init_catalog()

    def _init_catalog(self):
        catalog = [
            AIAsset(asset_id="store-agent-01", name="Forensic Audit Agent", department=StoreDepartment.AGENTS, version="1.0.0", author="KPMG Certified"),
            AIAsset(asset_id="store-wf-01", name="Automated SOC2 Evidence Collector", department=StoreDepartment.WORKFLOWS, version="2.1.0", author="ComplianceLabs"),
            AIAsset(asset_id="store-pmpt-01", name="Executive Board Summary Prompt", department=StoreDepartment.PROMPTS, version="1.4.0", author="BoardRoom AI"),
            AIAsset(asset_id="store-fcst-01", name="DeepAR Multi-Horizon Retail Model", department=StoreDepartment.FORECAST_MODELS, version="3.0.0", author="Stanford ML Group"),
            AIAsset(asset_id="store-conn-01", name="Workday HR & Payroll Connector", department=StoreDepartment.CONNECTORS, version="1.1.2", author="Workday Partner"),
            AIAsset(asset_id="store-dash-01", name="CFO Cash Flow Command Center", department=StoreDepartment.DASHBOARDS, version="2.0.0", author="Enterprise Analytics")
        ]
        for a in catalog:
            self._assets[a.asset_id] = a

    def browse_department(self, department: StoreDepartment) -> List[AIAsset]:
        """Browse assets within a specific store department."""
        return [a for a in self._assets.values() if a.department == department]

    def publish_asset(self, asset: AIAsset) -> bool:
        """Publish custom AI asset into enterprise marketplace."""
        self._assets[asset.asset_id] = asset
        logger.info("Published AI asset %s to %s store", asset.asset_id, asset.department.value)
        return True

    def install_asset(self, asset_id: str, tenant_id: str) -> Dict[str, Any]:
        """Install asset for tenant."""
        asset = self._assets.get(asset_id)
        if not asset:
            return {"success": False, "error": "Asset not found"}
        asset.downloads += 1
        return {
            "success": True,
            "tenant_id": tenant_id,
            "asset_id": asset_id,
            "asset_name": asset.name,
            "department": asset.department.value,
            "installed_at": time.time()
        }

    def get_catalog_summary(self) -> Dict[str, int]:
        counts = {}
        for dep in StoreDepartment:
            counts[dep.value] = len(self.browse_department(dep))
        return counts
