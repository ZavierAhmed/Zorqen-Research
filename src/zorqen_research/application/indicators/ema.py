"""Close-price exponential moving average."""

from __future__ import annotations

from decimal import Decimal

from zorqen_research.application.indicators.assembly import _calculated_indicator_series
from zorqen_research.domain.indicators.enums import IndicatorCode
from zorqen_research.domain.indicators.inputs import IndicatorInput
from zorqen_research.domain.indicators.math_policy import (
    default_math_policy,
    require_period,
)
from zorqen_research.domain.indicators.results import IndicatorSeries


def ema_close(indicator_input: IndicatorInput, period: object) -> IndicatorSeries:
    """Compute close EMA with SMA seed and recursive update under the fixed policy."""
    period_i = require_period(period)
    candles = indicator_input.candles
    n = len(candles)
    policy = default_math_policy()
    values: list[Decimal | None] = [None] * n

    with policy.local_decimal_context():
        if period_i == 1:
            for index, candle in enumerate(candles):
                values[index] = candle.close
        elif period_i > n:
            pass
        else:
            seed_sum = Decimal("0")
            for index in range(period_i):
                seed_sum += candles[index].close
            seed = seed_sum / Decimal(period_i)
            values[period_i - 1] = seed
            alpha = Decimal(2) / Decimal(period_i + 1)
            previous = seed
            for index in range(period_i, n):
                close = candles[index].close
                previous = previous + alpha * (close - previous)
                values[index] = previous

    return _calculated_indicator_series(
        indicator_code=IndicatorCode.EMA_CLOSE,
        indicator_input=indicator_input,
        parameters={"period": period_i},
        values=tuple(values),
        math_policy=policy,
    )
