"""Adversarial red-team loop for the indicator foundation."""

from __future__ import annotations

import inspect
from decimal import Decimal, getcontext

import pytest

from tests.unit.indicator_helpers import (
    SYMBOL,
    TIMEFRAME,
    candle_series,
    indicator_input_from_specs,
    make_candle,
    utc,
)
from zorqen_research.application.backtesting.provider import BacktestDecisionContext
from zorqen_research.application.indicators.ema import ema_close
from zorqen_research.application.indicators.extrema import (
    CountingSequence,
    prior_rolling_highest,
    rolling_highest_counted,
)
from zorqen_research.application.indicators.goldens import run_scenario
from zorqen_research.application.indicators.volatility import wilder_atr
from zorqen_research.application.strategy_backtesting.provider import (
    MultiTimeframeBacktestDecisionContext,
)
from zorqen_research.domain.indicators.enums import IndicatorCode
from zorqen_research.domain.indicators.errors import IndicatorValidationError
from zorqen_research.domain.indicators.inputs import IndicatorInput
from zorqen_research.domain.indicators.results import IndicatorSeries
from zorqen_research.domain.strategy_backtesting.histories import VisibleCandleHistory
from zorqen_research.indicators.cli import main as indicators_cli_main


def test_redteam_global_decimal_precision_extremely_low() -> None:
    specs = (
        ("10", "11", "9", "10"),
        ("11", "12", "10", "11"),
        ("12", "13", "11", "12"),
        ("13", "14", "12", "13"),
    )
    baseline = ema_close(indicator_input_from_specs(specs), 3)
    ctx = getcontext()
    previous = (ctx.prec, ctx.rounding, ctx.Emax, ctx.Emin)
    try:
        ctx.prec = 1
        ctx.rounding = "ROUND_CEILING"
        ctx.Emax = 5
        ctx.Emin = -5
        attacked = ema_close(indicator_input_from_specs(specs), 3)
        assert attacked.values == baseline.values
        assert attacked.result_hash == baseline.result_hash
    finally:
        ctx.prec, ctx.rounding, ctx.Emax, ctx.Emin = previous


def test_redteam_period_true_and_over_maximum() -> None:
    indicator_input = indicator_input_from_specs((("10", "11", "9", "10"),))
    with pytest.raises(IndicatorValidationError):
        ema_close(indicator_input, True)
    with pytest.raises(IndicatorValidationError):
        ema_close(indicator_input, 1_000_001)


def test_redteam_float_and_non_finite_smuggled_into_result() -> None:
    indicator_input = indicator_input_from_specs(
        (("10", "11", "9", "10"), ("11", "12", "10", "11"))
    )
    with pytest.raises(IndicatorValidationError):
        IndicatorSeries.from_calculation(
            indicator_code=IndicatorCode.EMA_CLOSE,
            indicator_input=indicator_input,
            parameters={"period": 1},
            values=(1.25, None),  # type: ignore[arg-type]
        )
    with pytest.raises(IndicatorValidationError):
        IndicatorSeries.from_calculation(
            indicator_code=IndicatorCode.EMA_CLOSE,
            indicator_input=indicator_input,
            parameters={"period": 1},
            values=(Decimal("NaN"), None),
        )


def test_redteam_signed_zero_canonical() -> None:
    indicator_input = indicator_input_from_specs(
        (("10", "11", "9", "10"), ("11", "12", "10", "11"))
    )
    series = IndicatorSeries.from_calculation(
        indicator_code=IndicatorCode.TRUE_RANGE,
        indicator_input=indicator_input,
        parameters={},
        values=(Decimal("-0"), Decimal("0")),
    )
    assert series.values[0] == Decimal("0")
    assert series.values[1] == Decimal("0")


def test_redteam_future_candle_changed_and_appended() -> None:
    base_specs = (
        ("10", "11", "9", "10"),
        ("11", "12", "10", "11"),
        ("12", "13", "11", "12"),
        ("13", "14", "12", "13"),
    )
    base = ema_close(indicator_input_from_specs(base_specs), 3)
    changed = ema_close(
        indicator_input_from_specs(base_specs[:3] + (("50", "60", "40", "55"),)),
        3,
    )
    appended = ema_close(
        indicator_input_from_specs(base_specs + (("20", "21", "19", "20"),)),
        3,
    )
    assert changed.values[:3] == base.values[:3]
    assert appended.values[:4] == base.values


def test_redteam_current_candle_change_prior_only() -> None:
    specs = (
        ("3", "5", "1", "4"),
        ("4", "7", "3", "5"),
        ("5", "7", "2", "6"),
        ("4", "6", "2", "5"),
        ("6", "8", "4", "7"),
    )
    base = prior_rolling_highest(indicator_input_from_specs(specs), 3)
    mutated = prior_rolling_highest(
        indicator_input_from_specs(specs[:3] + (("4", "100", "2", "5"),) + specs[4:]),
        3,
    )
    assert mutated.values[3] == base.values[3]


def test_redteam_duplicate_rolling_highs_lows() -> None:
    specs = (
        ("1", "5", "1", "3"),
        ("2", "5", "2", "3"),
        ("3", "5", "1", "4"),
        ("4", "4", "2", "3"),
    )
    highest = prior_rolling_highest(indicator_input_from_specs(specs), 2)
    # At index 2 prior window is indices 0..1 both high=5
    assert highest.values[2] == Decimal("5")


def test_redteam_very_large_and_small_magnitudes() -> None:
    start = utc(2024, 1, 1)
    from zorqen_research.domain.timeframes import timeframe_duration

    step = timeframe_duration(TIMEFRAME)
    candles = (
        make_candle(start, open="1e28", high="1e28", low="1e28", close="1e28"),
        make_candle(start + step, open="1e-28", high="1e-28", low="1e-28", close="1e-28"),
        make_candle(start + 2 * step, open="2e-28", high="2e-28", low="2e-28", close="2e-28"),
    )
    indicator_input = IndicatorInput.from_verified(
        symbol=SYMBOL, timeframe=TIMEFRAME, candles=candles
    )
    series = wilder_atr(indicator_input, 2)
    assert all(v is None or v.is_finite() for v in series.values)


def test_redteam_forged_input_and_result_hashes() -> None:
    with pytest.raises(IndicatorValidationError):
        IndicatorInput(
            symbol=SYMBOL,
            timeframe=TIMEFRAME,
            candles=candle_series((("10", "11", "9", "10"),)),
            candle_count=1,
            minimum_open_time=utc(2024, 1, 1),
            maximum_open_time=utc(2024, 1, 1),
            candle_sha256="deadbeef" * 8,
            input_hash="cafebabe" * 8,
        )
    with pytest.raises(IndicatorValidationError):
        IndicatorSeries(
            schema_version="1",
            indicator_code=IndicatorCode.EMA_CLOSE,
            symbol=SYMBOL,
            timeframe=TIMEFRAME,
            input_candle_sha256="deadbeef" * 8,
            input_candle_count=1,
            parameters=(),
            value_count=1,
            values=(Decimal("1"),),
            first_defined_index=0,
            defined_value_count=1,
            math_policy=None,
            result_hash="cafebabe" * 8,
        )


def test_redteam_result_value_length_mismatch() -> None:
    indicator_input = indicator_input_from_specs((("10", "11", "9", "10"),))
    with pytest.raises(IndicatorValidationError, match="length"):
        IndicatorSeries.from_calculation(
            indicator_code=IndicatorCode.TRUE_RANGE,
            indicator_input=indicator_input,
            parameters={},
            values=(Decimal("1"), Decimal("2")),
        )


def test_redteam_rolling_not_quadratic() -> None:
    n = 2000
    period = 200
    counted = CountingSequence(tuple(Decimal(i % 31) for i in range(n)))
    rolling_highest_counted(counted, period)
    assert counted.reads < n * period // 2


def test_redteam_indicator_series_not_in_decision_feed_types() -> None:
    single_params = inspect.signature(BacktestDecisionContext.__init__).parameters
    mtf_params = inspect.signature(MultiTimeframeBacktestDecisionContext.__init__).parameters
    assert "indicator" not in single_params
    assert "indicators" not in single_params
    assert "indicator" not in mtf_params
    assert "indicators" not in mtf_params
    history_params = inspect.signature(VisibleCandleHistory.__init__).parameters
    assert "indicator" not in history_params
    # Public annotations must not mention IndicatorSeries
    assert "IndicatorSeries" not in str(BacktestDecisionContext.__annotations__)
    assert "IndicatorSeries" not in str(MultiTimeframeBacktestDecisionContext.__annotations__)


def test_redteam_unknown_indicator_code_rejected() -> None:
    with pytest.raises(ValueError):
        IndicatorCode("macd")


def test_redteam_cli_unknown_scenario_and_mismatch() -> None:
    assert indicators_cli_main(["verify-golden", "--scenario", "not-a-scenario"]) == 1
    # Golden path succeeds
    assert indicators_cli_main(["verify-golden", "--scenario", "ema-close"]) == 0
    payload = run_scenario("ema-close")
    assert payload["ok"] is True
