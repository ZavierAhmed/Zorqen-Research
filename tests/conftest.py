"""Shared test fixtures."""

from __future__ import annotations

import os

import pytest


@pytest.fixture(autouse=True)
def _clear_settings_cache() -> None:
    """Ensure settings are not cached across tests."""
    from zorqen_research.core.config import clear_settings_cache

    clear_settings_cache()
    yield
    clear_settings_cache()


@pytest.fixture
def test_env(monkeypatch: pytest.MonkeyPatch) -> dict[str, str]:
    """Provide an explicit test configuration via environment variables."""
    values = {
        "ZORQEN_ENVIRONMENT": "test",
        "ZORQEN_LOG_LEVEL": "WARNING",
        "ZORQEN_API_HOST": "127.0.0.1",
        "ZORQEN_API_PORT": "8000",
        "ZORQEN_DATABASE_URL": (
            "postgresql+asyncpg://zorqen:zorqen@127.0.0.1:5432/zorqen_research_test"
        ),
        "ZORQEN_DATABASE_URL_SYNC": (
            "postgresql+psycopg://zorqen:zorqen@127.0.0.1:5432/zorqen_research_test"
        ),
        "ZORQEN_WORKER_IDLE_INTERVAL_SECONDS": "0.1",
        "ZORQEN_ARTIFACT_ROOT": "artifacts-test",
    }
    for key, value in values.items():
        monkeypatch.setenv(key, value)
    # Prevent accidental loading of a developer .env for critical settings
    monkeypatch.delenv("ZORQEN_DATABASE_URL", raising=False)
    monkeypatch.setenv("ZORQEN_DATABASE_URL", values["ZORQEN_DATABASE_URL"])
    from zorqen_research.core.config import clear_settings_cache

    clear_settings_cache()
    return values


@pytest.fixture
def postgres_url() -> str:
    """Return the async PostgreSQL URL for integration tests."""
    return os.environ.get(
        "ZORQEN_DATABASE_URL",
        "postgresql+asyncpg://zorqen:zorqen@127.0.0.1:5432/zorqen_research",
    )


@pytest.fixture
def postgres_url_sync() -> str:
    """Return the sync PostgreSQL URL for Alembic integration tests."""
    return os.environ.get(
        "ZORQEN_DATABASE_URL_SYNC",
        "postgresql+psycopg://zorqen:zorqen@127.0.0.1:5432/zorqen_research",
    )
