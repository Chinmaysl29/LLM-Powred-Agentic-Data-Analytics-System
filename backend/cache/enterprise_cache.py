"""Redis-backed cache services with deterministic keys and L1 fallback."""

from __future__ import annotations

import hashlib
import inspect
import json
from enum import Enum
from typing import Any, Awaitable, Callable, Mapping

from backend.app.database.redis import RedisCache
from backend.app.core.exceptions import RedisConnectionError
from backend.cache.cache_manager import CacheManager


class CacheNamespace(str, Enum):
    DATASET = "dataset"
    ANALYTICS = "analytics"
    FORECAST = "forecast"
    QUERY = "query"
    SESSION = "session"


DEFAULT_TTLS: dict[CacheNamespace, int] = {
    CacheNamespace.DATASET: 15 * 60,
    CacheNamespace.ANALYTICS: 5 * 60,
    CacheNamespace.FORECAST: 60 * 60,
    CacheNamespace.QUERY: 2 * 60,
    CacheNamespace.SESSION: 30 * 60,
}


class CacheKeyStrategy:
    """Produces stable, tenant-isolated keys without exposing raw query values."""

    PREFIX = "ai-analyst:v1"

    @classmethod
    def build(
        cls,
        namespace: CacheNamespace,
        tenant_id: str,
        identifier: str,
        parameters: Mapping[str, Any] | None = None,
    ) -> str:
        canonical = json.dumps(parameters or {}, sort_keys=True, separators=(",", ":"), default=str)
        digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]
        safe_tenant = cls._safe_segment(tenant_id)
        safe_identifier = cls._safe_segment(identifier)
        return f"{cls.PREFIX}:{namespace.value}:{safe_tenant}:{safe_identifier}:{digest}"

    @staticmethod
    def _safe_segment(value: str) -> str:
        cleaned = "".join(char if char.isalnum() or char in "-_" else "_" for char in value)
        return cleaned[:128] or "default"


class EnterpriseCache:
    """Two-tier cache using the application's Redis adapter and L1 fallback.

    A ``RedisCache`` instance is injected by the application; this class never
    constructs a Redis client or owns its lifecycle.
    """

    def __init__(self, redis_cache: RedisCache | None = None, l1_cache: CacheManager | None = None) -> None:
        self._redis = redis_cache
        self._l1 = l1_cache or CacheManager()

    async def get(self, key: str) -> Any | None:
        local_value = self._l1.get(key)
        if local_value is not None:
            return local_value
        if self._redis is None:
            return None
        try:
            raw = await self._redis.get(key)
            if raw is None:
                return None
            value = json.loads(raw)
            self._l1.set(key, value)
            return value
        except (RedisConnectionError, json.JSONDecodeError, TypeError):
            return None

    async def set(self, key: str, value: Any, ttl_seconds: int) -> bool:
        self._l1.set(key, value, ttl_seconds=ttl_seconds)
        if self._redis is None:
            return True
        try:
            return await self._redis.set(key, json.dumps(value, default=str), ttl_seconds=ttl_seconds)
        except (RedisConnectionError, TypeError, ValueError):
            return True  # L1 remains available when Redis is unavailable.

    async def get_or_set(
        self,
        key: str,
        producer: Callable[[], Any | Awaitable[Any]],
        ttl_seconds: int,
    ) -> tuple[Any, bool]:
        cached = await self.get(key)
        if cached is not None:
            return cached, True
        value = producer()
        if inspect.isawaitable(value):
            value = await value
        await self.set(key, value, ttl_seconds)
        return value, False

    async def invalidate(self, key: str) -> bool:
        local = self._l1.invalidate(key)
        if self._redis is None:
            return local
        try:
            return bool(await self._redis.delete(key)) or local
        except RedisConnectionError:
            return local

    async def invalidate_prefix(self, prefix: str) -> int:
        local = self._l1.invalidate_matching(prefix)
        if self._redis is None:
            return local
        try:
            return int(await self._redis.delete_matching(f"{prefix}*")) + local
        except RedisConnectionError:
            return local

    async def warm(self, entries: Mapping[str, tuple[Callable[[], Any | Awaitable[Any]], int]]) -> int:
        """Populate selected keys. Producer failures do not poison the cache."""
        warmed = 0
        for key, (producer, ttl_seconds) in entries.items():
            try:
                await self.get_or_set(key, producer, ttl_seconds)
                warmed += 1
            except Exception:
                continue
        return warmed

    def key(
        self,
        namespace: CacheNamespace,
        tenant_id: str,
        identifier: str,
        parameters: Mapping[str, Any] | None = None,
    ) -> str:
        return CacheKeyStrategy.build(namespace, tenant_id, identifier, parameters)

    @staticmethod
    def ttl(namespace: CacheNamespace) -> int:
        return DEFAULT_TTLS[namespace]
