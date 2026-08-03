"""Unit tests for market, symbol, and timeframe value objects."""

from __future__ import annotations

from datetime import timedelta

import pytest

from zorqen_research.domain.markets import Market, parse_market
from zorqen_research.domain.symbols import ALLOWED_SYMBOLS, parse_symbol
from zorqen_research.domain.timeframes import Timeframe, parse_timeframe, timeframe_duration


def test_parse_market_accepts_binance_futures() -> None:
    assert parse_market("binance_futures") is Market.BINANCE_FUTURES


def test_parse_market_rejects_unknown() -> None:
    with pytest.raises(ValueError, match="Unsupported market"):
        parse_market("coinbase")


def test_symbols_are_uppercase_and_centralized() -> None:
    assert frozenset({"BTCUSDT", "ETHUSDT", "BNBUSDT"}) == ALLOWED_SYMBOLS
    assert parse_symbol("btcusdt").value == "BTCUSDT"


def test_symbol_rejects_whitespace_and_unknown() -> None:
    with pytest.raises(ValueError, match="whitespace"):
        parse_symbol("BTC USDT")
    with pytest.raises(ValueError, match="Unsupported symbol"):
        parse_symbol("SOLUSDT")


@pytest.mark.parametrize(
    ("value", "duration"),
    [
        ("1m", timedelta(minutes=1)),
        ("1h", timedelta(hours=1)),
        ("1d", timedelta(days=1)),
        ("1w", timedelta(weeks=1)),
    ],
)
def test_timeframe_duration_mapping(value: str, duration: timedelta) -> None:
    spec = parse_timeframe(value)
    assert timeframe_duration(spec) == duration
    assert timeframe_duration(value) == duration


@pytest.mark.parametrize("alias", ["60m", "H1", "1D", "1W", "1H"])
def test_timeframe_rejects_aliases(alias: str) -> None:
    with pytest.raises(ValueError):
        parse_timeframe(alias)


def test_timeframe_enum_values() -> None:
    assert {item.value for item in Timeframe} == {
        "1m",
        "3m",
        "5m",
        "15m",
        "30m",
        "1h",
        "4h",
        "1d",
        "1w",
    }
