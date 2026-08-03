"""Immutable backtest execution policy."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from zorqen_research.domain.backtesting.enums import SameBarExitPolicy
from zorqen_research.domain.backtesting.errors import BacktestValidationError
from zorqen_research.domain.backtesting.math_rules import require_finite_decimal


@dataclass(frozen=True, slots=True)
class BacktestPolicy:
    initial_equity: Decimal
    taker_fee_bps: Decimal
    market_slippage_bps: Decimal
    tick_size: Decimal
    quantity_step: Decimal
    minimum_quantity: Decimal
    minimum_notional: Decimal
    force_close_at_end: bool
    same_bar_exit_policy: SameBarExitPolicy

    def __post_init__(self) -> None:
        if isinstance(self.force_close_at_end, bool) is False:
            msg = "force_close_at_end must be a bool"
            raise BacktestValidationError(msg)
        if not isinstance(self.same_bar_exit_policy, SameBarExitPolicy):
            msg = "same_bar_exit_policy must be a SameBarExitPolicy"
            raise BacktestValidationError(msg)
        if self.same_bar_exit_policy is not SameBarExitPolicy.STOP_FIRST:
            msg = "Only stop_first same-bar exit policy is supported"
            raise BacktestValidationError(msg)

        equity = require_finite_decimal(self.initial_equity, field="initial_equity")
        if equity <= 0:
            msg = "initial_equity must be positive"
            raise BacktestValidationError(msg)

        fee = require_finite_decimal(self.taker_fee_bps, field="taker_fee_bps")
        if fee < 0:
            msg = "taker_fee_bps must be non-negative"
            raise BacktestValidationError(msg)

        slip = require_finite_decimal(self.market_slippage_bps, field="market_slippage_bps")
        if slip < 0:
            msg = "market_slippage_bps must be non-negative"
            raise BacktestValidationError(msg)

        tick = require_finite_decimal(self.tick_size, field="tick_size")
        if tick <= 0:
            msg = "tick_size must be positive"
            raise BacktestValidationError(msg)

        step = require_finite_decimal(self.quantity_step, field="quantity_step")
        if step <= 0:
            msg = "quantity_step must be positive"
            raise BacktestValidationError(msg)

        min_qty = require_finite_decimal(self.minimum_quantity, field="minimum_quantity")
        if min_qty <= 0:
            msg = "minimum_quantity must be positive"
            raise BacktestValidationError(msg)

        min_notional = require_finite_decimal(self.minimum_notional, field="minimum_notional")
        if min_notional < 0:
            msg = "minimum_notional must be non-negative"
            raise BacktestValidationError(msg)
