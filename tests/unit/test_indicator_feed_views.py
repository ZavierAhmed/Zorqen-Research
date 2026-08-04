"""IndicatorDecisionFeed / view / lookup tests."""

from __future__ import annotations

import pytest

from tests.unit.indicator_helpers import indicator_input_from_specs
from zorqen_research.application.indicator_views.feed import IndicatorDecisionFeed
from zorqen_research.application.indicators.ema import ema_close
from zorqen_research.application.indicators.volatility import true_range, wilder_atr
from zorqen_research.domain.indicator_views.bundles import IndicatorSeriesBundle
from zorqen_research.domain.indicator_views.errors import IndicatorViewValidationError
from zorqen_research.domain.indicator_views.views import IndicatorDecisionView
from zorqen_research.domain.indicators.enums import IndicatorCode


def _bundle() -> IndicatorSeriesBundle:
    indicator_input = indicator_input_from_specs(
        (
            ("10", "11", "9", "10"),
            ("11", "12", "10", "11"),
            ("12", "13", "11", "12"),
            ("13", "14", "12", "13"),
            ("14", "15", "13", "14"),
        )
    )
    return IndicatorSeriesBundle.from_verified(
        indicator_input=indicator_input,
        series=(
            ema_close(indicator_input, 3),
            wilder_atr(indicator_input, 3),
            true_range(indicator_input),
        ),
    )


def test_view_at_accepts_exact_indices() -> None:
    feed = IndicatorDecisionFeed.from_bundle(_bundle())
    view0 = feed.view_at(0)
    view_final = feed.view_at(4)
    assert view0.bar_index == 0
    assert view0.visible_count == 1
    assert view_final.bar_index == 4
    assert view_final.visible_count == 5
    assert view_final.overall_ready is True


def test_view_at_rejects_bool_float_negative_future() -> None:
    feed = IndicatorDecisionFeed.from_bundle(_bundle())
    with pytest.raises(IndicatorViewValidationError, match="real int"):
        feed.view_at(True)
    with pytest.raises(IndicatorViewValidationError, match="real int"):
        feed.view_at(1.0)  # type: ignore[arg-type]
    with pytest.raises(IndicatorViewValidationError, match="within"):
        feed.view_at(-1)
    with pytest.raises(IndicatorViewValidationError, match="within"):
        feed.view_at(5)


def test_require_lookup_and_missing() -> None:
    view = IndicatorDecisionFeed.from_bundle(_bundle()).view_at(4)
    tr = view.require(IndicatorCode.TRUE_RANGE)
    ema = view.require(IndicatorCode.EMA_CLOSE, period=3)
    assert tr.indicator_code is IndicatorCode.TRUE_RANGE
    assert ema.parameters == (("period", 3),)
    with pytest.raises(IndicatorViewValidationError, match="not present"):
        view.require(IndicatorCode.EMA_CLOSE, period=99)
    with pytest.raises(IndicatorViewValidationError, match="IndicatorCode"):
        view.require("ema_close", period=3)  # type: ignore[arg-type]
    with pytest.raises(IndicatorViewValidationError, match="no period"):
        view.require(IndicatorCode.TRUE_RANGE, period=1)
    with pytest.raises(IndicatorViewValidationError, match="period is required"):
        view.require(IndicatorCode.EMA_CLOSE)
    with pytest.raises(IndicatorViewValidationError, match="period must be a real int"):
        view.require(IndicatorCode.EMA_CLOSE, period=True)


def test_view_has_no_complete_series_or_bundle() -> None:
    view = IndicatorDecisionFeed.from_bundle(_bundle()).view_at(2)
    for name in ("bundle", "series", "indicator_input", "result_hash", "input_hash"):
        assert not hasattr(view, name)
    for item in view.items:
        assert not hasattr(item, "result_hash")
        assert item.history.visible_count == 3
    text = repr(view)
    assert "IndicatorDecisionView(bar_index=2" in text
    assert str(view) == text


def test_direct_view_construction_blocked() -> None:
    with pytest.raises(IndicatorViewValidationError, match="view_at"):
        IndicatorDecisionView()
