"""Tests for Phase 8.8: Performance Optimization."""

import pytest
from backend.cache.cache_manager import CacheManager


@pytest.fixture
def cache():
    cm = CacheManager(default_ttl_seconds=60)
    cm.clear()
    return cm


def test_repeated_query_served_from_cache(cache):
    """Test Case: Repeated query served from cache."""
    query = "SELECT department, AVG(salary) FROM employees GROUP BY department"
    call_count = 0

    def expensive_query_fn():
        nonlocal call_count
        call_count += 1
        return [{"department": "Engineering", "avg_salary": 120000}]

    # First call: cache miss
    val1, is_cached1 = cache.get_or_compute(query, expensive_query_fn)
    assert val1 == [{"department": "Engineering", "avg_salary": 120000}]
    assert is_cached1 is False
    assert call_count == 1

    # Second call: cache hit, expensive_query_fn is NOT called again
    val2, is_cached2 = cache.get_or_compute(query, expensive_query_fn)
    assert val2 == val1
    assert is_cached2 is True
    assert call_count == 1  # Remained 1!

    stats = cache.get_cache_stats()
    assert stats["hits"] == 1
    assert stats["misses"] == 1


def test_optimization_score_output(cache):
    """Verify optimization score output structure."""
    # Seed cache to demonstrate efficiency
    cache.set("k1", "v1")
    cache.get("k1")  # Hit
    cache.get("k1")  # Hit

    opt_result = cache.calculate_optimization_score()
    assert "optimization_score" in opt_result
    assert isinstance(opt_result["optimization_score"], int)
    assert opt_result["optimization_score"] >= 90
    assert len(opt_result["techniques_active"]) >= 3


def test_cache_invalidation_by_key_and_tag(cache):
    """Verify invalidation mechanics."""
    cache.set("dataset:101:meta", {"rows": 500}, tags=["dataset:101", "datasets"])
    cache.set("dataset:101:stats", {"mean": 42}, tags=["dataset:101", "datasets"])
    cache.set("dataset:102:meta", {"rows": 100}, tags=["dataset:102", "datasets"])

    assert cache.get("dataset:101:meta") is not None

    # Invalidate dataset 101 by tag
    deleted_count = cache.invalidate_by_tag("dataset:101")
    assert deleted_count == 2

    assert cache.get("dataset:101:meta") is None
    assert cache.get("dataset:101:stats") is None
    # 102 should still be intact
    assert cache.get("dataset:102:meta") is not None

    # Invalidate single key
    cache.invalidate("dataset:102:meta")
    assert cache.get("dataset:102:meta") is None


def test_batch_processing(cache):
    """Verify batch processing chunking."""
    items = list(range(25))

    def mock_batch_worker(chunk: list[int]) -> list[int]:
        assert len(chunk) <= 10
        return [x * 2 for x in chunk]

    processed = cache.batch_process(items, mock_batch_worker, batch_size=10)
    assert len(processed) == 25
    assert processed == [x * 2 for x in items]
