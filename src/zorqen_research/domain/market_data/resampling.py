"""Strict complete-bucket candle resampling."""

from __future__ import annotations

from zorqen_research.domain.candles import Candle
from zorqen_research.domain.market_data.derivation import (
    TimeframeDerivationPlan,
    derive_timeframe_plan,
)
from zorqen_research.domain.market_data.errors import ResamplingValidationError
from zorqen_research.domain.market_data.hashes import hash_candle_tuple
from zorqen_research.domain.market_data.series import (
    ResampledCandleSeries,
    aggregate_complete_buckets,
    require_canonical_series,
)
from zorqen_research.domain.symbols import Symbol
from zorqen_research.domain.timeframes import align_floor, timeframe_duration


def resample_candles(
    candles: tuple[Candle, ...],
    *,
    symbol: Symbol,
    plan: TimeframeDerivationPlan,
    expected_source_sha256: str | None = None,
) -> ResampledCandleSeries:
    """
    Resample a gap-free source series into complete target buckets only.

    Always hashes with the canonical candle CSV serializer. Optional
    ``expected_source_sha256`` is an input integrity check only.
    """
    if not isinstance(symbol, Symbol):
        msg = "symbol must be a Symbol"
        raise ResamplingValidationError(msg)
    if not isinstance(plan, TimeframeDerivationPlan):
        msg = "plan must be a TimeframeDerivationPlan"
        raise ResamplingValidationError(msg)
    plan = derive_timeframe_plan(plan.source_timeframe, plan.target_timeframe)

    source = require_canonical_series(candles, timeframe=plan.source_timeframe, label="source")
    source_digest = hash_candle_tuple(source)
    if expected_source_sha256 is not None and expected_source_sha256 != source_digest:
        msg = "supplied source candle hash does not match canonical CSV bytes"
        raise ResamplingValidationError(msg)

    if len(source) % plan.ratio != 0:
        msg = (
            "source candle count is not divisible by the derivation ratio "
            "(trailing partial bucket is not allowed)"
        )
        raise ResamplingValidationError(msg)

    first_open = source[0].open_time
    if align_floor(first_open, plan.target_timeframe) != first_open:
        msg = "first source candle does not open on a canonical target boundary"
        raise ResamplingValidationError(msg)

    # Pre-check child placement before aggregation (fail message parity).
    source_duration = timeframe_duration(plan.source_timeframe)
    target_duration = timeframe_duration(plan.target_timeframe)
    ratio = plan.ratio
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

    target_tuple = aggregate_complete_buckets(source, plan=plan)
    return ResampledCandleSeries.from_verified_series(
        symbol=symbol,
        plan=plan,
        source_candles=source,
        target_candles=target_tuple,
    )
