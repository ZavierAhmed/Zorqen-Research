"""Unit tests for application settings."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from zorqen_research.core.config import Settings, clear_settings_cache, get_settings


def test_settings_load_expected_environment_values(
    test_env: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(".")
    clear_settings_cache()
    settings = get_settings()
    assert settings.environment == "test"
    assert settings.log_level == "WARNING"
    assert settings.api_host == "127.0.0.1"
    assert settings.api_port == 8000
    assert settings.database_url == test_env["ZORQEN_DATABASE_URL"]
    assert settings.database_url_sync == test_env["ZORQEN_DATABASE_URL_SYNC"]
    assert settings.worker_idle_interval_seconds == 0.1
    assert settings.artifact_root.name == "artifacts-test"
    assert settings.artifact_root_resolved.is_absolute()


def test_invalid_async_database_url_fails_clearly(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ZORQEN_DATABASE_URL", "postgresql://bad")
    monkeypatch.setenv(
        "ZORQEN_DATABASE_URL_SYNC",
        "postgresql+psycopg://zorqen:zorqen@127.0.0.1:5432/zorqen_research",
    )
    with pytest.raises(ValidationError) as exc_info:
        Settings()
    assert "postgresql+asyncpg://" in str(exc_info.value)


def test_invalid_sync_database_url_fails_clearly(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "ZORQEN_DATABASE_URL",
        "postgresql+asyncpg://zorqen:zorqen@127.0.0.1:5432/zorqen_research",
    )
    monkeypatch.setenv("ZORQEN_DATABASE_URL_SYNC", "sqlite:///tmp.db")
    with pytest.raises(ValidationError) as exc_info:
        Settings()
    assert "postgresql+psycopg://" in str(exc_info.value)


def test_empty_artifact_root_fails_clearly(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(
        "ZORQEN_DATABASE_URL",
        "postgresql+asyncpg://zorqen:zorqen@127.0.0.1:5432/zorqen_research",
    )
    monkeypatch.setenv(
        "ZORQEN_DATABASE_URL_SYNC",
        "postgresql+psycopg://zorqen:zorqen@127.0.0.1:5432/zorqen_research",
    )
    monkeypatch.setenv("ZORQEN_ARTIFACT_ROOT", "   ")
    with pytest.raises(ValidationError):
        Settings()
