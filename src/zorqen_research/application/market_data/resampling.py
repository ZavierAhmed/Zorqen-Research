"""Application facade for deterministic candle resampling."""

from __future__ import annotations

from zorqen_research.domain.candles import Candle
from zorqen_research.domain.market_data.derivation import (
    TimeframeDerivationPlan,
    derive_timeframe_plan,
)
from zorqen_research.domain.market_data.resampling import resample_candles as _resample
from zorqen_research.domain.market_data.series import ResampledCandleSeries
from zorqen_research.domain.symbols import Symbol
from zorqen_research.domain.timeframes import Timeframe


def resample(
    candles: tuple[Candle, ...],
    *,
    symbol: Symbol,
    source_timeframe: Timeframe,
    target_timeframe: Timeframe,
    expected_source_sha256: str | None = None,
) -> ResampledCandleSeries:
    plan = derive_timeframe_plan(source_timeframe, target_timeframe)
    return _resample(
        candles,
        symbol=symbol,
        plan=plan,
        expected_source_sha256=expected_source_sha256,
    )


def resample_with_plan(
    candles: tuple[Candle, ...],
    *,
    symbol: Symbol,
    plan: TimeframeDerivationPlan,
    expected_source_sha256: str | None = None,
) -> ResampledCandleSeries:
    return _resample(
        candles,
        symbol=symbol,
        plan=plan,
        expected_source_sha256=expected_source_sha256,
    )
