"""
Phase 12.9.5 — Distributed Cache Layer (Redis Cluster)
Multi-region Redis Cluster partitioning 16384 hash slots across nodes,
providing dedicated cache tiers for Sessions, Analytics, Forecasts, and SQL Queries.
"""

from typing import Dict, Any, List, Optional
import time
import hashlib
import logging
from pydantic import BaseModel, Field

logger = logging.getLogger("backend.global_scale.distributed_cache")


class RedisClusterNode(BaseModel):
    node_id: str
    host: str
    port: int
    slot_range: tuple[int, int] # e.g. (0, 5460)
    is_master: bool = True
    is_alive: bool = True
    replica_of: Optional[str] = None


class DistributedCacheLayer:
    """
    Simulates a high-throughput Redis Cluster with CRC16 key hashing,
    partitioned tiers (session, analytics, forecast, query), and node failover.
    """

    def __init__(self):
        self._nodes: Dict[str, RedisClusterNode] = {}
        self._data: Dict[str, Dict[str, Any]] = {
            "session": {},
            "analytics": {},
            "forecast": {},
            "query": {}
        }
        self._init_cluster()

    def _init_cluster(self):
        # 3 Master nodes partitioning 16384 hash slots
        m1 = RedisClusterNode(node_id="redis-node-1", host="10.0.1.1", port=6379, slot_range=(0, 5460), is_master=True)
        m2 = RedisClusterNode(node_id="redis-node-2", host="10.0.1.2", port=6379, slot_range=(5461, 10922), is_master=True)
        m3 = RedisClusterNode(node_id="redis-node-3", host="10.0.1.3", port=6379, slot_range=(10923, 16383), is_master=True)

        # 3 Replica nodes
        r1 = RedisClusterNode(node_id="redis-rep-1", host="10.0.2.1", port=6379, slot_range=(0, 5460), is_master=False, replica_of="redis-node-1")
        r2 = RedisClusterNode(node_id="redis-rep-2", host="10.0.2.2", port=6379, slot_range=(5461, 10922), is_master=False, replica_of="redis-node-2")
        r3 = RedisClusterNode(node_id="redis-rep-3", host="10.0.2.3", port=6379, slot_range=(10923, 16383), is_master=False, replica_of="redis-node-3")

        for n in [m1, m2, m3, r1, r2, r3]:
            self._nodes[n.node_id] = n

    def get_slot(self, key: str) -> int:
        """Hash key to 0..16383 slot using CRC16/MD5 representation."""
        h = int(hashlib.md5(key.encode("utf-8")).hexdigest()[:4], 16)
        return h % 16384

    def get_node_for_key(self, key: str) -> RedisClusterNode:
        """Determine which node holds the hash slot for key."""
        slot = self.get_slot(key)
        for n in self._nodes.values():
            if n.is_master and n.is_alive:
                if n.slot_range[0] <= slot <= n.slot_range[1]:
                    return n
        # Fallback to any alive replica promoted
        for n in self._nodes.values():
            if n.is_alive and n.slot_range[0] <= slot <= n.slot_range[1]:
                return n
        raise RuntimeError(f"Hash slot {slot} unavailable (cluster down)!")

    def set(self, tier: str, key: str, value: Any, ttl_seconds: int = 3600) -> bool:
        """Write key into designated cache tier (session, analytics, forecast, query)."""
        if tier not in self._data:
            raise ValueError(f"Invalid cache tier: {tier}")
        node = self.get_node_for_key(key)
        self._data[tier][key] = {
            "value": value,
            "node_id": node.node_id,
            "expires_at": time.time() + ttl_seconds
        }
        return True

    def get(self, tier: str, key: str) -> Optional[Any]:
        """Read key from cache tier."""
        if tier not in self._data:
            return None
        item = self._data[tier].get(key)
        if not item:
            return None
        if time.time() > item["expires_at"]:
            del self._data[tier][key]
            return None
        return item["value"]

    def failover_node(self, master_node_id: str) -> bool:
        """Promote replica when master node crashes."""
        master = self._nodes.get(master_node_id)
        if not master:
            return False
        master.is_alive = False

        # Find replica
        replica = next((n for n in self._nodes.values() if n.replica_of == master_node_id and n.is_alive), None)
        if replica:
            replica.is_master = True
            replica.replica_of = None
            logger.info("Promoted replica %s to master for slot range %s", replica.node_id, replica.slot_range)
            return True
        return False

    def get_cluster_health(self) -> Dict[str, Any]:
        alive_masters = sum(1 for n in self._nodes.values() if n.is_master and n.is_alive)
        return {
            "total_nodes": len(self._nodes),
            "alive_masters": alive_masters,
            "cluster_state": "ok" if alive_masters == 3 else "degraded",
            "keys_count": {t: len(v) for t, v in self._data.items()}
        }
