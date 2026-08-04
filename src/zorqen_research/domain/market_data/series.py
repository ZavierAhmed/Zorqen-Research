"""Immutable resampled candle series results."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal

from zorqen_research.domain.candles import Candle
from zorqen_research.domain.market_data.derivation import (
    TimeframeDerivationPlan,
    derive_timeframe_plan,
)
from zorqen_research.domain.market_data.errors import ResamplingValidationError
from zorqen_research.domain.market_data.hashes import hash_candle_tuple
from zorqen_research.domain.symbols import Symbol
from zorqen_research.domain.timeframes import (
    Timeframe,
    align_floor,
    is_aligned,
    timeframe_duration,
)


def _expected_close(open_time: datetime, timeframe: Timeframe) -> datetime:
    return open_time + timeframe_duration(timeframe) - timedelta(milliseconds=1)


def _require_canonical_utc(value: object, *, field: str) -> datetime:
    if not isinstance(value, datetime):
        msg = f"{field} must be a datetime"
        raise ResamplingValidationError(msg)
    if value.tzinfo is None:
        msg = f"{field} must be timezone-aware UTC"
        raise ResamplingValidationError(msg)
    offset = value.utcoffset()
    if offset is None or offset != timedelta(0):
        msg = f"{field} must have a zero UTC offset"
        raise ResamplingValidationError(msg)
    return value


def require_canonical_series(
    candles: object,
    *,
    timeframe: Timeframe,
    label: str,
) -> tuple[Candle, ...]:
    """Validate a gap-free aligned candle tuple for ``timeframe``."""
    if not isinstance(candles, tuple):
        msg = f"{label} candles must be an immutable tuple"
        raise ResamplingValidationError(msg)
    if len(candles) == 0:
        msg = f"{label} candles must be non-empty"
        raise ResamplingValidationError(msg)
    duration = timeframe_duration(timeframe)
    previous_open: datetime | None = None
    for index, candle in enumerate(candles):
        if not isinstance(candle, Candle):
            msg = f"{label} candles[{index}] must be a Candle"
            raise ResamplingValidationError(msg)
        _require_canonical_utc(candle.open_time, field=f"{label} candles[{index}].open_time")
        _require_canonical_utc(candle.close_time, field=f"{label} candles[{index}].close_time")
        if not is_aligned(candle.open_time, timeframe):
            msg = f"{label} candles[{index}] open_time is misaligned to {timeframe.value}"
            raise ResamplingValidationError(msg)
        if candle.close_time != _expected_close(candle.open_time, timeframe):
            msg = f"{label} candles[{index}] close_time violates the closed-candle convention"
            raise ResamplingValidationError(msg)
        if previous_open is not None:
            expected_open = previous_open + duration
            if candle.open_time == previous_open:
                msg = f"{label} candles[{index}] duplicates the previous open_time"
                raise ResamplingValidationError(msg)
            if candle.open_time < previous_open:
                msg = f"{label} candles[{index}] is out of order"
                raise ResamplingValidationError(msg)
            if candle.open_time != expected_open:
                msg = f"{label} candles[{index}] has a gap relative to the previous candle"
                raise ResamplingValidationError(msg)
        previous_open = candle.open_time
    return candles


def aggregate_bucket(
    children: tuple[Candle, ...],
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


def verify_complete_bucket_relationship(
    source: tuple[Candle, ...],
    target: tuple[Candle, ...],
    *,
    plan: TimeframeDerivationPlan,
) -> None:
    """Fail closed unless ``target`` is the deterministic aggregation of ``source``."""
    ratio = plan.ratio
    source_duration = timeframe_duration(plan.source_timeframe)
    target_duration = timeframe_duration(plan.target_timeframe)

    if len(source) % ratio != 0:
        msg = (
            "source candle count is not divisible by the derivation ratio "
            "(trailing partial bucket is not allowed)"
        )
        raise ResamplingValidationError(msg)
    expected_target_count = len(source) // ratio
    if len(target) != expected_target_count:
        msg = "target candle count does not match complete-bucket source length"
        raise ResamplingValidationError(msg)

    first_open = source[0].open_time
    if align_floor(first_open, plan.target_timeframe) != first_open:
        msg = "first source candle does not open on a canonical target boundary"
        raise ResamplingValidationError(msg)

    for bucket_index in range(expected_target_count):
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
        expected = aggregate_bucket(
            children,
            target_open=target_open,
            target_timeframe=plan.target_timeframe,
        )
        if target[bucket_index] != expected:
            msg = f"target candles[{bucket_index}] does not match deterministic aggregation"
            raise ResamplingValidationError(msg)

    if source[-1].close_time != target[-1].close_time:
        msg = "final source candle does not close exactly at the final target close_time"
        raise ResamplingValidationError(msg)


def aggregate_complete_buckets(
    source: tuple[Candle, ...],
    *,
    plan: TimeframeDerivationPlan,
) -> tuple[Candle, ...]:
    """Aggregate complete source buckets into target candles (caller pre-validated)."""
    ratio = plan.ratio
    target_duration = timeframe_duration(plan.target_timeframe)
    first_open = source[0].open_time
    targets: list[Candle] = []
    for bucket_index in range(len(source) // ratio):
        start = bucket_index * ratio
        children = source[start : start + ratio]
        target_open = first_open + bucket_index * target_duration
        targets.append(
            aggregate_bucket(
                children,
                target_open=target_open,
                target_timeframe=plan.target_timeframe,
            )
        )
    return tuple(targets)


@dataclass(frozen=True, slots=True, init=False)
class ResampledCandleSeries:
    """Deterministic complete-bucket resampling result with computed metadata."""

    symbol: Symbol
    source_timeframe: Timeframe
    target_timeframe: Timeframe
    candles: tuple[Candle, ...]
    ratio: int
    source_candle_count: int
    source_minimum_open_time: datetime
    source_maximum_open_time: datetime
    source_candle_sha256: str
    target_candle_count: int
    target_minimum_open_time: datetime
    target_maximum_open_time: datetime
    target_candle_sha256: str

    def __init__(self, *args: object, **kwargs: object) -> None:
        msg = "ResampledCandleSeries must be created via from_verified_series"
        raise ResamplingValidationError(msg)

    @classmethod
    def from_verified_series(
        cls,
        *,
        symbol: Symbol,
        plan: TimeframeDerivationPlan,
        source_candles: tuple[Candle, ...],
        target_candles: tuple[Candle, ...],
    ) -> ResampledCandleSeries:
        """
        Build a result only after revalidating source/target tuples and bucket equality.

        Counts, bounds, ratio, and hashes are computed — never caller-supplied.
        """
        if not isinstance(symbol, Symbol):
            msg = "symbol must be a Symbol"
            raise ResamplingValidationError(msg)
        if not isinstance(plan, TimeframeDerivationPlan):
            msg = "plan must be a TimeframeDerivationPlan"
            raise ResamplingValidationError(msg)
        plan = derive_timeframe_plan(plan.source_timeframe, plan.target_timeframe)

        source = require_canonical_series(
            source_candles, timeframe=plan.source_timeframe, label="source"
        )
        target = require_canonical_series(
            target_candles, timeframe=plan.target_timeframe, label="target"
        )
        verify_complete_bucket_relationship(source, target, plan=plan)

        self = object.__new__(cls)
        object.__setattr__(self, "symbol", symbol)
        object.__setattr__(self, "source_timeframe", plan.source_timeframe)
        object.__setattr__(self, "target_timeframe", plan.target_timeframe)
        object.__setattr__(self, "candles", target)
        object.__setattr__(self, "ratio", plan.ratio)
        object.__setattr__(self, "source_candle_count", len(source))
        object.__setattr__(self, "source_minimum_open_time", source[0].open_time)
        object.__setattr__(self, "source_maximum_open_time", source[-1].open_time)
        object.__setattr__(self, "source_candle_sha256", hash_candle_tuple(source))
        object.__setattr__(self, "target_candle_count", len(target))
        object.__setattr__(self, "target_minimum_open_time", target[0].open_time)
        object.__setattr__(self, "target_maximum_open_time", target[-1].open_time)
        object.__setattr__(self, "target_candle_sha256", hash_candle_tuple(target))
        return self
