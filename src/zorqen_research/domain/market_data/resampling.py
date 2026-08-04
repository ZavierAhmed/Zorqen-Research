"""Strict complete-bucket candle resampling."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import datetime, timedelta
from decimal import Decimal

from zorqen_research.domain.artifacts import sha256_hex
from zorqen_research.domain.candles import Candle
from zorqen_research.domain.market_data.derivation import (
    TimeframeDerivationPlan,
    derive_timeframe_plan,
)
from zorqen_research.domain.market_data.errors import ResamplingValidationError
from zorqen_research.domain.market_data.series import ResampledCandleSeries
from zorqen_research.domain.symbols import Symbol
from zorqen_research.domain.timeframes import (
    Timeframe,
    align_floor,
    is_aligned,
    timeframe_duration,
)

SerializeCsv = Callable[[Sequence[Candle]], bytes]


def _expected_close(open_time: datetime, timeframe: Timeframe) -> datetime:
    return open_time + timeframe_duration(timeframe) - timedelta(milliseconds=1)


def _require_canonical_source_series(
    candles: object,
    *,
    timeframe: Timeframe,
    expected_source_sha256: str | None,
    serialize_csv: SerializeCsv,
) -> tuple[Candle, ...]:
    if not isinstance(candles, tuple):
        msg = "source candles must be an immutable tuple"
        raise ResamplingValidationError(msg)
    if len(candles) == 0:
        msg = "source candles must be non-empty"
        raise ResamplingValidationError(msg)
    duration = timeframe_duration(timeframe)
    previous_open: datetime | None = None
    for index, candle in enumerate(candles):
        if not isinstance(candle, Candle):
            msg = f"source candles[{index}] must be a Candle"
            raise ResamplingValidationError(msg)
        if not is_aligned(candle.open_time, timeframe):
            msg = f"source candles[{index}] open_time is misaligned to {timeframe.value}"
            raise ResamplingValidationError(msg)
        if candle.close_time != _expected_close(candle.open_time, timeframe):
            msg = f"source candles[{index}] close_time violates the closed-candle convention"
            raise ResamplingValidationError(msg)
        if previous_open is not None:
            expected_open = previous_open + duration
            if candle.open_time == previous_open:
                msg = f"source candles[{index}] duplicates the previous open_time"
                raise ResamplingValidationError(msg)
            if candle.open_time < previous_open:
                msg = f"source candles[{index}] is out of order"
                raise ResamplingValidationError(msg)
            if candle.open_time != expected_open:
                msg = f"source candles[{index}] has a gap relative to the previous candle"
                raise ResamplingValidationError(msg)
        previous_open = candle.open_time

    digest = sha256_hex(serialize_csv(candles))
    if expected_source_sha256 is not None and expected_source_sha256 != digest:
        msg = "supplied source candle hash does not match canonical CSV bytes"
        raise ResamplingValidationError(msg)
    return candles


def _aggregate_bucket(
    children: Sequence[Candle],
    *,
    target_open: datetime,
    target_timeframe: Timeframe,
) -> Candle:
    high = children[0].high
    low = children[0].low
    volume = Decimal("0")
    quote = Decimal("0")
    trade_count = 0
    taker_base = Decimal("0")
    taker_quote = Decimal("0")
    for child in children:
        if child.high > high:
            high = child.high
        if child.low < low:
            low = child.low
        volume += child.volume
        quote += child.quote_asset_volume
        trade_count += child.trade_count
        taker_base += child.taker_buy_base_volume
        taker_quote += child.taker_buy_quote_volume
    try:
        return Candle(
            open_time=target_open,
            open=children[0].open,
            high=high,
            low=low,
            close=children[-1].close,
            volume=volume,
            close_time=_expected_close(target_open, target_timeframe),
            quote_asset_volume=quote,
            trade_count=trade_count,
            taker_buy_base_volume=taker_base,
            taker_buy_quote_volume=taker_quote,
        )
    except (TypeError, ValueError) as exc:
        msg = "aggregated target candle failed canonical Candle validation"
        raise ResamplingValidationError(msg) from exc


def resample_candles(
    candles: tuple[Candle, ...],
    *,
    symbol: Symbol,
    plan: TimeframeDerivationPlan,
    serialize_csv: SerializeCsv,
    expected_source_sha256: str | None = None,
) -> ResampledCandleSeries:
    """
    Resample a gap-free source series into complete target buckets only.

    ``serialize_csv`` is injected to keep the domain free of application imports
    while reusing the existing canonical CSV bytes contract.
    """
    if not isinstance(symbol, Symbol):
        msg = "symbol must be a Symbol"
        raise ResamplingValidationError(msg)
    if not isinstance(plan, TimeframeDerivationPlan):
        msg = "plan must be a TimeframeDerivationPlan"
        raise ResamplingValidationError(msg)
    # Re-validate plan consistency.
    plan = derive_timeframe_plan(plan.source_timeframe, plan.target_timeframe)

    source = _require_canonical_source_series(
        candles,
        timeframe=plan.source_timeframe,
        expected_source_sha256=expected_source_sha256,
        serialize_csv=serialize_csv,
    )
    source_duration = timeframe_duration(plan.source_timeframe)
    target_duration = timeframe_duration(plan.target_timeframe)
    ratio = plan.ratio

    if len(source) % ratio != 0:
        msg = (
            "source candle count is not divisible by the derivation ratio "
            "(trailing partial bucket is not allowed)"
        )
        raise ResamplingValidationError(msg)

    first_open = source[0].open_time
    if align_floor(first_open, plan.target_timeframe) != first_open:
        msg = "first source candle does not open on a canonical target boundary"
        raise ResamplingValidationError(msg)

    targets: list[Candle] = []
    for bucket_index in range(len(source) // ratio):
        start = bucket_index * ratio
        children = source[start : start + ratio]
        target_open = first_open + bucket_index * target_duration
        for child_index, child in enumerate(children):
            expected_child_open = target_open + child_index * source_duration
            if child.open_time != expected_child_open:
                msg = (
                    f"bucket {bucket_index} child {child_index} does not begin at "
                    "the expected source open within the target bucket"
                )
                raise ResamplingValidationError(msg)
        targets.append(
            _aggregate_bucket(
                children,
                target_open=target_open,
                target_timeframe=plan.target_timeframe,
            )
        )

    final_target_close = targets[-1].close_time
    if source[-1].close_time != final_target_close:
        msg = "final source candle does not close exactly at the final target close_time"
        raise ResamplingValidationError(msg)

    source_sha = sha256_hex(serialize_csv(source))
    target_tuple = tuple(targets)
    return ResampledCandleSeries(
        symbol=symbol,
        source_timeframe=plan.source_timeframe,
        target_timeframe=plan.target_timeframe,
        ratio=ratio,
        source_candle_count=len(source),
        source_minimum_open_time=source[0].open_time,
        source_maximum_open_time=source[-1].open_time,
        source_candle_sha256=source_sha,
        candles=target_tuple,
    )
