"""Protocol layering and fake MarketDataClient tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

from tests.helpers_binance import make_kline_page, page_bytes
from zorqen_research.application.market_data.client import (
    DEFAULT_KLINES_PAGE_LIMIT,
    MarketDataClient,
)
from zorqen_research.application.market_data.import_service import BinanceImportService
from zorqen_research.application.market_data.pagination import fetch_klines_range
from zorqen_research.application.market_data.ranges import parse_import_range
from zorqen_research.domain.candles import Candle
from zorqen_research.domain.timeframes import Timeframe
from zorqen_research.infrastructure.binance.schemas import parse_kline_page


class FakeMarketDataClient:
    """Application-level fake; no HTTPX dependency."""

    def __init__(self, candles: list[Candle], raw: bytes) -> None:
        self._candles = candles
        self._raw = raw
        self.calls = 0

    def fetch_klines_page(
        self,
        *,
        symbol: str,
        interval: Timeframe,
        start_time: datetime,
        end_time: datetime,
        limit: int,
    ) -> tuple[list[Candle], bytes]:
        self.calls += 1
        in_range = [c for c in self._candles if start_time <= c.open_time < end_time]
        return in_range[:limit], self._raw


def test_application_protocol_module_boundary() -> None:
    import zorqen_research.application.market_data.client as client_mod

    assert client_mod.MarketDataClient is MarketDataClient
    assert client_mod.DEFAULT_KLINES_PAGE_LIMIT == 1000
    assert not hasattr(client_mod, "BinanceFuturesPublicClient")
    assert not hasattr(client_mod, "PRODUCTION_ORIGIN")
    assert MarketDataClient.__module__ == "zorqen_research.application.market_data.client"


def test_infrastructure_client_has_no_duplicate_protocol() -> None:
    import zorqen_research.infrastructure.binance.client as infra_client

    assert "MarketDataClient" not in infra_client.__dict__


def test_import_service_accepts_fake_protocol_client() -> None:
    start = datetime(2026, 6, 1, tzinfo=UTC)
    rows = make_kline_page(start, 2, Timeframe.H1)
    candles = parse_kline_page(rows, timeframe=Timeframe.H1)
    fake: MarketDataClient = FakeMarketDataClient(candles, page_bytes(rows))
    service = BinanceImportService(
        MagicMock(),
        MagicMock(),
        fake,
        page_limit=DEFAULT_KLINES_PAGE_LIMIT,
    )
    assert service._client is fake  # noqa: SLF001


def test_pagination_through_fake_protocol_client() -> None:
    start = datetime(2026, 6, 1, tzinfo=UTC)
    rows = make_kline_page(start, 5, Timeframe.H1)
    candles = parse_kline_page(rows, timeframe=Timeframe.H1)
    fake = FakeMarketDataClient(candles, page_bytes(rows))
    rng = parse_import_range(
        start=start,
        end=start + timedelta(hours=5),
        timeframe=Timeframe.H1,
        now=datetime(2026, 7, 1, tzinfo=UTC),
    )
    result = fetch_klines_range(
        client_fetch=fake.fetch_klines_page,
        symbol="BTCUSDT",
        import_range=rng,
        page_limit=2,
    )
    assert len(result.candles) == 5
    assert fake.calls == 3
