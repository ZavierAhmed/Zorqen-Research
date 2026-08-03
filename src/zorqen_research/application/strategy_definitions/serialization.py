"""Application facade for strategy-definition serialization and hashing."""

from __future__ import annotations

from typing import Any

from zorqen_research.domain.strategy_definitions.canonical import (
    canonical_json_bytes,
    definition_to_document,
    hash_definition,
    hash_instance_components,
    serialize_definition,
)
from zorqen_research.domain.strategy_definitions.definitions import StrategyDefinition
from zorqen_research.domain.strategy_definitions.instances import (
    StrategyInstanceSpecification,
    StrategyParameterSet,
    bind_parameter_values,
    parameter_set_to_document,
)


def serialize_parameter_set(parameter_set: StrategyParameterSet) -> bytes:
    return canonical_json_bytes(parameter_set_to_document(parameter_set))


def hash_parameter_set(parameter_set: StrategyParameterSet) -> str:
    return parameter_set.parameter_set_hash


def instance_to_document(instance: StrategyInstanceSpecification) -> dict[str, Any]:
    return {
        "definition_hash": instance.definition_hash,
        "parameter_set_hash": instance.parameter_set_hash,
        "definition": definition_to_document(instance.definition),
        "parameter_set": parameter_set_to_document(instance.parameter_set),
    }


def serialize_instance(instance: StrategyInstanceSpecification) -> bytes:
    return canonical_json_bytes(instance_to_document(instance))


def build_instance(
    definition: StrategyDefinition,
    raw_values: dict[str, object],
) -> StrategyInstanceSpecification:
    definition_hash = hash_definition(definition)
    parameter_set = bind_parameter_values(
        definition,
        definition_hash=definition_hash,
        raw_values=raw_values,
    )
    return StrategyInstanceSpecification(
        definition=definition,
        parameter_set=parameter_set,
    )


__all__ = [
    "build_instance",
    "definition_to_document",
    "hash_definition",
    "hash_instance_components",
    "hash_parameter_set",
    "instance_to_document",
    "serialize_definition",
    "serialize_instance",
    "serialize_parameter_set",
]
