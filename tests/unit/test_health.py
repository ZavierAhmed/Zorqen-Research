"""Unit tests for health endpoints (no live PostgreSQL required)."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from zorqen_research.api.app import create_app
from zorqen_research.api.dependencies import get_engine
from zorqen_research.core.config import Settings


@pytest.fixture
def settings(test_env: dict[str, str]) -> Settings:
    return Settings()


def _build_app(settings: Settings, engine: Any) -> Any:
    """Create an app with the database engine dependency overridden."""
    app = create_app(settings)
    app.dependency_overrides[get_engine] = lambda: engine
    return app


@pytest.mark.asyncio
async def test_liveness_returns_200_without_database(settings: Settings) -> None:
    engine = MagicMock()
    app = _build_app(settings, engine)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/health/live")

    assert response.status_code == 200
    payload = response.json()
    assert payload["service"] == "zorqen-research-api"
    assert payload["status"] == "healthy"
    engine.connect.assert_not_called()


@pytest.mark.asyncio
async def test_readiness_returns_200_when_database_ok(
    settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = MagicMock()
    app = _build_app(settings, engine)

    async def _ok(_engine: Any) -> bool:
        return True

    monkeypatch.setattr(
        "zorqen_research.api.routes.health.check_database_ready",
        _ok,
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/health/ready")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ready"
    assert payload["components"]["database"]["status"] == "healthy"


@pytest.mark.asyncio
async def test_readiness_returns_503_when_database_fails(
    settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = MagicMock()
    app = _build_app(settings, engine)

    async def _fail(_engine: Any) -> bool:
        return False

    monkeypatch.setattr(
        "zorqen_research.api.routes.health.check_database_ready",
        _fail,
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/health/ready")

    assert response.status_code == 503
    payload = response.json()
    assert payload["status"] == "not_ready"
    assert payload["components"]["database"]["status"] == "unhealthy"


@pytest.mark.asyncio
async def test_readiness_errors_are_sanitized(
    settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Failures must not expose connection strings, credentials, or stack traces."""
    engine = MagicMock()
    app = _build_app(settings, engine)

    secret_url = settings.database_url

    async def _safe_false(_engine: Any) -> bool:
        _ = secret_url
        return False

    monkeypatch.setattr(
        "zorqen_research.api.routes.health.check_database_ready",
        _safe_false,
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/health/ready")

    body = response.text
    assert response.status_code == 503
    assert "password" not in body.lower()
    assert "zorqen:zorqen" not in body
    assert "Traceback" not in body
    assert "RuntimeError" not in body
    assert secret_url not in body


@pytest.mark.asyncio
async def test_root_metadata(settings: Settings) -> None:
    engine = MagicMock()
    app = _build_app(settings, engine)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/")

    assert response.status_code == 200
    payload = response.json()
    assert payload["service"] == "zorqen-research-api"
    assert "Trading execution is outside" in payload["message"]
