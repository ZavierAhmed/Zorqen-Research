"""Scripted decision provider for golden and unit tests only."""

from __future__ import annotations

from collections.abc import Mapping

from zorqen_research.application.backtesting.provider import BacktestDecisionContext
from zorqen_research.domain.backtesting.intents import BacktestIntent


class ScriptedDecisionProvider:
    """
    Deterministic bar-index → intents map.

    Not a production strategy implementation.
    """

    def __init__(self, schedule: Mapping[int, tuple[BacktestIntent, ...]]) -> None:
        self._schedule = {int(k): tuple(v) for k, v in schedule.items()}

    def on_bar_close(self, context: BacktestDecisionContext) -> tuple[BacktestIntent, ...]:
        return self._schedule.get(context.bar_index, ())
