"""Application-facing market-data client protocol."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from zorqen_research.domain.candles import Candle
from zorqen_research.domain.timeframes import Timeframe

# Owned by the application layer (not imported from infrastructure).
DEFAULT_KLINES_PAGE_LIMIT = 1000


class MarketDataClient(Protocol):
    """Public market-data client contract (no authentication)."""

    def fetch_klines_page(
        self,
        *,
        symbol: str,
        interval: Timeframe,
        start_time: datetime,
        end_time: datetime,
        limit: int,
    ) -> tuple[list[Candle], bytes]:
        """Return parsed candles and the exact successful response bytes."""
