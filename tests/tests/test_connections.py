"""Unit tests for PostgreSQL, Redis, and ChromaDB connection validation."""

from unittest.mock import AsyncMock, MagicMock, patch

from backend.app.core.config import Settings
from backend.app.database.chromadb import ChromaDatabase
from backend.app.database.postgres import PostgresDatabase
from backend.app.database.redis import RedisCache


def test_postgres_connect_validates_engine() -> None:
    """The PostgreSQL adapter validates a new SQLAlchemy engine."""
    mock_connection = MagicMock()
    mock_connection.__enter__.return_value = mock_connection
    mock_engine = MagicMock()
    mock_engine.connect.return_value = mock_connection

    with patch("backend.app.database.postgres.create_engine", return_value=mock_engine):
        database = PostgresDatabase(Settings(_env_file=None))
        database.connect()

    mock_connection.execute.assert_called_once()


def test_redis_connect_validates_ping() -> None:
    """The Redis adapter pings a newly created client."""
    client = MagicMock()
    client.ping = AsyncMock(return_value=True)

    with patch("backend.app.database.redis.redis.from_url", return_value=client):
        cache = RedisCache(Settings(_env_file=None))
        import asyncio

        asyncio.run(cache.connect())

    client.ping.assert_awaited_once()


def test_chroma_connect_validates_heartbeat() -> None:
    """The ChromaDB adapter validates its HTTP client heartbeat."""
    client = MagicMock()
    with patch("backend.app.database.chromadb.chromadb.HttpClient", return_value=client):
        chroma = ChromaDatabase(Settings(_env_file=None))
        import asyncio

        asyncio.run(chroma.connect())

    client.heartbeat.assert_called_once()
