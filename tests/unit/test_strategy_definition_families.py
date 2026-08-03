"""Seeded strategy-family identity binding tests."""

from __future__ import annotations

from uuid import UUID

import pytest

from tests.unit.strategy_definition_helpers import sample_definition
from zorqen_research.domain.strategy_definitions.errors import StrategyDefinitionValidationError
from zorqen_research.domain.strategy_families import (
    ADAPTIVE_MTF_TREND_BREAKOUT_CODE,
    ADAPTIVE_MTF_TREND_BREAKOUT_ID,
    SUPPORT_RESISTANCE_CODE,
    SUPPORT_RESISTANCE_ID,
    require_seeded_family_pair,
)


def test_both_valid_seeded_pairs() -> None:
    require_seeded_family_pair(
        family_id=ADAPTIVE_MTF_TREND_BREAKOUT_ID,
        family_code=ADAPTIVE_MTF_TREND_BREAKOUT_CODE,
    )
    require_seeded_family_pair(
        family_id=SUPPORT_RESISTANCE_ID,
        family_code=SUPPORT_RESISTANCE_CODE,
    )
    sample_definition(
        family_id=SUPPORT_RESISTANCE_ID,
        family_code=SUPPORT_RESISTANCE_CODE,
        definition_code="sr_test_definition",
    )


def test_correct_id_wrong_code() -> None:
    with pytest.raises(ValueError, match="mismatch"):
        require_seeded_family_pair(
            family_id=ADAPTIVE_MTF_TREND_BREAKOUT_ID,
            family_code=SUPPORT_RESISTANCE_CODE,
        )


def test_correct_code_wrong_id() -> None:
    with pytest.raises(ValueError, match="mismatch"):
        require_seeded_family_pair(
            family_id=SUPPORT_RESISTANCE_ID,
            family_code=ADAPTIVE_MTF_TREND_BREAKOUT_CODE,
        )


def test_unknown_id_and_code() -> None:
    with pytest.raises(ValueError, match="Unknown strategy family_id"):
        require_seeded_family_pair(
            family_id=UUID("99999999-9999-4999-8999-999999999999"),
            family_code=ADAPTIVE_MTF_TREND_BREAKOUT_CODE,
        )
    with pytest.raises(ValueError, match="Unknown strategy family_code"):
        require_seeded_family_pair(
            family_id=ADAPTIVE_MTF_TREND_BREAKOUT_ID,
            family_code="unknown_family",
        )


def test_nil_family_id_rejected_by_definition() -> None:
    with pytest.raises(StrategyDefinitionValidationError, match="nil"):
        sample_definition(family_id=UUID(int=0))
