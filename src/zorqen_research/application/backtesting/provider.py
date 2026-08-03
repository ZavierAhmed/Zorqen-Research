"""Strategy-independent decision provider protocol."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol

from zorqen_research.domain.backtesting.execution import PositionSnapshot
from zorqen_research.domain.backtesting.intents import BacktestIntent
from zorqen_research.domain.backtesting.trades import ClosedTrade
from zorqen_research.domain.candles import Candle
from zorqen_research.domain.symbols import Symbol
from zorqen_research.domain.timeframes import Timeframe


@dataclass(frozen=True, slots=True)
class BacktestDecisionContext:
    """Information available to a decision provider at candle close."""

    candle: Candle
    bar_index: int
    symbol: Symbol
    timeframe: Timeframe
    position: PositionSnapshot | None
    realized_equity: Decimal
    last_closed_trade: ClosedTrade | None
    candles_processed: int


class BacktestDecisionProvider(Protocol):
    def on_bar_close(self, context: BacktestDecisionContext) -> tuple[BacktestIntent, ...]:
        """Return intents that become eligible only on the next candle open."""
