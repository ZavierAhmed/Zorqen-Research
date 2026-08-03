"""Golden scripted backtest scenarios."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from zorqen_research.application.backtesting.engine import BacktestEngine
from zorqen_research.application.backtesting.golden_expectations import (
    GOLDEN_EXPECTATIONS,
    assert_matches_expectation,
)
from zorqen_research.application.backtesting.scripted import ScriptedDecisionProvider
from zorqen_research.domain.backtesting.enums import (
    FillReason,
    PositionDirection,
    SameBarExitPolicy,
)
from zorqen_research.domain.backtesting.intents import EnterIntent, ExitIntent
from zorqen_research.domain.backtesting.policy import BacktestPolicy
from zorqen_research.domain.backtesting.results import BacktestResult
from zorqen_research.domain.candles import Candle
from zorqen_research.domain.symbols import parse_symbol
from zorqen_research.domain.timeframes import Timeframe, timeframe_duration


def _candle(
    open_time: datetime,
    *,
    open_: str,
    high: str,
    low: str,
    close: str,
) -> Candle:
    duration = timeframe_duration(Timeframe.H1)
    close_time = open_time + duration - timedelta(milliseconds=1)
    return Candle(
        open_time=open_time,
        open=Decimal(open_),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
        volume=Decimal("1"),
        close_time=close_time,
        quote_asset_volume=Decimal("1"),
        trade_count=1,
        taker_buy_base_volume=Decimal("0.5"),
        taker_buy_quote_volume=Decimal("0.5"),
    )


def default_policy(**overrides: object) -> BacktestPolicy:
    base = {
        "initial_equity": Decimal("10000"),
        "taker_fee_bps": Decimal("10"),  # 0.10%
        "market_slippage_bps": Decimal("5"),  # 0.05%
        "tick_size": Decimal("0.01"),
        "quantity_step": Decimal("0.001"),
        "minimum_quantity": Decimal("0.001"),
        "minimum_notional": Decimal("0"),
        "force_close_at_end": True,
        "same_bar_exit_policy": SameBarExitPolicy.STOP_FIRST,
    }
    base.update(overrides)
    return BacktestPolicy(**base)  # type: ignore[arg-type]


def _seq(start: datetime, count: int) -> list[datetime]:
    return [start + timedelta(hours=i) for i in range(count)]


@dataclass(frozen=True, slots=True)
class GoldenScenario:
    name: str
    candles: tuple[Candle, ...]
    provider: ScriptedDecisionProvider
    policy: BacktestPolicy
    expected_closed_trades: int
    expected_exit_reason: FillReason | None
    expected_unfilled: int


def scenario_long_target() -> GoldenScenario:
    times = _seq(datetime(2026, 6, 1, tzinfo=UTC), 4)
    candles = (
        _candle(times[0], open_="100", high="101", low="99", close="100.5"),
        _candle(times[1], open_="100.5", high="102", low="100", close="101"),
        _candle(times[2], open_="101", high="110", low="100.8", close="109"),
        _candle(times[3], open_="109", high="110", low="108", close="109.5"),
    )
    enter = EnterIntent(
        intent_id="enter-long-target",
        decision_open_time=times[0],
        direction=PositionDirection.LONG,
        quantity=Decimal("1.000"),
        stop_loss=Decimal("95"),
        take_profit=Decimal("108"),
        label="long-target",
    )
    provider = ScriptedDecisionProvider({0: (enter,)})
    return GoldenScenario(
        name="long-target",
        candles=candles,
        provider=provider,
        policy=default_policy(),
        expected_closed_trades=1,
        expected_exit_reason=FillReason.TAKE_PROFIT,
        expected_unfilled=0,
    )


def scenario_long_stop() -> GoldenScenario:
    times = _seq(datetime(2026, 6, 1, tzinfo=UTC), 3)
    candles = (
        _candle(times[0], open_="100", high="101", low="99", close="100"),
        _candle(times[1], open_="100", high="100.5", low="99.5", close="100"),
        _candle(times[2], open_="100", high="100.2", low="90", close="91"),
    )
    enter = EnterIntent(
        intent_id="enter-long-stop",
        decision_open_time=times[0],
        direction=PositionDirection.LONG,
        quantity=Decimal("1.000"),
        stop_loss=Decimal("95"),
        take_profit=Decimal("120"),
    )
    return GoldenScenario(
        name="long-stop",
        candles=candles,
        provider=ScriptedDecisionProvider({0: (enter,)}),
        policy=default_policy(),
        expected_closed_trades=1,
        expected_exit_reason=FillReason.STOP_LOSS,
        expected_unfilled=0,
    )


def scenario_short_target() -> GoldenScenario:
    times = _seq(datetime(2026, 6, 1, tzinfo=UTC), 3)
    candles = (
        _candle(times[0], open_="100", high="101", low="99", close="100"),
        _candle(times[1], open_="100", high="100.5", low="99.5", close="100"),
        _candle(times[2], open_="100", high="100.2", low="90", close="91"),
    )
    enter = EnterIntent(
        intent_id="enter-short-target",
        decision_open_time=times[0],
        direction=PositionDirection.SHORT,
        quantity=Decimal("1.000"),
        stop_loss=Decimal("110"),
        take_profit=Decimal("92"),
    )
    return GoldenScenario(
        name="short-target",
        candles=candles,
        provider=ScriptedDecisionProvider({0: (enter,)}),
        policy=default_policy(),
        expected_closed_trades=1,
        expected_exit_reason=FillReason.TAKE_PROFIT,
        expected_unfilled=0,
    )


def scenario_same_bar_stop_first() -> GoldenScenario:
    times = _seq(datetime(2026, 6, 1, tzinfo=UTC), 2)
    candles = (
        _candle(times[0], open_="100", high="101", low="99", close="100"),
        # Entry at open 100; both stop 95 and target 108 touched same bar.
        _candle(times[1], open_="100", high="110", low="90", close="105"),
    )
    enter = EnterIntent(
        intent_id="enter-ambiguity",
        decision_open_time=times[0],
        direction=PositionDirection.LONG,
        quantity=Decimal("1.000"),
        stop_loss=Decimal("95"),
        take_profit=Decimal("108"),
    )
    return GoldenScenario(
        name="same-bar-stop-first",
        candles=candles,
        provider=ScriptedDecisionProvider({0: (enter,)}),
        policy=default_policy(),
        expected_closed_trades=1,
        expected_exit_reason=FillReason.STOP_LOSS,
        expected_unfilled=0,
    )


def scenario_explicit_exit() -> GoldenScenario:
    times = _seq(datetime(2026, 6, 1, tzinfo=UTC), 4)
    candles = (
        _candle(times[0], open_="100", high="101", low="99", close="100"),
        _candle(times[1], open_="100", high="101", low="99", close="100.5"),
        _candle(times[2], open_="100.5", high="101", low="100", close="100.8"),
        _candle(times[3], open_="100.8", high="101", low="100", close="100.9"),
    )
    enter = EnterIntent(
        intent_id="enter-explicit",
        decision_open_time=times[0],
        direction=PositionDirection.LONG,
        quantity=Decimal("1.000"),
        stop_loss=Decimal("90"),
        take_profit=Decimal("150"),
    )
    exit_intent = ExitIntent(
        intent_id="exit-explicit",
        decision_open_time=times[1],
        label="flat",
    )
    return GoldenScenario(
        name="explicit-exit",
        candles=candles,
        provider=ScriptedDecisionProvider({0: (enter,), 1: (exit_intent,)}),
        policy=default_policy(),
        expected_closed_trades=1,
        expected_exit_reason=FillReason.EXPLICIT_EXIT,
        expected_unfilled=0,
    )


def scenario_end_of_data() -> GoldenScenario:
    times = _seq(datetime(2026, 6, 1, tzinfo=UTC), 3)
    candles = (
        _candle(times[0], open_="100", high="101", low="99", close="100"),
        _candle(times[1], open_="100", high="101", low="99", close="100.5"),
        _candle(times[2], open_="100.5", high="101", low="100", close="100.8"),
    )
    enter = EnterIntent(
        intent_id="enter-eod",
        decision_open_time=times[0],
        direction=PositionDirection.LONG,
        quantity=Decimal("1.000"),
        stop_loss=Decimal("90"),
        take_profit=Decimal("150"),
    )
    return GoldenScenario(
        name="end-of-data",
        candles=candles,
        provider=ScriptedDecisionProvider({0: (enter,)}),
        policy=default_policy(force_close_at_end=True),
        expected_closed_trades=1,
        expected_exit_reason=FillReason.END_OF_DATA,
        expected_unfilled=0,
    )


def scenario_pending_final_entry() -> GoldenScenario:
    times = _seq(datetime(2026, 6, 1, tzinfo=UTC), 2)
    candles = (
        _candle(times[0], open_="100", high="101", low="99", close="100"),
        _candle(times[1], open_="100", high="101", low="99", close="100.5"),
    )
    enter = EnterIntent(
        intent_id="enter-final",
        decision_open_time=times[1],
        direction=PositionDirection.LONG,
        quantity=Decimal("1.000"),
        stop_loss=Decimal("90"),
        take_profit=Decimal("150"),
    )
    return GoldenScenario(
        name="pending-final-entry",
        candles=candles,
        provider=ScriptedDecisionProvider({1: (enter,)}),
        policy=default_policy(),
        expected_closed_trades=0,
        expected_exit_reason=None,
        expected_unfilled=1,
    )


SCENARIOS: dict[str, GoldenScenario] = {
    s.name: s
    for s in (
        scenario_long_target(),
        scenario_long_stop(),
        scenario_short_target(),
        scenario_same_bar_stop_first(),
        scenario_explicit_exit(),
        scenario_end_of_data(),
        scenario_pending_final_entry(),
    )
}


def run_scenario(name: str) -> BacktestResult:
    scenario = SCENARIOS[name]
    expected = GOLDEN_EXPECTATIONS[name]
    engine = BacktestEngine(
        symbol=parse_symbol("BTCUSDT"),
        timeframe=Timeframe.H1,
        policy=scenario.policy,
        provider=scenario.provider,
    )
    result = engine.run(scenario.candles)
    assert_matches_expectation(result, expected)
    return result
