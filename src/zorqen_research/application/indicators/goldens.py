"""Frozen literal golden expectations for indicator series.

Literal constants only — do not invoke production indicator functions to
derive expected values or hashes at import time.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from zorqen_research.application.indicators.ema import ema_close
from zorqen_research.application.indicators.extrema import (
    prior_rolling_highest,
    prior_rolling_lowest,
    rolling_highest,
    rolling_lowest,
)
from zorqen_research.application.indicators.volatility import true_range, wilder_atr
from zorqen_research.application.market_data.serialization import format_canonical_decimal
from zorqen_research.domain.candles import Candle
from zorqen_research.domain.indicators.inputs import IndicatorInput
from zorqen_research.domain.indicators.results import IndicatorSeries
from zorqen_research.domain.symbols import Symbol
from zorqen_research.domain.timeframes import Timeframe, timeframe_duration

SYMBOL = Symbol(value="BTCUSDT")
TIMEFRAME = Timeframe.M1


def _utc(year: int, month: int, day: int, hour: int = 0, minute: int = 0) -> datetime:
    return datetime(year, month, day, hour, minute, tzinfo=UTC)


def make_candle(
    open_time: datetime,
    *,
    open: str,
    high: str,
    low: str,
    close: str,
) -> Candle:
    return Candle(
        open_time=open_time,
        open=Decimal(open),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
        volume=Decimal("1"),
        close_time=open_time + timeframe_duration(TIMEFRAME) - timedelta(milliseconds=1),
        quote_asset_volume=Decimal("10"),
        trade_count=1,
        taker_buy_base_volume=Decimal("0.4"),
        taker_buy_quote_volume=Decimal("4"),
    )


_START = _utc(2024, 1, 1)
_STEP = timeframe_duration(TIMEFRAME)


def _series(
    specs: tuple[tuple[str, str, str, str], ...],
) -> tuple[Candle, ...]:
    return tuple(
        make_candle(
            _START + index * _STEP,
            open=open_,
            high=high,
            low=low,
            close=close,
        )
        for index, (open_, high, low, close) in enumerate(specs)
    )


EMA_CLOSE_CANDLES = _series(
    (
        ("10", "11", "9", "10"),
        ("11", "12", "10", "11"),
        ("12", "13", "11", "12"),
        ("13", "14", "12", "13"),
        ("14", "15", "13", "14"),
    )
)

TRUE_RANGE_CANDLES = _series(
    (
        ("10", "12", "10", "11"),
        ("14", "16", "14", "15"),
        ("9", "10", "8", "9"),
        ("10", "11", "9", "10"),
    )
)

EXTREMA_CANDLES = _series(
    (
        ("3", "5", "1", "4"),
        ("4", "7", "3", "5"),
        ("5", "7", "2", "6"),
        ("4", "6", "2", "5"),
        ("6", "8", "4", "7"),
    )
)


@dataclass(frozen=True, slots=True)
class IndicatorGoldenExpectation:
    scenario: str
    indicator_code: str
    input_candle_count: int
    input_candle_hash: str
    input_hash: str
    first_defined_index: int | None
    defined_value_count: int
    expected_values: tuple[str | None, ...]
    result_hash: str


@dataclass(frozen=True, slots=True)
class PairedExtremaGoldenExpectation:
    scenario: str
    input_candle_count: int
    input_candle_hash: str
    input_hash: str
    highest_code: str
    lowest_code: str
    highest_first_defined_index: int | None
    lowest_first_defined_index: int | None
    highest_defined_value_count: int
    lowest_defined_value_count: int
    expected_highest: tuple[str | None, ...]
    expected_lowest: tuple[str | None, ...]
    highest_result_hash: str
    lowest_result_hash: str


EMA_CLOSE_GOLDEN = IndicatorGoldenExpectation(
    scenario="ema-close",
    indicator_code="ema_close",
    input_candle_count=5,
    input_candle_hash="3de5c720fdd7bc7d2025a8d88aef4334a18a2314a9d0e4494b716c7ee350b6c9",
    input_hash="4dad6476771ca8af236269b9f2189c56a591ddee909c8524a65ebd1d9bf49cbf",
    first_defined_index=2,
    defined_value_count=3,
    expected_values=(None, None, "11", "12", "13"),
    result_hash="982dcb739655d2eb018e74911c8d53a66a9f86555ffa74aa8111c7134482d303",
)

TRUE_RANGE_GOLDEN = IndicatorGoldenExpectation(
    scenario="true-range",
    indicator_code="true_range",
    input_candle_count=4,
    input_candle_hash="05bbfb97290228e5a9b90a7345a624b9a47bedf25fe05cd3773a62b52e979be4",
    input_hash="0f6634f15b93d16d3deb6b5b12b03e8528f764a018dd47154156586b41ea2585",
    first_defined_index=0,
    defined_value_count=4,
    expected_values=("2", "5", "7", "2"),
    result_hash="4fba21ba2715717330ccf16df77a89ecf2627e7413bfdf833f3136fecb31f938",
)

WILDER_ATR_GOLDEN = IndicatorGoldenExpectation(
    scenario="wilder-atr",
    indicator_code="wilder_atr",
    input_candle_count=4,
    input_candle_hash="05bbfb97290228e5a9b90a7345a624b9a47bedf25fe05cd3773a62b52e979be4",
    input_hash="0f6634f15b93d16d3deb6b5b12b03e8528f764a018dd47154156586b41ea2585",
    first_defined_index=2,
    defined_value_count=2,
    expected_values=(
        None,
        None,
        "4.6666666666666666666666666666666666666666666666667",
        "3.7777777777777777777777777777777777777777777777777",
    ),
    result_hash="0c4b742242ed3ca00527f8ebc1c990d36c7970347692fd235380ffdbb448667e",
)

ROLLING_EXTREMA_GOLDEN = PairedExtremaGoldenExpectation(
    scenario="rolling-extrema",
    input_candle_count=5,
    input_candle_hash="de96bc3d80399720cf94502d131cc5c913c85c457e850aae5ac61da2c075ad38",
    input_hash="01b5bea559269b4e9554c8517e2fc16da3fd6e06098aec3bbe6b266f7944e312",
    highest_code="rolling_highest",
    lowest_code="rolling_lowest",
    highest_first_defined_index=2,
    lowest_first_defined_index=2,
    highest_defined_value_count=3,
    lowest_defined_value_count=3,
    expected_highest=(None, None, "7", "7", "8"),
    expected_lowest=(None, None, "1", "2", "2"),
    highest_result_hash="229d1a35dd067ac1d5e7fd6fe1fd6ee40ca6d91795fa7f4ab7c51f018b9384fa",
    lowest_result_hash="671ec35b969e7ecc36c44505d70205fc7fca4cdda047146790885c169ecdcf09",
)

PRIOR_EXTREMA_GOLDEN = PairedExtremaGoldenExpectation(
    scenario="prior-extrema",
    input_candle_count=5,
    input_candle_hash="de96bc3d80399720cf94502d131cc5c913c85c457e850aae5ac61da2c075ad38",
    input_hash="01b5bea559269b4e9554c8517e2fc16da3fd6e06098aec3bbe6b266f7944e312",
    highest_code="prior_rolling_highest",
    lowest_code="prior_rolling_lowest",
    highest_first_defined_index=3,
    lowest_first_defined_index=3,
    highest_defined_value_count=2,
    lowest_defined_value_count=2,
    expected_highest=(None, None, None, "7", "7"),
    expected_lowest=(None, None, None, "1", "2"),
    highest_result_hash="541d93b026b5f72eb44f62c8910294e088231f72a93bb9e4130209c0fe4a92c2",
    lowest_result_hash="5e03c3acc6108612a30467b86b7ed6f17450794438f0d11849c881d1024fbfcc",
)

# Decimal-context scenario reuses EMA-close literals (policy must ignore global context).
DECIMAL_CONTEXT_GOLDEN = IndicatorGoldenExpectation(
    scenario="decimal-context",
    indicator_code="ema_close",
    input_candle_count=EMA_CLOSE_GOLDEN.input_candle_count,
    input_candle_hash=EMA_CLOSE_GOLDEN.input_candle_hash,
    input_hash=EMA_CLOSE_GOLDEN.input_hash,
    first_defined_index=EMA_CLOSE_GOLDEN.first_defined_index,
    defined_value_count=EMA_CLOSE_GOLDEN.defined_value_count,
    expected_values=EMA_CLOSE_GOLDEN.expected_values,
    result_hash=EMA_CLOSE_GOLDEN.result_hash,
)

ALL_SCENARIO_NAMES: tuple[str, ...] = (
    "ema-close",
    "true-range",
    "wilder-atr",
    "rolling-extrema",
    "prior-extrema",
    "decimal-context",
)


class IndicatorGoldenMismatchError(Exception):
    """Raised when a computed indicator series diverges from frozen literals."""


def _format_values(series: IndicatorSeries) -> tuple[str | None, ...]:
    return tuple(
        None if value is None else format_canonical_decimal(value) for value in series.values
    )


def _check_single(
    *,
    expected: IndicatorGoldenExpectation,
    series: IndicatorSeries,
    indicator_input: IndicatorInput,
) -> dict[str, object]:
    if indicator_input.candle_sha256 != expected.input_candle_hash:
        msg = "input candle hash mismatch"
        raise IndicatorGoldenMismatchError(msg)
    if indicator_input.input_hash != expected.input_hash:
        msg = "input hash mismatch"
        raise IndicatorGoldenMismatchError(msg)
    if series.indicator_code.value != expected.indicator_code:
        msg = "indicator code mismatch"
        raise IndicatorGoldenMismatchError(msg)
    if series.input_candle_count != expected.input_candle_count:
        msg = "input candle count mismatch"
        raise IndicatorGoldenMismatchError(msg)
    if series.first_defined_index != expected.first_defined_index:
        msg = "first_defined_index mismatch"
        raise IndicatorGoldenMismatchError(msg)
    if series.defined_value_count != expected.defined_value_count:
        msg = "defined_value_count mismatch"
        raise IndicatorGoldenMismatchError(msg)
    actual_values = _format_values(series)
    if actual_values != expected.expected_values:
        msg = f"values mismatch: {actual_values!r} != {expected.expected_values!r}"
        raise IndicatorGoldenMismatchError(msg)
    if series.result_hash != expected.result_hash:
        msg = "result hash mismatch"
        raise IndicatorGoldenMismatchError(msg)
    return {
        "ok": True,
        "scenario": expected.scenario,
        "indicator_code": expected.indicator_code,
        "input_candle_count": expected.input_candle_count,
        "input_candle_hash": expected.input_candle_hash,
        "first_defined_index": expected.first_defined_index,
        "defined_value_count": expected.defined_value_count,
        "result_hash": expected.result_hash,
    }


def _check_paired(
    *,
    expected: PairedExtremaGoldenExpectation,
    highest: IndicatorSeries,
    lowest: IndicatorSeries,
    indicator_input: IndicatorInput,
) -> dict[str, object]:
    if indicator_input.candle_sha256 != expected.input_candle_hash:
        msg = "input candle hash mismatch"
        raise IndicatorGoldenMismatchError(msg)
    if indicator_input.input_hash != expected.input_hash:
        msg = "input hash mismatch"
        raise IndicatorGoldenMismatchError(msg)
    if highest.indicator_code.value != expected.highest_code:
        msg = "highest indicator code mismatch"
        raise IndicatorGoldenMismatchError(msg)
    if lowest.indicator_code.value != expected.lowest_code:
        msg = "lowest indicator code mismatch"
        raise IndicatorGoldenMismatchError(msg)
    if _format_values(highest) != expected.expected_highest:
        msg = "highest values mismatch"
        raise IndicatorGoldenMismatchError(msg)
    if _format_values(lowest) != expected.expected_lowest:
        msg = "lowest values mismatch"
        raise IndicatorGoldenMismatchError(msg)
    if highest.result_hash != expected.highest_result_hash:
        msg = "highest result hash mismatch"
        raise IndicatorGoldenMismatchError(msg)
    if lowest.result_hash != expected.lowest_result_hash:
        msg = "lowest result hash mismatch"
        raise IndicatorGoldenMismatchError(msg)
    if highest.first_defined_index != expected.highest_first_defined_index:
        msg = "highest first_defined_index mismatch"
        raise IndicatorGoldenMismatchError(msg)
    if lowest.first_defined_index != expected.lowest_first_defined_index:
        msg = "lowest first_defined_index mismatch"
        raise IndicatorGoldenMismatchError(msg)
    if highest.defined_value_count != expected.highest_defined_value_count:
        msg = "highest defined_value_count mismatch"
        raise IndicatorGoldenMismatchError(msg)
    if lowest.defined_value_count != expected.lowest_defined_value_count:
        msg = "lowest defined_value_count mismatch"
        raise IndicatorGoldenMismatchError(msg)
    return {
        "ok": True,
        "scenario": expected.scenario,
        "indicator_code": f"{expected.highest_code}+{expected.lowest_code}",
        "input_candle_count": expected.input_candle_count,
        "input_candle_hash": expected.input_candle_hash,
        "first_defined_index": expected.highest_first_defined_index,
        "defined_value_count": expected.highest_defined_value_count,
        "result_hash": expected.highest_result_hash,
        "highest_result_hash": expected.highest_result_hash,
        "lowest_result_hash": expected.lowest_result_hash,
    }


def run_scenario(name: str) -> dict[str, object]:
    if name == "ema-close":
        indicator_input = IndicatorInput.from_verified(
            symbol=SYMBOL,
            timeframe=TIMEFRAME,
            candles=EMA_CLOSE_CANDLES,
        )
        return _check_single(
            expected=EMA_CLOSE_GOLDEN,
            series=ema_close(indicator_input, 3),
            indicator_input=indicator_input,
        )
    if name == "true-range":
        indicator_input = IndicatorInput.from_verified(
            symbol=SYMBOL,
            timeframe=TIMEFRAME,
            candles=TRUE_RANGE_CANDLES,
        )
        return _check_single(
            expected=TRUE_RANGE_GOLDEN,
            series=true_range(indicator_input),
            indicator_input=indicator_input,
        )
    if name == "wilder-atr":
        indicator_input = IndicatorInput.from_verified(
            symbol=SYMBOL,
            timeframe=TIMEFRAME,
            candles=TRUE_RANGE_CANDLES,
        )
        return _check_single(
            expected=WILDER_ATR_GOLDEN,
            series=wilder_atr(indicator_input, 3),
            indicator_input=indicator_input,
        )
    if name == "rolling-extrema":
        indicator_input = IndicatorInput.from_verified(
            symbol=SYMBOL,
            timeframe=TIMEFRAME,
            candles=EXTREMA_CANDLES,
        )
        return _check_paired(
            expected=ROLLING_EXTREMA_GOLDEN,
            highest=rolling_highest(indicator_input, 3),
            lowest=rolling_lowest(indicator_input, 3),
            indicator_input=indicator_input,
        )
    if name == "prior-extrema":
        indicator_input = IndicatorInput.from_verified(
            symbol=SYMBOL,
            timeframe=TIMEFRAME,
            candles=EXTREMA_CANDLES,
        )
        return _check_paired(
            expected=PRIOR_EXTREMA_GOLDEN,
            highest=prior_rolling_highest(indicator_input, 3),
            lowest=prior_rolling_lowest(indicator_input, 3),
            indicator_input=indicator_input,
        )
    if name == "decimal-context":
        from decimal import getcontext

        ctx = getcontext()
        previous = (ctx.prec, ctx.rounding, ctx.Emax, ctx.Emin)
        try:
            ctx.prec = 5
            ctx.rounding = "ROUND_DOWN"
            ctx.Emax = 10
            ctx.Emin = -10
            indicator_input = IndicatorInput.from_verified(
                symbol=SYMBOL,
                timeframe=TIMEFRAME,
                candles=EMA_CLOSE_CANDLES,
            )
            return _check_single(
                expected=DECIMAL_CONTEXT_GOLDEN,
                series=ema_close(indicator_input, 3),
                indicator_input=indicator_input,
            )
        finally:
            ctx.prec, ctx.rounding, ctx.Emax, ctx.Emin = previous
    raise KeyError(name)
