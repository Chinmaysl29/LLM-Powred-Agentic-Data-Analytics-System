"""Phase 16.2 enterprise cache lifecycle coverage."""

import asyncio
import time

from backend.cache.enterprise_cache import CacheNamespace, EnterpriseCache
from backend.cache.cache_manager import CacheManager


class FakeRedisCache:
    def __init__(self):
        self.values = {}
        self.deleted_patterns = []

    async def get(self, key):
        return self.values.get(key)

    async def set(self, key, value, ttl_seconds=None):
        self.values[key] = value
        return True

    async def delete(self, key):
        return int(self.values.pop(key, None) is not None)

    async def delete_matching(self, pattern):
        self.deleted_patterns.append(pattern)
        prefix = pattern.rstrip("*")
        keys = [key for key in self.values if key.startswith(prefix)]
        for key in keys:
            del self.values[key]
        return len(keys)


def test_cache_write_read_invalidation_and_key_isolation():
    async def scenario():
        cache = EnterpriseCache(FakeRedisCache(), CacheManager())
        key = cache.key(CacheNamespace.DATASET, "tenant-a", "sales", {"version": 2})
        other_tenant_key = cache.key(CacheNamespace.DATASET, "tenant-b", "sales", {"version": 2})
        assert key != other_tenant_key
        await cache.set(key, {"rows": 42}, cache.ttl(CacheNamespace.DATASET))
        assert await cache.get(key) == {"rows": 42}
        assert await cache.invalidate(key) is True
        assert await cache.get(key) is None
    asyncio.run(scenario())


def test_cache_warming_and_redis_fallback():
    async def scenario():
        cache = EnterpriseCache(None, CacheManager())
        key = cache.key(CacheNamespace.ANALYTICS, "tenant-a", "revenue")
        calls = 0

        def producer():
            nonlocal calls
            calls += 1
            return {"mrr": 1200}

        first, cached = await cache.get_or_set(key, producer, 60)
        second, cached_second = await cache.get_or_set(key, producer, 60)
        assert first == second == {"mrr": 1200}
        assert cached is False and cached_second is True and calls == 1
        assert await cache.warm({key: (producer, 60)}) == 1
    asyncio.run(scenario())


def test_cache_expiry_and_prefix_invalidation():
    async def scenario():
        cache = EnterpriseCache(None, CacheManager())
        key = cache.key(CacheNamespace.QUERY, "tenant-a", "sales")
        await cache.set(key, {"result": 1}, 1)
        assert await cache.get(key) == {"result": 1}
        time.sleep(1.05)
        assert await cache.get(key) is None

        first = cache.key(CacheNamespace.DATASET, "tenant-a", "sales", {"version": 1})
        second = cache.key(CacheNamespace.DATASET, "tenant-a", "sales", {"version": 2})
        await cache.set(first, 1, 60)
        await cache.set(second, 2, 60)
        prefix = ":".join(first.split(":")[:-1]) + ":"
        assert await cache.invalidate_prefix(prefix) == 2
    asyncio.run(scenario())
