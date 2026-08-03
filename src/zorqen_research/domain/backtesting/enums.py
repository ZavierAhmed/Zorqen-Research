"""Backtest domain enumerations."""

from __future__ import annotations

from enum import StrEnum


class PositionDirection(StrEnum):
    LONG = "long"
    SHORT = "short"


class IntentType(StrEnum):
    ENTER = "enter"
    EXIT = "exit"


class FillReason(StrEnum):
    MARKET_ENTRY = "market_entry"
    EXPLICIT_EXIT = "explicit_exit"
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"
    END_OF_DATA = "end_of_data"


class LiquidityRole(StrEnum):
    TAKER = "taker"


class SameBarExitPolicy(StrEnum):
    STOP_FIRST = "stop_first"


class FillSide(StrEnum):
    BUY = "buy"
    SELL = "sell"
