"""Timeframe derivation plan tests."""

from __future__ import annotations

import pytest

from zorqen_research.domain.market_data.derivation import (
    MAX_DERIVATION_RATIO,
    derive_timeframe_plan,
)
from zorqen_research.domain.market_data.errors import ResamplingValidationError
from zorqen_research.domain.timeframes import Timeframe


@pytest.mark.parametrize(
    ("source", "target", "ratio"),
    [
        (Timeframe.M1, Timeframe.M5, 5),
        (Timeframe.M3, Timeframe.M15, 5),
        (Timeframe.M5, Timeframe.H1, 12),
        (Timeframe.M15, Timeframe.H1, 4),
        (Timeframe.M30, Timeframe.H4, 8),
        (Timeframe.H1, Timeframe.H4, 4),
        (Timeframe.H4, Timeframe.D1, 6),
        (Timeframe.D1, Timeframe.W1, 7),
        (Timeframe.M1, Timeframe.W1, MAX_DERIVATION_RATIO),
    ],
)
def test_valid_derivation_pairs(source: Timeframe, target: Timeframe, ratio: int) -> None:
    plan = derive_timeframe_plan(source, target)
    assert plan.ratio == ratio
    assert plan.source_timeframe is source
    assert plan.target_timeframe is target


@pytest.mark.parametrize(
    ("source", "target"),
    [
        (Timeframe.M3, Timeframe.M5),
        (Timeframe.M5, Timeframe.M3),
        (Timeframe.H1, Timeframe.H1),
        (Timeframe.D1, Timeframe.H4),
        (Timeframe.W1, Timeframe.D1),
    ],
)
def test_invalid_derivation_pairs(source: Timeframe, target: Timeframe) -> None:
    with pytest.raises(ResamplingValidationError):
        derive_timeframe_plan(source, target)


def test_wrong_runtime_types() -> None:
    with pytest.raises(ResamplingValidationError):
        derive_timeframe_plan("1m", Timeframe.M5)  # type: ignore[arg-type]
    with pytest.raises(ResamplingValidationError):
        derive_timeframe_plan(Timeframe.M1, "5m")  # type: ignore[arg-type]
