"""Application layer for standalone indicator decision feeds."""

from __future__ import annotations

from typing import Any

__all__ = [
    "IndicatorDecisionFeed",
]


def __getattr__(name: str) -> Any:
    if name == "IndicatorDecisionFeed":
        from zorqen_research.application.indicator_views.feed import IndicatorDecisionFeed

        globals()[name] = IndicatorDecisionFeed
        return IndicatorDecisionFeed
    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)
