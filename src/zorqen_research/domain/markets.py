"""Canonical market / exchange identifiers (no connectivity)."""

from __future__ import annotations

from enum import StrEnum


class Market(StrEnum):
    """Supported research markets."""

    BINANCE_FUTURES = "binance_futures"


def parse_market(value: str) -> Market:
    """Parse and validate a market identifier."""
    normalized = value.strip()
    try:
        return Market(normalized)
    except ValueError as exc:
        msg = f"Unsupported market: {value!r}"
        raise ValueError(msg) from exc
