"""Structural constant-time proofs for indicator decision views."""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal

from tests.unit.indicator_helpers import candle_series, utc
from zorqen_research.application.indicator_views.feed import IndicatorDecisionFeed
from zorqen_research.application.indicators.ema import ema_close
from zorqen_research.domain.indicator_views.bundles import IndicatorSeriesBundle
from zorqen_research.domain.indicator_views.histories import VisibleIndicatorHistory
from zorqen_research.domain.indicators.enums import IndicatorCode
from zorqen_research.domain.indicators.inputs import IndicatorInput
from zorqen_research.domain.symbols import Symbol
from zorqen_research.domain.timeframes import Timeframe


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


def _large_feed(count: int = 100_001) -> tuple[IndicatorDecisionFeed, InstrumentedValues]:
    specs = tuple(("10", "11", "9", "10") for _ in range(count))
    candles = candle_series(specs, start=utc(2024, 1, 1), timeframe=Timeframe.M1)
    indicator_input = IndicatorInput.from_verified(
        symbol=Symbol(value="BTCUSDT"),
        timeframe=Timeframe.M1,
        candles=candles,
    )
    series = ema_close(indicator_input, 3)
    bundle = IndicatorSeriesBundle.from_verified(
        indicator_input=indicator_input,
        series=(series,),
    )
    feed = IndicatorDecisionFeed.from_bundle(bundle)
    instrumented = InstrumentedValues(series.values)
    source = feed._sources[0]
    object.__setattr__(source, "_values", instrumented)
    return feed, instrumented


def test_feed_creation_scans_each_series_once_for_prefixes() -> None:
    specs = tuple(("10", "11", "9", "10") for _ in range(20))
    indicator_input = IndicatorInput.from_verified(
        symbol=Symbol(value="BTCUSDT"),
        timeframe=Timeframe.M1,
        candles=candle_series(specs),
    )
    series = ema_close(indicator_input, 3)
    bundle = IndicatorSeriesBundle.from_verified(
        indicator_input=indicator_input,
        series=(series,),
    )
    feed = IndicatorDecisionFeed.from_bundle(bundle)
    assert len(feed._sources) == 1
    assert len(feed._sources[0]._prefix_hashes) == series.value_count + 1
    # Prefix chain prepared once; view_at must not grow the chain.
    before = feed._sources[0]._prefix_hashes
    feed.view_at(5)
    feed.view_at(15)
    assert feed._sources[0]._prefix_hashes is before


def test_view_at_constant_value_reads_independent_of_bar_index() -> None:
    feed, instrumented = _large_feed()
    baseline = (instrumented.access_count, instrumented.slice_count, instrumented.iter_count)
    view_small = feed.view_at(10)
    after_small = (instrumented.access_count, instrumented.slice_count, instrumented.iter_count)
    view_large = feed.view_at(100_000)
    after_large = (instrumented.access_count, instrumented.slice_count, instrumented.iter_count)

    small_delta = tuple(a - b for a, b in zip(after_small, baseline, strict=True))
    large_delta = tuple(a - b for a, b in zip(after_large, after_small, strict=True))
    assert small_delta == large_delta
    # Construction reads latest once per item (ready/latest) — no slicing/iteration.
    assert small_delta[1] == 0
    assert small_delta[2] == 0
    assert small_delta[0] == 1
    assert view_small.visible_count == 11
    assert view_large.visible_count == 100_001
    history = view_small.require(IndicatorCode.EMA_CLOSE, period=3).history
    assert isinstance(history, VisibleIndicatorHistory)
    assert history._source._values is instrumented


def test_bounded_slice_costs_only_returned_values() -> None:
    feed, instrumented = _large_feed(count=50)
    history = feed.view_at(20).require(IndicatorCode.EMA_CLOSE, period=3).history
    before = instrumented.access_count
    sliced = history[5:10]
    assert len(sliced) == 5
    assert instrumented.access_count - before == 5
    assert instrumented.slice_count == 0
