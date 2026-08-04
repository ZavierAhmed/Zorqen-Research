"""EMA close indicator tests."""

from __future__ import annotations

from decimal import Decimal, getcontext

from tests.unit.indicator_helpers import indicator_input_from_specs, make_candle, utc
from zorqen_research.application.indicators.ema import ema_close
from zorqen_research.application.market_data.serialization import format_canonical_decimal
from zorqen_research.domain.indicators.inputs import IndicatorInput
from zorqen_research.domain.symbols import Symbol
from zorqen_research.domain.timeframes import Timeframe


def test_ema_period_one_equals_close() -> None:
    indicator_input = indicator_input_from_specs(
        (("10", "11", "9", "10"), ("11", "12", "10", "11"), ("12", "13", "11", "12"))
    )
    series = ema_close(indicator_input, 1)
    assert series.values == tuple(c.close for c in indicator_input.candles)


def test_ema_exact_seed_and_recurrence() -> None:
    indicator_input = indicator_input_from_specs(
        (
            ("10", "11", "9", "10"),
            ("11", "12", "10", "11"),
            ("12", "13", "11", "12"),
            ("13", "14", "12", "13"),
            ("14", "15", "13", "14"),
        )
    )
    series = ema_close(indicator_input, 3)
    assert series.values[0] is None
    assert series.values[1] is None
    assert series.values[2] == Decimal("11")
    assert series.values[3] == Decimal("12")
    assert series.values[4] == Decimal("13")


def test_ema_warmup_none_before_seed() -> None:
    specs = (
        ("10", "11", "9", "10"),
        ("10", "11", "9", "10"),
        ("10", "11", "9", "10"),
        ("10", "11", "9", "10"),
    )
    indicator_input = indicator_input_from_specs(specs)
    series = ema_close(indicator_input, 4)
    assert series.values[:3] == (None, None, None)
    assert series.values[3] == Decimal("10")


def test_ema_prefix_equivalence() -> None:
    full_specs = (
        ("10", "11", "9", "10"),
        ("11", "12", "10", "11"),
        ("12", "13", "11", "12"),
        ("13", "14", "12", "13"),
        ("14", "15", "13", "14"),
    )
    full = ema_close(indicator_input_from_specs(full_specs), 3)
    prefix = ema_close(indicator_input_from_specs(full_specs[:4]), 3)
    assert prefix.values == full.values[:4]


def test_ema_future_candle_independence() -> None:
    base_specs = (
        ("10", "11", "9", "10"),
        ("11", "12", "10", "11"),
        ("12", "13", "11", "12"),
        ("13", "14", "12", "13"),
    )
    extended = base_specs + (("99", "100", "98", "99"),)
    base = ema_close(indicator_input_from_specs(base_specs), 3)
    longer = ema_close(indicator_input_from_specs(extended), 3)
    assert longer.values[:4] == base.values


def test_ema_global_decimal_context_independence() -> None:
    specs = (
        ("10", "11", "9", "10"),
        ("11", "12", "10", "11"),
        ("12", "13", "11", "12"),
        ("13", "14", "12", "13"),
        ("14", "15", "13", "14"),
    )
    ctx = getcontext()
    previous = (ctx.prec, ctx.rounding, ctx.Emax, ctx.Emin)
    try:
        baseline = ema_close(indicator_input_from_specs(specs), 3)
        ctx.prec = 3
        ctx.rounding = "ROUND_FLOOR"
        ctx.Emax = 20
        ctx.Emin = -20
        attacked = ema_close(indicator_input_from_specs(specs), 3)
        assert attacked.values == baseline.values
        assert attacked.result_hash == baseline.result_hash
    finally:
        ctx.prec, ctx.rounding, ctx.Emax, ctx.Emin = previous


def test_ema_large_and_small_finite_prices() -> None:
    start = utc(2024, 1, 1)
    from zorqen_research.domain.timeframes import timeframe_duration

    step = timeframe_duration(Timeframe.M1)
    candles = (
        make_candle(
            start,
            open="1e20",
            high="1e20",
            low="1e20",
            close="1e20",
        ),
        make_candle(
            start + step,
            open="1e-20",
            high="1e-20",
            low="1e-20",
            close="1e-20",
        ),
        make_candle(
            start + 2 * step,
            open="2e-20",
            high="2e-20",
            low="2e-20",
            close="2e-20",
        ),
    )
    indicator_input = IndicatorInput.from_verified(
        symbol=Symbol(value="BTCUSDT"),
        timeframe=Timeframe.M1,
        candles=candles,
    )
    series = ema_close(indicator_input, 2)
    assert series.values[0] is None
    assert series.values[1] is not None
    assert series.values[1].is_finite()
    assert series.values[2] is not None
    assert series.values[2].is_finite()
    assert format_canonical_decimal(series.values[1]) != ""
