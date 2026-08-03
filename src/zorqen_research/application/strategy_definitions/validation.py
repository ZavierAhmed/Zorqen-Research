"""High-level validation helpers for strategy definitions."""

from __future__ import annotations

from pathlib import Path

from zorqen_research.application.strategy_definitions.parsing import (
    coerce_parameter_values_for_definition,
    parse_definition_file,
    parse_parameter_values_file,
)
from zorqen_research.application.strategy_definitions.serialization import (
    build_instance,
    hash_definition,
)
from zorqen_research.domain.strategy_definitions.definitions import StrategyDefinition
from zorqen_research.domain.strategy_definitions.instances import StrategyInstanceSpecification


def validate_definition_file(path: Path) -> tuple[StrategyDefinition, str]:
    definition = parse_definition_file(path)
    return definition, hash_definition(definition)


def bind_parameters_files(
    *,
    definition_path: Path,
    parameters_path: Path,
) -> StrategyInstanceSpecification:
    definition = parse_definition_file(definition_path)
    raw = parse_parameter_values_file(parameters_path)
    typed = coerce_parameter_values_for_definition(definition, raw)
    return build_instance(definition, typed)
