"""Backtest result summary and aggregate result."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from zorqen_research.domain.backtesting.execution import FillRecord
from zorqen_research.domain.backtesting.intents import BacktestIntent
from zorqen_research.domain.backtesting.policy import BacktestPolicy
from zorqen_research.domain.backtesting.trades import ClosedTrade
from zorqen_research.domain.symbols import Symbol
from zorqen_research.domain.timeframes import Timeframe


@dataclass(frozen=True, slots=True)
class BacktestSummary:
    initial_equity: Decimal
    final_equity: Decimal
    gross_pnl: Decimal
    net_pnl: Decimal
    total_fees: Decimal
    closed_trade_count: int
    winning_trade_count: int
    losing_trade_count: int
    breakeven_trade_count: int
    forced_close_count: int
    stop_loss_count: int
    take_profit_count: int
    explicit_exit_count: int
    unfilled_intent_count: int
    max_realized_equity_drawdown: Decimal
    input_candle_count: int
    input_candle_hash: str
    policy_hash: str
    result_hash: str


@dataclass(frozen=True, slots=True)
class UnfilledIntentRecord:
    intent: BacktestIntent
    reason: str


@dataclass(frozen=True, slots=True)
class BacktestResult:
    symbol: Symbol
    timeframe: Timeframe
    policy: BacktestPolicy
    fills: tuple[FillRecord, ...]
    trades: tuple[ClosedTrade, ...]
    unfilled_intents: tuple[UnfilledIntentRecord, ...]
    equity_curve: tuple[Decimal, ...]
    summary: BacktestSummary
