"""Bound parameter sets and logical strategy instance specifications."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal

from zorqen_research.domain.strategy_definitions.definitions import StrategyDefinition
from zorqen_research.domain.strategy_definitions.errors import StrategyDefinitionValidationError
from zorqen_research.domain.strategy_definitions.parameters import (
    BooleanParameterDefinition,
    DecimalParameterDefinition,
    EnumParameterDefinition,
    IntegerParameterDefinition,
    StrategyParameterDefinition,
)


@dataclass(frozen=True, slots=True)
class BoundParameterValue:
    key: str
    value: Decimal | int | bool | str


@dataclass(frozen=True, slots=True)
class StrategyParameterSet:
    definition_hash: str
    values: tuple[BoundParameterValue, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.definition_hash, str) or len(self.definition_hash) != 64:
            msg = "definition_hash must be a 64-character hex digest"
            raise StrategyDefinitionValidationError(msg)
        if not isinstance(self.values, tuple):
            msg = "parameter values must be an immutable tuple"
            raise StrategyDefinitionValidationError(msg)
        keys = [item.key for item in self.values]
        if len(set(keys)) != len(keys):
            msg = "parameter values contain duplicate keys"
            raise StrategyDefinitionValidationError(msg)
        if tuple(keys) != tuple(sorted(keys)):
            msg = "parameter values must be sorted lexicographically by key"
            raise StrategyDefinitionValidationError(msg)


@dataclass(frozen=True, slots=True)
class StrategyInstanceSpecification:
    definition: StrategyDefinition
    parameter_set: StrategyParameterSet
    definition_hash: str
    parameter_set_hash: str
    instance_hash: str

    def __post_init__(self) -> None:
        if self.parameter_set.definition_hash != self.definition_hash:
            msg = "parameter set definition_hash does not match instance definition_hash"
            raise StrategyDefinitionValidationError(msg)


def _default_for(param: StrategyParameterDefinition) -> Decimal | int | bool | str:
    return param.default_value


def bind_parameter_values(
    definition: StrategyDefinition,
    *,
    definition_hash: str,
    raw_values: Mapping[str, object],
) -> StrategyParameterSet:
    """Bind exact values to every parameter; defaults are not auto-applied."""
    if not isinstance(raw_values, Mapping):
        msg = "parameter values must be a mapping"
        raise StrategyDefinitionValidationError(msg)
    expected_keys = {param.key for param in definition.parameters}
    provided_keys = set(raw_values.keys())
    missing = expected_keys - provided_keys
    unknown = provided_keys - expected_keys
    if missing:
        msg = f"missing parameter keys: {sorted(missing)}"
        raise StrategyDefinitionValidationError(msg)
    if unknown:
        msg = f"unknown parameter keys: {sorted(unknown)}"
        raise StrategyDefinitionValidationError(msg)

    by_key = {param.key: param for param in definition.parameters}
    bound: list[BoundParameterValue] = []
    for key in sorted(expected_keys):
        param = by_key[key]
        validated = param.validate_value(raw_values[key])
        bound.append(BoundParameterValue(key=key, value=validated))
    return StrategyParameterSet(definition_hash=definition_hash, values=tuple(bound))


def bind_default_parameter_set(
    definition: StrategyDefinition,
    *,
    definition_hash: str,
) -> StrategyParameterSet:
    """Explicit deterministic helper that binds every parameter to its default."""
    defaults = {param.key: _default_for(param) for param in definition.parameters}
    return bind_parameter_values(
        definition,
        definition_hash=definition_hash,
        raw_values=defaults,
    )


def parameter_kind_label(param: StrategyParameterDefinition) -> str:
    if isinstance(param, DecimalParameterDefinition):
        return "decimal"
    if isinstance(param, IntegerParameterDefinition):
        return "integer"
    if isinstance(param, BooleanParameterDefinition):
        return "boolean"
    if isinstance(param, EnumParameterDefinition):
        return "enum"
    msg = "unknown parameter definition type"
    raise StrategyDefinitionValidationError(msg)
