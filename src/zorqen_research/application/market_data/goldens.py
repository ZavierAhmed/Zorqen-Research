"""Frozen golden expectations for timeframe resampling and alignment.

Literal constants only — do not invoke the production resampler to derive
expected hashes or candles at import time.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from zorqen_research.application.market_data.alignment import (
    align_execution_to_context,
    align_execution_to_contexts,
    hash_candles,
)
from zorqen_research.application.market_data.resampling import resample
from zorqen_research.domain.candles import Candle
from zorqen_research.domain.symbols import Symbol
from zorqen_research.domain.timeframes import Timeframe, timeframe_duration

SYMBOL = Symbol(value="BTCUSDT")


def _utc(year: int, month: int, day: int, hour: int = 0, minute: int = 0) -> datetime:
    return datetime(year, month, day, hour, minute, tzinfo=UTC)


def make_candle(
    open_time: datetime,
    *,
    timeframe: Timeframe,
    open: Decimal,
    high: Decimal,
    low: Decimal,
    close: Decimal,
    volume: Decimal = Decimal("1"),
    quote_asset_volume: Decimal = Decimal("10"),
    trade_count: int = 1,
    taker_buy_base_volume: Decimal = Decimal("0.4"),
    taker_buy_quote_volume: Decimal = Decimal("4"),
) -> Candle:
    return Candle(
        open_time=open_time,
        open=open,
        high=high,
        low=low,
        close=close,
        volume=volume,
        close_time=open_time + timeframe_duration(timeframe) - timedelta(milliseconds=1),
        quote_asset_volume=quote_asset_volume,
        trade_count=trade_count,
        taker_buy_base_volume=taker_buy_base_volume,
        taker_buy_quote_volume=taker_buy_quote_volume,
    )


def build_source_series(
    *,
    start: datetime,
    timeframe: Timeframe,
    count: int,
    open_base: Decimal = Decimal("100"),
) -> tuple[Candle, ...]:
    step = timeframe_duration(timeframe)
    candles: list[Candle] = []
    for index in range(count):
        open_time = start + index * step
        level = open_base + Decimal(index)
        candles.append(
            make_candle(
                open_time,
                timeframe=timeframe,
                open=level,
                high=level + Decimal("1"),
                low=level - Decimal("1"),
                close=level + Decimal("0.5"),
                volume=Decimal("1") + Decimal(index),
                quote_asset_volume=Decimal("10") + Decimal(index),
                trade_count=1 + index,
                taker_buy_base_volume=Decimal("0.5"),
                taker_buy_quote_volume=Decimal("5"),
            )
        )
    return tuple(candles)


def _target(
    open_time: datetime,
    timeframe: Timeframe,
    open: str,
    high: str,
    low: str,
    close: str,
    volume: str,
    quote: str,
    trade_count: int,
    taker_base: str,
    taker_quote: str,
) -> Candle:
    return make_candle(
        open_time,
        timeframe=timeframe,
        open=Decimal(open),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
        volume=Decimal(volume),
        quote_asset_volume=Decimal(quote),
        trade_count=trade_count,
        taker_buy_base_volume=Decimal(taker_base),
        taker_buy_quote_volume=Decimal(taker_quote),
    )


@dataclass(frozen=True, slots=True)
class ResampleGoldenExpectation:
    scenario: str
    source_timeframe: Timeframe
    target_timeframe: Timeframe
    source_count: int
    target_count: int
    source_start: datetime
    expected_target_candles: tuple[Candle, ...]
    source_hash: str
    target_hash: str


@dataclass(frozen=True, slots=True)
class AlignmentGoldenExpectation:
    scenario: str
    execution_timeframe: Timeframe
    execution_count: int
    context_specs: tuple[tuple[Timeframe, int], ...]
    expected_mappings: tuple[tuple[int | None, ...], ...]
    alignment_hash: str | None
    execution_hash: str
    context_hashes: tuple[str, ...]


_START = _utc(2024, 1, 1)

RESAMPLE_GOLDENS: dict[str, ResampleGoldenExpectation] = {
    "one-minute-to-five-minute": ResampleGoldenExpectation(
        scenario="one-minute-to-five-minute",
        source_timeframe=Timeframe.M1,
        target_timeframe=Timeframe.M5,
        source_count=10,
        target_count=2,
        source_start=_START,
        expected_target_candles=(
            _target(
                _START,
                Timeframe.M5,
                "100",
                "105",
                "99",
                "104.5",
                "15",
                "60",
                15,
                "2.5",
                "25",
            ),
            _target(
                _START + timedelta(minutes=5),
                Timeframe.M5,
                "105",
                "110",
                "104",
                "109.5",
                "40",
                "85",
                40,
                "2.5",
                "25",
            ),
        ),
        source_hash="797ff060d9b36a7ae4de4268d73113ee2e65fdbc1c3cfface25a1579606bfc60",
        target_hash="56c28d9a685c7e36ea8c0c511ec41630bf58d567c00f7f99f3d3e8ad68f8db94",
    ),
    "three-minute-to-fifteen-minute": ResampleGoldenExpectation(
        scenario="three-minute-to-fifteen-minute",
        source_timeframe=Timeframe.M3,
        target_timeframe=Timeframe.M15,
        source_count=5,
        target_count=1,
        source_start=_START,
        expected_target_candles=(
            _target(
                _START,
                Timeframe.M15,
                "100",
                "105",
                "99",
                "104.5",
                "15",
                "60",
                15,
                "2.5",
                "25",
            ),
        ),
        source_hash="ac748ddd0d4d7a83c57a25a48ec40fc2a5a31d0fe3276a2789d75c7023ab6ee1",
        target_hash="11d98ca40e25366fd268c7220b3b3cd1639d019e328863e0f8917bbcdd514940",
    ),
    "fifteen-minute-to-one-hour": ResampleGoldenExpectation(
        scenario="fifteen-minute-to-one-hour",
        source_timeframe=Timeframe.M15,
        target_timeframe=Timeframe.H1,
        source_count=4,
        target_count=1,
        source_start=_START,
        expected_target_candles=(
            _target(_START, Timeframe.H1, "100", "104", "99", "103.5", "10", "46", 10, "2.0", "20"),
        ),
        source_hash="e75c5a887322757b646cb6df83f8e5347245eb55a3994189b27ff7ff471296b9",
        target_hash="50a6b2ddd1bc888e9d9bbc49e222025528a34b2f07773d168cc0c2929306af04",
    ),
    "one-hour-to-four-hour": ResampleGoldenExpectation(
        scenario="one-hour-to-four-hour",
        source_timeframe=Timeframe.H1,
        target_timeframe=Timeframe.H4,
        source_count=4,
        target_count=1,
        source_start=_START,
        expected_target_candles=(
            _target(_START, Timeframe.H4, "100", "104", "99", "103.5", "10", "46", 10, "2.0", "20"),
        ),
        source_hash="79002a739079da3916ebf7cd91c5e927959b2a74272bd6664085022de5db3dcb",
        target_hash="7762636a0bafc047b942ad51623cb5d40aae6ae389c256e47b9aac11028f76a7",
    ),
    "four-hour-to-one-day": ResampleGoldenExpectation(
        scenario="four-hour-to-one-day",
        source_timeframe=Timeframe.H4,
        target_timeframe=Timeframe.D1,
        source_count=6,
        target_count=1,
        source_start=_START,
        expected_target_candles=(
            _target(_START, Timeframe.D1, "100", "106", "99", "105.5", "21", "75", 21, "3.0", "30"),
        ),
        source_hash="01382157594631837ea28d0feac14ff14a1eb20c25ee8968fbc898487a18cc83",
        target_hash="6a3800671b847193f484959759964fbecbb72ce5e6a96a35e2b49cb636c70b23",
    ),
    "one-day-to-one-week": ResampleGoldenExpectation(
        scenario="one-day-to-one-week",
        source_timeframe=Timeframe.D1,
        target_timeframe=Timeframe.W1,
        source_count=7,
        target_count=1,
        source_start=_START,
        expected_target_candles=(
            _target(_START, Timeframe.W1, "100", "107", "99", "106.5", "28", "91", 28, "3.5", "35"),
        ),
        source_hash="7873677bb56a959202a57136063e6437ff25546b4a2ff8429a5ebf6e8d35401c",
        target_hash="522ca23a8e8b5b400dd78de03a396421af980f5a91bff06085c751634b743a80",
    ),
}


_ALIGN_1H_4H_MAP = (
    None,
    None,
    None,
    0,
    0,
    0,
    0,
    1,
    1,
    1,
    1,
    2,
    2,
    2,
    2,
    3,
    3,
    3,
    3,
    4,
    4,
    4,
    4,
    5,
)
_ALIGN_1H_1D_MAP = tuple([None] * 23 + [0])

ALIGNMENT_GOLDENS: dict[str, AlignmentGoldenExpectation] = {
    "execution-one-hour-context-four-hour": AlignmentGoldenExpectation(
        scenario="execution-one-hour-context-four-hour",
        execution_timeframe=Timeframe.H1,
        execution_count=24,
        context_specs=((Timeframe.H4, 6),),
        expected_mappings=(_ALIGN_1H_4H_MAP,),
        alignment_hash=None,
        execution_hash="12ad15d6cf957b337720019aa4766687fb643e163394b001621c5c0d38f96abd",
        context_hashes=("01382157594631837ea28d0feac14ff14a1eb20c25ee8968fbc898487a18cc83",),
    ),
    "execution-one-hour-contexts-four-hour-one-day": AlignmentGoldenExpectation(
        scenario="execution-one-hour-contexts-four-hour-one-day",
        execution_timeframe=Timeframe.H1,
        execution_count=24,
        context_specs=((Timeframe.H4, 6), (Timeframe.D1, 1)),
        expected_mappings=(_ALIGN_1H_4H_MAP, _ALIGN_1H_1D_MAP),
        alignment_hash="30abad8971a01b39c3a8579e9929c42f56fc168b4694885834ab911c9b1f904e",
        execution_hash="12ad15d6cf957b337720019aa4766687fb643e163394b001621c5c0d38f96abd",
        context_hashes=(
            "01382157594631837ea28d0feac14ff14a1eb20c25ee8968fbc898487a18cc83",
            "4c3919b2b135b30e4682baa6848d0b2fe7a55fdc633fd2e3e008b09c3fe8c360",
        ),
    ),
}

ALL_SCENARIO_NAMES: tuple[str, ...] = tuple(
    sorted([*RESAMPLE_GOLDENS.keys(), *ALIGNMENT_GOLDENS.keys()])
)


class TimeframeGoldenMismatchError(Exception):
    """Golden expectation mismatch."""


def run_resample_scenario(name: str) -> dict[str, object]:
    expectation = RESAMPLE_GOLDENS[name]
    source = build_source_series(
        start=expectation.source_start,
        timeframe=expectation.source_timeframe,
        count=expectation.source_count,
    )
    series = resample(
        source,
        symbol=SYMBOL,
        source_timeframe=expectation.source_timeframe,
        target_timeframe=expectation.target_timeframe,
    )
    if series.source_candle_sha256 != expectation.source_hash:
        msg = f"{name}: source_hash mismatch"
        raise TimeframeGoldenMismatchError(msg)
    if series.target_candle_sha256 != expectation.target_hash:
        msg = f"{name}: target_hash mismatch"
        raise TimeframeGoldenMismatchError(msg)
    if series.candles != expectation.expected_target_candles:
        msg = f"{name}: target candles mismatch"
        raise TimeframeGoldenMismatchError(msg)
    if series.target_candle_count != expectation.target_count:
        msg = f"{name}: target_count mismatch"
        raise TimeframeGoldenMismatchError(msg)
    return {
        "ok": True,
        "scenario": name,
        "source_timeframe": expectation.source_timeframe.value,
        "target_timeframe": expectation.target_timeframe.value,
        "source_count": series.source_candle_count,
        "target_count": series.target_candle_count,
        "source_hash": series.source_candle_sha256,
        "target_hash": series.target_candle_sha256,
    }


def run_alignment_scenario(name: str) -> dict[str, object]:
    expectation = ALIGNMENT_GOLDENS[name]
    execution = build_source_series(
        start=_START,
        timeframe=expectation.execution_timeframe,
        count=expectation.execution_count,
    )
    if hash_candles(execution) != expectation.execution_hash:
        msg = f"{name}: execution_hash mismatch"
        raise TimeframeGoldenMismatchError(msg)
    contexts: list[tuple[Timeframe, tuple[Candle, ...]]] = []
    for timeframe, count in expectation.context_specs:
        contexts.append(
            (
                timeframe,
                build_source_series(start=_START, timeframe=timeframe, count=count),
            )
        )
    for index, (_, candles) in enumerate(contexts):
        if hash_candles(candles) != expectation.context_hashes[index]:
            msg = f"{name}: context_hash[{index}] mismatch"
            raise TimeframeGoldenMismatchError(msg)

    if len(contexts) == 1:
        alignment = align_execution_to_context(
            symbol=SYMBOL,
            execution_timeframe=expectation.execution_timeframe,
            context_timeframe=contexts[0][0],
            execution_candles=execution,
            context_candles=contexts[0][1],
        )
        if alignment.mapping != expectation.expected_mappings[0]:
            msg = f"{name}: mapping mismatch"
            raise TimeframeGoldenMismatchError(msg)
        payload: dict[str, object] = {
            "ok": True,
            "scenario": name,
            "source_timeframe": expectation.execution_timeframe.value,
            "target_timeframe": contexts[0][0].value,
            "source_count": len(execution),
            "target_count": len(contexts[0][1]),
            "source_hash": expectation.execution_hash,
            "target_hash": expectation.context_hashes[0],
        }
        return payload

    multi = align_execution_to_contexts(
        symbol=SYMBOL,
        execution_timeframe=expectation.execution_timeframe,
        execution_candles=execution,
        context_series=tuple(contexts),
    )
    actual_maps = tuple(item.mapping for item in multi.alignments)
    if actual_maps != expectation.expected_mappings:
        msg = f"{name}: multi mapping mismatch"
        raise TimeframeGoldenMismatchError(msg)
    if multi.alignment_hash != expectation.alignment_hash:
        msg = f"{name}: alignment_hash mismatch"
        raise TimeframeGoldenMismatchError(msg)
    return {
        "ok": True,
        "scenario": name,
        "source_timeframe": expectation.execution_timeframe.value,
        "target_timeframe": ",".join(tf.value for tf, _ in expectation.context_specs),
        "source_count": len(execution),
        "target_count": sum(count for _, count in expectation.context_specs),
        "source_hash": expectation.execution_hash,
        "target_hash": expectation.context_hashes[-1],
        "alignment_hash": multi.alignment_hash,
    }


def run_scenario(name: str) -> dict[str, object]:
    if name in RESAMPLE_GOLDENS:
        return run_resample_scenario(name)
    if name in ALIGNMENT_GOLDENS:
        return run_alignment_scenario(name)
    raise KeyError(name)
