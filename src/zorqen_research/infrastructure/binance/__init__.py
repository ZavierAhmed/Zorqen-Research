"""Binance infrastructure package."""

from zorqen_research.infrastructure.binance.client import (
    KLINES_PATH,
    PRODUCTION_ORIGIN,
    BinanceFuturesPublicClient,
)
from zorqen_research.infrastructure.binance.errors import (
    BinanceClientError,
    BinanceRateLimitError,
    BinanceResponseError,
)

# Backward-compatible alias used by older docs/tests; value is the fixed origin.
PRODUCTION_HOST = PRODUCTION_ORIGIN

__all__ = [
    "KLINES_PATH",
    "PRODUCTION_HOST",
    "PRODUCTION_ORIGIN",
    "BinanceClientError",
    "BinanceFuturesPublicClient",
    "BinanceRateLimitError",
    "BinanceResponseError",
]
