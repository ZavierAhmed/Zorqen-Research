"""Backtest engine, goldens, and determinism tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from zorqen_research.application.backtesting.engine import BacktestEngine
from zorqen_research.application.backtesting.golden import SCENARIOS, default_policy, run_scenario
from zorqen_research.application.backtesting.scripted import ScriptedDecisionProvider
from zorqen_research.application.backtesting.serialization import hash_result, serialize_result
from zorqen_research.domain.backtesting.enums import FillReason, PositionDirection
from zorqen_research.domain.backtesting.errors import (
    BacktestExecutionError,
    BacktestValidationError,
)
from zorqen_research.domain.backtesting.intents import EnterIntent, ExitIntent
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


def test_all_golden_scenarios() -> None:
    hashes: dict[str, str] = {}
    for name in SCENARIOS:
        first = run_scenario(name)
        second = run_scenario(name)
        assert serialize_result(first) == serialize_result(second)
        assert first.summary.result_hash == second.summary.result_hash
        hashes[name] = first.summary.result_hash
    # Stable non-empty hashes
    assert all(len(v) == 64 for v in hashes.values())
    assert len(set(hashes.values())) == len(hashes)


def test_no_fill_on_signal_candle() -> None:
    times = [datetime(2026, 6, 1, tzinfo=UTC) + timedelta(hours=i) for i in range(3)]
    candles = (
        _candle(times[0], "100", "110", "90", "100"),
        _candle(times[1], "100", "101", "99", "100"),
        _candle(times[2], "100", "101", "99", "100"),
    )
    enter = EnterIntent(
        intent_id="e1",
        decision_open_time=times[0],
        direction=PositionDirection.LONG,
        quantity=Decimal("1.000"),
        stop_loss=Decimal("95"),
        take_profit=Decimal("108"),
    )
    calls: list[int] = []

    class Tracking(ScriptedDecisionProvider):
        def on_bar_close(self, context):  # type: ignore[no-untyped-def]
            calls.append(context.bar_index)
            assert context.candles_processed == context.bar_index + 1
            return super().on_bar_close(context)

    provider = Tracking({0: (enter,)})
    engine = BacktestEngine(
        symbol=parse_symbol("BTCUSDT"),
        timeframe=Timeframe.H1,
        policy=default_policy(),
        provider=provider,
    )
    result = engine.run(candles)
    assert calls == [0, 1, 2]
    assert result.fills[0].bar_index == 1
    assert result.fills[0].fill_time == times[1]


def test_force_close_disabled_raises() -> None:
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
        stop_loss=Decimal("90"),
        take_profit=Decimal("150"),
    )
    engine = BacktestEngine(
        symbol=parse_symbol("BTCUSDT"),
        timeframe=Timeframe.H1,
        policy=default_policy(force_close_at_end=False),
        provider=ScriptedDecisionProvider({0: (enter,)}),
    )
    with pytest.raises(BacktestExecutionError, match="force_close_at_end"):
        engine.run(candles)


def test_gap_and_empty_inputs() -> None:
    engine = BacktestEngine(
        symbol=parse_symbol("BTCUSDT"),
        timeframe=Timeframe.H1,
        policy=default_policy(),
        provider=ScriptedDecisionProvider({}),
    )
    with pytest.raises(BacktestValidationError, match="non-empty"):
        engine.run(())
    t0 = datetime(2026, 6, 1, tzinfo=UTC)
    t2 = t0 + timedelta(hours=2)
    with pytest.raises(BacktestValidationError, match="Gap"):
        engine.run((_candle(t0, "1", "1", "1", "1"), _candle(t2, "1", "1", "1", "1")))


def test_unaligned_quantity_rejected() -> None:
    times = [datetime(2026, 6, 1, tzinfo=UTC) + timedelta(hours=i) for i in range(2)]
    candles = (
        _candle(times[0], "100", "101", "99", "100"),
        _candle(times[1], "100", "101", "99", "100"),
    )
    enter = EnterIntent(
        intent_id="e1",
        decision_open_time=times[0],
        direction=PositionDirection.LONG,
        quantity=Decimal("1.0005"),
        stop_loss=Decimal("90"),
        take_profit=Decimal("150"),
    )
    engine = BacktestEngine(
        symbol=parse_symbol("BTCUSDT"),
        timeframe=Timeframe.H1,
        policy=default_policy(),
        provider=ScriptedDecisionProvider({0: (enter,)}),
    )
    with pytest.raises(BacktestValidationError, match="quantity_step"):
        engine.run(candles)


def test_exit_while_flat_rejected() -> None:
    times = [datetime(2026, 6, 1, tzinfo=UTC) + timedelta(hours=i) for i in range(2)]
    candles = (
        _candle(times[0], "100", "101", "99", "100"),
        _candle(times[1], "100", "101", "99", "100"),
    )
    exit_intent = ExitIntent(intent_id="x1", decision_open_time=times[0])
    engine = BacktestEngine(
        symbol=parse_symbol("BTCUSDT"),
        timeframe=Timeframe.H1,
        policy=default_policy(),
        provider=ScriptedDecisionProvider({0: (exit_intent,)}),
    )
    with pytest.raises(BacktestValidationError, match="flat"):
        engine.run(candles)


def test_policy_change_changes_hash() -> None:
    a = run_scenario("long-target")
    times = SCENARIOS["long-target"].candles
    engine = BacktestEngine(
        symbol=parse_symbol("BTCUSDT"),
        timeframe=Timeframe.H1,
        policy=default_policy(taker_fee_bps=Decimal("20")),
        provider=SCENARIOS["long-target"].provider,
    )
    b = engine.run(times)
    assert a.summary.policy_hash != b.summary.policy_hash
    assert a.summary.result_hash != b.summary.result_hash


def test_explicit_exit_before_protective() -> None:
    result = run_scenario("explicit-exit")
    assert result.trades[0].exit_reason is FillReason.EXPLICIT_EXIT
    assert result.fills[1].reason is FillReason.EXPLICIT_EXIT


def test_equity_reconciles() -> None:
    for name in SCENARIOS:
        result = run_scenario(name)
        assert result.summary.final_equity == (
            result.summary.initial_equity + result.summary.net_pnl
        )
        assert hash_result(result) == result.summary.result_hash
