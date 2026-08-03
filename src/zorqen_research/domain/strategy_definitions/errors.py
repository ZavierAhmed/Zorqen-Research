"""Errors for immutable strategy-definition schema validation."""

from __future__ import annotations


class StrategyDefinitionError(RuntimeError):
    """Base error for strategy-definition schema failures."""


class StrategyDefinitionValidationError(StrategyDefinitionError, ValueError):
    """Invalid strategy definition, parameter, or binding input."""


class StrategyDefinitionParseError(StrategyDefinitionError, ValueError):
    """Malformed or rejected strategy-definition JSON document."""
