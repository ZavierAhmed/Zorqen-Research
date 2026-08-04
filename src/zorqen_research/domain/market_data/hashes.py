"""Canonical candle-tuple hashing for resampling and alignment integrity."""

from __future__ import annotations

from collections.abc import Sequence

from zorqen_research.domain.artifacts import sha256_hex
from zorqen_research.domain.candles import Candle


def hash_candle_tuple(candles: Sequence[Candle]) -> str:
    """SHA-256 of canonical candle CSV bytes (single serialization contract)."""
    # Deferred import keeps the CSV serializer owned by application.market_data
    # while domain factories always use that same contract.
    from zorqen_research.application.market_data.serialization import serialize_candles_csv

    return sha256_hex(serialize_candles_csv(candles))
