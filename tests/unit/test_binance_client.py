"""Unit tests for Binance HTTP client origin and auth boundaries."""

from __future__ import annotations

import inspect
from datetime import UTC, datetime, timedelta

import httpx
import pytest

from tests.helpers_binance import make_kline_page, page_bytes
from zorqen_research.domain.timeframes import Timeframe
from zorqen_research.infrastructure.binance.client import (
    PRODUCTION_ORIGIN,
    BinanceFuturesPublicClient,
)
from zorqen_research.infrastructure.binance.errors import (
    BinanceRateLimitError,
)


def test_client_has_no_public_base_url_parameter() -> None:
    signature = inspect.signature(BinanceFuturesPublicClient.__init__)
    assert "base_url" not in signature.parameters


def test_client_always_uses_exact_production_origin() -> None:
    client = BinanceFuturesPublicClient(
        transport=httpx.MockTransport(lambda _r: httpx.Response(200, content=b"[]")),
        sleeper=lambda _: None,
    )
    try:
        assert client.origin == "https://fapi.binance.com"
        assert str(client._client.base_url).rstrip("/") == PRODUCTION_ORIGIN  # noqa: SLF001
    finally:
        client.close()


def test_fetch_page_success_and_no_api_key_header() -> None:
    start = datetime(2026, 6, 1, tzinfo=UTC)
    rows = make_kline_page(start, 1, Timeframe.H1)
    raw = page_bytes(rows)

    def handler(request: httpx.Request) -> httpx.Response:
        assert "X-MBX-APIKEY" not in request.headers
        assert "Authorization" not in request.headers
        assert request.url.path == "/fapi/v1/klines"
        assert request.url.scheme == "https"
        assert request.url.host == "fapi.binance.com"
        assert request.url.port is None or request.url.port == 443
        return httpx.Response(200, content=raw)

    transport = httpx.MockTransport(handler)
    sleeps: list[float] = []
    client = BinanceFuturesPublicClient(
        transport=transport,
        sleeper=sleeps.append,
    )
    candles, body = client.fetch_klines_page(
        symbol="BTCUSDT",
        interval=Timeframe.H1,
        start_time=start,
        end_time=start + timedelta(hours=1),
        limit=1000,
    )
    assert len(candles) == 1
    assert body == raw
    assert sleeps == []
    client.close()


def test_retry_429_then_success() -> None:
    start = datetime(2026, 6, 1, tzinfo=UTC)
    rows = make_kline_page(start, 1, Timeframe.H1)
    state = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        state["n"] += 1
        if state["n"] == 1:
            return httpx.Response(429, headers={"Retry-After": "0.01"})
        return httpx.Response(200, content=page_bytes(rows))

    sleeps: list[float] = []
    client = BinanceFuturesPublicClient(
        transport=httpx.MockTransport(handler),
        sleeper=sleeps.append,
        max_attempts=3,
    )
    candles, _ = client.fetch_klines_page(
        symbol="BTCUSDT",
        interval=Timeframe.H1,
        start_time=start,
        end_time=start + timedelta(hours=1),
        limit=1000,
    )
    assert len(candles) == 1
    assert sleeps == [0.01]
    client.close()


def test_418_is_terminal() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(418)

    client = BinanceFuturesPublicClient(
        transport=httpx.MockTransport(handler),
        sleeper=lambda _: None,
        max_attempts=3,
    )
    with pytest.raises(BinanceRateLimitError) as exc:
        client.fetch_klines_page(
            symbol="BTCUSDT",
            interval=Timeframe.H1,
            start_time=datetime(2026, 6, 1, tzinfo=UTC),
            end_time=datetime(2026, 6, 1, 1, tzinfo=UTC),
            limit=1000,
        )
    assert exc.value.terminal is True
    client.close()


def test_no_binance_local_wildcard_in_client_module() -> None:
    import zorqen_research.infrastructure.binance.client as client_mod

    assert not hasattr(client_mod, "ALLOWED_HOSTS")
    assert ".binance.local" not in inspect.getsource(client_mod)
    assert "MarketDataClient" not in client_mod.__dict__
