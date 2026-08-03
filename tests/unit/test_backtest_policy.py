"""Backtest policy validation tests."""

from __future__ import annotations

from decimal import Decimal

import pytest

from zorqen_research.application.backtesting.golden import default_policy
from zorqen_research.domain.backtesting.enums import SameBarExitPolicy
from zorqen_research.domain.backtesting.errors import BacktestValidationError
from zorqen_research.domain.backtesting.policy import BacktestPolicy


def test_valid_policy() -> None:
    policy = default_policy()
    assert policy.same_bar_exit_policy is SameBarExitPolicy.STOP_FIRST


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("initial_equity", Decimal("NaN")),
        ("initial_equity", Decimal("-1")),
        ("initial_equity", Decimal("0")),
        ("taker_fee_bps", Decimal("-1")),
        ("market_slippage_bps", Decimal("-0.1")),
        ("tick_size", Decimal("0")),
        ("tick_size", Decimal("-1")),
        ("quantity_step", Decimal("0")),
        ("minimum_quantity", Decimal("0")),
        ("minimum_notional", Decimal("-1")),
    ],
)
def test_invalid_policy_values(field: str, value: Decimal) -> None:
    kwargs = {
        "initial_equity": Decimal("1000"),
        "taker_fee_bps": Decimal("1"),
        "market_slippage_bps": Decimal("1"),
        "tick_size": Decimal("0.01"),
        "quantity_step": Decimal("0.001"),
        "minimum_quantity": Decimal("0.001"),
        "minimum_notional": Decimal("0"),
        "force_close_at_end": True,
        "same_bar_exit_policy": SameBarExitPolicy.STOP_FIRST,
    }
    kwargs[field] = value
    with pytest.raises(BacktestValidationError):
        BacktestPolicy(**kwargs)  # type: ignore[arg-type]


def test_bool_not_accepted_as_numeric() -> None:
    with pytest.raises(BacktestValidationError):
        BacktestPolicy(
            initial_equity=True,  # type: ignore[arg-type]
            taker_fee_bps=Decimal("1"),
            market_slippage_bps=Decimal("1"),
            tick_size=Decimal("0.01"),
            quantity_step=Decimal("0.001"),
            minimum_quantity=Decimal("0.001"),
            minimum_notional=Decimal("0"),
            force_close_at_end=True,
            same_bar_exit_policy=SameBarExitPolicy.STOP_FIRST,
        )
