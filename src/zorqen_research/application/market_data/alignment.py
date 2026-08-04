"""Application facade for no-lookahead context alignment."""

from __future__ import annotations

from collections.abc import Sequence

from zorqen_research.domain.candles import Candle
from zorqen_research.domain.market_data.alignment import (
    ContextAlignment,
    MultiContextAlignment,
    align_context_to_execution,
    align_multi_context,
)
from zorqen_research.domain.market_data.hashes import hash_candle_tuple
from zorqen_research.domain.symbols import Symbol
from zorqen_research.domain.timeframes import Timeframe


def hash_candles(candles: tuple[Candle, ...]) -> str:
    return hash_candle_tuple(candles)


def align_execution_to_context(
    *,
    symbol: Symbol,
    execution_timeframe: Timeframe,
    context_timeframe: Timeframe,
    execution_candles: tuple[Candle, ...],
    context_candles: tuple[Candle, ...],
) -> ContextAlignment:
    return align_context_to_execution(
        symbol=symbol,
        execution_timeframe=execution_timeframe,
        context_timeframe=context_timeframe,
        execution_candles=execution_candles,
        context_candles=context_candles,
    )


def align_execution_to_contexts(
    *,
    symbol: Symbol,
    execution_timeframe: Timeframe,
    execution_candles: tuple[Candle, ...],
    context_series: Sequence[tuple[Timeframe, tuple[Candle, ...]]],
) -> MultiContextAlignment:
    """Align contexts. Caller must supply unique contexts ordered by increasing duration."""
    return align_multi_context(
        symbol=symbol,
        execution_timeframe=execution_timeframe,
        execution_candles=execution_candles,
        contexts=context_series,
    )
