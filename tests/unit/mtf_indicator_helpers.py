"""Shared fixtures for Milestone 1.2 MTF indicator composition tests."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from zorqen_research.application.indicators.ema import ema_close
from zorqen_research.application.market_data.goldens import build_source_series
from zorqen_research.application.strategy_backtesting.goldens import mtf_definition
from zorqen_research.application.strategy_definitions.serialization import build_instance
from zorqen_research.domain.candles import Candle
from zorqen_research.domain.indicators.inputs import IndicatorInput
from zorqen_research.domain.strategy_definitions.timeframes import TimeframeRequirement
from zorqen_research.domain.symbols import Symbol
from zorqen_research.domain.timeframes import Timeframe

if TYPE_CHECKING:
    from zorqen_research.domain.indicator_views.bundles import IndicatorSeriesBundle
    from zorqen_research.domain.strategy_backtesting.indicator_composition import (
        MultiTimeframeIndicatorInput,
    )
    from zorqen_research.domain.strategy_backtesting.inputs import MultiTimeframeBacktestInput

SYMBOL = Symbol(value="BTCUSDT")
START = datetime(2024, 1, 1, tzinfo=UTC)


def standard_mtf(
    *,
    execution_count: int = 8,
    context_count: int = 2,
    execution_warmup: int = 4,
    definition_code: str = "mtf_ind_test",
) -> tuple[MultiTimeframeBacktestInput, tuple[Candle, ...], tuple[Candle, ...]]:
    from zorqen_research.domain.strategy_backtesting.inputs import MultiTimeframeBacktestInput

    definition = mtf_definition(
        execution_warmup=execution_warmup,
        contexts=(TimeframeRequirement(timeframe=Timeframe.H4, warmup_bars=1),),
        definition_code=definition_code,
    )
    instance = build_instance(definition, {"signal_strength": 1})
    execution = build_source_series(start=START, timeframe=Timeframe.H1, count=execution_count)
    context = build_source_series(start=START, timeframe=Timeframe.H4, count=context_count)
    bundle = MultiTimeframeBacktestInput.from_verified(
        strategy_instance=instance,
        symbol=SYMBOL,
        execution_candles=execution,
        context_series=((Timeframe.H4, context),),
    )
    return bundle, execution, context


def indicator_bundle_for(
    candles: tuple[Candle, ...],
    timeframe: Timeframe,
    *,
    period: int = 1,
) -> IndicatorSeriesBundle:
    from zorqen_research.domain.indicator_views.bundles import IndicatorSeriesBundle

    indicator_input = IndicatorInput.from_verified(
        symbol=SYMBOL,
        timeframe=timeframe,
        candles=candles,
    )
    return IndicatorSeriesBundle.from_verified(
        indicator_input=indicator_input,
        series=(ema_close(indicator_input, period),),
    )


def standard_composition(
    *,
    period: int = 1,
) -> MultiTimeframeIndicatorInput:
    from zorqen_research.domain.strategy_backtesting.indicator_composition import (
        MultiTimeframeIndicatorInput,
    )

    mtf, execution, _context = standard_mtf()
    exec_ind = indicator_bundle_for(execution, Timeframe.H1, period=period)
    return MultiTimeframeIndicatorInput.from_verified(
        input_bundle=mtf,
        execution_indicators=exec_ind,
        context_indicators=(None,),
    )
