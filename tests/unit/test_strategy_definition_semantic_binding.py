"""Direct parameter-set construction must not bypass definition schema binding."""

from __future__ import annotations

from decimal import Decimal

import pytest

from tests.unit.strategy_definition_helpers import sample_definition
from zorqen_research.application.strategy_definitions.serialization import hash_definition
from zorqen_research.domain.strategy_definitions.errors import StrategyDefinitionValidationError
from zorqen_research.domain.strategy_definitions.instances import (
    BoundParameterValue,
    StrategyInstanceSpecification,
    StrategyParameterSet,
    bind_default_parameter_set,
    validate_parameter_set_against_definition,
)


def _valid_values() -> tuple[BoundParameterValue, ...]:
    return (
        BoundParameterValue(key="atr_multiplier", value=Decimal("2.5")),
        BoundParameterValue(key="atr_period", value=14),
        BoundParameterValue(key="entry_mode", value="strict"),
        BoundParameterValue(key="use_confirmation", value=True),
    )


def _set_with(
    definition_hash: str,
    values: tuple[BoundParameterValue, ...],
) -> StrategyParameterSet:
    return StrategyParameterSet(definition_hash=definition_hash, values=values)


def test_direct_construction_missing_required_parameter() -> None:
    definition = sample_definition()
    digest = hash_definition(definition)
    values = tuple(v for v in _valid_values() if v.key != "atr_period")
    parameter_set = _set_with(digest, values)
    with pytest.raises(StrategyDefinitionValidationError, match="missing"):
        validate_parameter_set_against_definition(definition, parameter_set)
    with pytest.raises(StrategyDefinitionValidationError, match="missing"):
        StrategyInstanceSpecification(definition=definition, parameter_set=parameter_set)


def test_direct_construction_unknown_parameter() -> None:
    definition = sample_definition()
    digest = hash_definition(definition)
    values = _valid_values() + (BoundParameterValue(key="extra_knob", value=1),)
    # Unsorted / extra key rejected by parameter set structural rules first.
    with pytest.raises(StrategyDefinitionValidationError):
        _set_with(digest, values)
    ordered = tuple(sorted(values, key=lambda item: item.key))
    parameter_set = _set_with(digest, ordered)
    with pytest.raises(StrategyDefinitionValidationError, match="unknown"):
        StrategyInstanceSpecification(definition=definition, parameter_set=parameter_set)


def test_direct_construction_empty_against_non_empty_definition() -> None:
    definition = sample_definition()
    digest = hash_definition(definition)
    parameter_set = _set_with(digest, ())
    with pytest.raises(StrategyDefinitionValidationError, match="missing"):
        StrategyInstanceSpecification(definition=definition, parameter_set=parameter_set)


def test_direct_construction_integer_as_string() -> None:
    definition = sample_definition()
    digest = hash_definition(definition)
    values = (
        BoundParameterValue(key="atr_multiplier", value=Decimal("2.5")),
        BoundParameterValue(key="atr_period", value="14"),
        BoundParameterValue(key="entry_mode", value="strict"),
        BoundParameterValue(key="use_confirmation", value=True),
    )
    parameter_set = _set_with(digest, values)
    with pytest.raises(StrategyDefinitionValidationError):
        StrategyInstanceSpecification(definition=definition, parameter_set=parameter_set)


def test_direct_construction_boolean_as_integer() -> None:
    definition = sample_definition()
    digest = hash_definition(definition)
    values = (
        BoundParameterValue(key="atr_multiplier", value=Decimal("2.5")),
        BoundParameterValue(key="atr_period", value=14),
        BoundParameterValue(key="entry_mode", value="strict"),
        BoundParameterValue(key="use_confirmation", value=1),
    )
    parameter_set = _set_with(digest, values)
    with pytest.raises(StrategyDefinitionValidationError):
        StrategyInstanceSpecification(definition=definition, parameter_set=parameter_set)


def test_direct_construction_decimal_as_int_or_string() -> None:
    definition = sample_definition()
    digest = hash_definition(definition)
    for bad in (3, "2.5"):
        values = (
            BoundParameterValue(key="atr_multiplier", value=bad),  # type: ignore[arg-type]
            BoundParameterValue(key="atr_period", value=14),
            BoundParameterValue(key="entry_mode", value="strict"),
            BoundParameterValue(key="use_confirmation", value=True),
        )
        parameter_set = _set_with(digest, values)
        with pytest.raises(StrategyDefinitionValidationError):
            StrategyInstanceSpecification(definition=definition, parameter_set=parameter_set)


def test_direct_construction_decimal_outside_bounds() -> None:
    definition = sample_definition()
    digest = hash_definition(definition)
    values = (
        BoundParameterValue(key="atr_multiplier", value=Decimal("99")),
        BoundParameterValue(key="atr_period", value=14),
        BoundParameterValue(key="entry_mode", value="strict"),
        BoundParameterValue(key="use_confirmation", value=True),
    )
    parameter_set = _set_with(digest, values)
    with pytest.raises(StrategyDefinitionValidationError):
        StrategyInstanceSpecification(definition=definition, parameter_set=parameter_set)


def test_direct_construction_decimal_step_misalignment() -> None:
    definition = sample_definition()
    digest = hash_definition(definition)
    values = (
        BoundParameterValue(key="atr_multiplier", value=Decimal("2.6")),
        BoundParameterValue(key="atr_period", value=14),
        BoundParameterValue(key="entry_mode", value="strict"),
        BoundParameterValue(key="use_confirmation", value=True),
    )
    parameter_set = _set_with(digest, values)
    with pytest.raises(StrategyDefinitionValidationError):
        StrategyInstanceSpecification(definition=definition, parameter_set=parameter_set)


def test_direct_construction_invalid_enum_value() -> None:
    definition = sample_definition()
    digest = hash_definition(definition)
    values = (
        BoundParameterValue(key="atr_multiplier", value=Decimal("2.5")),
        BoundParameterValue(key="atr_period", value=14),
        BoundParameterValue(key="entry_mode", value="nope"),
        BoundParameterValue(key="use_confirmation", value=True),
    )
    parameter_set = _set_with(digest, values)
    with pytest.raises(StrategyDefinitionValidationError):
        StrategyInstanceSpecification(definition=definition, parameter_set=parameter_set)


def test_parameterless_definition_accepts_empty_parameter_set() -> None:
    definition = sample_definition(parameters=())
    digest = hash_definition(definition)
    parameter_set = _set_with(digest, ())
    validate_parameter_set_against_definition(definition, parameter_set)
    instance = StrategyInstanceSpecification(definition=definition, parameter_set=parameter_set)
    assert instance.parameter_set.values == ()
    assert instance.definition_hash == digest
    assert instance.instance_hash


def test_valid_directly_constructed_parameter_set_succeeds() -> None:
    definition = sample_definition()
    digest = hash_definition(definition)
    parameter_set = _set_with(digest, _valid_values())
    validate_parameter_set_against_definition(definition, parameter_set)
    instance = StrategyInstanceSpecification(definition=definition, parameter_set=parameter_set)
    assert instance.parameter_set_hash == parameter_set.parameter_set_hash
    via_bind = bind_default_parameter_set(definition, definition_hash=digest)
    assert via_bind.parameter_set_hash == parameter_set.parameter_set_hash


def test_tampered_parameter_set_cannot_form_instance() -> None:
    definition = sample_definition()
    digest = hash_definition(definition)
    # Shares definition hash but drops a required parameter.
    parameter_set = _set_with(
        digest,
        (
            BoundParameterValue(key="atr_multiplier", value=Decimal("2.5")),
            BoundParameterValue(key="atr_period", value=14),
            BoundParameterValue(key="entry_mode", value="strict"),
        ),
    )
    with pytest.raises(StrategyDefinitionValidationError, match="missing"):
        StrategyInstanceSpecification(definition=definition, parameter_set=parameter_set)


def test_invalid_instance_rejected_before_instance_hash_exposed() -> None:
    definition = sample_definition()
    digest = hash_definition(definition)
    parameter_set = _set_with(digest, ())
    with pytest.raises(StrategyDefinitionValidationError):
        StrategyInstanceSpecification(definition=definition, parameter_set=parameter_set)
    # Construction must not yield a usable object with instance_hash.
    try:
        StrategyInstanceSpecification(definition=definition, parameter_set=parameter_set)
    except StrategyDefinitionValidationError:
        pass
    else:
        pytest.fail("expected StrategyDefinitionValidationError")
