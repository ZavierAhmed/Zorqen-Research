"""HTTPX Binance USDⓈ-M Futures public klines client."""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import UTC, datetime

import httpx

from zorqen_research.domain.candles import Candle
from zorqen_research.domain.timeframes import Timeframe
from zorqen_research.infrastructure.binance.errors import (
    BinanceClientError,
    BinanceRateLimitError,
    BinanceResponseError,
)
from zorqen_research.infrastructure.binance.schemas import parse_kline_page

logger = logging.getLogger(__name__)

# Fixed production origin. Not configurable via settings or constructor.
PRODUCTION_ORIGIN = "https://fapi.binance.com"
KLINES_PATH = "/fapi/v1/klines"
# Infrastructure-local page-size default for this HTTP client implementation.
_DEFAULT_PAGE_LIMIT = 1000


def _to_ms(value: datetime) -> int:
    return int(value.astimezone(UTC).timestamp() * 1000)


class BinanceFuturesPublicClient:
    """Public REST client for Binance USDⓈ-M Futures klines (no auth)."""

    def __init__(
        self,
        *,
        timeout_seconds: float = 30.0,
        max_attempts: int = 4,
        max_retry_delay_seconds: float = 30.0,
        transport: httpx.BaseTransport | None = None,
        sleeper: Callable[[float], None] | None = None,
    ) -> None:
        self._timeout = timeout_seconds
        self._max_attempts = max(1, max_attempts)
        self._max_retry_delay = max_retry_delay_seconds
        self._sleeper = sleeper or (lambda seconds: __import__("time").sleep(seconds))
        self._client = httpx.Client(
            base_url=PRODUCTION_ORIGIN,
            timeout=timeout_seconds,
            transport=transport,
            headers={"Accept": "application/json", "User-Agent": "zorqen-research/0.4"},
        )

    @property
    def origin(self) -> str:
        """Return the fixed production HTTPS origin."""
        return PRODUCTION_ORIGIN

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> BinanceFuturesPublicClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def fetch_klines_page(
        self,
        *,
        symbol: str,
        interval: Timeframe,
        start_time: datetime,
        end_time: datetime,
        limit: int = _DEFAULT_PAGE_LIMIT,
    ) -> tuple[list[Candle], bytes]:
        params = {
            "symbol": symbol,
            "interval": interval.value,
            "startTime": _to_ms(start_time),
            "endTime": _to_ms(end_time),
            "limit": limit,
        }
        # Ensure no auth headers can be introduced.
        forbidden = {"x-mbx-apikey", "authorization"}
        for key in self._client.headers:
            if key.lower() in forbidden:
                msg = "API-key headers are not permitted"
                raise BinanceClientError(msg)

        attempt = 0
        while attempt < self._max_attempts:
            attempt += 1
            try:
                response = self._client.get(KLINES_PATH, params=params)
            except httpx.TimeoutException as exc:
                if attempt >= self._max_attempts:
                    msg = "Binance request timed out"
                    raise BinanceClientError(msg) from exc
                self._sleeper(min(2**attempt, self._max_retry_delay))
                continue
            except httpx.TransportError as exc:
                if attempt >= self._max_attempts:
                    msg = "Binance transport failure"
                    raise BinanceClientError(msg) from exc
                self._sleeper(min(2**attempt, self._max_retry_delay))
                continue

            if response.status_code == 418:
                msg = "Binance rejected the request (HTTP 418)"
                raise BinanceRateLimitError(msg, terminal=True)
            if response.status_code == 429:
                retry_after_raw = response.headers.get("Retry-After")
                delay = 1.0
                if retry_after_raw:
                    try:
                        delay = float(retry_after_raw)
                    except ValueError:
                        delay = 1.0
                delay = min(max(delay, 0.0), self._max_retry_delay)
                if attempt >= self._max_attempts:
                    msg = "Binance rate limit exceeded"
                    raise BinanceRateLimitError(msg, retry_after=delay, terminal=True)
                self._sleeper(delay)
                continue
            if response.status_code >= 500:
                if attempt >= self._max_attempts:
                    msg = "Binance server error"
                    raise BinanceClientError(msg)
                self._sleeper(min(2**attempt, self._max_retry_delay))
                continue
            if response.status_code != 200:
                msg = f"Binance request failed with HTTP {response.status_code}"
                raise BinanceClientError(msg)

            raw = response.content
            try:
                payload = response.json()
            except ValueError as exc:
                msg = "Binance response is not valid JSON"
                raise BinanceResponseError(msg) from exc
            candles = parse_kline_page(payload, timeframe=interval)
            logger.info(
                "Fetched Binance klines page symbol=%s interval=%s rows=%s",
                symbol,
                interval.value,
                len(candles),
            )
            return candles, raw

        msg = "Binance request failed after retries"
        raise BinanceClientError(msg)
