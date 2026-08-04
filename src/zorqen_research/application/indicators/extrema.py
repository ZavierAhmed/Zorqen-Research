"""Inclusive and prior-window rolling extrema (monotonic deque, O(n))."""

from __future__ import annotations

from collections import deque
from decimal import Decimal

from zorqen_research.application.indicators.assembly import _calculated_indicator_series
from zorqen_research.domain.indicators.enums import IndicatorCode
from zorqen_research.domain.indicators.inputs import IndicatorInput
from zorqen_research.domain.indicators.math_policy import (
    default_math_policy,
    require_period,
)
from zorqen_research.domain.indicators.results import IndicatorSeries


class CountingSequence:
    """Instrumented sequence wrapper for structural complexity tests."""

    def __init__(self, values: tuple[Decimal, ...]) -> None:
        self._values = values
        self.reads = 0

    def __len__(self) -> int:
        return len(self._values)

    def __getitem__(self, index: int) -> Decimal:
        self.reads += 1
        return self._values[index]


def _rolling_extrema(
    series: CountingSequence | tuple[Decimal, ...],
    period: int,
    *,
    want_max: bool,
) -> tuple[Decimal | None, ...]:
    n = len(series)
    out: list[Decimal | None] = [None] * n
    if period > n:
        return tuple(out)

    # Monotonic deque of indices; front is extreme of the current window.
    window: deque[int] = deque()
    for index in range(n):
        value = series[index]
        if want_max:
            while window and series[window[-1]] <= value:
                window.pop()
        else:
            while window and series[window[-1]] >= value:
                window.pop()
        window.append(index)
        left = index - period + 1
        if left < 0:
            continue
        while window and window[0] < left:
            window.popleft()
        out[index] = series[window[0]]
    return tuple(out)


def _prior_extrema(
    series: CountingSequence | tuple[Decimal, ...],
    period: int,
    *,
    want_max: bool,
) -> tuple[Decimal | None, ...]:
    """
    Prior-window extrema: at index i (>= period), use candles [i-period, i-1].

    Current candle is excluded. Indexes 0..period-1 remain undefined.
    """
    n = len(series)
    out: list[Decimal | None] = [None] * n
    if n <= period:
        return tuple(out)

    window: deque[int] = deque()
    # Seed deque with the first ``period`` candles (indices 0..period-1).
    for index in range(period):
        value = series[index]
        if want_max:
            while window and series[window[-1]] <= value:
                window.pop()
        else:
            while window and series[window[-1]] >= value:
                window.pop()
        window.append(index)
    out[period] = series[window[0]]

    for index in range(period, n - 1):
        # Slide: drop index-period, add index (which becomes the new right edge
        # of the prior window for output at index+1).
        left = index - period + 1
        while window and window[0] < left:
            window.popleft()
        value = series[index]
        if want_max:
            while window and series[window[-1]] <= value:
                window.pop()
        else:
            while window and series[window[-1]] >= value:
                window.pop()
        window.append(index)
        out[index + 1] = series[window[0]]
    return tuple(out)


def rolling_highest(indicator_input: IndicatorInput, period: object) -> IndicatorSeries:
    period_i = require_period(period)
    highs = tuple(c.high for c in indicator_input.candles)
    values = _rolling_extrema(highs, period_i, want_max=True)
    return _calculated_indicator_series(
        indicator_code=IndicatorCode.ROLLING_HIGHEST,
        indicator_input=indicator_input,
        parameters={"period": period_i},
        values=values,
        math_policy=default_math_policy(),
    )


def rolling_lowest(indicator_input: IndicatorInput, period: object) -> IndicatorSeries:
    period_i = require_period(period)
    lows = tuple(c.low for c in indicator_input.candles)
    values = _rolling_extrema(lows, period_i, want_max=False)
    return _calculated_indicator_series(
        indicator_code=IndicatorCode.ROLLING_LOWEST,
        indicator_input=indicator_input,
        parameters={"period": period_i},
        values=values,
        math_policy=default_math_policy(),
    )


def prior_rolling_highest(indicator_input: IndicatorInput, period: object) -> IndicatorSeries:
    period_i = require_period(period)
    highs = tuple(c.high for c in indicator_input.candles)
    values = _prior_extrema(highs, period_i, want_max=True)
    return _calculated_indicator_series(
        indicator_code=IndicatorCode.PRIOR_ROLLING_HIGHEST,
        indicator_input=indicator_input,
        parameters={"period": period_i},
        values=values,
        math_policy=default_math_policy(),
    )


def prior_rolling_lowest(indicator_input: IndicatorInput, period: object) -> IndicatorSeries:
    period_i = require_period(period)
    lows = tuple(c.low for c in indicator_input.candles)
    values = _prior_extrema(lows, period_i, want_max=False)
    return _calculated_indicator_series(
        indicator_code=IndicatorCode.PRIOR_ROLLING_LOWEST,
        indicator_input=indicator_input,
        parameters={"period": period_i},
        values=values,
        math_policy=default_math_policy(),
    )


def rolling_highest_counted(series: CountingSequence, period: int) -> tuple[Decimal | None, ...]:
    """Test helper: rolling highest over an instrumented sequence."""
    return _rolling_extrema(series, period, want_max=True)


def prior_rolling_highest_counted(
    series: CountingSequence, period: int
) -> tuple[Decimal | None, ...]:
    """Test helper: prior rolling highest over an instrumented sequence."""
    return _prior_extrema(series, period, want_max=True)
