"""Milestone 1.0A provenance, type, and golden-mismatch adversarial tests."""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
from io import StringIO
from unittest.mock import patch

import pytest

from tests.unit.indicator_helpers import (
    SYMBOL,
    TIMEFRAME,
    candle_series,
    indicator_input_from_specs,
    make_candle,
    utc,
)
from zorqen_research.application.indicators import goldens as goldens_module
from zorqen_research.application.indicators.assembly import _calculated_indicator_series
from zorqen_research.application.indicators.ema import ema_close
from zorqen_research.application.indicators.goldens import (
    EMA_CLOSE_GOLDEN,
    EMA_RECURSIVE_CANDLES,
    EMA_RECURSIVE_GOLDEN,
    ROLLING_EXTREMA_GOLDEN,
    WILDER_ATR_GOLDEN,
    IndicatorGoldenMismatchError,
    run_scenario,
)
from zorqen_research.application.indicators.serialization import serialize_indicator_series
from zorqen_research.application.indicators.volatility import true_range, wilder_atr
from zorqen_research.application.market_data.serialization import format_canonical_decimal
from zorqen_research.domain.candles import Candle
from zorqen_research.domain.indicators.enums import IndicatorCode
from zorqen_research.domain.indicators.errors import IndicatorValidationError
from zorqen_research.domain.indicators.inputs import IndicatorInput
from zorqen_research.domain.indicators.results import IndicatorSeries
from zorqen_research.indicators.cli import main as indicators_cli_main


class _CountingTuple(tuple):
    iter_calls = 0
    getitem_calls = 0
    len_calls = 0

    def __iter__(self):  # type: ignore[override]
        type(self).iter_calls += 1
        return super().__iter__()

    def __getitem__(self, key):  # type: ignore[override]
        type(self).getitem_calls += 1
        return super().__getitem__(key)

    def __len__(self):  # type: ignore[override]
        type(self).len_calls += 1
        return super().__len__()


class _MutatingIterTuple(tuple):
    def __iter__(self):  # type: ignore[override]
        yield from ()


class _LyingLenTuple(tuple):
    def __len__(self):  # type: ignore[override]
        return 0


class _CandleSubclass(Candle):
    pass


class _DecimalSubclass(Decimal):
    pass


def test_exact_tuple_and_candle_types_required() -> None:
    candles = candle_series((("10", "11", "9", "10"), ("11", "12", "10", "11")))
    _CountingTuple.iter_calls = 0
    _CountingTuple.getitem_calls = 0
    _CountingTuple.len_calls = 0
    evil = _CountingTuple(candles)
    with pytest.raises(IndicatorValidationError, match="exact tuple"):
        IndicatorInput.from_verified(symbol=SYMBOL, timeframe=TIMEFRAME, candles=evil)
    assert _CountingTuple.iter_calls == 0
    assert _CountingTuple.getitem_calls == 0
    assert _CountingTuple.len_calls == 0

    with pytest.raises(IndicatorValidationError, match="exact tuple"):
        IndicatorInput.from_verified(
            symbol=SYMBOL,
            timeframe=TIMEFRAME,
            candles=_MutatingIterTuple(candles),
        )
    with pytest.raises(IndicatorValidationError, match="exact tuple"):
        IndicatorInput.from_verified(
            symbol=SYMBOL,
            timeframe=TIMEFRAME,
            candles=_LyingLenTuple(candles),
        )


def test_candle_subclass_rejected() -> None:
    base = make_candle(utc(2024, 1, 1), open="10", high="11", low="9", close="10")
    subclassed = _CandleSubclass(
        open_time=base.open_time,
        open=base.open,
        high=base.high,
        low=base.low,
        close=base.close,
        volume=base.volume,
        close_time=base.close_time,
        quote_asset_volume=base.quote_asset_volume,
        trade_count=base.trade_count,
        taker_buy_base_volume=base.taker_buy_base_volume,
        taker_buy_quote_volume=base.taker_buy_quote_volume,
    )
    with pytest.raises(IndicatorValidationError, match="exact Candle"):
        IndicatorInput.from_verified(
            symbol=SYMBOL,
            timeframe=TIMEFRAME,
            candles=(subclassed,),
        )


def test_stored_input_preserves_exact_tuple_identity() -> None:
    candles = candle_series((("10", "11", "9", "10"), ("11", "12", "10", "11")))
    indicator_input = IndicatorInput.from_verified(
        symbol=SYMBOL,
        timeframe=TIMEFRAME,
        candles=candles,
    )
    assert indicator_input.candles is candles
    assert indicator_input.candle_count == len(candles)


def test_public_api_cannot_supply_arbitrary_ema_values() -> None:
    assert not hasattr(IndicatorSeries, "from_calculation")
    indicator_input = indicator_input_from_specs(
        (("10", "11", "9", "10"), ("11", "12", "10", "11"), ("12", "13", "11", "12"))
    )
    with pytest.raises(IndicatorValidationError, match="warmup|undefined"):
        _calculated_indicator_series(
            indicator_code=IndicatorCode.EMA_CLOSE,
            indicator_input=indicator_input,
            parameters={"period": 3},
            values=(Decimal("99"), Decimal("99"), Decimal("99")),
        )


def test_negative_atr_values_rejected() -> None:
    indicator_input = indicator_input_from_specs(
        (("10", "11", "9", "10"), ("11", "12", "10", "11"), ("12", "13", "11", "12"))
    )
    with pytest.raises(IndicatorValidationError, match="non-negative"):
        _calculated_indicator_series(
            indicator_code=IndicatorCode.WILDER_ATR,
            indicator_input=indicator_input,
            parameters={"period": 2},
            values=(None, Decimal("-1"), Decimal("1")),
        )


def test_true_range_rejects_unrelated_period_parameter() -> None:
    indicator_input = indicator_input_from_specs((("10", "11", "9", "10"),))
    with pytest.raises(IndicatorValidationError, match="no parameters"):
        _calculated_indicator_series(
            indicator_code=IndicatorCode.TRUE_RANGE,
            indicator_input=indicator_input,
            parameters={"period": 1},
            values=(Decimal("1"),),
        )


def test_ema_rejects_missing_period_and_false_warmup() -> None:
    indicator_input = indicator_input_from_specs(
        (("10", "11", "9", "10"), ("11", "12", "10", "11"), ("12", "13", "11", "12"))
    )
    with pytest.raises(IndicatorValidationError, match="period"):
        _calculated_indicator_series(
            indicator_code=IndicatorCode.EMA_CLOSE,
            indicator_input=indicator_input,
            parameters={},
            values=(None, None, Decimal("11")),
        )
    with pytest.raises(IndicatorValidationError, match="undefined warmup"):
        _calculated_indicator_series(
            indicator_code=IndicatorCode.EMA_CLOSE,
            indicator_input=indicator_input,
            parameters={"period": 3},
            values=(Decimal("1"), None, Decimal("11")),
        )


def test_mixed_parameter_key_types_and_unsafe_text_rejected() -> None:
    indicator_input = indicator_input_from_specs((("10", "11", "9", "10"),))
    with pytest.raises(IndicatorValidationError):
        _calculated_indicator_series(
            indicator_code=IndicatorCode.EMA_CLOSE,
            indicator_input=indicator_input,
            parameters={1: 1},  # type: ignore[dict-item]
            values=(Decimal("10"),),
        )
    with pytest.raises(IndicatorValidationError, match="NUL|UTF-8|period"):
        _calculated_indicator_series(
            indicator_code=IndicatorCode.EMA_CLOSE,
            indicator_input=indicator_input,
            parameters={"peri\x00od": 1},
            values=(Decimal("10"),),
        )
    lone = "\ud800"
    with pytest.raises(IndicatorValidationError):
        _calculated_indicator_series(
            indicator_code=IndicatorCode.EMA_CLOSE,
            indicator_input=indicator_input,
            parameters={lone: 1},
            values=(Decimal("10"),),
        )


def test_decimal_subclass_rejected_as_result_value() -> None:
    indicator_input = indicator_input_from_specs((("10", "11", "9", "10"),))
    with pytest.raises(IndicatorValidationError, match="exact Decimal"):
        _calculated_indicator_series(
            indicator_code=IndicatorCode.TRUE_RANGE,
            indicator_input=indicator_input,
            parameters={},
            values=(_DecimalSubclass("1"),),
        )


def test_nonlinear_ema_differs_from_rolling_sma() -> None:
    indicator_input = IndicatorInput.from_verified(
        symbol=SYMBOL,
        timeframe=TIMEFRAME,
        candles=EMA_RECURSIVE_CANDLES,
    )
    series = ema_close(indicator_input, 4)
    assert [None if v is None else format_canonical_decimal(v) for v in series.values] == [
        None,
        None,
        None,
        "16.25",
        "12.55",
        "23.53",
    ]
    # Rolling SMA of last 4 closes at the final index would be (5+30+7+40)/4 = 20.5
    closes = [c.close for c in indicator_input.candles]
    rolling_sma_last = sum(closes[-4:]) / Decimal(4)
    assert series.values[-1] != rolling_sma_last
    assert series.values[-1] == Decimal("23.53")
    assert series.result_hash == EMA_RECURSIVE_GOLDEN.result_hash
    serialize_indicator_series(series).decode("utf-8")


def test_golden_value_mismatch_raises_and_cli_exits_nonzero() -> None:
    bad = replace(
        EMA_CLOSE_GOLDEN,
        expected_values=(None, None, "11", "12", "999"),
    )
    with (
        patch.object(goldens_module, "EMA_CLOSE_GOLDEN", bad),
        pytest.raises(IndicatorGoldenMismatchError, match="values mismatch"),
    ):
        run_scenario("ema-close")
    stderr = StringIO()
    with patch.object(goldens_module, "EMA_CLOSE_GOLDEN", bad), patch("sys.stderr", stderr):
        code = indicators_cli_main(["verify-golden", "--scenario", "ema-close"])
    assert code == 1
    err = stderr.getvalue()
    assert '"ok":false' in err
    assert "golden_mismatch" in err


def test_golden_atr_value_and_hash_mismatch() -> None:
    bad_values = replace(
        WILDER_ATR_GOLDEN,
        expected_values=(
            None,
            None,
            "4.6666666666666666666666666666666666666666666666667",
            "9.99",
        ),
    )
    with (
        patch.object(goldens_module, "WILDER_ATR_GOLDEN", bad_values),
        pytest.raises(IndicatorGoldenMismatchError, match="values mismatch"),
    ):
        run_scenario("wilder-atr")

    bad_hash = replace(WILDER_ATR_GOLDEN, result_hash="0" * 64)
    with (
        patch.object(goldens_module, "WILDER_ATR_GOLDEN", bad_hash),
        pytest.raises(IndicatorGoldenMismatchError, match="result hash"),
    ):
        run_scenario("wilder-atr")


def test_paired_extrema_value_and_hash_mismatch() -> None:
    bad_values = replace(
        ROLLING_EXTREMA_GOLDEN,
        expected_highest=(None, None, "7", "7", "999"),
    )
    with (
        patch.object(goldens_module, "ROLLING_EXTREMA_GOLDEN", bad_values),
        pytest.raises(IndicatorGoldenMismatchError, match="highest values"),
    ):
        run_scenario("rolling-extrema")

    bad_hash = replace(ROLLING_EXTREMA_GOLDEN, highest_result_hash="0" * 64)
    with (
        patch.object(goldens_module, "ROLLING_EXTREMA_GOLDEN", bad_hash),
        pytest.raises(IndicatorGoldenMismatchError, match="highest result hash"),
    ):
        run_scenario("rolling-extrema")


def test_scenario_all_mismatch_exits_nonzero_on_stderr() -> None:
    bad = replace(EMA_CLOSE_GOLDEN, result_hash="0" * 64)
    stdout = StringIO()
    stderr = StringIO()
    with (
        patch.object(goldens_module, "EMA_CLOSE_GOLDEN", bad),
        patch("sys.stdout", stdout),
        patch("sys.stderr", stderr),
    ):
        code = indicators_cli_main(["verify-golden", "--scenario", "all"])
    assert code == 1
    err = stderr.getvalue()
    assert "golden_mismatch" in err
    assert '"ok":false' in err
    # Successful scenarios may still print ok:true on stdout; failure must not
    # appear only as a successful-looking stdout-only entry.
    assert '"scenario":"ema-close"' in err or "ema-close" in err
    for line in stdout.getvalue().splitlines():
        if '"scenario":"ema-close"' in line:
            assert '"ok":true' not in line


def test_redteam_cli_unknown_scenario_and_mismatch() -> None:
    assert indicators_cli_main(["verify-golden", "--scenario", "not-a-scenario"]) == 1
    bad = replace(EMA_CLOSE_GOLDEN, expected_values=(None, None, "0", "0", "0"))
    stderr = StringIO()
    with patch.object(goldens_module, "EMA_CLOSE_GOLDEN", bad), patch("sys.stderr", stderr):
        code = indicators_cli_main(["verify-golden", "--scenario", "ema-close"])
    assert code == 1
    assert "golden_mismatch" in stderr.getvalue()


def test_calculators_still_produce_nonnegative_tr_atr() -> None:
    indicator_input = indicator_input_from_specs(
        (
            ("10", "12", "10", "11"),
            ("14", "16", "14", "15"),
            ("9", "10", "8", "9"),
        )
    )
    tr = true_range(indicator_input)
    atr = wilder_atr(indicator_input, 2)
    assert all(v is not None and v >= 0 for v in tr.values)
    assert all(v is None or v >= 0 for v in atr.values)
