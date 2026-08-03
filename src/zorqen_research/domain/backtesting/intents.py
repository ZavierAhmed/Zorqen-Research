"""Immutable backtest intents."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal

from zorqen_research.domain.backtesting.enums import IntentType, PositionDirection
from zorqen_research.domain.backtesting.errors import BacktestValidationError
from zorqen_research.domain.backtesting.math_rules import (
    assert_quantity_aligned,
    require_finite_decimal,
)
from zorqen_research.domain.backtesting.policy import BacktestPolicy


def _require_canonical_utc(value: datetime, *, field: str) -> None:
    if value.tzinfo is None:
        msg = f"{field} must be timezone-aware UTC"
        raise BacktestValidationError(msg)
    if value.utcoffset() != timedelta(0):
        msg = f"{field} must have a zero UTC offset"
        raise BacktestValidationError(msg)


@dataclass(frozen=True, slots=True)
class EnterIntent:
    intent_id: str
    decision_open_time: datetime
    direction: PositionDirection
    quantity: Decimal
    stop_loss: Decimal
    take_profit: Decimal
    label: str | None = None

    @property
    def intent_type(self) -> IntentType:
        return IntentType.ENTER

    def validate_for_policy(self, policy: BacktestPolicy) -> None:
        if not isinstance(self.intent_id, str) or not self.intent_id:
            msg = "intent_id must be a non-empty string"
            raise BacktestValidationError(msg)
        _require_canonical_utc(self.decision_open_time, field="decision_open_time")
        if not isinstance(self.direction, PositionDirection):
            msg = "direction must be a PositionDirection"
            raise BacktestValidationError(msg)
        assert_quantity_aligned(
            self.quantity,
            quantity_step=policy.quantity_step,
            minimum_quantity=policy.minimum_quantity,
        )
        stop = require_finite_decimal(self.stop_loss, field="stop_loss")
        target = require_finite_decimal(self.take_profit, field="take_profit")
        if stop <= 0 or target <= 0:
            msg = "stop_loss and take_profit must be positive"
            raise BacktestValidationError(msg)
        if self.label is not None and not isinstance(self.label, str):
            msg = "label must be a string or None"
            raise BacktestValidationError(msg)

    def validate_brackets_against_fill(self, fill_price: Decimal) -> None:
        fill = require_finite_decimal(fill_price, field="fill_price")
        if self.direction is PositionDirection.LONG:
            if not (self.stop_loss < fill < self.take_profit):
                msg = "Long brackets require stop_loss < fill_price < take_profit"
                raise BacktestValidationError(msg)
        else:
            if not (self.take_profit < fill < self.stop_loss):
                msg = "Short brackets require take_profit < fill_price < stop_loss"
                raise BacktestValidationError(msg)


@dataclass(frozen=True, slots=True)
class ExitIntent:
    intent_id: str
    decision_open_time: datetime
    label: str | None = None

    @property
    def intent_type(self) -> IntentType:
        return IntentType.EXIT

    def validate(self) -> None:
        if not isinstance(self.intent_id, str) or not self.intent_id:
            msg = "intent_id must be a non-empty string"
            raise BacktestValidationError(msg)
        _require_canonical_utc(self.decision_open_time, field="decision_open_time")
        if self.label is not None and not isinstance(self.label, str):
            msg = "label must be a string or None"
            raise BacktestValidationError(msg)


BacktestIntent = EnterIntent | ExitIntent
