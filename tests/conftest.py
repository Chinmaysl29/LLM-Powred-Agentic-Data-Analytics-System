"""
Shared pytest fixtures for the AI Data Analyst OS backend test suite.

Provides:
- In-memory SQLite engine & session factory
- FastAPI TestClient with all infra mocked out
- JWT token helpers
- Standard test DataFrames
- Common mock patching helpers
"""

import io
import sys
import uuid
from pathlib import Path
from typing import Generator
from unittest.mock import AsyncMock, MagicMock

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

# ---------------------------------------------------------------------------
# Ensure project root is on sys.path
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# ---------------------------------------------------------------------------
# Import application components
# ---------------------------------------------------------------------------
from backend.app.database.chromadb import ChromaDatabase
from backend.app.database.postgres import PostgresDatabase, get_db_session
from backend.app.database.redis import RedisCache
from backend.app.models.base import Base
from backend.app.models.dataset import Dataset
from backend.app.models.dataset_metadata import DatasetMetadata
from backend.app.models.dataset_profile import DatasetProfile
from backend.app.models.dataset_quality import DatasetQuality
from backend.app.models.dataset_version import DatasetVersion
from backend.app.models.user import User
from backend.app.core.config import Settings
from backend.app.core.security import hash_password
from backend.main import app
from backend.security.auth_service import AuthService


# ===========================================================================
# Infrastructure Mocking Helpers
# ===========================================================================

def _mock_infra(monkeypatch: pytest.MonkeyPatch) -> None:
    """Patch all three infrastructure connectors so tests run offline."""
    monkeypatch.setattr(PostgresDatabase, "connect", lambda self: None)
    monkeypatch.setattr(
        PostgresDatabase, "health_check", AsyncMock(return_value=(True, "PostgreSQL is reachable"))
    )
    monkeypatch.setattr(RedisCache, "connect", AsyncMock(return_value=None))
    monkeypatch.setattr(RedisCache, "close", AsyncMock(return_value=None))
    monkeypatch.setattr(
        RedisCache, "health_check", AsyncMock(return_value=(True, "Redis is reachable"))
    )
    monkeypatch.setattr(ChromaDatabase, "connect", AsyncMock(return_value=None))
    monkeypatch.setattr(ChromaDatabase, "close", AsyncMock(return_value=None))
    monkeypatch.setattr(
        ChromaDatabase, "health_check", AsyncMock(return_value=(True, "ChromaDB is reachable"))
    )


# ===========================================================================
# SQLite in-memory fixtures
# ===========================================================================

@pytest.fixture(scope="function")
def sqlite_engine():
    """Create a fresh in-memory SQLite engine for each test."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(sqlite_engine) -> Generator[Session, None, None]:
    """Yield a single SQLAlchemy session backed by the in-memory SQLite engine."""
    SessionLocal = sessionmaker(bind=sqlite_engine, autoflush=False, autocommit=False)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="function")
def session_factory(sqlite_engine):
    """Return a sessionmaker bound to the SQLite engine."""
    return sessionmaker(bind=sqlite_engine, autoflush=False, autocommit=False)


# ===========================================================================
# FastAPI test client with full infra mocked
# ===========================================================================

@pytest.fixture(scope="function")
def api_client(monkeypatch: pytest.MonkeyPatch, session_factory) -> Generator[TestClient, None, None]:
    """
    Return a TestClient with:
    - All infrastructure (Postgres, Redis, ChromaDB) mocked
    - DB session overridden with in-memory SQLite
    """
    _mock_infra(monkeypatch)

    def _override_db():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db_session] = _override_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


# ===========================================================================
# Auth fixtures
# ===========================================================================

@pytest.fixture(scope="session")
def auth_svc() -> AuthService:
    return AuthService()


@pytest.fixture(scope="function")
def admin_token(auth_svc: AuthService) -> str:
    tokens = auth_svc.create_token_pair(
        user_id=str(uuid.uuid4()), email="admin@test.com", role="admin"
    )
    return tokens["access_token"]


@pytest.fixture(scope="function")
def analyst_token(auth_svc: AuthService) -> str:
    tokens = auth_svc.create_token_pair(
        user_id=str(uuid.uuid4()), email="analyst@test.com", role="analyst"
    )
    return tokens["access_token"]


@pytest.fixture(scope="function")
def auth_headers(analyst_token: str) -> dict:
    return {"Authorization": f"Bearer {analyst_token}"}


# ===========================================================================
# Seeded DB fixtures
# ===========================================================================

@pytest.fixture(scope="function")
def seeded_user(db_session: Session) -> User:
    """Insert a test user into the in-memory DB."""
    user = User(
        id=uuid.uuid4(),
        email="tester@example.com",
        hashed_password=hash_password("SecurePass1!"),
        full_name="Test User",
        role="analyst",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture(scope="function")
def seeded_dataset(db_session: Session) -> Dataset:
    """Insert a minimal dataset record."""
    ds = Dataset(
        dataset_id=str(uuid.uuid4()),
        dataset_name="Test Dataset",
        file_name="test.csv",
        file_type="csv",
        file_path="/tmp/test.csv",
        version=1,
        status="uploaded",
    )
    db_session.add(ds)
    db_session.commit()
    db_session.refresh(ds)
    return ds


# ===========================================================================
# DataFrame fixtures
# ===========================================================================

@pytest.fixture(scope="session")
def sales_df() -> pd.DataFrame:
    """A standard sales DataFrame with known statistical properties."""
    np.random.seed(42)
    n = 100
    dates = pd.date_range("2024-01-01", periods=n, freq="D")
    marketing = np.linspace(1000, 5000, n) + np.random.normal(0, 50, n)
    revenue = marketing * 2.5 + np.random.normal(0, 100, n)
    revenue[95] = 25000.0  # outlier
    regions = np.random.choice(["North", "South", "East", "West"], size=n)
    units = np.random.uniform(10, 50, n)
    units[0] = np.nan  # missing values
    units[1] = np.nan
    return pd.DataFrame(
        {
            "order_date": dates,
            "revenue": revenue,
            "marketing_spend": marketing,
            "region": regions,
            "units_sold": units,
        }
    )


@pytest.fixture(scope="session")
def small_df() -> pd.DataFrame:
    """A minimal DataFrame for fast unit tests."""
    return pd.DataFrame(
        {
            "id": [1, 2, 3, 4, 5],
            "value": [10.0, 20.0, 30.0, 40.0, 50.0],
            "category": ["A", "B", "A", "B", "A"],
        }
    )


@pytest.fixture(scope="session")
def csv_bytes() -> bytes:
    return b"col1,col2,col3\n10,20,30\n40,50,60\n70,80,90\n"


@pytest.fixture(scope="session")
def settings() -> Settings:
    """Return a test Settings instance."""
    return Settings(
        environment="test",
        postgres_host="localhost",
        redis_host="localhost",
        chroma_host="localhost",
        debug=True,
    )
