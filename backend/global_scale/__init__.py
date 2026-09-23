"""
Phase 12.9 — Global Scale Architecture Package Exports
"""

from backend.global_scale.k8s_foundation import (
    KubernetesClusterManager,
    K8sServiceSpec,
    PodStatus,
)
from backend.global_scale.service_mesh import (
    IstioServiceMesh,
    TLSMode,
    VirtualServiceRoute,
)
from backend.global_scale.multi_region import (
    MultiRegionOrchestrator,
    GlobalRegion,
    RegionalClusterStatus,
)
from backend.global_scale.database_cluster import (
    DatabaseClusterManager,
    DatabaseNode,
)
from backend.global_scale.distributed_cache import (
    DistributedCacheLayer,
    RedisClusterNode,
)
from backend.global_scale.disaster_recovery import (
    DisasterRecoveryEngine,
    BackupRecord,
)
from backend.global_scale.high_availability import (
    HighAvailabilityManager,
    CircuitBreaker,
    CircuitState,
)
from backend.global_scale.observability import (
    ObservabilityPlatform,
    TraceSpan,
)
from backend.global_scale.security_hardening import (
    SecurityHardeningManager,
)

__all__ = [
    "KubernetesClusterManager",
    "K8sServiceSpec",
    "PodStatus",
    "IstioServiceMesh",
    "TLSMode",
    "VirtualServiceRoute",
    "MultiRegionOrchestrator",
    "GlobalRegion",
    "RegionalClusterStatus",
    "DatabaseClusterManager",
    "DatabaseNode",
    "DistributedCacheLayer",
    "RedisClusterNode",
    "DisasterRecoveryEngine",
    "BackupRecord",
    "HighAvailabilityManager",
    "CircuitBreaker",
    "CircuitState",
    "ObservabilityPlatform",
    "TraceSpan",
    "SecurityHardeningManager",
]
