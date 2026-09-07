"""Strongly typed application configuration loaded from environment variables."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    """Runtime settings shared by all infrastructure adapters and services."""

    # ------------------------------------------------------------------
    # Application
    # ------------------------------------------------------------------
    app_name: str = "Enterprise AI Data Analyst OS"
    app_version: str = "1.0.0"
    environment: str = "development"
    debug: bool = False
    log_level: str = "INFO"

    # ------------------------------------------------------------------
    # CORS
    # ------------------------------------------------------------------
    frontend_url: str = "http://localhost:5173"
    backend_url: str = "http://localhost:8000"

    # ------------------------------------------------------------------
    # PostgreSQL
    # ------------------------------------------------------------------
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "ai_analyst"
    postgres_user: str = "postgres"
    postgres_password: SecretStr = SecretStr("postgres")
    database_url: str | None = None
    database_pool_size: int = Field(default=5, ge=1)
    database_max_overflow: int = Field(default=10, ge=0)

    # ------------------------------------------------------------------
    # Redis
    # ------------------------------------------------------------------
    redis_host: str = "redis"
    redis_port: int = 6379
    redis_url: str = "redis://localhost:6379/0"
    default_tenant_id: str = "system"

    # ------------------------------------------------------------------
    # ChromaDB
    # ------------------------------------------------------------------
    chroma_host: str = "localhost"
    chroma_port: int = Field(default=8001, ge=1, le=65535)
    chroma_persist_dir: str = "/chroma"

    # ------------------------------------------------------------------
    # LLM Providers
    # ------------------------------------------------------------------
    groq_api_key: SecretStr | None = None
    gemini_api_key: SecretStr | None = None
    openai_api_key: SecretStr | None = None
    default_llm: str = "llama-3.3-70b-versatile"
    default_embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"

    # ------------------------------------------------------------------
    # HuggingFace
    # ------------------------------------------------------------------
    huggingface_api_key: SecretStr | None = None

    # ------------------------------------------------------------------
    # LangChain / LangSmith
    # ------------------------------------------------------------------
    langchain_tracing_v2: bool = False
    langchain_project: str = "AI-Data-Analyst-OS"
    langsmith_api_key: SecretStr | None = None

    # ------------------------------------------------------------------
    # JWT Authentication
    # ------------------------------------------------------------------
    jwt_secret_key: SecretStr | None = None
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440

    # ------------------------------------------------------------------
    # Financial Data APIs
    # ------------------------------------------------------------------
    alpha_vantage_api_key: str | None = None
    finnhub_api_key: str | None = None

    # ------------------------------------------------------------------
    # News & Sentiment
    # ------------------------------------------------------------------
    news_api_key: str | None = None

    # ------------------------------------------------------------------
    # Forecasting
    # ------------------------------------------------------------------
    forecast_horizon_days: int = 30
    default_time_series_model: str = "prophet"

    # ------------------------------------------------------------------
    # RAG Configuration
    # ------------------------------------------------------------------
    rag_chunk_size: int = 1000
    rag_chunk_overlap: int = 200
    top_k_documents: int = 5
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"

    # ------------------------------------------------------------------
    # SQL Agent
    # ------------------------------------------------------------------
    sql_agent_max_iterations: int = 10
    sql_agent_timeout: int = 60

    # ------------------------------------------------------------------
    # File Uploads
    # ------------------------------------------------------------------
    max_file_size_mb: int = 100
    allowed_file_types: str = "csv,xlsx,xls,json,parquet"
    upload_dir: str = "uploads"

    # ------------------------------------------------------------------
    # Visualization
    # ------------------------------------------------------------------
    default_chart_engine: str = "plotly"

    # ------------------------------------------------------------------
    # Monitoring
    # ------------------------------------------------------------------
    enable_metrics: bool = True
    enable_audit_logs: bool = True

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        extra="ignore",
    )

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, value: str) -> str:
        """Restrict application mode to known deployment environments."""
        normalized = value.lower()
        if normalized == "testing":
            normalized = "test"
        if normalized not in {"development", "test", "staging", "production"}:
            raise ValueError("ENVIRONMENT must be development, test, staging, or production")
        return normalized

    @property
    def postgres_dsn(self) -> str:
        """Return the SQLAlchemy-compatible PostgreSQL connection URL."""
        if self.database_url:
            return self.database_url
        password = self.postgres_password.get_secret_value()
        return (
            "postgresql+psycopg://"
            f"{self.postgres_user}:{password}@{self.postgres_host}:"
            f"{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def allowed_extension_set(self) -> set[str]:
        """Return normalized set of allowed file upload extensions."""
        return {
            f".{ext.strip().lower().lstrip('.')}"
            for ext in self.allowed_file_types.split(",")
            if ext.strip()
        }

    @property
    def upload_path(self) -> Path:
        """Return the resolved upload directory, creating it if needed."""
        path = PROJECT_ROOT / self.upload_dir
        path.mkdir(parents=True, exist_ok=True)
        return path


@lru_cache
def get_settings() -> Settings:
    """Create one immutable settings instance per process."""
    return Settings()
