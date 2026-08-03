"""Closed-trade ledger models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from zorqen_research.domain.backtesting.enums import FillReason, PositionDirection


@dataclass(frozen=True, slots=True)
class ClosedTrade:
    trade_id: str
    position_id: str
    direction: PositionDirection
    quantity: Decimal
    entry_fill_id: str
    exit_fill_id: str
    entry_time: datetime
    exit_time: datetime
    entry_price: Decimal
    exit_price: Decimal
    stop_loss: Decimal
    take_profit: Decimal
    exit_reason: FillReason
    entry_fee: Decimal
    exit_fee: Decimal
    total_fees: Decimal
    gross_pnl: Decimal
    net_pnl: Decimal
    bars_held: int
    same_bar_ambiguity_used: bool
