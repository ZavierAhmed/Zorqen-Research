"""Unit tests for strategy-family HTTP routes (mocked services)."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from zorqen_research.api.app import create_app
from zorqen_research.api.dependencies import get_engine
from zorqen_research.api.routes import strategy_families as strategy_families_routes
from zorqen_research.application.strategy_families.service import (
    StrategyFamilyNotFoundError,
)
from zorqen_research.core.config import Settings
from zorqen_research.domain.strategy_families import (
    ADAPTIVE_MTF_TREND_BREAKOUT_ID,
    SUPPORT_RESISTANCE_ID,
    ResearchPriority,
    StrategyFamily,
    StrategyFamilyStatus,
)


@pytest.fixture
def settings(test_env: dict[str, str]) -> Settings:
    return Settings()


def _build_app(settings: Settings) -> Any:
    app = create_app(settings)
    app.dependency_overrides[get_engine] = lambda: MagicMock()
    return app


def _sample_families() -> list[StrategyFamily]:
    return [
        StrategyFamily(
            id=ADAPTIVE_MTF_TREND_BREAKOUT_ID,
            code="adaptive_mtf_trend_breakout",
            display_name="Adaptive Multi-Timeframe Trend Breakout",
            description="primary metadata",
            research_priority=ResearchPriority.PRIMARY,
            status=StrategyFamilyStatus.ACTIVE,
        ),
        StrategyFamily(
            id=SUPPORT_RESISTANCE_ID,
            code="support_resistance",
            display_name="Support and Resistance",
            description="secondary metadata",
            research_priority=ResearchPriority.SECONDARY,
            status=StrategyFamilyStatus.ACTIVE,
        ),
    ]


@pytest.mark.asyncio
async def test_list_strategy_families_schema(
    settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _build_app(settings)
    service = MagicMock()
    service.list_active = AsyncMock(return_value=_sample_families())
    monkeypatch.setattr(
        strategy_families_routes,
        "get_strategy_family_service",
        lambda: service,
    )
    app.dependency_overrides[strategy_families_routes.get_strategy_family_service] = lambda: service

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/strategy-families")

    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 2
    assert payload["items"][0]["code"] == "adaptive_mtf_trend_breakout"
    assert payload["items"][0]["id"] == str(ADAPTIVE_MTF_TREND_BREAKOUT_ID)
    assert "sa_state" not in response.text
    assert "StrategyFamilyModel" not in response.text


@pytest.mark.asyncio
async def test_get_strategy_family_not_found_is_sanitized(
    settings: Settings,
) -> None:
    app = _build_app(settings)
    service = MagicMock()
    service.get_active_by_code = AsyncMock(side_effect=StrategyFamilyNotFoundError("missing"))
    app.dependency_overrides[strategy_families_routes.get_strategy_family_service] = lambda: service

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/strategy-families/missing")

    assert response.status_code == 404
    assert response.json()["detail"] == "Strategy family not found."
    assert "Traceback" not in response.text
    assert "password" not in response.text.lower()


@pytest.mark.asyncio
async def test_no_mutation_routes_for_strategy_families(settings: Settings) -> None:
    app = _build_app(settings)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        assert (await client.post("/api/v1/strategy-families", json={"code": "x"})).status_code in {
            405,
            404,
            422,
        }
        assert (await client.put("/api/v1/strategy-families", json={"code": "x"})).status_code in {
            405,
            404,
            422,
        }
        assert (
            await client.patch("/api/v1/strategy-families", json={"code": "x"})
        ).status_code in {405, 404, 422}
        assert (await client.delete("/api/v1/strategy-families")).status_code in {
            405,
            404,
            422,
        }
