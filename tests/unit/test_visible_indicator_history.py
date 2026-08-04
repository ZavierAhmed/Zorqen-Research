"""VisibleIndicatorHistory boundary and representation tests."""

from __future__ import annotations

from decimal import Decimal

import pytest

from tests.unit.indicator_helpers import indicator_input_from_specs
from zorqen_research.application.indicator_views.feed import IndicatorDecisionFeed
from zorqen_research.application.indicators.ema import ema_close
from zorqen_research.domain.indicator_views.bundles import IndicatorSeriesBundle
from zorqen_research.domain.indicator_views.errors import IndicatorViewValidationError
from zorqen_research.domain.indicator_views.histories import VisibleIndicatorHistory
from zorqen_research.domain.indicators.enums import IndicatorCode


def _feed() -> IndicatorDecisionFeed:
    indicator_input = indicator_input_from_specs(
        (
            ("10", "11", "9", "10"),
            ("11", "12", "10", "11"),
            ("12", "13", "11", "12"),
            ("13", "14", "12", "13"),
            ("14", "15", "13", "14"),
        )
    )
    bundle = IndicatorSeriesBundle.from_verified(
        indicator_input=indicator_input,
        series=(ema_close(indicator_input, 3),),
    )
    return IndicatorDecisionFeed.from_bundle(bundle)


def test_bar_zero_and_final_history() -> None:
    feed = _feed()
    zero = feed.view_at(0).require(IndicatorCode.EMA_CLOSE, period=3).history
    final = feed.view_at(4).require(IndicatorCode.EMA_CLOSE, period=3).history
    assert len(zero) == 1
    assert zero.latest is None
    assert zero.latest_defined is False
    assert zero.defined_visible_count == 0
    assert len(final) == 5
    assert final.latest == Decimal("13")
    assert final.latest_defined is True
    assert final.defined_visible_count == 3


def test_index_equal_to_visible_count_and_oversized() -> None:
    history = _feed().view_at(2).require(IndicatorCode.EMA_CLOSE, period=3).history
    with pytest.raises(IndexError):
        _ = history[3]
    with pytest.raises(IndexError):
        _ = history[100]


def test_negative_indexing_stays_visible() -> None:
    history = _feed().view_at(2).require(IndicatorCode.EMA_CLOSE, period=3).history
    assert history[-1] == Decimal("11")
    assert history[-3] is None
    with pytest.raises(IndexError):
        _ = history[-4]


def test_bounded_slices_and_reverse() -> None:
    history = _feed().view_at(3).require(IndicatorCode.EMA_CLOSE, period=3).history
    assert history[0:10] == (None, None, Decimal("11"), Decimal("12"))
    assert history[-2:] == (Decimal("11"), Decimal("12"))
    assert history[::-1] == (Decimal("12"), Decimal("11"), None, None)
    assert history[5:1:-1] == (Decimal("12"), Decimal("11"))


def test_iteration_and_no_complete_source_api() -> None:
    history = _feed().view_at(2).require(IndicatorCode.EMA_CLOSE, period=3).history
    assert tuple(history) == (None, None, Decimal("11"))
    for name in ("values", "source", "series", "to_tuple", "all", "full"):
        assert not hasattr(history, name)


def test_direct_construction_blocked_and_safe_repr() -> None:
    with pytest.raises(IndicatorViewValidationError, match="IndicatorDecisionFeed"):
        VisibleIndicatorHistory()
    history = _feed().view_at(1).require(IndicatorCode.EMA_CLOSE, period=3).history
    text = repr(history)
    assert text == "VisibleIndicatorHistory(visible_count=2, latest_defined=false)"
    assert str(history) == text
    assert "999999" not in text
