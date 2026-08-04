"""Period validation tests for indicators."""

from __future__ import annotations

from decimal import Decimal

import pytest

from tests.unit.indicator_helpers import indicator_input_from_specs
from zorqen_research.application.indicators.ema import ema_close
from zorqen_research.domain.indicators.errors import IndicatorValidationError
from zorqen_research.domain.indicators.math_policy import require_period


@pytest.mark.parametrize("period", [1, 5, 1_000_000])
def test_require_period_accepts_valid_ints(period: int) -> None:
    assert require_period(period) == period


def test_period_equal_to_input_length_is_valid() -> None:
    indicator_input = indicator_input_from_specs(
        (("10", "11", "9", "10"), ("11", "12", "10", "11"), ("12", "13", "11", "12"))
    )
    series = ema_close(indicator_input, 3)
    assert series.first_defined_index == 2
    assert series.defined_value_count == 1


def test_period_greater_than_input_length_yields_all_undefined() -> None:
    indicator_input = indicator_input_from_specs(
        (("10", "11", "9", "10"), ("11", "12", "10", "11"))
    )
    series = ema_close(indicator_input, 5)
    assert series.values == (None, None)
    assert series.first_defined_index is None
    assert series.defined_value_count == 0


@pytest.mark.parametrize(
    "period",
    [0, -1, True, False, 1.5, Decimal("3"), "3", 1_000_001],
)
def test_require_period_rejects_invalid(period: object) -> None:
    with pytest.raises(IndicatorValidationError):
        require_period(period)


def test_ema_rejects_bool_period() -> None:
    indicator_input = indicator_input_from_specs((("10", "11", "9", "10"),))
    with pytest.raises(IndicatorValidationError, match="real int"):
        ema_close(indicator_input, True)
