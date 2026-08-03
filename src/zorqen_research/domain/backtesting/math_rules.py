"""Exact Decimal helpers for tick and quantity alignment."""

from __future__ import annotations

from decimal import ROUND_CEILING, ROUND_FLOOR, Decimal

from zorqen_research.domain.backtesting.errors import BacktestValidationError


def require_finite_decimal(value: object, *, field: str) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, Decimal):
        msg = f"{field} must be a Decimal"
        raise BacktestValidationError(msg)
    if not value.is_finite():
        msg = f"{field} must be a finite Decimal"
        raise BacktestValidationError(msg)
    return value


def is_quantity_aligned(quantity: Decimal, quantity_step: Decimal) -> bool:
    return quantity % quantity_step == Decimal("0")


def assert_quantity_aligned(
    quantity: Decimal,
    *,
    quantity_step: Decimal,
    minimum_quantity: Decimal,
    field: str = "quantity",
) -> Decimal:
    quantity = require_finite_decimal(quantity, field=field)
    if quantity <= 0:
        msg = f"{field} must be positive"
        raise BacktestValidationError(msg)
    if quantity < minimum_quantity:
        msg = f"{field} is below minimum_quantity"
        raise BacktestValidationError(msg)
    if not is_quantity_aligned(quantity, quantity_step):
        msg = f"{field} must align exactly to quantity_step"
        raise BacktestValidationError(msg)
    return quantity


def floor_to_tick(price: Decimal, tick_size: Decimal) -> Decimal:
    units = (price / tick_size).to_integral_value(rounding=ROUND_FLOOR)
    return units * tick_size


def ceil_to_tick(price: Decimal, tick_size: Decimal) -> Decimal:
    units = (price / tick_size).to_integral_value(rounding=ROUND_CEILING)
    return units * tick_size


def normalize_buy_fill(price: Decimal, tick_size: Decimal) -> Decimal:
    """Conservative buy: round price upward."""
    return ceil_to_tick(price, tick_size)


def normalize_sell_fill(price: Decimal, tick_size: Decimal) -> Decimal:
    """Conservative sell: round price downward."""
    return floor_to_tick(price, tick_size)


def normalize_long_stop(price: Decimal, tick_size: Decimal) -> Decimal:
    return floor_to_tick(price, tick_size)


def normalize_long_target(price: Decimal, tick_size: Decimal) -> Decimal:
    """Conservative long target fill reference: floor (sell lower)."""
    return floor_to_tick(price, tick_size)


def normalize_short_stop(price: Decimal, tick_size: Decimal) -> Decimal:
    return ceil_to_tick(price, tick_size)


def normalize_short_target(price: Decimal, tick_size: Decimal) -> Decimal:
    """Conservative short target fill reference: ceil (buy higher)."""
    return ceil_to_tick(price, tick_size)


def apply_buy_slippage(reference: Decimal, slippage_bps: Decimal) -> Decimal:
    rate = slippage_bps / Decimal("10000")
    return reference * (Decimal("1") + rate)


def apply_sell_slippage(reference: Decimal, slippage_bps: Decimal) -> Decimal:
    rate = slippage_bps / Decimal("10000")
    return reference * (Decimal("1") - rate)


def compute_fee(fill_price: Decimal, quantity: Decimal, fee_bps: Decimal) -> Decimal:
    notional = abs(fill_price * quantity)
    return notional * fee_bps / Decimal("10000")
