"""Unit tests for Binance HTTP client retries and auth boundaries."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import httpx
import pytest

from tests.helpers_binance import make_kline_page, page_bytes
from zorqen_research.domain.timeframes import Timeframe
from zorqen_research.infrastructure.binance.client import (
    PRODUCTION_HOST,
    BinanceFuturesPublicClient,
)
from zorqen_research.infrastructure.binance.errors import (
    BinanceClientError,
    BinanceRateLimitError,
)


def test_client_rejects_unknown_host_without_transport() -> None:
    with pytest.raises(BinanceClientError, match="allowlisted"):
        BinanceFuturesPublicClient(base_url="https://evil.example.com")


def test_client_rejects_unknown_host_even_with_transport() -> None:
    with pytest.raises(BinanceClientError, match="allowlisted"):
        BinanceFuturesPublicClient(
            base_url="https://evil.example.com",
            transport=httpx.MockTransport(lambda r: httpx.Response(200, content=b"[]")),
        )


def test_fetch_page_success_and_no_api_key_header() -> None:
    start = datetime(2026, 6, 1, tzinfo=UTC)
    rows = make_kline_page(start, 1, Timeframe.H1)
    raw = page_bytes(rows)

    def handler(request: httpx.Request) -> httpx.Response:
        assert "X-MBX-APIKEY" not in request.headers
        assert "Authorization" not in request.headers
        assert request.url.path == "/fapi/v1/klines"
        return httpx.Response(200, content=raw)

    transport = httpx.MockTransport(handler)
    sleeps: list[float] = []
    client = BinanceFuturesPublicClient(
        base_url=PRODUCTION_HOST,
        transport=transport,
        sleeper=sleeps.append,
    )
    candles, body = client.fetch_klines_page(
        symbol="BTCUSDT",
        interval=Timeframe.H1,
        start_time=start,
        end_time=start + timedelta(hours=1),
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
        base_url=PRODUCTION_HOST,
        transport=httpx.MockTransport(handler),
        sleeper=sleeps.append,
        max_attempts=3,
    )
    candles, _ = client.fetch_klines_page(
        symbol="BTCUSDT",
        interval=Timeframe.H1,
        start_time=start,
        end_time=start + timedelta(hours=1),
    )
    assert len(candles) == 1
    assert sleeps == [0.01]
    client.close()


def test_418_is_terminal() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(418)

    client = BinanceFuturesPublicClient(
        base_url=PRODUCTION_HOST,
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
        )
    assert exc.value.terminal is True
    client.close()
