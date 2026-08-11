from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    app_name: str = "Enterprise AI Data Analyst OS"
    app_version: str = "0.1.0"
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/ai_analyst"
    upload_dir: Path = PROJECT_ROOT / "datasets" / "raw"
    max_upload_size_mb: int = 100
    allowed_extensions: str = "csv,xlsx,xls,json,parquet"

    model_config = SettingsConfigDict(env_file=PROJECT_ROOT / ".env", extra="ignore")

    @property
    def allowed_extension_set(self) -> set[str]:
        return {f".{item.strip().lower().lstrip('.') }" for item in self.allowed_extensions.split(",") if item.strip()}


settings = Settings()
settings.upload_dir.mkdir(parents=True, exist_ok=True)
