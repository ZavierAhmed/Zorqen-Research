"""Additional kernel validation and determinism coverage."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from zorqen_research.application.backtesting.engine import BacktestEngine
from zorqen_research.application.backtesting.golden import SCENARIOS, default_policy, run_scenario
from zorqen_research.application.backtesting.scripted import ScriptedDecisionProvider
from zorqen_research.application.backtesting.serialization import hash_result
from zorqen_research.domain.backtesting.enums import FillReason, PositionDirection
from zorqen_research.domain.backtesting.errors import BacktestValidationError
from zorqen_research.domain.backtesting.intents import EnterIntent
from zorqen_research.domain.candles import Candle
from zorqen_research.domain.symbols import parse_symbol
from zorqen_research.domain.timeframes import Timeframe, timeframe_duration


def _candle(
    open_time: datetime, o: str = "100", h: str = "101", low: str = "99", c: str = "100"
) -> Candle:
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


def _engine(provider: ScriptedDecisionProvider, **policy_kw: object) -> BacktestEngine:
    return BacktestEngine(
        symbol=parse_symbol("BTCUSDT"),
        timeframe=Timeframe.H1,
        policy=default_policy(**policy_kw),
        provider=provider,
    )


def test_duplicate_candle_rejected() -> None:
    t0 = datetime(2026, 6, 1, tzinfo=UTC)
    with pytest.raises(BacktestValidationError, match="Duplicate"):
        _engine(ScriptedDecisionProvider({})).run((_candle(t0), _candle(t0)))


def test_out_of_order_candle_rejected() -> None:
    t0 = datetime(2026, 6, 1, tzinfo=UTC)
    t1 = t0 + timedelta(hours=1)
    with pytest.raises(BacktestValidationError, match="Out-of-order"):
        _engine(ScriptedDecisionProvider({})).run((_candle(t1), _candle(t0)))


def test_misaligned_candle_rejected() -> None:
    t0 = datetime(2026, 6, 1, minute=30, tzinfo=UTC)
    with pytest.raises(BacktestValidationError, match="aligned"):
        _engine(ScriptedDecisionProvider({})).run((_candle(t0),))


def test_invalid_close_time_convention_rejected() -> None:
    t0 = datetime(2026, 6, 1, tzinfo=UTC)
    bad = Candle(
        open_time=t0,
        open=Decimal("1"),
        high=Decimal("1"),
        low=Decimal("1"),
        close=Decimal("1"),
        volume=Decimal("1"),
        close_time=t0 + timedelta(hours=1),  # should be duration - 1ms
        quote_asset_volume=Decimal("1"),
        trade_count=1,
        taker_buy_base_volume=Decimal("0"),
        taker_buy_quote_volume=Decimal("0"),
    )
    with pytest.raises(BacktestValidationError, match="close_time"):
        _engine(ScriptedDecisionProvider({})).run((bad,))


def test_expected_input_hash_mismatch() -> None:
    t0 = datetime(2026, 6, 1, tzinfo=UTC)
    with pytest.raises(BacktestValidationError, match="Input candle hash"):
        _engine(ScriptedDecisionProvider({})).run(
            (_candle(t0),),
            expected_input_hash="0" * 64,
        )


def test_entry_while_positioned_rejected() -> None:
    times = [datetime(2026, 6, 1, tzinfo=UTC) + timedelta(hours=i) for i in range(4)]
    candles = tuple(_candle(t) for t in times)
    enter1 = EnterIntent(
        intent_id="e1",
        decision_open_time=times[0],
        direction=PositionDirection.LONG,
        quantity=Decimal("1.000"),
        stop_loss=Decimal("50"),
        take_profit=Decimal("200"),
    )
    enter2 = EnterIntent(
        intent_id="e2",
        decision_open_time=times[1],
        direction=PositionDirection.LONG,
        quantity=Decimal("1.000"),
        stop_loss=Decimal("50"),
        take_profit=Decimal("200"),
    )
    with pytest.raises(BacktestValidationError, match="position is open"):
        _engine(ScriptedDecisionProvider({0: (enter1,), 1: (enter2,)})).run(candles)


def test_more_than_one_returned_intent() -> None:
    t0 = datetime(2026, 6, 1, tzinfo=UTC)
    candles = (_candle(t0), _candle(t0 + timedelta(hours=1)))
    a = EnterIntent(
        intent_id="e1",
        decision_open_time=t0,
        direction=PositionDirection.LONG,
        quantity=Decimal("1.000"),
        stop_loss=Decimal("90"),
        take_profit=Decimal("150"),
    )
    b = EnterIntent(
        intent_id="e2",
        decision_open_time=t0,
        direction=PositionDirection.LONG,
        quantity=Decimal("1.000"),
        stop_loss=Decimal("90"),
        take_profit=Decimal("150"),
    )
    with pytest.raises(BacktestValidationError, match="At most one"):
        _engine(ScriptedDecisionProvider({0: (a, b)})).run(candles)


def test_no_pyramiding_explicit() -> None:
    """Flat→enter→hold→cannot add; must exit first (covered by entry-while-positioned)."""
    result = run_scenario("long-target")
    assert result.summary.closed_trade_count == 1
    assert len(result.fills) == 2


def test_short_stop_loss() -> None:
    times = [datetime(2026, 6, 1, tzinfo=UTC) + timedelta(hours=i) for i in range(3)]
    candles = (
        _candle(times[0], "100", "101", "99", "100"),
        _candle(times[1], "100", "101", "99", "100"),
        _candle(times[2], "100", "120", "99", "115"),
    )
    enter = EnterIntent(
        intent_id="short-stop",
        decision_open_time=times[0],
        direction=PositionDirection.SHORT,
        quantity=Decimal("1.000"),
        stop_loss=Decimal("110"),
        take_profit=Decimal("80"),
    )
    result = _engine(ScriptedDecisionProvider({0: (enter,)})).run(candles)
    assert result.trades[0].exit_reason is FillReason.STOP_LOSS
    assert result.fills[0].side.value == "sell"
    assert result.fills[1].side.value == "buy"


def test_fill_and_trade_id_stability() -> None:
    a = run_scenario("long-target")
    b = run_scenario("long-target")
    assert (
        [f.fill_id for f in a.fills]
        == [f.fill_id for f in b.fills]
        == ["fill-000001", "fill-000002"]
    )
    assert [t.trade_id for t in a.trades] == [t.trade_id for t in b.trades] == ["trade-000001"]
    assert a.fills[0].position_id == b.fills[0].position_id == "pos-000001"


def test_candle_change_modifies_result_hash() -> None:
    base = run_scenario("long-stop")
    scenario = SCENARIOS["long-stop"]
    candles = list(scenario.candles)
    last = candles[-1]
    candles[-1] = _candle(last.open_time, "100", "100.2", "89", "90")
    engine = BacktestEngine(
        symbol=parse_symbol("BTCUSDT"),
        timeframe=Timeframe.H1,
        policy=scenario.policy,
        provider=scenario.provider,
    )
    altered = engine.run(candles)
    assert altered.summary.result_hash != base.summary.result_hash
    assert altered.summary.input_candle_hash != base.summary.input_candle_hash


def test_intent_change_modifies_result_hash() -> None:
    base = run_scenario("long-stop")
    scenario = SCENARIOS["long-stop"]
    times = [c.open_time for c in scenario.candles]
    enter = EnterIntent(
        intent_id="enter-long-stop-altered",
        decision_open_time=times[0],
        direction=PositionDirection.LONG,
        quantity=Decimal("1.000"),
        stop_loss=Decimal("95"),
        take_profit=Decimal("120"),
    )
    altered = _engine(ScriptedDecisionProvider({0: (enter,)})).run(scenario.candles)
    assert altered.summary.result_hash != base.summary.result_hash


def test_total_fee_reconciliation() -> None:
    for name in SCENARIOS:
        result = run_scenario(name)
        assert result.summary.total_fees == sum((f.fee for f in result.fills), Decimal("0"))
        for trade in result.trades:
            assert trade.total_fees == trade.entry_fee + trade.exit_fee


def test_one_entry_and_one_exit_fill_per_closed_trade() -> None:
    for name in SCENARIOS:
        result = run_scenario(name)
        for trade in result.trades:
            entry = next(f for f in result.fills if f.fill_id == trade.entry_fill_id)
            exit_fill = next(f for f in result.fills if f.fill_id == trade.exit_fill_id)
            assert entry.reason is FillReason.MARKET_ENTRY
            assert exit_fill.reason is trade.exit_reason
            assert entry.position_id == exit_fill.position_id == trade.position_id


def test_hash_result_matches_summary() -> None:
    for name in SCENARIOS:
        result = run_scenario(name)
        assert hash_result(result) == result.summary.result_hash
