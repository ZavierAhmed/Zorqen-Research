"""True Range and Wilder Average True Range."""

from __future__ import annotations

from decimal import Decimal

from zorqen_research.domain.indicators.enums import IndicatorCode
from zorqen_research.domain.indicators.inputs import IndicatorInput
from zorqen_research.domain.indicators.math_policy import (
    default_math_policy,
    require_period,
)
from zorqen_research.domain.indicators.results import IndicatorSeries


def _true_range_values(indicator_input: IndicatorInput) -> tuple[Decimal, ...]:
    candles = indicator_input.candles
    policy = default_math_policy()
    out: list[Decimal] = []
    with policy.local_decimal_context():
        first = candles[0]
        out.append(first.high - first.low)
        previous_close = first.close
        for candle in candles[1:]:
            range_hl = candle.high - candle.low
            range_hc = abs(candle.high - previous_close)
            range_lc = abs(candle.low - previous_close)
            tr = range_hl
            if range_hc > tr:
                tr = range_hc
            if range_lc > tr:
                tr = range_lc
            out.append(tr)
            previous_close = candle.close
    return tuple(out)


def true_range(indicator_input: IndicatorInput) -> IndicatorSeries:
    """Compute True Range for every candle (defined from index 0)."""
    tr_values = _true_range_values(indicator_input)
    return IndicatorSeries.from_calculation(
        indicator_code=IndicatorCode.TRUE_RANGE,
        indicator_input=indicator_input,
        parameters={},
        values=tr_values,
        math_policy=default_math_policy(),
    )


def wilder_atr(indicator_input: IndicatorInput, period: object) -> IndicatorSeries:
    """Compute Wilder ATR composing canonical True Range semantics."""
    period_i = require_period(period)
    tr_values = _true_range_values(indicator_input)
    n = len(tr_values)
    policy = default_math_policy()
    values: list[Decimal | None] = [None] * n

    with policy.local_decimal_context():
        if period_i == 1:
            for index, tr in enumerate(tr_values):
                values[index] = tr
        elif period_i > n:
            pass
        else:
            seed_sum = Decimal("0")
            for index in range(period_i):
                seed_sum += tr_values[index]
            atr = seed_sum / Decimal(period_i)
            values[period_i - 1] = atr
            period_dec = Decimal(period_i)
            period_minus_one = Decimal(period_i - 1)
            for index in range(period_i, n):
                atr = (atr * period_minus_one + tr_values[index]) / period_dec
                values[index] = atr

    return IndicatorSeries.from_calculation(
        indicator_code=IndicatorCode.WILDER_ATR,
        indicator_input=indicator_input,
        parameters={"period": period_i},
        values=tuple(values),
        math_policy=policy,
    )
