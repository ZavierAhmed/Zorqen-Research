"""Application package for multi-timeframe strategy backtest bridging."""

from __future__ import annotations

from typing import Any

from zorqen_research.application.strategy_backtesting.feed import MultiTimeframeDecisionFeed
from zorqen_research.application.strategy_backtesting.provider import (
    MultiTimeframeBacktestDecisionContext,
    MultiTimeframeDecisionProvider,
    MultiTimeframeProviderAdapter,
)
from zorqen_research.application.strategy_backtesting.runner import MultiTimeframeBacktestRunner

__all__ = [
    "MultiTimeframeBacktestDecisionContext",
    "MultiTimeframeBacktestRunner",
    "MultiTimeframeDecisionFeed",
    "MultiTimeframeDecisionProvider",
    "MultiTimeframeIndicatorBacktestDecisionContext",
    "MultiTimeframeIndicatorBacktestRunner",
    "MultiTimeframeIndicatorDecisionFeed",
    "MultiTimeframeIndicatorDecisionProvider",
    "MultiTimeframeIndicatorProviderAdapter",
    "MultiTimeframeProviderAdapter",
]

_LAZY_EXPORTS = {
    "MultiTimeframeIndicatorBacktestDecisionContext": (
        "zorqen_research.application.strategy_backtesting.indicator_provider",
        "MultiTimeframeIndicatorBacktestDecisionContext",
    ),
    "MultiTimeframeIndicatorBacktestRunner": (
        "zorqen_research.application.strategy_backtesting.indicator_runner",
        "MultiTimeframeIndicatorBacktestRunner",
    ),
    "MultiTimeframeIndicatorDecisionFeed": (
        "zorqen_research.application.strategy_backtesting.indicator_feed",
        "MultiTimeframeIndicatorDecisionFeed",
    ),
    "MultiTimeframeIndicatorDecisionProvider": (
        "zorqen_research.application.strategy_backtesting.indicator_provider",
        "MultiTimeframeIndicatorDecisionProvider",
    ),
    "MultiTimeframeIndicatorProviderAdapter": (
        "zorqen_research.application.strategy_backtesting.indicator_provider",
        "MultiTimeframeIndicatorProviderAdapter",
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
