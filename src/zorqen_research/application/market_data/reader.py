"""Application-owned verified candle partition reader contract."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from zorqen_research.domain.candles import Candle
from zorqen_research.domain.symbols import Symbol
from zorqen_research.domain.timeframes import Timeframe


@dataclass(frozen=True, slots=True)
class VerifiedCandlePartition:
    """Immutable verified candle partition read model."""

    candles: tuple[Candle, ...]
    artifact_key: str
    sha256: str
    byte_size: int
    row_count: int
    minimum_open_time: datetime
    maximum_open_time: datetime
    symbol: Symbol
    timeframe: Timeframe
    canonical_schema_version: str


class CandlePartitionReader(Protocol):
    """Verify and read a content-addressed canonical candle partition."""

    def read_verified(
        self,
        *,
        artifact_key: str,
        expected_sha256: str,
        expected_byte_size: int,
        symbol: Symbol,
        timeframe: Timeframe,
        expected_row_count: int,
        expected_minimum_open_time: datetime | None,
        expected_maximum_open_time: datetime | None,
    ) -> VerifiedCandlePartition:
        """Return verified candles or raise a sanitized integrity error."""
