"""Typed application settings loaded from environment variables."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with the ZORQEN_ environment prefix."""

    model_config = SettingsConfigDict(
        env_prefix="ZORQEN_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: Literal["development", "test", "production"] = "development"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    api_host: str = "127.0.0.1"
    api_port: int = Field(default=8000, ge=1, le=65535)

    database_url: str = Field(
        default="postgresql+asyncpg://zorqen:zorqen@127.0.0.1:5432/zorqen_research",
        min_length=1,
    )
    database_url_sync: str = Field(
        default="postgresql+psycopg://zorqen:zorqen@127.0.0.1:5432/zorqen_research",
        min_length=1,
    )

    worker_idle_interval_seconds: float = Field(default=5.0, gt=0.0)
    artifact_root: Path = Path("artifacts")

    @field_validator("database_url")
    @classmethod
    def validate_async_database_url(cls, value: str) -> str:
        if not value.startswith("postgresql+asyncpg://"):
            msg = "ZORQEN_DATABASE_URL must use the postgresql+asyncpg:// scheme"
            raise ValueError(msg)
        return value

    @field_validator("database_url_sync")
    @classmethod
    def validate_sync_database_url(cls, value: str) -> str:
        if not value.startswith("postgresql+psycopg://"):
            msg = "ZORQEN_DATABASE_URL_SYNC must use the postgresql+psycopg:// scheme"
            raise ValueError(msg)
        return value

    @field_validator("artifact_root", mode="before")
    @classmethod
    def coerce_artifact_root(cls, value: object) -> Path:
        if isinstance(value, Path):
            return value
        if isinstance(value, str) and value.strip():
            return Path(value)
        msg = "ZORQEN_ARTIFACT_ROOT must be a non-empty path"
        raise ValueError(msg)

    @property
    def artifact_root_resolved(self) -> Path:
        """Return the artifact root as an absolute path without drive hardcoding."""
        return self.artifact_root.expanduser().resolve()


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings()


def clear_settings_cache() -> None:
    """Clear the settings cache (useful in tests)."""
    get_settings.cache_clear()
