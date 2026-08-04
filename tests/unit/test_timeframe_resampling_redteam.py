"""Red-team adversarial attacks for resampling and alignment."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from zorqen_research.application.market_data.alignment import align_execution_to_contexts
from zorqen_research.application.market_data.goldens import build_source_series
from zorqen_research.application.market_data.resampling import resample
from zorqen_research.domain.market_data.derivation import derive_timeframe_plan
from zorqen_research.domain.market_data.errors import (
    AlignmentValidationError,
    ResamplingValidationError,
)
from zorqen_research.domain.symbols import Symbol
from zorqen_research.domain.timeframes import Timeframe
from zorqen_research.timeframes.cli import main as timeframe_main

SYM = Symbol(value="BTCUSDT")
START = datetime(2024, 1, 1, tzinfo=UTC)


def test_redteam_invalid_pairs_and_partials() -> None:
    with pytest.raises(ResamplingValidationError):
        derive_timeframe_plan(Timeframe.M3, Timeframe.M5)
    with pytest.raises(ResamplingValidationError):
        derive_timeframe_plan(Timeframe.H1, Timeframe.H1)
    with pytest.raises(ResamplingValidationError):
        derive_timeframe_plan(Timeframe.H4, Timeframe.H1)
    misaligned_start = START + timedelta(minutes=1)
    with pytest.raises(ResamplingValidationError):
        resample(
            build_source_series(start=misaligned_start, timeframe=Timeframe.M1, count=5),
            symbol=SYM,
            source_timeframe=Timeframe.M1,
            target_timeframe=Timeframe.M5,
        )
    with pytest.raises(ResamplingValidationError):
        resample(
            build_source_series(start=START, timeframe=Timeframe.M1, count=9),
            symbol=SYM,
            source_timeframe=Timeframe.M1,
            target_timeframe=Timeframe.M5,
        )


def test_redteam_list_forged_hash_tuesday_mutation() -> None:
    source = build_source_series(start=START, timeframe=Timeframe.M1, count=5)
    with pytest.raises(ResamplingValidationError):
        resample(
            list(source),  # type: ignore[arg-type]
            symbol=SYM,
            source_timeframe=Timeframe.M1,
            target_timeframe=Timeframe.M5,
        )
    with pytest.raises(ResamplingValidationError):
        resample(
            source,
            symbol=SYM,
            source_timeframe=Timeframe.M1,
            target_timeframe=Timeframe.M5,
            expected_source_sha256="0" * 64,
        )
    tuesday = datetime(2024, 1, 2, tzinfo=UTC)
    with pytest.raises(ResamplingValidationError):
        resample(
            build_source_series(start=tuesday, timeframe=Timeframe.D1, count=7),
            symbol=SYM,
            source_timeframe=Timeframe.D1,
            target_timeframe=Timeframe.W1,
        )
    series = resample(
        source, symbol=SYM, source_timeframe=Timeframe.M1, target_timeframe=Timeframe.M5
    )
    with pytest.raises(TypeError):
        series.candles[0] = series.candles[0]  # type: ignore[index]


def test_redteam_alignment_and_cli() -> None:
    execution = build_source_series(start=START, timeframe=Timeframe.H1, count=4)
    context = build_source_series(start=START, timeframe=Timeframe.H4, count=1)
    with pytest.raises(AlignmentValidationError):
        align_execution_to_contexts(
            symbol=SYM,
            execution_timeframe=Timeframe.H1,
            execution_candles=execution,
            context_series=((Timeframe.D1, context), (Timeframe.H4, context)),
        )
    assert timeframe_main(["verify-golden", "--scenario", "not-a-scenario"]) == 1
    assert timeframe_main(["verify-golden", "--scenario", "one-minute-to-five-minute"]) == 0
