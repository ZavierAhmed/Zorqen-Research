"""IndicatorSeriesBundle integrity tests."""

from __future__ import annotations

from decimal import Decimal

import pytest

from tests.unit.indicator_helpers import SYMBOL, TIMEFRAME, indicator_input_from_specs
from zorqen_research.application.indicators.ema import ema_close
from zorqen_research.application.indicators.volatility import true_range, wilder_atr
from zorqen_research.domain.indicator_views.bundles import IndicatorSeriesBundle
from zorqen_research.domain.indicator_views.errors import IndicatorViewValidationError
from zorqen_research.domain.indicators.enums import IndicatorCode
from zorqen_research.domain.indicators.inputs import IndicatorInput
from zorqen_research.domain.indicators.results import IndicatorSeries
from zorqen_research.domain.symbols import Symbol
from zorqen_research.domain.timeframes import Timeframe


def _specs() -> tuple[tuple[str, str, str, str], ...]:
    return (
        ("10", "11", "9", "10"),
        ("11", "12", "10", "11"),
        ("12", "13", "11", "12"),
        ("13", "14", "12", "13"),
        ("14", "15", "13", "14"),
    )


def test_exact_valid_bundle() -> None:
    indicator_input = indicator_input_from_specs(_specs())
    ema = ema_close(indicator_input, 3)
    atr = wilder_atr(indicator_input, 3)
    bundle = IndicatorSeriesBundle.from_verified(
        indicator_input=indicator_input,
        series=(atr, ema),
    )
    assert bundle.series_count == 2
    assert bundle.series[0].indicator_code is IndicatorCode.EMA_CLOSE
    assert bundle.series[1].indicator_code is IndicatorCode.WILDER_ATR
    assert len(bundle.bundle_hash) == 64
    assert bundle.input_candle_count == 5
    assert bundle.input_candle_hash == indicator_input.candle_sha256
    assert bundle.input_hash == indicator_input.input_hash


def test_empty_series_tuple_rejected() -> None:
    indicator_input = indicator_input_from_specs(_specs())
    with pytest.raises(IndicatorViewValidationError, match="at least one"):
        IndicatorSeriesBundle.from_verified(indicator_input=indicator_input, series=())


def test_mutable_series_list_rejected() -> None:
    indicator_input = indicator_input_from_specs(_specs())
    series = ema_close(indicator_input, 3)
    with pytest.raises(IndicatorViewValidationError, match="exact tuple"):
        IndicatorSeriesBundle.from_verified(
            indicator_input=indicator_input,
            series=[series],  # type: ignore[arg-type]
        )


def test_tuple_subclass_rejected() -> None:
    class SeriesTuple(tuple):
        pass

    indicator_input = indicator_input_from_specs(_specs())
    series = ema_close(indicator_input, 3)
    with pytest.raises(IndicatorViewValidationError, match="exact tuple"):
        IndicatorSeriesBundle.from_verified(
            indicator_input=indicator_input,
            series=SeriesTuple((series,)),
        )


def test_non_indicator_series_item_rejected() -> None:
    indicator_input = indicator_input_from_specs(_specs())
    with pytest.raises(IndicatorViewValidationError, match="exact IndicatorSeries"):
        IndicatorSeriesBundle.from_verified(
            indicator_input=indicator_input,
            series=("not-a-series",),  # type: ignore[arg-type]
        )


def test_series_from_another_symbol_rejected() -> None:
    specs = _specs()
    left = IndicatorInput.from_verified(
        symbol=SYMBOL,
        timeframe=TIMEFRAME,
        candles=indicator_input_from_specs(specs).candles,
    )
    right = IndicatorInput.from_verified(
        symbol=Symbol(value="ETHUSDT"),
        timeframe=TIMEFRAME,
        candles=indicator_input_from_specs(specs).candles,
    )
    with pytest.raises(IndicatorViewValidationError, match="symbol"):
        IndicatorSeriesBundle.from_verified(
            indicator_input=left,
            series=(ema_close(right, 3),),
        )


def test_series_from_another_timeframe_rejected() -> None:
    from tests.unit.indicator_helpers import candle_series

    specs = _specs()
    left = IndicatorInput.from_verified(
        symbol=SYMBOL,
        timeframe=TIMEFRAME,
        candles=candle_series(specs, timeframe=TIMEFRAME),
    )
    right = IndicatorInput.from_verified(
        symbol=SYMBOL,
        timeframe=Timeframe.M5,
        candles=candle_series(specs, timeframe=Timeframe.M5),
    )
    with pytest.raises(IndicatorViewValidationError, match="timeframe"):
        IndicatorSeriesBundle.from_verified(
            indicator_input=left,
            series=(ema_close(right, 3),),
        )


def test_series_from_another_candle_tuple_rejected() -> None:
    left = indicator_input_from_specs(_specs())
    right = indicator_input_from_specs(
        (
            ("10", "11", "9", "10"),
            ("11", "12", "10", "11"),
            ("12", "13", "11", "12"),
            ("13", "14", "12", "13"),
            ("99", "100", "98", "99"),
        )
    )
    with pytest.raises(IndicatorViewValidationError, match="candle hash"):
        IndicatorSeriesBundle.from_verified(
            indicator_input=left,
            series=(ema_close(right, 3),),
        )


def test_candle_count_mismatch_rejected() -> None:
    left = indicator_input_from_specs(_specs())
    right = indicator_input_from_specs(_specs()[:3])
    with pytest.raises(IndicatorViewValidationError, match="candle count|candle hash"):
        IndicatorSeriesBundle.from_verified(
            indicator_input=left,
            series=(ema_close(right, 2),),
        )


def test_result_hash_mismatch_rejected() -> None:
    indicator_input = indicator_input_from_specs(_specs())
    series = ema_close(indicator_input, 3)
    object.__setattr__(series, "result_hash", "0" * 64)
    with pytest.raises(IndicatorViewValidationError, match="result hash"):
        IndicatorSeriesBundle.from_verified(
            indicator_input=indicator_input,
            series=(series,),
        )


def test_duplicate_key_rejected() -> None:
    indicator_input = indicator_input_from_specs(_specs())
    series = ema_close(indicator_input, 3)
    with pytest.raises(IndicatorViewValidationError, match="duplicate"):
        IndicatorSeriesBundle.from_verified(
            indicator_input=indicator_input,
            series=(series, series),
        )


def test_canonical_series_ordering() -> None:
    indicator_input = indicator_input_from_specs(_specs())
    tr = true_range(indicator_input)
    ema4 = ema_close(indicator_input, 4)
    ema2 = ema_close(indicator_input, 2)
    atr = wilder_atr(indicator_input, 3)
    bundle = IndicatorSeriesBundle.from_verified(
        indicator_input=indicator_input,
        series=(atr, ema4, tr, ema2),
    )
    codes = [key.indicator_code for key in bundle.series_keys]
    assert codes == [
        IndicatorCode.EMA_CLOSE,
        IndicatorCode.EMA_CLOSE,
        IndicatorCode.TRUE_RANGE,
        IndicatorCode.WILDER_ATR,
    ]
    assert bundle.series_keys[0].parameters == (("period", 2),)
    assert bundle.series_keys[1].parameters == (("period", 4),)


def test_direct_forged_bundle_construction_fails() -> None:
    with pytest.raises(IndicatorViewValidationError, match="from_verified"):
        IndicatorSeriesBundle()
    forged = object.__new__(IndicatorSeriesBundle)
    with pytest.raises(IndicatorViewValidationError):
        # Incomplete forged objects must not be usable as accepted bundles.
        from zorqen_research.application.indicator_views.feed import IndicatorDecisionFeed

        IndicatorDecisionFeed.from_bundle(forged)


def test_caller_cannot_supply_false_counts() -> None:
    indicator_input = indicator_input_from_specs(_specs())
    bundle = IndicatorSeriesBundle.from_verified(
        indicator_input=indicator_input,
        series=(ema_close(indicator_input, 3),),
    )
    assert bundle.series_count == 1
    assert len(bundle.series_keys) == 1
    assert type(bundle.series) is tuple
    assert type(bundle.series[0]) is IndicatorSeries
    assert Decimal("11") in (v for v in bundle.series[0].values if v is not None)
