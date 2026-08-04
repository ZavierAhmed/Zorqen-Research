"""Closed deterministic recalculation of trusted indicator series."""

from __future__ import annotations

from zorqen_research.application.indicators.ema import ema_close
from zorqen_research.application.indicators.extrema import (
    prior_rolling_highest,
    prior_rolling_lowest,
    rolling_highest,
    rolling_lowest,
)
from zorqen_research.application.indicators.volatility import true_range, wilder_atr
from zorqen_research.domain.indicator_views.errors import IndicatorViewValidationError
from zorqen_research.domain.indicator_views.keys import IndicatorSeriesKey
from zorqen_research.domain.indicators.enums import IndicatorCode
from zorqen_research.domain.indicators.inputs import IndicatorInput
from zorqen_research.domain.indicators.results import IndicatorSeries


def recalculate_indicator_series(
    *,
    indicator_input: IndicatorInput,
    series_key: IndicatorSeriesKey,
) -> IndicatorSeries:
    """
    Recalculate one series from candles via the closed calculator set.

    No dynamic imports, registries, or caller-supplied values.
    """
    if type(indicator_input) is not IndicatorInput:
        msg = "indicator_input must be an exact IndicatorInput"
        raise IndicatorViewValidationError(msg)
    if type(series_key) is not IndicatorSeriesKey:
        msg = "series_key must be an exact IndicatorSeriesKey"
        raise IndicatorViewValidationError(msg)

    code = series_key.indicator_code
    if code is IndicatorCode.TRUE_RANGE:
        if series_key.parameters:
            msg = "true_range recalculation requires no period"
            raise IndicatorViewValidationError(msg)
        return true_range(indicator_input)

    if len(series_key.parameters) != 1 or series_key.parameters[0][0] != "period":
        msg = "period indicator recalculation requires exactly period"
        raise IndicatorViewValidationError(msg)
    period = series_key.parameters[0][1]

    if code is IndicatorCode.EMA_CLOSE:
        return ema_close(indicator_input, period)
    if code is IndicatorCode.WILDER_ATR:
        return wilder_atr(indicator_input, period)
    if code is IndicatorCode.ROLLING_HIGHEST:
        return rolling_highest(indicator_input, period)
    if code is IndicatorCode.ROLLING_LOWEST:
        return rolling_lowest(indicator_input, period)
    if code is IndicatorCode.PRIOR_ROLLING_HIGHEST:
        return prior_rolling_highest(indicator_input, period)
    if code is IndicatorCode.PRIOR_ROLLING_LOWEST:
        return prior_rolling_lowest(indicator_input, period)

    msg = "unsupported indicator code for recalculation"
    raise IndicatorViewValidationError(msg)
