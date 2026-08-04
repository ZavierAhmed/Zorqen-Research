"""No-lookahead context alignment tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from zorqen_research.application.market_data.alignment import (
    align_execution_to_context,
    align_execution_to_contexts,
)
from zorqen_research.application.market_data.goldens import build_source_series
from zorqen_research.domain.market_data.alignment import (
    CountingSequence,
    align_with_counting_context,
    context_available_at_decision,
)
from zorqen_research.domain.market_data.errors import AlignmentValidationError
from zorqen_research.domain.symbols import Symbol
from zorqen_research.domain.timeframes import Timeframe

SYM = Symbol(value="BTCUSDT")
START = datetime(2024, 1, 1, tzinfo=UTC)


def test_availability_around_exact_close() -> None:
    execution = build_source_series(start=START, timeframe=Timeframe.H1, count=4)
    context = build_source_series(start=START, timeframe=Timeframe.H4, count=1)
    alignment = align_execution_to_context(
        symbol=SYM,
        execution_timeframe=Timeframe.H1,
        context_timeframe=Timeframe.H4,
        execution_candles=execution,
        context_candles=context,
    )
    assert alignment.mapping == (None, None, None, 0)
    ctx_close = context[0].close_time
    assert context_available_at_decision(
        context_close_time=ctx_close, execution_close_time=execution[3].close_time
    )
    assert not context_available_at_decision(
        context_close_time=ctx_close,
        execution_close_time=ctx_close - timedelta(milliseconds=1),
    )


def test_symbol_same_tf_finer_duplicate_unsorted() -> None:
    execution = build_source_series(start=START, timeframe=Timeframe.H1, count=4)
    context = build_source_series(start=START, timeframe=Timeframe.H4, count=1)
    with pytest.raises(AlignmentValidationError):
        align_execution_to_context(
            symbol=SYM,
            execution_timeframe=Timeframe.H1,
            context_timeframe=Timeframe.H1,
            execution_candles=execution,
            context_candles=execution,
        )
    with pytest.raises(AlignmentValidationError):
        align_execution_to_context(
            symbol=SYM,
            execution_timeframe=Timeframe.H4,
            context_timeframe=Timeframe.H1,
            execution_candles=context,
            context_candles=execution,
        )
    with pytest.raises(AlignmentValidationError, match="ordered"):
        align_execution_to_contexts(
            symbol=SYM,
            execution_timeframe=Timeframe.H1,
            execution_candles=build_source_series(start=START, timeframe=Timeframe.H1, count=24),
            context_series=(
                (Timeframe.D1, build_source_series(start=START, timeframe=Timeframe.D1, count=1)),
                (Timeframe.H4, build_source_series(start=START, timeframe=Timeframe.H4, count=6)),
            ),
        )
    with pytest.raises(AlignmentValidationError, match="duplicate"):
        align_execution_to_contexts(
            symbol=SYM,
            execution_timeframe=Timeframe.H1,
            execution_candles=build_source_series(start=START, timeframe=Timeframe.H1, count=24),
            context_series=(
                (Timeframe.H4, build_source_series(start=START, timeframe=Timeframe.H4, count=6)),
                (Timeframe.H4, build_source_series(start=START, timeframe=Timeframe.H4, count=6)),
            ),
        )
    from zorqen_research.domain.market_data.alignment import MultiContextAlignment

    good = align_execution_to_context(
        symbol=SYM,
        execution_timeframe=Timeframe.H1,
        context_timeframe=Timeframe.H4,
        execution_candles=execution,
        context_candles=context,
    )
    foreign = align_execution_to_context(
        symbol=Symbol(value="ETHUSDT"),
        execution_timeframe=Timeframe.H1,
        context_timeframe=Timeframe.H4,
        execution_candles=execution,
        context_candles=context,
    )
    with pytest.raises(AlignmentValidationError, match="symbol"):
        MultiContextAlignment.from_alignments((good, foreign))


def test_mapping_monotonic_and_linear() -> None:
    execution = build_source_series(start=START, timeframe=Timeframe.H1, count=24)
    context = build_source_series(start=START, timeframe=Timeframe.H4, count=6)
    alignment = align_execution_to_context(
        symbol=SYM,
        execution_timeframe=Timeframe.H1,
        context_timeframe=Timeframe.H4,
        execution_candles=execution,
        context_candles=context,
    )
    last = -1
    for value in alignment.mapping:
        if value is not None:
            assert value >= last
            last = value
    counted, reads = align_with_counting_context(
        symbol=SYM,
        execution_timeframe=Timeframe.H1,
        context_timeframe=Timeframe.H4,
        execution_candles=execution,
        context_candles=CountingSequence(context),
    )
    assert counted.mapping == alignment.mapping
    assert reads <= len(execution) + len(context)


def test_alignment_hash_sensitivity() -> None:
    execution = build_source_series(start=START, timeframe=Timeframe.H1, count=24)
    c4 = build_source_series(start=START, timeframe=Timeframe.H4, count=6)
    c1d = build_source_series(start=START, timeframe=Timeframe.D1, count=1)
    multi = align_execution_to_contexts(
        symbol=SYM,
        execution_timeframe=Timeframe.H1,
        execution_candles=execution,
        context_series=((Timeframe.H4, c4), (Timeframe.D1, c1d)),
    )
    multi2 = align_execution_to_contexts(
        symbol=SYM,
        execution_timeframe=Timeframe.H1,
        execution_candles=execution,
        context_series=((Timeframe.H4, c4), (Timeframe.D1, c1d)),
    )
    assert multi.alignment_hash == multi2.alignment_hash
    from decimal import Decimal

    tweaked_exec = build_source_series(
        start=START,
        timeframe=Timeframe.H1,
        count=24,
        open_base=Decimal("101"),
    )
    multi3 = align_execution_to_contexts(
        symbol=SYM,
        execution_timeframe=Timeframe.H1,
        execution_candles=tweaked_exec,
        context_series=((Timeframe.H4, c4), (Timeframe.D1, c1d)),
    )
    assert multi3.alignment_hash != multi.alignment_hash
