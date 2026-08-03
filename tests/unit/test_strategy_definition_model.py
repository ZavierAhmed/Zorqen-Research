"""Strategy definition model governance and structural tests."""

from __future__ import annotations

import pytest

from tests.unit.strategy_definition_helpers import (
    sample_decimal_param,
    sample_definition,
    sample_integer_param,
)
from zorqen_research.domain.backtesting.enums import PositionDirection
from zorqen_research.domain.strategy_definitions.enums import DefinitionStatus
from zorqen_research.domain.strategy_definitions.errors import StrategyDefinitionValidationError
from zorqen_research.domain.strategy_definitions.timeframes import TimeframeRequirement
from zorqen_research.domain.timeframes import Timeframe


def test_draft_without_source_hash() -> None:
    definition = sample_definition(status=DefinitionStatus.DRAFT, source_spec_sha256=None)
    assert definition.status is DefinitionStatus.DRAFT


def test_approved_requires_valid_source_hash() -> None:
    with pytest.raises(StrategyDefinitionValidationError, match="source_spec_sha256"):
        sample_definition(status=DefinitionStatus.APPROVED, source_spec_sha256=None)
    good = sample_definition(
        status=DefinitionStatus.APPROVED,
        source_spec_sha256="ab" * 32,
    )
    assert good.source_spec_sha256 == "ab" * 32
    with pytest.raises(StrategyDefinitionValidationError):
        sample_definition(status=DefinitionStatus.APPROVED, source_spec_sha256="AB" * 32)


def test_wrong_schema_version() -> None:
    with pytest.raises(StrategyDefinitionValidationError, match="schema_version"):
        sample_definition(schema_version="2")


def test_duplicate_and_unsorted_parameter_keys() -> None:
    a = sample_decimal_param(key="alpha")
    b = sample_integer_param(key="alpha")
    with pytest.raises(StrategyDefinitionValidationError, match="unique"):
        sample_definition(parameters=(a, b))
    first = sample_integer_param(key="zzz")
    second = sample_decimal_param(key="aaa")
    with pytest.raises(StrategyDefinitionValidationError, match="lexicographically"):
        sample_definition(parameters=(first, second))


def test_context_timeframe_rules() -> None:
    with pytest.raises(StrategyDefinitionValidationError, match="duplicate"):
        sample_definition(
            context_requirements=(
                TimeframeRequirement(Timeframe.H4, 1),
                TimeframeRequirement(Timeframe.H4, 2),
            )
        )
    with pytest.raises(StrategyDefinitionValidationError, match="execution"):
        sample_definition(
            execution_timeframe=Timeframe.H1,
            context_requirements=(TimeframeRequirement(Timeframe.H1, 1),),
        )
    with pytest.raises(StrategyDefinitionValidationError, match="ordered"):
        sample_definition(
            context_requirements=(
                TimeframeRequirement(Timeframe.D1, 1),
                TimeframeRequirement(Timeframe.H4, 1),
            )
        )


def test_warmup_and_directions() -> None:
    with pytest.raises(StrategyDefinitionValidationError):
        sample_definition(execution_warmup_bars=True)  # type: ignore[arg-type]
    with pytest.raises(StrategyDefinitionValidationError):
        sample_definition(execution_warmup_bars=-1)
    with pytest.raises(StrategyDefinitionValidationError):
        sample_definition(supported_directions=())
    with pytest.raises(StrategyDefinitionValidationError):
        sample_definition(supported_directions=(PositionDirection.LONG, PositionDirection.LONG))
    with pytest.raises(StrategyDefinitionValidationError, match="canonical order"):
        sample_definition(supported_directions=(PositionDirection.SHORT, PositionDirection.LONG))
    with pytest.raises(StrategyDefinitionValidationError):
        sample_definition(supported_directions={PositionDirection.LONG})  # type: ignore[arg-type]


def test_immutability() -> None:
    definition = sample_definition()
    with pytest.raises(AttributeError):
        definition.version = "9.9.9"  # type: ignore[misc]
