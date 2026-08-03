"""Unit tests for the worker service."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from zorqen_research.core.config import Settings
from zorqen_research.worker.service import WorkerService


@pytest.mark.asyncio
async def test_check_mode_success(
    settings_fixture: Settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = WorkerService(settings_fixture)
    fake_engine = MagicMock()

    monkeypatch.setattr(
        "zorqen_research.worker.service.create_engine",
        lambda _url: fake_engine,
    )
    monkeypatch.setattr(
        "zorqen_research.worker.service.check_database_ready",
        AsyncMock(return_value=True),
    )
    dispose = AsyncMock()
    monkeypatch.setattr("zorqen_research.worker.service.dispose_engine", dispose)

    code = await service.check()
    assert code == 0
    dispose.assert_awaited_once_with(fake_engine)


@pytest.mark.asyncio
async def test_check_mode_failure(
    settings_fixture: Settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = WorkerService(settings_fixture)
    fake_engine = MagicMock()

    monkeypatch.setattr(
        "zorqen_research.worker.service.create_engine",
        lambda _url: fake_engine,
    )
    monkeypatch.setattr(
        "zorqen_research.worker.service.check_database_ready",
        AsyncMock(return_value=False),
    )
    dispose = AsyncMock()
    monkeypatch.setattr("zorqen_research.worker.service.dispose_engine", dispose)

    code = await service.check()
    assert code == 1
    dispose.assert_awaited_once_with(fake_engine)


@pytest.mark.asyncio
async def test_clean_shutdown(
    settings_fixture: Settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = WorkerService(settings_fixture)
    fake_engine = MagicMock()

    monkeypatch.setattr(
        "zorqen_research.worker.service.create_engine",
        lambda _url: fake_engine,
    )
    monkeypatch.setattr(
        "zorqen_research.worker.service.check_database_ready",
        AsyncMock(return_value=True),
    )
    dispose = AsyncMock()
    monkeypatch.setattr("zorqen_research.worker.service.dispose_engine", dispose)

    async def _run_and_stop() -> None:
        task = asyncio.create_task(service.run())
        await asyncio.sleep(0.05)
        service.request_shutdown()
        await asyncio.wait_for(task, timeout=2.0)

    await _run_and_stop()
    dispose.assert_awaited_once_with(fake_engine)


@pytest.fixture
def settings_fixture(test_env: dict[str, str]) -> Settings:
    return Settings()
