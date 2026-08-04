"""Provider / MTF boundary: Milestone 1.1 must not modify existing feeds."""

from __future__ import annotations

import inspect

from zorqen_research.application.strategy_backtesting.feed import MultiTimeframeDecisionFeed
from zorqen_research.application.strategy_backtesting.provider import (
    MultiTimeframeBacktestDecisionContext,
    MultiTimeframeProviderAdapter,
)
from zorqen_research.domain.strategy_backtesting.decision_views import (
    ContextDecisionView,
    MultiTimeframeDecisionView,
)


def test_mtf_types_have_no_indicator_fields() -> None:
    for cls in (
        MultiTimeframeDecisionFeed,
        MultiTimeframeDecisionView,
        ContextDecisionView,
        MultiTimeframeProviderAdapter,
        MultiTimeframeBacktestDecisionContext,
    ):
        source = inspect.getsource(cls)
        assert "IndicatorSeries" not in source
        assert "IndicatorSeriesBundle" not in source
        assert "IndicatorDecisionFeed" not in source
        assert "VisibleIndicatorHistory" not in source
