"""Enums for strategy-definition schema (stable string values only)."""

from __future__ import annotations

from enum import StrEnum

from zorqen_research.domain.strategy_definitions.errors import StrategyDefinitionValidationError


class DefinitionStatus(StrEnum):
    DRAFT = "draft"
    APPROVED = "approved"


class ParameterKind(StrEnum):
    DECIMAL = "decimal"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    ENUM = "enum"


def parse_definition_status(value: object) -> DefinitionStatus:
    if not isinstance(value, str):
        msg = "status must be a string"
        raise StrategyDefinitionValidationError(msg)
    try:
        return DefinitionStatus(value)
    except ValueError as exc:
        msg = f"Unsupported definition status: {value!r}"
        raise StrategyDefinitionValidationError(msg) from exc


def parse_parameter_kind(value: object) -> ParameterKind:
    if not isinstance(value, str):
        msg = "parameter kind must be a string"
        raise StrategyDefinitionValidationError(msg)
    try:
        return ParameterKind(value)
    except ValueError as exc:
        msg = f"Unsupported parameter kind: {value!r}"
        raise StrategyDefinitionValidationError(msg) from exc
