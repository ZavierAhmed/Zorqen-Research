"""Immutable backtest intents."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation

from zorqen_research.domain.backtesting.enums import IntentType, PositionDirection
from zorqen_research.domain.backtesting.errors import BacktestValidationError
from zorqen_research.domain.backtesting.math_rules import (
    assert_quantity_aligned,
    require_finite_decimal,
    require_positive_price,
)
from zorqen_research.domain.backtesting.policy import BacktestPolicy


def _require_trimmed_intent_id(value: object) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        msg = "intent_id must be a non-empty trimmed string"
        raise BacktestValidationError(msg)
    return value


def _require_canonical_utc(value: object, *, field: str) -> datetime:
    if not isinstance(value, datetime):
        msg = f"{field} must be a datetime"
        raise BacktestValidationError(msg)
    if value.tzinfo is None:
        msg = f"{field} must be timezone-aware UTC"
        raise BacktestValidationError(msg)
    try:
        offset = value.utcoffset()
    except Exception as exc:  # noqa: BLE001 — sanitize exotic tzinfo
        msg = f"{field} must have a zero UTC offset"
        raise BacktestValidationError(msg) from exc
    if offset != timedelta(0):
        msg = f"{field} must have a zero UTC offset"
        raise BacktestValidationError(msg)
    return value


def _require_optional_label(value: object) -> str | None:
    if value is not None and not isinstance(value, str):
        msg = "label must be a string or None"
        raise BacktestValidationError(msg)
    return value


@dataclass(frozen=True, slots=True)
class EnterIntent:
    intent_id: str
    decision_open_time: datetime
    direction: PositionDirection
    quantity: Decimal
    stop_loss: Decimal
    take_profit: Decimal
    label: str | None = None

    def __post_init__(self) -> None:
        self.validate_intrinsic()

    @property
    def intent_type(self) -> IntentType:
        return IntentType.ENTER

    def validate_intrinsic(self) -> None:
        """Policy-independent field validation (safe for malformed runtime types)."""
        try:
            _require_trimmed_intent_id(self.intent_id)
            _require_canonical_utc(self.decision_open_time, field="decision_open_time")
            if not isinstance(self.direction, PositionDirection):
                msg = "direction must be a PositionDirection"
                raise BacktestValidationError(msg)
            quantity = require_finite_decimal(self.quantity, field="quantity")
            if quantity <= 0:
                msg = "quantity must be a finite positive Decimal"
                raise BacktestValidationError(msg)
            require_positive_price(self.stop_loss, field="stop_loss")
            require_positive_price(self.take_profit, field="take_profit")
            _require_optional_label(self.label)
        except BacktestValidationError:
            raise
        except (AttributeError, TypeError, InvalidOperation) as exc:
            msg = "EnterIntent contains invalid runtime values"
            raise BacktestValidationError(msg) from exc

    def validate_for_policy(self, policy: BacktestPolicy) -> None:
        self.validate_intrinsic()
        assert_quantity_aligned(
            self.quantity,
            quantity_step=policy.quantity_step,
            minimum_quantity=policy.minimum_quantity,
        )

    def validate_brackets_against_fill(self, fill_price: Decimal) -> None:
        try:
            fill = require_positive_price(fill_price, field="fill_price")
            stop = require_positive_price(self.stop_loss, field="stop_loss")
            target = require_positive_price(self.take_profit, field="take_profit")
            if self.direction is PositionDirection.LONG:
                if not (stop < fill < target):
                    msg = "Long brackets require stop_loss < fill_price < take_profit"
                    raise BacktestValidationError(msg)
            elif not (target < fill < stop):
                msg = "Short brackets require take_profit < fill_price < stop_loss"
                raise BacktestValidationError(msg)
        except BacktestValidationError:
            raise
        except (AttributeError, TypeError, InvalidOperation) as exc:
            msg = "Invalid bracket comparison"
            raise BacktestValidationError(msg) from exc


@dataclass(frozen=True, slots=True)
class ExitIntent:
    intent_id: str
    decision_open_time: datetime
    label: str | None = None

    def __post_init__(self) -> None:
        self.validate()

    @property
    def intent_type(self) -> IntentType:
        return IntentType.EXIT

    def validate(self) -> None:
        try:
            _require_trimmed_intent_id(self.intent_id)
            _require_canonical_utc(self.decision_open_time, field="decision_open_time")
            _require_optional_label(self.label)
        except BacktestValidationError:
            raise
        except (AttributeError, TypeError, InvalidOperation) as exc:
            msg = "ExitIntent contains invalid runtime values"
            raise BacktestValidationError(msg) from exc


BacktestIntent = EnterIntent | ExitIntent
