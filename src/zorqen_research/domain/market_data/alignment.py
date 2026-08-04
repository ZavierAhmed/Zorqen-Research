"""No-lookahead execution/context candle alignment."""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from zorqen_research.domain.artifacts import sha256_hex
from zorqen_research.domain.candles import Candle
from zorqen_research.domain.market_data.derivation import derive_timeframe_plan
from zorqen_research.domain.market_data.errors import (
    AlignmentValidationError,
    ResamplingValidationError,
)
from zorqen_research.domain.symbols import Symbol
from zorqen_research.domain.timeframes import (
    Timeframe,
    duration_milliseconds,
    is_aligned,
    timeframe_duration,
)


def _require_derivable_pair(execution: Timeframe, context: Timeframe) -> None:
    try:
        derive_timeframe_plan(execution, context)
    except ResamplingValidationError as exc:
        raise AlignmentValidationError(str(exc)) from exc


def _require_gap_free_series(
    candles: object,
    *,
    timeframe: Timeframe,
    label: str,
) -> tuple[Candle, ...]:
    if not isinstance(candles, tuple):
        msg = f"{label} candles must be an immutable tuple"
        raise AlignmentValidationError(msg)
    if not candles:
        msg = f"{label} candles must be non-empty"
        raise AlignmentValidationError(msg)
    duration = timeframe_duration(timeframe)
    previous: datetime | None = None
    for index, candle in enumerate(candles):
        if not isinstance(candle, Candle):
            msg = f"{label} candles[{index}] must be a Candle"
            raise AlignmentValidationError(msg)
        if not is_aligned(candle.open_time, timeframe):
            msg = f"{label} candles[{index}] open_time is misaligned"
            raise AlignmentValidationError(msg)
        expected_close = candle.open_time + duration - timedelta(milliseconds=1)
        if candle.close_time != expected_close:
            msg = f"{label} candles[{index}] close_time is invalid"
            raise AlignmentValidationError(msg)
        if previous is not None and candle.open_time != previous + duration:
            msg = f"{label} candles[{index}] is gapped or out of order"
            raise AlignmentValidationError(msg)
        previous = candle.open_time
    return candles


@dataclass(frozen=True, slots=True)
class ContextAlignment:
    """Index map from execution bars to the latest fully closed context bar."""

    symbol: Symbol
    execution_timeframe: Timeframe
    context_timeframe: Timeframe
    execution_candle_sha256: str
    context_candle_sha256: str
    mapping: tuple[int | None, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.symbol, Symbol):
            msg = "symbol must be a Symbol"
            raise AlignmentValidationError(msg)
        _require_derivable_pair(self.execution_timeframe, self.context_timeframe)
        if not isinstance(self.mapping, tuple):
            msg = "mapping must be an immutable tuple"
            raise AlignmentValidationError(msg)
        previous = -1
        for index, value in enumerate(self.mapping):
            if value is None:
                continue
            if type(value) is not int or isinstance(value, bool) or value < 0:
                msg = f"mapping[{index}] must be None or a non-negative int"
                raise AlignmentValidationError(msg)
            if value < previous:
                msg = "context mapping indexes must be monotonically non-decreasing"
                raise AlignmentValidationError(msg)
            previous = value


@dataclass(frozen=True, slots=True)
class MultiContextAlignment:
    """Ordered unique context alignments for one execution series."""

    symbol: Symbol
    execution_timeframe: Timeframe
    execution_candle_sha256: str
    alignments: tuple[ContextAlignment, ...]
    alignment_hash: str = field(init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.alignments, tuple) or not self.alignments:
            msg = "alignments must be a non-empty tuple"
            raise AlignmentValidationError(msg)
        seen: set[Timeframe] = set()
        durations: list[int] = []
        for alignment in self.alignments:
            if not isinstance(alignment, ContextAlignment):
                msg = "alignments must contain ContextAlignment values"
                raise AlignmentValidationError(msg)
            if alignment.symbol != self.symbol:
                msg = "alignment symbol mismatch"
                raise AlignmentValidationError(msg)
            if alignment.execution_timeframe != self.execution_timeframe:
                msg = "alignment execution timeframe mismatch"
                raise AlignmentValidationError(msg)
            if alignment.execution_candle_sha256 != self.execution_candle_sha256:
                msg = "alignment execution candle hash mismatch"
                raise AlignmentValidationError(msg)
            if alignment.context_timeframe in seen:
                msg = "duplicate context timeframe"
                raise AlignmentValidationError(msg)
            if alignment.context_timeframe is self.execution_timeframe:
                msg = "execution timeframe cannot appear as context"
                raise AlignmentValidationError(msg)
            seen.add(alignment.context_timeframe)
            durations.append(duration_milliseconds(timeframe_duration(alignment.context_timeframe)))
        if durations != sorted(durations):
            msg = "context timeframes must be ordered from smallest to largest duration"
            raise AlignmentValidationError(msg)
        digest = sha256_hex(_alignment_hash_payload(self).encode("utf-8"))
        object.__setattr__(self, "alignment_hash", digest)


def _alignment_hash_payload(multi: MultiContextAlignment) -> str:
    document = {
        "context_hashes": [a.context_candle_sha256 for a in multi.alignments],
        "context_timeframes": [a.context_timeframe.value for a in multi.alignments],
        "execution_candle_sha256": multi.execution_candle_sha256,
        "execution_timeframe": multi.execution_timeframe.value,
        "mappings": [list(a.mapping) for a in multi.alignments],
        "schema_version": "1",
        "symbol": multi.symbol.value,
    }
    return json.dumps(document, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def align_context_to_execution(
    *,
    symbol: Symbol,
    execution_timeframe: Timeframe,
    context_timeframe: Timeframe,
    execution_candles: tuple[Candle, ...],
    context_candles: tuple[Candle, ...],
    execution_candle_sha256: str,
    context_candle_sha256: str,
) -> ContextAlignment:
    """
    Map each execution candle to the latest context candle with close_time <= execution close.

    Runs in linear time with a monotonic context pointer.
    """
    if not isinstance(symbol, Symbol):
        msg = "symbol must be a Symbol"
        raise AlignmentValidationError(msg)
    _require_derivable_pair(execution_timeframe, context_timeframe)
    execution = _require_gap_free_series(
        execution_candles, timeframe=execution_timeframe, label="execution"
    )
    context = _require_gap_free_series(
        context_candles, timeframe=context_timeframe, label="context"
    )

    mapping: list[int | None] = []
    context_index = -1
    for execution_candle in execution:
        decision_close = execution_candle.close_time
        while (
            context_index + 1 < len(context)
            and context[context_index + 1].close_time <= decision_close
        ):
            context_index += 1
        mapping.append(None if context_index < 0 else context_index)

    return ContextAlignment(
        symbol=symbol,
        execution_timeframe=execution_timeframe,
        context_timeframe=context_timeframe,
        execution_candle_sha256=execution_candle_sha256,
        context_candle_sha256=context_candle_sha256,
        mapping=tuple(mapping),
    )


def align_multi_context(
    *,
    symbol: Symbol,
    execution_timeframe: Timeframe,
    execution_candles: tuple[Candle, ...],
    execution_candle_sha256: str,
    contexts: Sequence[tuple[Timeframe, tuple[Candle, ...], str]],
) -> MultiContextAlignment:
    """
    Align multiple context series.

    ``contexts`` entries are ``(timeframe, candles, candle_sha256)`` and must already
    be ordered by increasing duration with unique timeframes.
    """
    if not contexts:
        msg = "at least one context series is required"
        raise AlignmentValidationError(msg)
    alignments: list[ContextAlignment] = []
    for context_timeframe, context_candles, context_hash in contexts:
        alignments.append(
            align_context_to_execution(
                symbol=symbol,
                execution_timeframe=execution_timeframe,
                context_timeframe=context_timeframe,
                execution_candles=execution_candles,
                context_candles=context_candles,
                execution_candle_sha256=execution_candle_sha256,
                context_candle_sha256=context_hash,
            )
        )
    return MultiContextAlignment(
        symbol=symbol,
        execution_timeframe=execution_timeframe,
        execution_candle_sha256=execution_candle_sha256,
        alignments=tuple(alignments),
    )


def context_available_at_decision(
    *,
    context_close_time: datetime,
    execution_close_time: datetime,
) -> bool:
    """True iff the context candle is fully closed by the execution decision close."""
    return context_close_time <= execution_close_time


class CountingSequence:
    """Test helper: wraps a random-access sequence and counts element reads."""

    def __init__(self, items: Sequence[Candle]) -> None:
        self._items = list(items)
        self.index_reads = 0

    def __len__(self) -> int:
        return len(self._items)

    def __getitem__(self, index: int) -> Candle:
        self.index_reads += 1
        return self._items[index]


def align_with_counting_context(
    *,
    symbol: Symbol,
    execution_timeframe: Timeframe,
    context_timeframe: Timeframe,
    execution_candles: tuple[Candle, ...],
    context_candles: CountingSequence,
    execution_candle_sha256: str,
    context_candle_sha256: str,
) -> tuple[ContextAlignment, int]:
    """Alignment against an instrumented context sequence; returns (result, index_reads)."""
    _require_derivable_pair(execution_timeframe, context_timeframe)
    execution = _require_gap_free_series(
        execution_candles, timeframe=execution_timeframe, label="execution"
    )
    if len(context_candles) == 0:
        msg = "context candles must be non-empty"
        raise AlignmentValidationError(msg)
    mapping: list[int | None] = []
    context_index = -1
    before = context_candles.index_reads
    for execution_candle in execution:
        decision_close = execution_candle.close_time
        while (
            context_index + 1 < len(context_candles)
            and context_candles[context_index + 1].close_time <= decision_close
        ):
            context_index += 1
        mapping.append(None if context_index < 0 else context_index)
    reads = context_candles.index_reads - before
    alignment = ContextAlignment(
        symbol=symbol,
        execution_timeframe=execution_timeframe,
        context_timeframe=context_timeframe,
        execution_candle_sha256=execution_candle_sha256,
        context_candle_sha256=context_candle_sha256,
        mapping=tuple(mapping),
    )
    return alignment, reads


# Silence unused UTC import if only used indirectly — keep for callers.
_ = UTC
