"""Fills and positions for the backtest kernel."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from zorqen_research.domain.backtesting.enums import (
    FillReason,
    FillSide,
    LiquidityRole,
    PositionDirection,
)


@dataclass(frozen=True, slots=True)
class FillRecord:
    fill_id: str
    intent_id: str | None
    position_id: str
    bar_index: int
    fill_time: datetime
    side: FillSide
    direction: PositionDirection
    reason: FillReason
    reference_price: Decimal
    fill_price: Decimal
    quantity: Decimal
    notional: Decimal
    fee: Decimal
    liquidity_role: LiquidityRole
    tick_normalized: bool


@dataclass(frozen=True, slots=True)
class PositionSnapshot:
    position_id: str
    entry_intent_id: str
    direction: PositionDirection
    quantity: Decimal
    entry_decision_time: datetime
    entry_fill_time: datetime
    entry_price: Decimal
    entry_fee: Decimal
    stop_loss: Decimal
    take_profit: Decimal
    entry_bar_index: int
