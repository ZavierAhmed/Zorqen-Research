"""Milestone 0.8A — bind resampling/alignment results to verified candle content."""

from __future__ import annotations

import inspect
from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal

import pytest

from zorqen_research.application.market_data.alignment import (
    align_execution_to_context,
    align_execution_to_contexts,
)
from zorqen_research.application.market_data.goldens import build_source_series, make_candle
from zorqen_research.application.market_data.resampling import resample
from zorqen_research.domain.market_data import alignment as alignment_mod
from zorqen_research.domain.market_data.alignment import (
    ContextAlignment,
    MultiContextAlignment,
    align_context_to_execution,
)
from zorqen_research.domain.market_data.derivation import derive_timeframe_plan
from zorqen_research.domain.market_data.errors import (
    AlignmentValidationError,
    ResamplingValidationError,
)
from zorqen_research.domain.market_data.resampling import resample_candles
from zorqen_research.domain.market_data.series import ResampledCandleSeries
from zorqen_research.domain.symbols import Symbol
from zorqen_research.domain.timeframes import Timeframe

SYM = Symbol(value="BTCUSDT")
START = datetime(2024, 1, 1, tzinfo=UTC)


def _valid_series() -> ResampledCandleSeries:
    source = build_source_series(start=START, timeframe=Timeframe.M1, count=5)
    return resample(
        source, symbol=SYM, source_timeframe=Timeframe.M1, target_timeframe=Timeframe.M5
    )


def test_forged_source_hash_direct_construction_rejected() -> None:
    with pytest.raises(ResamplingValidationError, match="from_verified_series"):
        ResampledCandleSeries(  # type: ignore[call-arg]
            symbol=SYM,
            source_timeframe=Timeframe.M1,
            target_timeframe=Timeframe.M5,
            candles=_valid_series().candles,
            source_candle_sha256="ab" * 32,
        )


def test_forged_source_minimum_time_direct_construction_rejected() -> None:
    with pytest.raises(ResamplingValidationError, match="from_verified_series"):
        ResampledCandleSeries(  # type: ignore[call-arg]
            symbol=SYM,
            source_timeframe=Timeframe.M1,
            target_timeframe=Timeframe.M5,
            candles=_valid_series().candles,
            source_minimum_open_time=START + timedelta(minutes=1),
        )


def test_forged_source_maximum_time_direct_construction_rejected() -> None:
    with pytest.raises(ResamplingValidationError, match="from_verified_series"):
        ResampledCandleSeries(  # type: ignore[call-arg]
            symbol=SYM,
            source_timeframe=Timeframe.M1,
            target_timeframe=Timeframe.M5,
            candles=_valid_series().candles,
            source_maximum_open_time=START + timedelta(minutes=99),
        )


def test_naive_source_bound_direct_construction_rejected() -> None:
    naive = datetime(2024, 1, 1)
    with pytest.raises(ResamplingValidationError, match="from_verified_series"):
        ResampledCandleSeries(  # type: ignore[call-arg]
            symbol=SYM,
            source_timeframe=Timeframe.M1,
            target_timeframe=Timeframe.M5,
            candles=_valid_series().candles,
            source_minimum_open_time=naive,
        )


def test_nonzero_offset_source_bound_direct_construction_rejected() -> None:
    offset = datetime(2024, 1, 1, tzinfo=timezone(timedelta(hours=5)))
    with pytest.raises(ResamplingValidationError, match="from_verified_series"):
        ResampledCandleSeries(  # type: ignore[call-arg]
            symbol=SYM,
            source_timeframe=Timeframe.M1,
            target_timeframe=Timeframe.M5,
            candles=_valid_series().candles,
            source_minimum_open_time=offset,
        )


def test_gapped_target_candles_in_factory_rejected() -> None:
    source = build_source_series(start=START, timeframe=Timeframe.M1, count=10)
    series = resample(
        source, symbol=SYM, source_timeframe=Timeframe.M1, target_timeframe=Timeframe.M5
    )
    gapped_targets = (series.candles[0], series.candles[0])
    with pytest.raises(ResamplingValidationError):
        ResampledCandleSeries.from_verified_series(
            symbol=SYM,
            plan=derive_timeframe_plan(Timeframe.M1, Timeframe.M5),
            source_candles=source,
            target_candles=gapped_targets,
        )


def test_misaligned_target_candle_in_factory_rejected() -> None:
    source = build_source_series(start=START, timeframe=Timeframe.M1, count=5)
    bad = make_candle(
        START + timedelta(minutes=1),
        timeframe=Timeframe.M5,
        open=Decimal("100"),
        high=Decimal("101"),
        low=Decimal("99"),
        close=Decimal("100.5"),
    )
    with pytest.raises(ResamplingValidationError, match="misaligned"):
        ResampledCandleSeries.from_verified_series(
            symbol=SYM,
            plan=derive_timeframe_plan(Timeframe.M1, Timeframe.M5),
            source_candles=source,
            target_candles=(bad,),
        )


def test_public_alignment_rejects_caller_supplied_execution_hash() -> None:
    sig = inspect.signature(align_context_to_execution)
    assert "execution_candle_sha256" not in sig.parameters
    execution = build_source_series(start=START, timeframe=Timeframe.H1, count=4)
    context = build_source_series(start=START, timeframe=Timeframe.H4, count=1)
    with pytest.raises(AlignmentValidationError):
        align_context_to_execution(  # type: ignore[call-arg]
            symbol=SYM,
            execution_timeframe=Timeframe.H1,
            context_timeframe=Timeframe.H4,
            execution_candles=execution,
            context_candles=context,
            execution_candle_sha256="ab" * 32,
        )


def test_public_alignment_rejects_caller_supplied_context_hash() -> None:
    execution = build_source_series(start=START, timeframe=Timeframe.H1, count=4)
    context = build_source_series(start=START, timeframe=Timeframe.H4, count=1)
    with pytest.raises(AlignmentValidationError):
        align_context_to_execution(  # type: ignore[call-arg]
            symbol=SYM,
            execution_timeframe=Timeframe.H1,
            context_timeframe=Timeframe.H4,
            execution_candles=execution,
            context_candles=context,
            context_candle_sha256="cd" * 32,
        )


def test_mapping_shorter_than_execution_rejected() -> None:
    execution = build_source_series(start=START, timeframe=Timeframe.H1, count=4)
    context = build_source_series(start=START, timeframe=Timeframe.H4, count=1)
    with pytest.raises(AlignmentValidationError, match="length"):
        alignment_mod._assert_mapping_bound_to_candles(
            execution=execution,
            context=context,
            mapping=(None, None, None),
        )


def test_mapping_longer_than_execution_rejected() -> None:
    execution = build_source_series(start=START, timeframe=Timeframe.H1, count=4)
    context = build_source_series(start=START, timeframe=Timeframe.H4, count=1)
    with pytest.raises(AlignmentValidationError, match="length"):
        alignment_mod._assert_mapping_bound_to_candles(
            execution=execution,
            context=context,
            mapping=(None, None, None, 0, 0),
        )


def test_context_index_equal_to_context_count_rejected() -> None:
    execution = build_source_series(start=START, timeframe=Timeframe.H1, count=4)
    context = build_source_series(start=START, timeframe=Timeframe.H4, count=1)
    with pytest.raises(AlignmentValidationError, match="out of range"):
        alignment_mod._assert_mapping_bound_to_candles(
            execution=execution,
            context=context,
            mapping=(None, None, None, 1),
        )


def test_extremely_large_context_index_rejected() -> None:
    execution = build_source_series(start=START, timeframe=Timeframe.H1, count=4)
    context = build_source_series(start=START, timeframe=Timeframe.H4, count=1)
    with pytest.raises(AlignmentValidationError, match="out of range"):
        alignment_mod._assert_mapping_bound_to_candles(
            execution=execution,
            context=context,
            mapping=(None, None, None, 10**12),
        )


def test_monotonic_but_future_leaking_mapping_rejected() -> None:
    execution = build_source_series(start=START, timeframe=Timeframe.H1, count=4)
    context = build_source_series(start=START, timeframe=Timeframe.H4, count=1)
    # Index 0 is only valid at the final bar; leaking it early is future use.
    with pytest.raises(AlignmentValidationError):
        alignment_mod._assert_mapping_bound_to_candles(
            execution=execution,
            context=context,
            mapping=(0, 0, 0, 0),
        )


def test_incorrect_null_before_already_closed_context_rejected() -> None:
    execution = build_source_series(start=START, timeframe=Timeframe.H1, count=4)
    context = build_source_series(start=START, timeframe=Timeframe.H4, count=1)
    with pytest.raises(AlignmentValidationError, match="no-lookahead"):
        alignment_mod._assert_mapping_bound_to_candles(
            execution=execution,
            context=context,
            mapping=(None, None, None, None),
        )


def test_incorrect_context_index_when_newer_context_closed_rejected() -> None:
    execution = build_source_series(start=START, timeframe=Timeframe.H1, count=8)
    context = build_source_series(start=START, timeframe=Timeframe.H4, count=2)
    # After the second 4h close, mapping must advance to 1 — staying at 0 is wrong.
    with pytest.raises(AlignmentValidationError, match="no-lookahead"):
        alignment_mod._assert_mapping_bound_to_candles(
            execution=execution,
            context=context,
            mapping=(None, None, None, 0, 0, 0, 0, 0),
        )


def test_forged_single_alignment_hash_direct_construction_rejected() -> None:
    with pytest.raises(AlignmentValidationError, match="from_candles"):
        ContextAlignment(  # type: ignore[call-arg]
            symbol=SYM,
            execution_timeframe=Timeframe.H1,
            context_timeframe=Timeframe.H4,
            alignment_hash="ab" * 32,
        )


def test_forged_multi_alignment_hash_direct_construction_rejected() -> None:
    with pytest.raises(AlignmentValidationError, match="from_alignments"):
        MultiContextAlignment(  # type: ignore[call-arg]
            symbol=SYM,
            execution_timeframe=Timeframe.H1,
            execution_candle_sha256="ab" * 32,
            alignments=(),
            alignment_hash="cd" * 32,
        )


def test_direct_unsafe_low_level_construction_unavailable() -> None:
    assert "serialize_csv" not in inspect.signature(resample_candles).parameters
    public = __import__(
        "zorqen_research.domain.market_data",
        fromlist=["*"],
    )
    exported = set(public.__all__)
    assert "align_with_counting_context" not in exported
    assert "_assert_mapping_bound_to_candles" not in exported
    with pytest.raises(ResamplingValidationError):
        ResampledCandleSeries()
    with pytest.raises(AlignmentValidationError):
        ContextAlignment()
    with pytest.raises(AlignmentValidationError):
        MultiContextAlignment()


def test_valid_normal_resampling_and_alignment_unchanged() -> None:
    source = build_source_series(start=START, timeframe=Timeframe.M1, count=10)
    series = resample(
        source, symbol=SYM, source_timeframe=Timeframe.M1, target_timeframe=Timeframe.M5
    )
    assert series.source_candle_count == 10
    assert series.target_candle_count == 2
    assert (
        series.target_candle_sha256
        == "56c28d9a685c7e36ea8c0c511ec41630bf58d567c00f7f99f3d3e8ad68f8db94"
    )
    execution = build_source_series(start=START, timeframe=Timeframe.H1, count=24)
    context = build_source_series(start=START, timeframe=Timeframe.H4, count=6)
    alignment = align_execution_to_context(
        symbol=SYM,
        execution_timeframe=Timeframe.H1,
        context_timeframe=Timeframe.H4,
        execution_candles=execution,
        context_candles=context,
    )
    assert (
        alignment.alignment_hash
        == "f8c8d2548fc6772ce421c9abb459efafd6e46aefd415dbf174406678f31d6698"
    )
    multi = align_execution_to_contexts(
        symbol=SYM,
        execution_timeframe=Timeframe.H1,
        execution_candles=execution,
        context_series=(
            (Timeframe.H4, context),
            (Timeframe.D1, build_source_series(start=START, timeframe=Timeframe.D1, count=1)),
        ),
    )
    assert (
        multi.alignment_hash == "1ced7609616bfc7e79039cd8ac9cbead378c7feffbeeec5db4bda3b7174f48ac"
    )
