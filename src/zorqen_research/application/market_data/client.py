"""Application-facing market-data client protocol."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from zorqen_research.domain.candles import Candle
from zorqen_research.domain.timeframes import Timeframe
from zorqen_research.infrastructure.binance.client import PAGE_LIMIT


class MarketDataClient(Protocol):
    """Public market-data client (no authentication)."""

    def fetch_klines_page(
        self,
        *,
        symbol: str,
        interval: Timeframe,
        start_time: datetime,
        end_time: datetime,
        limit: int = PAGE_LIMIT,
    ) -> tuple[list[Candle], bytes]:
        """Return parsed candles and the exact successful response bytes."""
