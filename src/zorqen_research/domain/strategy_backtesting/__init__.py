"""Domain package for multi-timeframe strategy backtest bridging."""

from __future__ import annotations

from typing import Any

from zorqen_research.domain.strategy_backtesting.decision_views import (
    ContextDecisionView,
    MultiTimeframeDecisionView,
    required_visible_count,
)
from zorqen_research.domain.strategy_backtesting.errors import (
    StrategyBacktestError,
    StrategyBacktestValidationError,
)
from zorqen_research.domain.strategy_backtesting.histories import VisibleCandleHistory
from zorqen_research.domain.strategy_backtesting.inputs import (
    ContextSeriesInput,
    MultiTimeframeBacktestInput,
)
from zorqen_research.domain.strategy_backtesting.results import StrategyBacktestEnvelope

__all__ = [
    "ContextDecisionView",
    "ContextIndicatorDecisionView",
    "ContextSeriesInput",
    "IndicatorStrategyBacktestEnvelope",
    "MultiTimeframeBacktestInput",
    "MultiTimeframeDecisionView",
    "MultiTimeframeIndicatorDecisionView",
    "MultiTimeframeIndicatorInput",
    "StrategyBacktestEnvelope",
    "StrategyBacktestError",
    "StrategyBacktestValidationError",
    "VisibleCandleHistory",
    "required_visible_count",
]

_LAZY_EXPORTS = {
    "ContextIndicatorDecisionView": (
        "zorqen_research.domain.strategy_backtesting.indicator_decision_views",
        "ContextIndicatorDecisionView",
    ),
    "IndicatorStrategyBacktestEnvelope": (
        "zorqen_research.domain.strategy_backtesting.indicator_results",
        "IndicatorStrategyBacktestEnvelope",
    ),
    "MultiTimeframeIndicatorDecisionView": (
        "zorqen_research.domain.strategy_backtesting.indicator_decision_views",
        "MultiTimeframeIndicatorDecisionView",
    ),
    "MultiTimeframeIndicatorInput": (
        "zorqen_research.domain.strategy_backtesting.indicator_composition",
        "MultiTimeframeIndicatorInput",
    ),
}


def __getattr__(name: str) -> Any:
    target = _LAZY_EXPORTS.get(name)
    if target is None:
        msg = f"module {__name__!r} has no attribute {name!r}"
        raise AttributeError(msg)
    module_name, attr_name = target
    from importlib import import_module

    value = getattr(import_module(module_name), attr_name)
    globals()[name] = value
    return value
