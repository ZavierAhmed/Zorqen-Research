"""IndicatorSeries integrity and serialization tests."""

from __future__ import annotations

from decimal import Decimal

import pytest

from tests.unit.indicator_helpers import indicator_input_from_specs
from zorqen_research.application.indicators.ema import ema_close
from zorqen_research.application.indicators.serialization import (
    hash_indicator_series,
    serialize_indicator_series,
)
from zorqen_research.domain.indicators.enums import IndicatorCode
from zorqen_research.domain.indicators.errors import IndicatorValidationError
from zorqen_research.domain.indicators.math_policy import IndicatorMathPolicy
from zorqen_research.domain.indicators.results import IndicatorSeries


def _base_input():
    return indicator_input_from_specs(
        (
            ("10", "11", "9", "10"),
            ("11", "12", "10", "11"),
            ("12", "13", "11", "12"),
        )
    )


def test_series_rejects_values_length_mismatch() -> None:
    indicator_input = _base_input()
    with pytest.raises(IndicatorValidationError, match="length"):
        IndicatorSeries.from_calculation(
            indicator_code=IndicatorCode.EMA_CLOSE,
            indicator_input=indicator_input,
            parameters={"period": 2},
            values=(Decimal("1"), Decimal("2")),
        )


def test_series_rejects_float_int_bool_values() -> None:
    indicator_input = _base_input()
    for bad in (1.5, 1, True):
        with pytest.raises(IndicatorValidationError, match="Decimal or None"):
            IndicatorSeries.from_calculation(
                indicator_code=IndicatorCode.EMA_CLOSE,
                indicator_input=indicator_input,
                parameters={"period": 1},
                values=(bad, None, None),  # type: ignore[arg-type]
            )


def test_series_rejects_nan_and_infinity() -> None:
    indicator_input = _base_input()
    for bad in (Decimal("NaN"), Decimal("Infinity"), Decimal("-Infinity")):
        with pytest.raises(IndicatorValidationError, match="finite"):
            IndicatorSeries.from_calculation(
                indicator_code=IndicatorCode.EMA_CLOSE,
                indicator_input=indicator_input,
                parameters={"period": 1},
                values=(bad, None, None),
            )


def test_series_rejects_direct_forged_construction() -> None:
    with pytest.raises(IndicatorValidationError, match="from_calculation"):
        IndicatorSeries(  # type: ignore[call-arg]
            schema_version="1",
            indicator_code=IndicatorCode.EMA_CLOSE,
            symbol=_base_input().symbol,
            timeframe=_base_input().timeframe,
            input_candle_sha256="0" * 64,
            input_candle_count=3,
            parameters=(("period", 1),),
            value_count=3,
            values=(None, None, None),
            first_defined_index=None,
            defined_value_count=0,
            math_policy=None,
            result_hash="0" * 64,
        )


def test_series_rejects_forged_math_policy_instance() -> None:
    indicator_input = _base_input()
    with pytest.raises(IndicatorValidationError, match="math policy"):
        IndicatorSeries.from_calculation(
            indicator_code=IndicatorCode.EMA_CLOSE,
            indicator_input=indicator_input,
            parameters={"period": 1},
            values=(Decimal("1"), Decimal("2"), Decimal("3")),
            math_policy=object.__new__(IndicatorMathPolicy),  # type: ignore[arg-type]
        )


def test_math_policy_rejects_direct_construction() -> None:
    with pytest.raises(IndicatorValidationError, match="default_math_policy"):
        IndicatorMathPolicy()  # type: ignore[call-arg]


def test_deterministic_canonical_bytes_and_hash_sensitivity() -> None:
    indicator_input = _base_input()
    a = ema_close(indicator_input, 2)
    b = ema_close(indicator_input, 2)
    assert serialize_indicator_series(a) == serialize_indicator_series(b)
    assert hash_indicator_series(a) == a.result_hash == b.result_hash
    c = ema_close(indicator_input, 3)
    assert c.result_hash != a.result_hash
    other_input = indicator_input_from_specs(
        (
            ("10", "11", "9", "10"),
            ("11", "12", "10", "11"),
            ("12", "13", "11", "13"),
        )
    )
    d = ema_close(other_input, 2)
    assert d.result_hash != a.result_hash


def test_signed_zero_serializes_as_zero() -> None:
    indicator_input = _base_input()
    series = IndicatorSeries.from_calculation(
        indicator_code=IndicatorCode.TRUE_RANGE,
        indicator_input=indicator_input,
        parameters={},
        values=(Decimal("-0"), Decimal("0"), None),
    )
    payload = serialize_indicator_series(series).decode("utf-8")
    assert '"0"' in payload
    assert '"-0"' not in payload


def test_unknown_indicator_code_type_rejected() -> None:
    indicator_input = _base_input()
    with pytest.raises(IndicatorValidationError, match="IndicatorCode"):
        IndicatorSeries.from_calculation(
            indicator_code="ema_close",  # type: ignore[arg-type]
            indicator_input=indicator_input,
            parameters={"period": 1},
            values=(Decimal("1"), Decimal("2"), Decimal("3")),
        )
