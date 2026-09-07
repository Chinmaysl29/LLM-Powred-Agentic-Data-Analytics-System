"""
Phase 13.2 — Infrastructure as Code (IaC) Manager
Orchestrates multi-environment provisioning (Dev, Staging, Production),
validates Terraform specifications, manages Kubernetes namespace quotas, and handles drift detection.
"""

from typing import Dict, Any, List, Optional
import logging
from enum import Enum
from pydantic import BaseModel, Field

logger = logging.getLogger("backend.operations.iac")


class TargetEnvironment(str, Enum):
    DEV = "dev"
    STAGING = "staging"
    PRODUCTION = "production"


class EnvironmentConfig(BaseModel):
    environment: TargetEnvironment
    cluster_nodes: int
    db_instance_type: str
    redis_nodes: int
    auto_scaling_max_pods: int
    monthly_budget_usd: float
    multi_region: bool = False
    enforce_strict_tls: bool = False


class IaCManager:
    """
    Manages Infrastructure as Code declarations across environments,
    validates Terraform plans, and verifies resource allocation boundaries.
    """

    def __init__(self):
        self._configs: Dict[TargetEnvironment, EnvironmentConfig] = {
            TargetEnvironment.DEV: EnvironmentConfig(
                environment=TargetEnvironment.DEV,
                cluster_nodes=2,
                db_instance_type="db.t4g.medium",
                redis_nodes=1,
                auto_scaling_max_pods=5,
                monthly_budget_usd=300.0,
                multi_region=False,
                enforce_strict_tls=False
            ),
            TargetEnvironment.STAGING: EnvironmentConfig(
                environment=TargetEnvironment.STAGING,
                cluster_nodes=4,
                db_instance_type="db.r6g.large",
                redis_nodes=3,
                auto_scaling_max_pods=15,
                monthly_budget_usd=1500.0,
                multi_region=False,
                enforce_strict_tls=True
            ),
            TargetEnvironment.PRODUCTION: EnvironmentConfig(
                environment=TargetEnvironment.PRODUCTION,
                cluster_nodes=12,
                db_instance_type="db.r6g.4xlarge",
                redis_nodes=6,
                auto_scaling_max_pods=60,
                monthly_budget_usd=12000.0,
                multi_region=True,
                enforce_strict_tls=True
            )
        }

    def get_environment_config(self, env: TargetEnvironment) -> EnvironmentConfig:
        return self._configs[env]

    def validate_terraform_plan(self, env: TargetEnvironment, plan_resources: List[str]) -> Dict[str, Any]:
        """Validate proposed Terraform resource plan against environment governance rules."""
        cfg = self._configs[env]
        required_bases = ["module.vpc", "module.k8s_cluster", "module.rds_postgres", "module.elasticache_redis"]
        missing = [r for r in required_bases if not any(p.startswith(r) for p in plan_resources)]

        if missing:
            return {
                "valid": False,
                "environment": env.value,
                "error": f"Missing required foundational modules: {missing}"
            }

        # Check multi-region requirement for production
        if cfg.multi_region and not any("replica_region" in p for p in plan_resources):
            return {
                "valid": False,
                "environment": env.value,
                "error": "Production environment requires multi-region replica definitions"
            }

        return {
            "valid": True,
            "environment": env.value,
            "resource_count": len(plan_resources),
            "estimated_monthly_cost": cfg.monthly_budget_usd
        }

    def render_environment_manifest(self, env: TargetEnvironment) -> Dict[str, Any]:
        """Produce Kubernetes namespace manifest and resource quota spec."""
        cfg = self._configs[env]
        return {
            "apiVersion": "v1",
            "kind": "ResourceQuota",
            "metadata": {"name": f"quota-{env.value}", "namespace": f"analystos-{env.value}"},
            "spec": {
                "hard": {
                    "requests.cpu": f"{cfg.cluster_nodes * 2}",
                    "requests.memory": f"{cfg.cluster_nodes * 8}Gi",
                    "limits.cpu": f"{cfg.cluster_nodes * 4}",
                    "limits.memory": f"{cfg.cluster_nodes * 16}Gi",
                    "pods": str(cfg.auto_scaling_max_pods)
                }
            }
        }
