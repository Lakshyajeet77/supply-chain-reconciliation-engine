"""Application configuration loaded from environment variables."""

from decimal import Decimal
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings. Secrets never belong in source control."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "development"
    app_name: str = "Supply-Chain Reconciliation Engine"

    upload_dir: Path = Path("./uploads")
    max_upload_bytes: int = Field(default=10 * 1024 * 1024, ge=1)

    money_decimal_places: int = Field(default=2, ge=0, le=6)
    price_tolerance: Decimal = Decimal("0.00")
    quantity_tolerance: Decimal = Decimal("0.000")


@lru_cache
def get_settings() -> Settings:
    return Settings()
