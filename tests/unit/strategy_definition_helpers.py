"""Shared helpers for strategy-definition unit tests."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from uuid import UUID

from zorqen_research.domain.backtesting.enums import PositionDirection
from zorqen_research.domain.strategy_definitions.definitions import StrategyDefinition
from zorqen_research.domain.strategy_definitions.enums import DefinitionStatus
from zorqen_research.domain.strategy_definitions.parameters import (
    BooleanParameterDefinition,
    DecimalParameterDefinition,
    EnumParameterDefinition,
    IntegerParameterDefinition,
    StrategyParameterDefinition,
)
from zorqen_research.domain.strategy_definitions.timeframes import TimeframeRequirement
from zorqen_research.domain.strategy_families import (
    ADAPTIVE_MTF_TREND_BREAKOUT_CODE,
    ADAPTIVE_MTF_TREND_BREAKOUT_ID,
)
from zorqen_research.domain.timeframes import Timeframe

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "strategy_definitions"
EXAMPLE_DEFINITION = FIXTURES / "example_definition_v1.json"
EXAMPLE_PARAMETERS = FIXTURES / "example_parameters_v1.json"


def sample_decimal_param(**overrides: object) -> DecimalParameterDefinition:
    base: dict[str, object] = {
        "key": "atr_multiplier",
        "display_name": "ATR Multiplier",
        "description": "Test decimal",
        "researchable": True,
        "default_value": Decimal("2.5"),
        "minimum": Decimal("0.5"),
        "maximum": Decimal("10"),
        "step": Decimal("0.5"),
    }
    base.update(overrides)
    return DecimalParameterDefinition(**base)  # type: ignore[arg-type]


def sample_integer_param(**overrides: object) -> IntegerParameterDefinition:
    base: dict[str, object] = {
        "key": "atr_period",
        "display_name": "ATR Period",
        "description": "Test integer",
        "researchable": True,
        "default_value": 14,
        "minimum": 2,
        "maximum": 100,
        "step": 1,
    }
    base.update(overrides)
    return IntegerParameterDefinition(**base)  # type: ignore[arg-type]


def sample_bool_param(**overrides: object) -> BooleanParameterDefinition:
    base: dict[str, object] = {
        "key": "use_confirmation",
        "display_name": "Use Confirmation",
        "description": "Test bool",
        "researchable": False,
        "default_value": True,
    }
    base.update(overrides)
    return BooleanParameterDefinition(**base)  # type: ignore[arg-type]


def sample_enum_param(**overrides: object) -> EnumParameterDefinition:
    base: dict[str, object] = {
        "key": "entry_mode",
        "display_name": "Entry Mode",
        "description": "Test enum",
        "researchable": False,
        "default_value": "strict",
        "choices": ("strict", "relaxed"),
    }
    base.update(overrides)
    return EnumParameterDefinition(**base)  # type: ignore[arg-type]


def sample_parameters() -> tuple[StrategyParameterDefinition, ...]:
    return (
        sample_decimal_param(),
        sample_integer_param(),
        sample_enum_param(),
        sample_bool_param(),
    )


def sample_definition(**overrides: object) -> StrategyDefinition:
    params = sample_parameters()
    # lexicographic: atr_multiplier, atr_period, entry_mode, use_confirmation
    ordered = tuple(sorted(params, key=lambda p: p.key))
    base: dict[str, object] = {
        "schema_version": "1",
        "definition_id": UUID("11111111-1111-4111-8111-111111111111"),
        "family_id": ADAPTIVE_MTF_TREND_BREAKOUT_ID,
        "family_code": ADAPTIVE_MTF_TREND_BREAKOUT_CODE,
        "definition_code": "example_test_definition",
        "display_name": "Example Test Definition",
        "description": "Test-only schema fixture.",
        "version": "0.1.0",
        "status": DefinitionStatus.DRAFT,
        "execution_timeframe": Timeframe.H1,
        "execution_warmup_bars": 200,
        "context_requirements": (TimeframeRequirement(timeframe=Timeframe.H4, warmup_bars=100),),
        "supported_directions": (PositionDirection.LONG, PositionDirection.SHORT),
        "parameters": ordered,
        "source_spec_sha256": None,
    }
    base.update(overrides)
    return StrategyDefinition(**base)  # type: ignore[arg-type]
