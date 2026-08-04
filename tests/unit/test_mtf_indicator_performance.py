"""Structural constant-time proofs for composed MTF indicator views."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from decimal import Decimal

from zorqen_research.application.indicators.ema import ema_close
from zorqen_research.application.market_data.goldens import make_candle
from zorqen_research.application.strategy_backtesting.goldens import mtf_definition
from zorqen_research.application.strategy_backtesting.indicator_feed import (
    MultiTimeframeIndicatorDecisionFeed,
)
from zorqen_research.application.strategy_definitions.serialization import build_instance
from zorqen_research.domain.indicator_views.bundles import IndicatorSeriesBundle
from zorqen_research.domain.indicators.inputs import IndicatorInput
from zorqen_research.domain.strategy_backtesting.indicator_composition import (
    MultiTimeframeIndicatorInput,
)
from zorqen_research.domain.strategy_backtesting.inputs import MultiTimeframeBacktestInput
from zorqen_research.domain.strategy_definitions.timeframes import TimeframeRequirement
from zorqen_research.domain.symbols import Symbol
from zorqen_research.domain.timeframes import Timeframe, timeframe_duration


class InstrumentedValues(Sequence[Decimal | None]):
    def __init__(self, values: tuple[Decimal | None, ...]) -> None:
        self._values = values
        self.access_count = 0
        self.slice_count = 0
        self.iter_count = 0

    def __len__(self) -> int:
        return len(self._values)

    def __getitem__(self, key):  # noqa: ANN001
        if isinstance(key, slice):
            self.slice_count += 1
            return self._values[key]
        self.access_count += 1
        return self._values[key]

    def __iter__(self):
        self.iter_count += 1
        return iter(self._values)


def _long_composition(
    count: int = 100_001,
) -> tuple[
    MultiTimeframeIndicatorDecisionFeed,
    InstrumentedValues,
]:
    """Build H1/H4 composition with instrumented execution EMA values."""
    start = datetime(2020, 1, 1, tzinfo=UTC)
    step = timeframe_duration(Timeframe.H1)
    execution = tuple(
        make_candle(
            start + index * step,
            timeframe=Timeframe.H1,
            open=Decimal("10"),
            high=Decimal("11"),
            low=Decimal("9"),
            close=Decimal("10"),
        )
        for index in range(count)
    )
    # Enough H4 candles for alignment across the full H1 series.
    h4_count = count // 4
    h4_step = timeframe_duration(Timeframe.H4)
    context = tuple(
        make_candle(
            start + index * h4_step,
            timeframe=Timeframe.H4,
            open=Decimal("10"),
            high=Decimal("11"),
            low=Decimal("9"),
            close=Decimal("10"),
        )
        for index in range(h4_count)
    )
    definition = mtf_definition(
        execution_warmup=1,
        contexts=(TimeframeRequirement(timeframe=Timeframe.H4, warmup_bars=1),),
        definition_code="mtf_ind_perf",
    )
    instance = build_instance(definition, {"signal_strength": 1})
    mtf = MultiTimeframeBacktestInput.from_verified(
        strategy_instance=instance,
        symbol=Symbol(value="BTCUSDT"),
        execution_candles=execution,
        context_series=((Timeframe.H4, context),),
    )
    indicator_input = IndicatorInput.from_verified(
        symbol=Symbol(value="BTCUSDT"),
        timeframe=Timeframe.H1,
        candles=execution,
    )
    series = ema_close(indicator_input, 1)
    bundle = IndicatorSeriesBundle.from_verified(
        indicator_input=indicator_input,
        series=(series,),
    )
    composition = MultiTimeframeIndicatorInput.from_verified(
        input_bundle=mtf,
        execution_indicators=bundle,
        context_indicators=(None,),
    )
    feed = MultiTimeframeIndicatorDecisionFeed.from_composition(composition)
    instrumented = InstrumentedValues(series.values)
    assert feed._execution_indicator_feed is not None
    source = feed._execution_indicator_feed._sources[0]
    object.__setattr__(source, "_values", instrumented)
    return feed, instrumented


def test_mtf_indicator_view_at_constant_work_independent_of_bar_index() -> None:
    feed, instrumented = _long_composition()
    # Prefix hashes prepared once at feed creation.
    assert feed._execution_indicator_feed is not None
    before_prefixes = feed._execution_indicator_feed._sources[0]._prefix_hashes
    baseline = (instrumented.access_count, instrumented.slice_count, instrumented.iter_count)
    view_small = feed.view_at(10)
    after_small = (instrumented.access_count, instrumented.slice_count, instrumented.iter_count)
    view_large = feed.view_at(100_000)
    after_large = (instrumented.access_count, instrumented.slice_count, instrumented.iter_count)

    small_delta = tuple(a - b for a, b in zip(after_small, baseline, strict=True))
    large_delta = tuple(a - b for a, b in zip(after_large, after_small, strict=True))
    assert small_delta == large_delta
    assert small_delta[1] == 0  # no slicing
    assert small_delta[2] == 0  # no iteration
    assert feed._execution_indicator_feed._sources[0]._prefix_hashes is before_prefixes
    assert view_small.overall_ready is True
    assert view_large.base_view.execution_bar_index == 100_000
