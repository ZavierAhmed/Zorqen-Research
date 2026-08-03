"""Positive-price and slippage fail-closed tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from zorqen_research.application.backtesting.engine import BacktestEngine
from zorqen_research.application.backtesting.golden import default_policy
from zorqen_research.application.backtesting.scripted import ScriptedDecisionProvider
from zorqen_research.domain.backtesting.enums import PositionDirection, SameBarExitPolicy
from zorqen_research.domain.backtesting.errors import BacktestValidationError
from zorqen_research.domain.backtesting.intents import EnterIntent
from zorqen_research.domain.backtesting.policy import BacktestPolicy
from zorqen_research.domain.candles import Candle
from zorqen_research.domain.symbols import parse_symbol
from zorqen_research.domain.timeframes import Timeframe, timeframe_duration


def _candle(open_time: datetime, o: str, h: str, low: str, c: str) -> Candle:
    close_time = open_time + timeframe_duration(Timeframe.H1) - timedelta(milliseconds=1)
    return Candle(
        open_time=open_time,
        open=Decimal(o),
        high=Decimal(h),
        low=Decimal(low),
        close=Decimal(c),
        volume=Decimal("1"),
        close_time=close_time,
        quote_asset_volume=Decimal("1"),
        trade_count=1,
        taker_buy_base_volume=Decimal("0"),
        taker_buy_quote_volume=Decimal("0"),
    )


@pytest.mark.parametrize("slip", [Decimal("10000"), Decimal("10001"), Decimal("20000")])
def test_slippage_at_or_above_10000_rejected(slip: Decimal) -> None:
    with pytest.raises(BacktestValidationError, match="market_slippage_bps"):
        BacktestPolicy(
            initial_equity=Decimal("1000"),
            taker_fee_bps=Decimal("1"),
            market_slippage_bps=slip,
            tick_size=Decimal("0.01"),
            quantity_step=Decimal("0.001"),
            minimum_quantity=Decimal("0.001"),
            minimum_notional=Decimal("0"),
            force_close_at_end=True,
            same_bar_exit_policy=SameBarExitPolicy.STOP_FIRST,
        )


def test_large_tick_normalizes_long_stop_to_zero() -> None:
    times = [datetime(2026, 6, 1, tzinfo=UTC) + timedelta(hours=i) for i in range(2)]
    candles = (
        _candle(times[0], "100", "101", "99", "100"),
        _candle(times[1], "100", "101", "99", "100"),
    )
    enter = EnterIntent(
        intent_id="e1",
        decision_open_time=times[0],
        direction=PositionDirection.LONG,
        quantity=Decimal("1.000"),
        stop_loss=Decimal("50"),
        take_profit=Decimal("150"),
    )
    engine = BacktestEngine(
        symbol=parse_symbol("BTCUSDT"),
        timeframe=Timeframe.H1,
        policy=default_policy(tick_size=Decimal("100")),
        provider=ScriptedDecisionProvider({0: (enter,)}),
    )
    with pytest.raises(BacktestValidationError, match="stop_loss"):
        engine.run(candles)


def test_large_tick_normalizes_sell_exit_to_zero() -> None:
    times = [datetime(2026, 6, 1, tzinfo=UTC) + timedelta(hours=i) for i in range(3)]
    candles = (
        _candle(times[0], "100", "101", "99", "100"),
        _candle(times[1], "100", "101", "99", "100"),
        _candle(times[2], "100", "101", "0.5", "50"),
    )
    enter = EnterIntent(
        intent_id="e1",
        decision_open_time=times[0],
        direction=PositionDirection.LONG,
        quantity=Decimal("1.000"),
        stop_loss=Decimal("1"),
        take_profit=Decimal("500"),
    )
    engine = BacktestEngine(
        symbol=parse_symbol("BTCUSDT"),
        timeframe=Timeframe.H1,
        policy=default_policy(tick_size=Decimal("0.1"), market_slippage_bps=Decimal("9999")),
        provider=ScriptedDecisionProvider({0: (enter,)}),
    )
    with pytest.raises(BacktestValidationError, match="exit_fill_price"):
        engine.run(candles)


def test_no_nonpositive_fill_or_bracket_on_valid_run() -> None:
    from zorqen_research.application.backtesting.golden import SCENARIOS, run_scenario

    for name in SCENARIOS:
        result = run_scenario(name)
        for fill in result.fills:
            assert fill.fill_price > 0
            assert fill.fill_price.is_finite()
        for trade in result.trades:
            assert trade.entry_price > 0
            assert trade.exit_price > 0
            assert trade.stop_loss > 0
            assert trade.take_profit > 0


def test_valid_near_max_slippage_still_works() -> None:
    policy = default_policy(market_slippage_bps=Decimal("9999"))
    assert policy.market_slippage_bps == Decimal("9999")
