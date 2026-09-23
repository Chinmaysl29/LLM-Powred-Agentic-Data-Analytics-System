"""
Tests for backend/app/database/ — PostgresDatabase, RedisCache, ChromaDatabase.
Uses mocking to test all connection/health/CRUD logic without live infrastructure.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

from backend.app.core.config import Settings
from backend.app.core.exceptions import (
    ChromaConnectionError,
    DatabaseConnectionError,
    RedisConnectionError,
)
from backend.app.database.chromadb import ChromaDatabase
from backend.app.database.postgres import PostgresDatabase
from backend.app.database.redis import RedisCache


# ===========================================================================
# Shared Settings Fixture
# ===========================================================================

@pytest.fixture
def test_settings() -> Settings:
    return Settings(
        environment="test",
        postgres_host="localhost",
        postgres_port=5432,
        postgres_db="test_db",
        postgres_user="test_user",
        postgres_password="test_pass",
        redis_host="localhost",
        redis_port=6379,
        redis_url="redis://localhost:6379/0",
        chroma_host="localhost",
        chroma_port=8001,
    )


# ===========================================================================
# PostgresDatabase Tests
# ===========================================================================

class TestPostgresDatabase:
    """Unit tests for PostgresDatabase without a live database."""

    def test_engine_property_raises_before_connect(self, test_settings):
        db = PostgresDatabase(test_settings)
        with pytest.raises(DatabaseConnectionError, match="not been initialized"):
            _ = db.engine

    def test_connect_creates_engine_and_validates(self, test_settings):
        db = PostgresDatabase(test_settings)
        mock_engine = MagicMock()
        mock_conn = MagicMock()
        mock_engine.connect.return_value.__enter__ = lambda s: mock_conn
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)

        with patch("backend.app.database.postgres.create_engine", return_value=mock_engine):
            db.connect()
        assert db._engine is mock_engine

    def test_connect_raises_on_validation_failure(self, test_settings):
        db = PostgresDatabase(test_settings)
        mock_engine = MagicMock()
        mock_engine.connect.side_effect = Exception("connection refused")

        with patch("backend.app.database.postgres.create_engine", return_value=mock_engine):
            with pytest.raises(DatabaseConnectionError):
                db.connect()

    def test_close_disposes_engine(self, test_settings):
        db = PostgresDatabase(test_settings)
        mock_engine = MagicMock()
        db._engine = mock_engine
        db._session_factory = MagicMock()
        db.close()
        mock_engine.dispose.assert_called_once()
        assert db._engine is None

    def test_close_noop_when_not_connected(self, test_settings):
        db = PostgresDatabase(test_settings)
        # Must not raise
        db.close()

    @pytest.mark.asyncio
    async def test_health_check_returns_true_on_success(self, test_settings):
        db = PostgresDatabase(test_settings)
        with patch.object(db, "connect"):
            ok, msg = await db.health_check()
        assert ok is True
        assert "reachable" in msg

    @pytest.mark.asyncio
    async def test_health_check_returns_false_on_failure(self, test_settings):
        db = PostgresDatabase(test_settings)
        with patch.object(db, "connect", side_effect=DatabaseConnectionError("down")):
            ok, msg = await db.health_check()
        assert ok is False
        assert "unavailable" in msg.lower()

    def test_session_raises_when_factory_not_initialized(self, test_settings):
        db = PostgresDatabase(test_settings)
        with pytest.raises(DatabaseConnectionError, match="session factory"):
            list(db.session())

    def test_session_yields_and_closes(self, test_settings):
        db = PostgresDatabase(test_settings)
        mock_session = MagicMock()
        mock_factory = MagicMock(return_value=mock_session)
        db._session_factory = mock_factory
        db._engine = MagicMock()

        sessions = list(db.session())
        assert sessions == [mock_session]
        mock_session.close.assert_called_once()

    def test_double_connect_skips_engine_recreation(self, test_settings):
        db = PostgresDatabase(test_settings)
        mock_engine = MagicMock()
        mock_conn = MagicMock()
        mock_engine.connect.return_value.__enter__ = lambda s: mock_conn
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)

        with patch("backend.app.database.postgres.create_engine", return_value=mock_engine) as mock_create:
            db.connect()
            db.connect()
        # create_engine should only be called once
        assert mock_create.call_count == 1


# ===========================================================================
# RedisCache Tests
# ===========================================================================

class TestRedisCache:
    """Unit tests for RedisCache without a live Redis server."""

    def test_client_property_raises_before_connect(self, test_settings):
        cache = RedisCache(test_settings)
        with pytest.raises(RedisConnectionError, match="not been initialized"):
            _ = cache.client

    @pytest.mark.asyncio
    async def test_connect_pings_successfully(self, test_settings):
        cache = RedisCache(test_settings)
        mock_client = AsyncMock()
        mock_client.ping = AsyncMock(return_value=True)

        with patch("redis.asyncio.from_url", return_value=mock_client):
            await cache.connect()
        assert cache._client is mock_client

    @pytest.mark.asyncio
    async def test_connect_raises_on_ping_failure(self, test_settings):
        from redis.exceptions import RedisError
        cache = RedisCache(test_settings)
        mock_client = AsyncMock()
        mock_client.ping = AsyncMock(side_effect=RedisError("ping failed"))
        mock_client.aclose = AsyncMock()

        with patch("redis.asyncio.from_url", return_value=mock_client):
            with pytest.raises(RedisConnectionError):
                await cache.connect()

    @pytest.mark.asyncio
    async def test_health_check_returns_true(self, test_settings):
        cache = RedisCache(test_settings)
        with patch.object(cache, "connect", new_callable=AsyncMock):
            ok, msg = await cache.health_check()
        assert ok is True
        assert "reachable" in msg

    @pytest.mark.asyncio
    async def test_health_check_returns_false_on_error(self, test_settings):
        cache = RedisCache(test_settings)
        with patch.object(cache, "connect", side_effect=RedisConnectionError("down")):
            ok, msg = await cache.health_check()
        assert ok is False

    @pytest.mark.asyncio
    async def test_get_returns_value(self, test_settings):
        cache = RedisCache(test_settings)
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value="my_value")
        cache._client = mock_client

        result = await cache.get("my_key")
        assert result == "my_value"

    @pytest.mark.asyncio
    async def test_set_returns_true(self, test_settings):
        cache = RedisCache(test_settings)
        mock_client = AsyncMock()
        mock_client.set = AsyncMock(return_value=True)
        cache._client = mock_client

        result = await cache.set("key", "val", ttl_seconds=60)
        assert result is True

    @pytest.mark.asyncio
    async def test_set_with_ttl_passes_ex(self, test_settings):
        cache = RedisCache(test_settings)
        mock_client = AsyncMock()
        mock_client.set = AsyncMock(return_value=True)
        cache._client = mock_client

        await cache.set("k", "v", ttl_seconds=120)
        mock_client.set.assert_called_once_with("k", "v", ex=120)

    @pytest.mark.asyncio
    async def test_delete_returns_count(self, test_settings):
        cache = RedisCache(test_settings)
        mock_client = AsyncMock()
        mock_client.delete = AsyncMock(return_value=1)
        cache._client = mock_client

        result = await cache.delete("key")
        assert result == 1

    @pytest.mark.asyncio
    async def test_delete_missing_key_returns_zero(self, test_settings):
        cache = RedisCache(test_settings)
        mock_client = AsyncMock()
        mock_client.delete = AsyncMock(return_value=0)
        cache._client = mock_client

        result = await cache.delete("nonexistent")
        assert result == 0

    @pytest.mark.asyncio
    async def test_push_appends_to_list(self, test_settings):
        cache = RedisCache(test_settings)
        mock_client = AsyncMock()
        mock_client.rpush = AsyncMock(return_value=1)
        cache._client = mock_client

        result = await cache.push("queue", "job-1")
        assert result == 1

    @pytest.mark.asyncio
    async def test_pop_returns_value_or_none(self, test_settings):
        cache = RedisCache(test_settings)
        mock_client = AsyncMock()
        mock_client.lpop = AsyncMock(return_value="job-1")
        cache._client = mock_client

        result = await cache.pop("queue")
        assert result == "job-1"

    @pytest.mark.asyncio
    async def test_close_disconnects_client(self, test_settings):
        cache = RedisCache(test_settings)
        mock_client = AsyncMock()
        mock_client.aclose = AsyncMock()
        cache._client = mock_client

        await cache.close()
        mock_client.aclose.assert_called_once()
        assert cache._client is None

    @pytest.mark.asyncio
    async def test_close_noop_when_not_connected(self, test_settings):
        cache = RedisCache(test_settings)
        await cache.close()  # Must not raise

    @pytest.mark.asyncio
    async def test_get_raises_redis_connection_error_on_failure(self, test_settings):
        from redis.exceptions import RedisError
        cache = RedisCache(test_settings)
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=RedisError("failed"))
        cache._client = mock_client

        with pytest.raises(RedisConnectionError):
            await cache.get("key")

    @pytest.mark.asyncio
    async def test_delete_matching_removes_pattern_keys(self, test_settings):
        cache = RedisCache(test_settings)
        mock_client = AsyncMock()

        async def _scan_iter(*args, **kwargs):
            for k in ["key:1", "key:2"]:
                yield k

        mock_client.scan_iter = _scan_iter
        mock_client.delete = AsyncMock(return_value=2)
        cache._client = mock_client

        result = await cache.delete_matching("key:*")
        assert result == 2


# ===========================================================================
# ChromaDatabase Tests
# ===========================================================================

class TestChromaDatabase:
    """Unit tests for ChromaDatabase without a live ChromaDB server."""

    def test_client_property_raises_before_connect(self, test_settings):
        chroma = ChromaDatabase(test_settings)
        with pytest.raises(ChromaConnectionError, match="not been initialized"):
            _ = chroma.client

    @pytest.mark.asyncio
    async def test_connect_calls_heartbeat(self, test_settings):
        chroma = ChromaDatabase(test_settings)
        mock_client = MagicMock()
        mock_client.heartbeat.return_value = True

        with patch("chromadb.HttpClient", return_value=mock_client):
            await chroma.connect()
        assert chroma._client is mock_client

    @pytest.mark.asyncio
    async def test_connect_raises_on_heartbeat_failure(self, test_settings):
        chroma = ChromaDatabase(test_settings)
        mock_client = MagicMock()
        mock_client.heartbeat.side_effect = Exception("server unavailable")

        with patch("chromadb.HttpClient", return_value=mock_client):
            with pytest.raises(ChromaConnectionError):
                await chroma.connect()

    @pytest.mark.asyncio
    async def test_health_check_returns_true(self, test_settings):
        chroma = ChromaDatabase(test_settings)
        with patch.object(chroma, "connect", new_callable=AsyncMock):
            ok, msg = await chroma.health_check()
        assert ok is True
        assert "reachable" in msg

    @pytest.mark.asyncio
    async def test_health_check_returns_false_on_failure(self, test_settings):
        chroma = ChromaDatabase(test_settings)
        with patch.object(chroma, "connect", side_effect=ChromaConnectionError("down")):
            ok, msg = await chroma.health_check()
        assert ok is False

    @pytest.mark.asyncio
    async def test_close_clears_client(self, test_settings):
        chroma = ChromaDatabase(test_settings)
        chroma._client = MagicMock()
        await chroma.close()
        assert chroma._client is None

    @pytest.mark.asyncio
    async def test_get_or_create_collection_delegates_to_client(self, test_settings):
        chroma = ChromaDatabase(test_settings)
        mock_collection = MagicMock()
        mock_client = MagicMock()
        mock_client.get_or_create_collection = MagicMock(return_value=mock_collection)
        chroma._client = mock_client

        result = await chroma.get_or_create_collection("my_collection")
        assert result is mock_collection

    @pytest.mark.asyncio
    async def test_get_or_create_collection_raises_on_error(self, test_settings):
        chroma = ChromaDatabase(test_settings)
        mock_client = MagicMock()
        mock_client.get_or_create_collection.side_effect = Exception("collection error")
        chroma._client = mock_client

        with pytest.raises(ChromaConnectionError):
            await chroma.get_or_create_collection("bad_collection")
