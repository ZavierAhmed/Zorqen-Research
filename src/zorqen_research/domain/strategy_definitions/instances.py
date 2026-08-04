"""Bound parameter sets and logical strategy instance specifications."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from decimal import Decimal

from zorqen_research.domain.strategy_definitions.canonical import (
    compute_parameter_set_hash,
    hash_definition,
    hash_instance_components,
    parameter_set_document,
)
from zorqen_research.domain.strategy_definitions.definitions import StrategyDefinition
from zorqen_research.domain.strategy_definitions.errors import StrategyDefinitionValidationError
from zorqen_research.domain.strategy_definitions.identifiers import (
    require_canonical_identifier,
    require_logical_sha256,
    require_unicode_scalars,
)
from zorqen_research.domain.strategy_definitions.parameters import StrategyParameterDefinition


def _require_bound_runtime_value(value: object, *, field: str) -> Decimal | int | bool | str:
    if isinstance(value, bool):
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    if isinstance(value, Decimal):
        if not value.is_finite():
            msg = f"{field} must be a finite Decimal"
            raise StrategyDefinitionValidationError(msg)
        return value
    if isinstance(value, str):
        require_unicode_scalars(value, field=field)
        return value
    if isinstance(value, float):
        msg = f"{field} must not be a float"
        raise StrategyDefinitionValidationError(msg)
    msg = f"{field} must be Decimal, int, bool, or str"
    raise StrategyDefinitionValidationError(msg)


@dataclass(frozen=True, slots=True)
class BoundParameterValue:
    key: str
    value: Decimal | int | bool | str

    def __post_init__(self) -> None:
        try:
            require_canonical_identifier(self.key, field="bound.key")
            object.__setattr__(
                self,
                "value",
                _require_bound_runtime_value(self.value, field="bound.value"),
            )
        except StrategyDefinitionValidationError:
            raise
        except (AttributeError, TypeError, ValueError) as exc:
            msg = "BoundParameterValue contains invalid runtime values"
            raise StrategyDefinitionValidationError(msg) from exc


@dataclass(frozen=True, slots=True)
class StrategyParameterSet:
    definition_hash: str
    values: tuple[BoundParameterValue, ...]
    parameter_set_hash: str = field(init=False)

    def __post_init__(self) -> None:
        try:
            digest_in = require_logical_sha256(self.definition_hash, field="definition_hash")
            if not isinstance(self.values, tuple):
                msg = "parameter values must be an immutable tuple"
                raise StrategyDefinitionValidationError(msg)
            for item in self.values:
                if not isinstance(item, BoundParameterValue):
                    msg = "parameter values must be BoundParameterValue instances"
                    raise StrategyDefinitionValidationError(msg)
            keys = [item.key for item in self.values]
            if len(set(keys)) != len(keys):
                msg = "parameter values contain duplicate keys"
                raise StrategyDefinitionValidationError(msg)
            if tuple(keys) != tuple(sorted(keys)):
                msg = "parameter values must be sorted lexicographically by key"
                raise StrategyDefinitionValidationError(msg)
            digest = compute_parameter_set_hash(
                definition_hash=digest_in,
                values=tuple((item.key, item.value) for item in self.values),
            )
            object.__setattr__(self, "parameter_set_hash", digest)
        except StrategyDefinitionValidationError:
            raise
        except (AttributeError, TypeError, ValueError) as exc:
            msg = "StrategyParameterSet contains invalid runtime values"
            raise StrategyDefinitionValidationError(msg) from exc


@dataclass(frozen=True, slots=True)
class StrategyInstanceSpecification:
    definition: StrategyDefinition
    parameter_set: StrategyParameterSet
    definition_hash: str = field(init=False)
    parameter_set_hash: str = field(init=False)
    instance_hash: str = field(init=False)

    def __post_init__(self) -> None:
        try:
            if not isinstance(self.definition, StrategyDefinition):
                msg = "definition must be a StrategyDefinition"
                raise StrategyDefinitionValidationError(msg)
            if not isinstance(self.parameter_set, StrategyParameterSet):
                msg = "parameter_set must be a StrategyParameterSet"
                raise StrategyDefinitionValidationError(msg)
            validate_parameter_set_against_definition(self.definition, self.parameter_set)
            definition_hash = hash_definition(self.definition)
            parameter_set_hash = self.parameter_set.parameter_set_hash
            instance_hash = hash_instance_components(
                definition_hash=definition_hash,
                parameter_set_hash=parameter_set_hash,
            )
            object.__setattr__(self, "definition_hash", definition_hash)
            object.__setattr__(self, "parameter_set_hash", parameter_set_hash)
            object.__setattr__(self, "instance_hash", instance_hash)
        except StrategyDefinitionValidationError:
            raise
        except (AttributeError, TypeError, ValueError) as exc:
            msg = "StrategyInstanceSpecification contains invalid runtime values"
            raise StrategyDefinitionValidationError(msg) from exc


def _default_for(param: StrategyParameterDefinition) -> Decimal | int | bool | str:
    return param.default_value


def validate_parameter_set_against_definition(
    definition: StrategyDefinition,
    parameter_set: StrategyParameterSet,
) -> None:
    """
    Revalidate a parameter set against a definition's schema and hashes.

    Closes the bypass where a set shares ``definition_hash`` but omits, invents,
    or mistypes parameters relative to the definition schema.
    """
    if not isinstance(definition, StrategyDefinition):
        msg = "definition must be a StrategyDefinition"
        raise StrategyDefinitionValidationError(msg)
    if not isinstance(parameter_set, StrategyParameterSet):
        msg = "parameter_set must be a StrategyParameterSet"
        raise StrategyDefinitionValidationError(msg)

    expected_hash = hash_definition(definition)
    if parameter_set.definition_hash != expected_hash:
        msg = "parameter set definition_hash does not match definition"
        raise StrategyDefinitionValidationError(msg)

    expected_keys = [param.key for param in definition.parameters]
    provided_keys = [item.key for item in parameter_set.values]
    expected_set = set(expected_keys)
    provided_set = set(provided_keys)
    missing = expected_set - provided_set
    unknown = provided_set - expected_set
    if missing:
        msg = f"missing parameter keys: {sorted(missing)}"
        raise StrategyDefinitionValidationError(msg)
    if unknown:
        msg = f"unknown parameter keys: {sorted(unknown)}"
        raise StrategyDefinitionValidationError(msg)
    if provided_keys != expected_keys:
        msg = "parameter values must exactly match definition parameter keys in order"
        raise StrategyDefinitionValidationError(msg)

    by_key = {param.key: param for param in definition.parameters}
    validated_values: list[tuple[str, Decimal | int | bool | str]] = []
    for item in parameter_set.values:
        validated = by_key[item.key].validate_value(item.value)
        if validated != item.value:
            msg = f"parameters.{item.key} does not match its validated value"
            raise StrategyDefinitionValidationError(msg)
        validated_values.append((item.key, validated))

    recomputed = compute_parameter_set_hash(
        definition_hash=parameter_set.definition_hash,
        values=tuple(validated_values),
    )
    if recomputed != parameter_set.parameter_set_hash:
        msg = "parameter_set_hash does not match validated parameter set content"
        raise StrategyDefinitionValidationError(msg)


def bind_parameter_values(
    definition: StrategyDefinition,
    *,
    definition_hash: str,
    raw_values: Mapping[str, object],
) -> StrategyParameterSet:
    """Bind exact values to every parameter; defaults are not auto-applied."""
    digest = require_logical_sha256(definition_hash, field="definition_hash")
    expected = hash_definition(definition)
    if digest != expected:
        msg = "definition_hash does not match the provided definition"
        raise StrategyDefinitionValidationError(msg)
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
    return StrategyParameterSet(definition_hash=digest, values=tuple(bound))


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
    from zorqen_research.domain.strategy_definitions.canonical import (
        parameter_kind_label as _label,
    )

    return _label(param)


def parameter_set_to_document(parameter_set: StrategyParameterSet) -> dict[str, object]:
    return parameter_set_document(
        definition_hash=parameter_set.definition_hash,
        values=tuple((item.key, item.value) for item in parameter_set.values),
    )
