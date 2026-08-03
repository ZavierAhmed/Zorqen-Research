"""Parameter binding and instance construction tests."""

from __future__ import annotations

from decimal import Decimal

import pytest

from tests.unit.strategy_definition_helpers import sample_definition
from zorqen_research.application.strategy_definitions.serialization import (
    build_instance,
    hash_definition,
)
from zorqen_research.domain.strategy_definitions.errors import StrategyDefinitionValidationError
from zorqen_research.domain.strategy_definitions.instances import (
    StrategyParameterSet,
    bind_default_parameter_set,
    bind_parameter_values,
)


def test_complete_valid_binding_and_defaults() -> None:
    definition = sample_definition()
    digest = hash_definition(definition)
    bound = bind_parameter_values(
        definition,
        definition_hash=digest,
        raw_values={
            "atr_multiplier": Decimal("2.5"),
            "atr_period": 14,
            "entry_mode": "strict",
            "use_confirmation": True,
        },
    )
    assert [v.key for v in bound.values] == [
        "atr_multiplier",
        "atr_period",
        "entry_mode",
        "use_confirmation",
    ]
    defaults = bind_default_parameter_set(definition, definition_hash=digest)
    assert defaults.values == bound.values
    instance = build_instance(
        definition,
        {
            "atr_multiplier": Decimal("2.5"),
            "atr_period": 14,
            "entry_mode": "strict",
            "use_confirmation": True,
        },
    )
    assert instance.definition_hash == digest
    assert instance.parameter_set.definition_hash == digest


def test_missing_unknown_wrong_kind_bounds() -> None:
    definition = sample_definition()
    digest = hash_definition(definition)
    with pytest.raises(StrategyDefinitionValidationError, match="missing"):
        bind_parameter_values(definition, definition_hash=digest, raw_values={"atr_period": 14})
    with pytest.raises(StrategyDefinitionValidationError, match="unknown"):
        bind_parameter_values(
            definition,
            definition_hash=digest,
            raw_values={
                "atr_multiplier": Decimal("2.5"),
                "atr_period": 14,
                "entry_mode": "strict",
                "use_confirmation": True,
                "extra": 1,
            },
        )
    with pytest.raises(StrategyDefinitionValidationError):
        bind_parameter_values(
            definition,
            definition_hash=digest,
            raw_values={
                "atr_multiplier": Decimal("2.5"),
                "atr_period": True,
                "entry_mode": "strict",
                "use_confirmation": True,
            },
        )
    with pytest.raises(StrategyDefinitionValidationError):
        bind_parameter_values(
            definition,
            definition_hash=digest,
            raw_values={
                "atr_multiplier": Decimal("99"),
                "atr_period": 14,
                "entry_mode": "strict",
                "use_confirmation": True,
            },
        )
    with pytest.raises(StrategyDefinitionValidationError):
        bind_parameter_values(
            definition,
            definition_hash=digest,
            raw_values={
                "atr_multiplier": Decimal("2.5"),
                "atr_period": 14,
                "entry_mode": "nope",
                "use_confirmation": True,
            },
        )


def test_definition_hash_mismatch_on_instance() -> None:
    definition = sample_definition()
    digest = hash_definition(definition)
    parameter_set = bind_default_parameter_set(definition, definition_hash=digest)
    with pytest.raises(StrategyDefinitionValidationError, match="definition_hash"):
        StrategyParameterSet(definition_hash="0" * 63, values=parameter_set.values)
    from zorqen_research.domain.strategy_definitions.instances import (
        StrategyInstanceSpecification,
    )

    with pytest.raises(StrategyDefinitionValidationError, match="does not match"):
        StrategyInstanceSpecification(
            definition=definition,
            parameter_set=parameter_set,
            definition_hash="a" * 64,
            parameter_set_hash="b" * 64,
            instance_hash="c" * 64,
        )
