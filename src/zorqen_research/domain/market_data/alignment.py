"""No-lookahead execution/context candle alignment."""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta

from zorqen_research.domain.artifacts import sha256_hex
from zorqen_research.domain.candles import Candle
from zorqen_research.domain.market_data.derivation import derive_timeframe_plan
from zorqen_research.domain.market_data.errors import (
    AlignmentValidationError,
    ResamplingValidationError,
)
from zorqen_research.domain.market_data.hashes import hash_candle_tuple
from zorqen_research.domain.symbols import Symbol
from zorqen_research.domain.timeframes import (
    Timeframe,
    duration_milliseconds,
    is_aligned,
    timeframe_duration,
)

_SINGLE_ALIGNMENT_SCHEMA = "1"
_MULTI_ALIGNMENT_SCHEMA = "1"


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
        if candle.open_time.tzinfo is None:
            msg = f"{label} candles[{index}] open_time must be timezone-aware UTC"
            raise AlignmentValidationError(msg)
        offset = candle.open_time.utcoffset()
        if offset is None or offset != timedelta(0):
            msg = f"{label} candles[{index}] open_time must have a zero UTC offset"
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


def _compute_no_lookahead_mapping(
    execution: Sequence[Candle],
    context: Sequence[Candle] | CountingSequence,
) -> tuple[int | None, ...]:
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
    return tuple(mapping)


def _assert_mapping_bound_to_candles(
    *,
    execution: Sequence[Candle],
    context: Sequence[Candle],
    mapping: object,
) -> tuple[int | None, ...]:
    """Reject mappings that are not the exact no-lookahead derivation."""
    if not isinstance(mapping, tuple):
        msg = "mapping must be an immutable tuple"
        raise AlignmentValidationError(msg)
    if len(mapping) != len(execution):
        msg = "mapping length must equal execution candle count"
        raise AlignmentValidationError(msg)
    previous = -1
    for index, value in enumerate(mapping):
        if value is None:
            continue
        if type(value) is not int or isinstance(value, bool) or value < 0:
            msg = f"mapping[{index}] must be None or a non-negative int"
            raise AlignmentValidationError(msg)
        if value >= len(context):
            msg = f"mapping[{index}] is out of range for context candle count"
            raise AlignmentValidationError(msg)
        if value < previous:
            msg = "context mapping indexes must be monotonically non-decreasing"
            raise AlignmentValidationError(msg)
        previous = value
        if context[value].close_time > execution[index].close_time:
            msg = "mapping references a future context candle"
            raise AlignmentValidationError(msg)
    expected = _compute_no_lookahead_mapping(execution, context)
    if mapping != expected:
        msg = "mapping does not match no-lookahead close-time derivation"
        raise AlignmentValidationError(msg)
    return mapping


def _single_alignment_hash_payload(
    *,
    symbol: Symbol,
    execution_timeframe: Timeframe,
    context_timeframe: Timeframe,
    execution_candle_sha256: str,
    context_candle_sha256: str,
    mapping: tuple[int | None, ...],
) -> str:
    document = {
        "context_candle_sha256": context_candle_sha256,
        "context_timeframe": context_timeframe.value,
        "execution_candle_sha256": execution_candle_sha256,
        "execution_timeframe": execution_timeframe.value,
        "mapping": list(mapping),
        "schema_version": _SINGLE_ALIGNMENT_SCHEMA,
        "symbol": symbol.value,
    }
    return json.dumps(document, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def _multi_alignment_hash_payload(multi: MultiContextAlignment) -> str:
    document = {
        "alignment_hashes": [a.alignment_hash for a in multi.alignments],
        "context_hashes": [a.context_candle_sha256 for a in multi.alignments],
        "context_timeframes": [a.context_timeframe.value for a in multi.alignments],
        "execution_candle_sha256": multi.execution_candle_sha256,
        "execution_timeframe": multi.execution_timeframe.value,
        "mappings": [list(a.mapping) for a in multi.alignments],
        "schema_version": _MULTI_ALIGNMENT_SCHEMA,
        "symbol": multi.symbol.value,
    }
    return json.dumps(document, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


@dataclass(frozen=True, slots=True, init=False)
class ContextAlignment:
    """Index map from execution bars to the latest fully closed context bar."""

    symbol: Symbol
    execution_timeframe: Timeframe
    context_timeframe: Timeframe
    execution_candle_count: int
    context_candle_count: int
    execution_candle_sha256: str
    context_candle_sha256: str
    mapping: tuple[int | None, ...]
    alignment_hash: str

    def __init__(self, *args: object, **kwargs: object) -> None:
        msg = "ContextAlignment must be created via from_candles"
        raise AlignmentValidationError(msg)

    @classmethod
    def from_candles(
        cls,
        *,
        symbol: Symbol,
        execution_timeframe: Timeframe,
        context_timeframe: Timeframe,
        execution_candles: tuple[Candle, ...],
        context_candles: tuple[Candle, ...],
    ) -> ContextAlignment:
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
        mapping = _compute_no_lookahead_mapping(execution, context)
        mapping = _assert_mapping_bound_to_candles(
            execution=execution,
            context=context,
            mapping=mapping,
        )
        execution_hash = hash_candle_tuple(execution)
        context_hash = hash_candle_tuple(context)
        digest = sha256_hex(
            _single_alignment_hash_payload(
                symbol=symbol,
                execution_timeframe=execution_timeframe,
                context_timeframe=context_timeframe,
                execution_candle_sha256=execution_hash,
                context_candle_sha256=context_hash,
                mapping=mapping,
            ).encode("utf-8")
        )
        self = object.__new__(cls)
        object.__setattr__(self, "symbol", symbol)
        object.__setattr__(self, "execution_timeframe", execution_timeframe)
        object.__setattr__(self, "context_timeframe", context_timeframe)
        object.__setattr__(self, "execution_candle_count", len(execution))
        object.__setattr__(self, "context_candle_count", len(context))
        object.__setattr__(self, "execution_candle_sha256", execution_hash)
        object.__setattr__(self, "context_candle_sha256", context_hash)
        object.__setattr__(self, "mapping", mapping)
        object.__setattr__(self, "alignment_hash", digest)
        return self


@dataclass(frozen=True, slots=True, init=False)
class MultiContextAlignment:
    """Ordered unique context alignments for one execution series."""

    symbol: Symbol
    execution_timeframe: Timeframe
    execution_candle_count: int
    execution_candle_sha256: str
    alignments: tuple[ContextAlignment, ...]
    alignment_hash: str

    def __init__(self, *args: object, **kwargs: object) -> None:
        msg = "MultiContextAlignment must be created via from_alignments"
        raise AlignmentValidationError(msg)

    @classmethod
    def from_alignments(
        cls,
        alignments: tuple[ContextAlignment, ...],
    ) -> MultiContextAlignment:
        if not isinstance(alignments, tuple) or not alignments:
            msg = "alignments must be a non-empty tuple"
            raise AlignmentValidationError(msg)
        first = alignments[0]
        if not isinstance(first, ContextAlignment):
            msg = "alignments must contain ContextAlignment values"
            raise AlignmentValidationError(msg)
        symbol = first.symbol
        execution_timeframe = first.execution_timeframe
        execution_hash = first.execution_candle_sha256
        execution_count = first.execution_candle_count
        seen: set[Timeframe] = set()
        durations: list[int] = []
        for alignment in alignments:
            if not isinstance(alignment, ContextAlignment):
                msg = "alignments must contain ContextAlignment values"
                raise AlignmentValidationError(msg)
            if alignment.symbol != symbol:
                msg = "alignment symbol mismatch"
                raise AlignmentValidationError(msg)
            if alignment.execution_timeframe != execution_timeframe:
                msg = "alignment execution timeframe mismatch"
                raise AlignmentValidationError(msg)
            if alignment.execution_candle_sha256 != execution_hash:
                msg = "alignment execution candle hash mismatch"
                raise AlignmentValidationError(msg)
            if alignment.execution_candle_count != execution_count:
                msg = "alignment execution candle count mismatch"
                raise AlignmentValidationError(msg)
            if alignment.context_timeframe in seen:
                msg = "duplicate context timeframe"
                raise AlignmentValidationError(msg)
            if alignment.context_timeframe is execution_timeframe:
                msg = "execution timeframe cannot appear as context"
                raise AlignmentValidationError(msg)
            expected_hash = sha256_hex(
                _single_alignment_hash_payload(
                    symbol=alignment.symbol,
                    execution_timeframe=alignment.execution_timeframe,
                    context_timeframe=alignment.context_timeframe,
                    execution_candle_sha256=alignment.execution_candle_sha256,
                    context_candle_sha256=alignment.context_candle_sha256,
                    mapping=alignment.mapping,
                ).encode("utf-8")
            )
            if alignment.alignment_hash != expected_hash:
                msg = "child alignment_hash does not match computed binding"
                raise AlignmentValidationError(msg)
            seen.add(alignment.context_timeframe)
            durations.append(duration_milliseconds(timeframe_duration(alignment.context_timeframe)))
        if durations != sorted(durations):
            msg = "context timeframes must be ordered from smallest to largest duration"
            raise AlignmentValidationError(msg)

        self = object.__new__(cls)
        object.__setattr__(self, "symbol", symbol)
        object.__setattr__(self, "execution_timeframe", execution_timeframe)
        object.__setattr__(self, "execution_candle_count", execution_count)
        object.__setattr__(self, "execution_candle_sha256", execution_hash)
        object.__setattr__(self, "alignments", alignments)
        digest = sha256_hex(_multi_alignment_hash_payload(self).encode("utf-8"))
        object.__setattr__(self, "alignment_hash", digest)
        return self


def align_context_to_execution(
    *,
    symbol: Symbol,
    execution_timeframe: Timeframe,
    context_timeframe: Timeframe,
    execution_candles: tuple[Candle, ...],
    context_candles: tuple[Candle, ...],
    **kwargs: object,
) -> ContextAlignment:
    """
    Map each execution candle to the latest context candle with close_time <= execution close.

    Candle hashes and the no-lookahead mapping are computed from the supplied tuples.
    """
    if kwargs:
        msg = "caller-supplied candle hashes and extra alignment arguments are not accepted"
        raise AlignmentValidationError(msg)
    return ContextAlignment.from_candles(
        symbol=symbol,
        execution_timeframe=execution_timeframe,
        context_timeframe=context_timeframe,
        execution_candles=execution_candles,
        context_candles=context_candles,
    )


def align_multi_context(
    *,
    symbol: Symbol,
    execution_timeframe: Timeframe,
    execution_candles: tuple[Candle, ...],
    contexts: Sequence[tuple[Timeframe, tuple[Candle, ...]]],
    **kwargs: object,
) -> MultiContextAlignment:
    """
    Align multiple context series.

    ``contexts`` entries are ``(timeframe, candles)`` and must already be ordered by
    increasing duration with unique timeframes.
    """
    if kwargs:
        msg = "caller-supplied candle hashes and extra alignment arguments are not accepted"
        raise AlignmentValidationError(msg)
    if not contexts:
        msg = "at least one context series is required"
        raise AlignmentValidationError(msg)
    alignments: list[ContextAlignment] = []
    for context_timeframe, context_candles in contexts:
        alignments.append(
            align_context_to_execution(
                symbol=symbol,
                execution_timeframe=execution_timeframe,
                context_timeframe=context_timeframe,
                execution_candles=execution_candles,
                context_candles=context_candles,
            )
        )
    return MultiContextAlignment.from_alignments(tuple(alignments))


def context_available_at_decision(
    *,
    context_close_time: datetime,
    execution_close_time: datetime,
) -> bool:
    """True iff the context candle is fully closed by the execution decision close."""
    return context_close_time <= execution_close_time


def align_with_counting_context(
    *,
    symbol: Symbol,
    execution_timeframe: Timeframe,
    context_timeframe: Timeframe,
    execution_candles: tuple[Candle, ...],
    context_candles: CountingSequence,
) -> tuple[ContextAlignment, int]:
    """Alignment against an instrumented context sequence; returns (result, index_reads)."""
    _require_derivable_pair(execution_timeframe, context_timeframe)
    execution = _require_gap_free_series(
        execution_candles, timeframe=execution_timeframe, label="execution"
    )
    if len(context_candles) == 0:
        msg = "context candles must be non-empty"
        raise AlignmentValidationError(msg)
    # Materialize once for hashing / result binding; count reads during mapping only.
    materialized = tuple(context_candles[i] for i in range(len(context_candles)))
    context_material = _require_gap_free_series(
        materialized, timeframe=context_timeframe, label="context"
    )
    before = context_candles.index_reads
    mapping = _compute_no_lookahead_mapping(execution, context_candles)
    reads = context_candles.index_reads - before
    alignment = ContextAlignment.from_candles(
        symbol=symbol,
        execution_timeframe=execution_timeframe,
        context_timeframe=context_timeframe,
        execution_candles=execution,
        context_candles=context_material,
    )
    if alignment.mapping != mapping:
        msg = "instrumented mapping diverged from factory mapping"
        raise AlignmentValidationError(msg)
    return alignment, reads
