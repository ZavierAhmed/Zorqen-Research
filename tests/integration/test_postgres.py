"""PostgreSQL-backed integration tests."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from tests.helpers import lifespan_client
from zorqen_research.api.app import create_app
from zorqen_research.core.config import Settings, clear_settings_cache
from zorqen_research.infrastructure.database.engine import check_database_ready
from zorqen_research.worker.service import WorkerService

pytestmark = pytest.mark.integration

REPO_ROOT = Path(__file__).resolve().parents[2]


def _require_postgres(async_url: str) -> None:
    """Skip the module if PostgreSQL is not reachable."""
    import asyncio

    async def _probe() -> bool:
        engine = create_async_engine(async_url)
        try:
            return await check_database_ready(engine)
        finally:
            await engine.dispose()

    if not asyncio.run(_probe()):
        pytest.skip("PostgreSQL is not available for integration tests")


@pytest.fixture(scope="module")
def integration_urls() -> tuple[str, str]:
    async_url = os.environ.get(
        "ZORQEN_DATABASE_URL",
        "postgresql+asyncpg://zorqen:zorqen@127.0.0.1:5432/zorqen_research",
    )
    sync_url = os.environ.get(
        "ZORQEN_DATABASE_URL_SYNC",
        "postgresql+psycopg://zorqen:zorqen@127.0.0.1:5432/zorqen_research",
    )
    _require_postgres(async_url)
    return async_url, sync_url


@pytest.fixture
def integration_settings(
    integration_urls: tuple[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> Settings:
    async_url, sync_url = integration_urls
    monkeypatch.setenv("ZORQEN_ENVIRONMENT", "test")
    monkeypatch.setenv("ZORQEN_LOG_LEVEL", "WARNING")
    monkeypatch.setenv("ZORQEN_DATABASE_URL", async_url)
    monkeypatch.setenv("ZORQEN_DATABASE_URL_SYNC", sync_url)
    monkeypatch.setenv("ZORQEN_ARTIFACT_ROOT", "artifacts-test")
    clear_settings_cache()
    return Settings()


@pytest.mark.asyncio
async def test_real_postgres_connection_succeeds(
    integration_settings: Settings,
) -> None:
    engine = create_async_engine(integration_settings.database_url)
    try:
        assert await check_database_ready(engine) is True
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            assert result.scalar_one() == 1
    finally:
        await engine.dispose()


def test_alembic_upgrade_from_empty_database(
    integration_settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ZORQEN_DATABASE_URL_SYNC", integration_settings.database_url_sync)
    monkeypatch.setenv("ZORQEN_DATABASE_URL", integration_settings.database_url)
    clear_settings_cache()

    env = os.environ.copy()
    env["ZORQEN_DATABASE_URL"] = integration_settings.database_url
    env["ZORQEN_DATABASE_URL_SYNC"] = integration_settings.database_url_sync

    # Reset then upgrade to ensure a clean path from empty alembic state.
    subprocess.run(
        [sys.executable, "-m", "alembic", "downgrade", "base"],
        cwd=REPO_ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=REPO_ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0


@pytest.mark.asyncio
async def test_worker_check_succeeds_with_postgres(
    integration_settings: Settings,
) -> None:
    service = WorkerService(integration_settings)
    assert await service.check() == 0


@pytest.mark.asyncio
async def test_api_readiness_healthy_against_postgres(
    integration_settings: Settings,
) -> None:
    app = create_app(integration_settings)
    async with lifespan_client(app) as client:
        live = await client.get("/api/v1/health/live")
        ready = await client.get("/api/v1/health/ready")

    assert live.status_code == 200
    assert ready.status_code == 200
    assert ready.json()["components"]["database"]["status"] == "healthy"
