"""Application configuration loaded from environment variables."""
from decimal import Decimal
from functools import lru_cache
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
PROJECT_ROOT = Path(__file__).resolve().parents[2]
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")
    app_env: str = "development"
    app_name: str = "Supply-Chain Reconciliation Engine"
    log_level: str = "INFO"
    extraction_provider_mode: str = "fixture"
    extraction_fixtures_dir: Path = PROJECT_ROOT / "backend" / "app" / "fixtures" / "extraction"
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-3.8-flash"
    upload_dir: Path = Path("./uploads")
    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173"],
        description="Allowed browser origins for the local dev frontend.",
    )
    max_upload_bytes: int = Field(default=10 * 1024 * 1024, ge=1)
    database_url: str = Field(default="postgresql+psycopg://reconcile:reconcile@localhost:5433/reconcile", description="SQLAlchemy database URL")
    money_decimal_places: int = Field(default=2, ge=0, le=6)
    price_tolerance: Decimal = Decimal("0.00")
    quantity_tolerance: Decimal = Decimal("0.000")
@lru_cache
def get_settings() -> Settings:
    return Settings()
