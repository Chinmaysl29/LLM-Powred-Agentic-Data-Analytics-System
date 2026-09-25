"""Tests for strongly typed environment configuration."""

from backend.app.core.config import Settings
from pytest import MonkeyPatch


def test_database_url_is_composed_from_postgres_settings(monkeypatch: MonkeyPatch) -> None:
    """A PostgreSQL DSN is built when DATABASE_URL is not supplied."""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    settings = Settings(
        _env_file=None,
        postgres_host="db",
        postgres_port=5433,
        postgres_db="analytics",
        postgres_user="service",
        postgres_password="secret",
    )

    assert settings.postgres_dsn == "postgresql+psycopg://service:secret@db:5433/analytics"


def test_explicit_database_url_overrides_component_settings() -> None:
    """Deployment environments may provide one complete database URL."""
    settings = Settings(_env_file=None, database_url="postgresql+psycopg://configured")

    assert settings.postgres_dsn == "postgresql+psycopg://configured"
