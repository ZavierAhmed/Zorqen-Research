"""Parameter definition type-boundary tests."""

from __future__ import annotations

from decimal import Decimal

import pytest

from tests.unit.strategy_definition_helpers import (
    sample_bool_param,
    sample_decimal_param,
    sample_enum_param,
    sample_integer_param,
)
from zorqen_research.application.market_data.serialization import format_canonical_decimal
from zorqen_research.domain.strategy_definitions.errors import StrategyDefinitionValidationError


def test_decimal_valid_and_alignment() -> None:
    param = sample_decimal_param()
    assert param.validate_value(Decimal("2.5")) == Decimal("2.5")
    assert param.validate_value(Decimal("0.5")) == Decimal("0.5")
    with pytest.raises(StrategyDefinitionValidationError, match="align"):
        sample_decimal_param(default_value=Decimal("2.6"))
    with pytest.raises(StrategyDefinitionValidationError, match="align"):
        param.validate_value(Decimal("2.6"))


def test_decimal_minimum_relative_step() -> None:
    param = sample_decimal_param(
        minimum=Decimal("1"),
        maximum=Decimal("5"),
        step=Decimal("0.5"),
        default_value=Decimal("1.5"),
    )
    assert param.validate_value(Decimal("2")) == Decimal("2")
    with pytest.raises(StrategyDefinitionValidationError):
        param.validate_value(Decimal("1.25"))


def test_decimal_rejects_float_bool_int_nan() -> None:
    with pytest.raises(StrategyDefinitionValidationError):
        sample_decimal_param(default_value=2.5)  # type: ignore[arg-type]
    with pytest.raises(StrategyDefinitionValidationError):
        sample_decimal_param(default_value=True)  # type: ignore[arg-type]
    with pytest.raises(StrategyDefinitionValidationError):
        sample_decimal_param(default_value=2)  # type: ignore[arg-type]
    with pytest.raises(StrategyDefinitionValidationError):
        sample_decimal_param(default_value=Decimal("NaN"))
    with pytest.raises(StrategyDefinitionValidationError):
        sample_decimal_param(default_value=Decimal("Infinity"))
    with pytest.raises(StrategyDefinitionValidationError):
        sample_decimal_param(step=Decimal("0"))
    with pytest.raises(StrategyDefinitionValidationError):
        sample_decimal_param(default_value=Decimal("11"))


def test_signed_zero_canonical() -> None:
    assert format_canonical_decimal(Decimal("-0")) == "0"
    assert format_canonical_decimal(Decimal("0.0")) == "0"


def test_integer_rules() -> None:
    param = sample_integer_param()
    assert param.validate_value(14) == 14
    with pytest.raises(StrategyDefinitionValidationError):
        sample_integer_param(default_value=True)  # type: ignore[arg-type]
    with pytest.raises(StrategyDefinitionValidationError):
        sample_integer_param(default_value=Decimal("14"))  # type: ignore[arg-type]
    with pytest.raises(StrategyDefinitionValidationError):
        sample_integer_param(default_value=14.0)  # type: ignore[arg-type]
    with pytest.raises(StrategyDefinitionValidationError):
        sample_integer_param(default_value=101)
    with pytest.raises(StrategyDefinitionValidationError):
        sample_integer_param(step=0)
    with pytest.raises(StrategyDefinitionValidationError):
        sample_integer_param(minimum=10, maximum=20, step=3, default_value=12)


def test_boolean_rules() -> None:
    param = sample_bool_param()
    assert param.validate_value(False) is False
    with pytest.raises(StrategyDefinitionValidationError):
        param.validate_value(0)  # type: ignore[arg-type]
    with pytest.raises(StrategyDefinitionValidationError):
        param.validate_value(1)  # type: ignore[arg-type]
    with pytest.raises(StrategyDefinitionValidationError):
        param.validate_value("true")  # type: ignore[arg-type]


def test_enum_rules() -> None:
    param = sample_enum_param()
    assert param.validate_value("strict") == "strict"
    with pytest.raises(StrategyDefinitionValidationError):
        sample_enum_param(choices=("only",))
    with pytest.raises(StrategyDefinitionValidationError):
        sample_enum_param(choices=("a", "a"))
    with pytest.raises(StrategyDefinitionValidationError):
        sample_enum_param(choices=["a", "b"])  # type: ignore[arg-type]
    with pytest.raises(StrategyDefinitionValidationError):
        sample_enum_param(choices={"a", "b"})  # type: ignore[arg-type]
    with pytest.raises(StrategyDefinitionValidationError):
        sample_enum_param(default_value="missing")
    with pytest.raises(StrategyDefinitionValidationError):
        param.validate_value("STRICT")
