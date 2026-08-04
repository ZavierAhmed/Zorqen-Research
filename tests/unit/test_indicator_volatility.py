"""True Range and Wilder ATR tests."""

from __future__ import annotations

from decimal import Decimal, getcontext

from tests.unit.indicator_helpers import indicator_input_from_specs
from zorqen_research.application.indicators.volatility import true_range, wilder_atr

TR_SPECS = (
    ("10", "12", "10", "11"),
    ("14", "16", "14", "15"),
    ("9", "10", "8", "9"),
    ("10", "11", "9", "10"),
)


def test_true_range_first_candle_and_gaps() -> None:
    series = true_range(indicator_input_from_specs(TR_SPECS))
    assert series.values[0] == Decimal("2")
    assert series.values[1] == Decimal("5")  # up gap
    assert series.values[2] == Decimal("7")  # down gap
    assert series.values[3] == Decimal("2")
    assert all(v is not None and v >= 0 for v in series.values)


def test_wilder_atr_period_one_equals_tr() -> None:
    indicator_input = indicator_input_from_specs(TR_SPECS)
    atr = wilder_atr(indicator_input, 1)
    tr = true_range(indicator_input)
    assert atr.values == tr.values


def test_wilder_atr_seed_recurrence_warmup() -> None:
    series = wilder_atr(indicator_input_from_specs(TR_SPECS), 3)
    assert series.values[0] is None
    assert series.values[1] is None
    assert series.values[2] == Decimal("4.6666666666666666666666666666666666666666666666667")
    assert series.values[3] == Decimal("3.7777777777777777777777777777777777777777777777777")
    assert all(v is None or v >= 0 for v in series.values)


def test_true_range_and_atr_prefix_equivalence() -> None:
    full_input = indicator_input_from_specs(TR_SPECS)
    prefix_input = indicator_input_from_specs(TR_SPECS[:3])
    assert true_range(prefix_input).values == true_range(full_input).values[:3]
    assert wilder_atr(prefix_input, 3).values == wilder_atr(full_input, 3).values[:3]


def test_true_range_atr_global_context_independence() -> None:
    ctx = getcontext()
    previous = (ctx.prec, ctx.rounding, ctx.Emax, ctx.Emin)
    try:
        baseline_tr = true_range(indicator_input_from_specs(TR_SPECS))
        baseline_atr = wilder_atr(indicator_input_from_specs(TR_SPECS), 3)
        ctx.prec = 4
        ctx.rounding = "ROUND_UP"
        ctx.Emax = 15
        ctx.Emin = -15
        assert true_range(indicator_input_from_specs(TR_SPECS)).result_hash == (
            baseline_tr.result_hash
        )
        assert wilder_atr(indicator_input_from_specs(TR_SPECS), 3).result_hash == (
            baseline_atr.result_hash
        )
    finally:
        ctx.prec, ctx.rounding, ctx.Emax, ctx.Emin = previous
