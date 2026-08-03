"""Binance public market-data client errors."""

from __future__ import annotations


class BinanceClientError(RuntimeError):
    """Sanitized Binance client failure."""


class BinanceRateLimitError(BinanceClientError):
    """Terminal or retryable rate-limit response."""

    def __init__(
        self, message: str, *, retry_after: float | None = None, terminal: bool = False
    ) -> None:
        super().__init__(message)
        self.retry_after = retry_after
        self.terminal = terminal


class BinanceResponseError(BinanceClientError):
    """Malformed or invalid Binance response content."""
