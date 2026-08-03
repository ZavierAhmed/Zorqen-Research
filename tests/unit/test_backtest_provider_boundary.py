"""Decision-provider boundary and intrinsic intent validation tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal

import pytest

from zorqen_research.application.backtesting.engine import BacktestEngine
from zorqen_research.application.backtesting.golden import default_policy
from zorqen_research.application.backtesting.provider import BacktestDecisionContext
from zorqen_research.application.backtesting.scripted import ScriptedDecisionProvider
from zorqen_research.domain.backtesting.enums import PositionDirection
from zorqen_research.domain.backtesting.errors import (
    BacktestExecutionError,
    BacktestValidationError,
)
from zorqen_research.domain.backtesting.intents import EnterIntent, ExitIntent
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


def _engine(provider: object) -> BacktestEngine:
    return BacktestEngine(
        symbol=parse_symbol("BTCUSDT"),
        timeframe=Timeframe.H1,
        policy=default_policy(),
        provider=provider,  # type: ignore[arg-type]
    )


def _two_bars() -> tuple[Candle, Candle]:
    t0 = datetime(2026, 6, 1, tzinfo=UTC)
    return _candle(t0), _candle(t0 + timedelta(hours=1))


class _FixedProvider:
    def __init__(self, value: object) -> None:
        self.value = value
        self.calls = 0

    def on_bar_close(self, context: BacktestDecisionContext) -> object:
        self.calls += 1
        return self.value


class _RaisingProvider:
    def __init__(self) -> None:
        self.calls = 0

    def on_bar_close(self, context: BacktestDecisionContext) -> object:
        self.calls += 1
        msg = "provider boom"
        raise RuntimeError(msg)


def test_provider_none_rejected() -> None:
    provider = _FixedProvider(None)
    with pytest.raises(BacktestValidationError, match="None"):
        _engine(provider).run(_two_bars())
    assert provider.calls == 1


def test_provider_string_rejected() -> None:
    with pytest.raises(BacktestValidationError, match="string"):
        _engine(_FixedProvider("not-intents")).run(_two_bars())


def test_provider_non_iterable_rejected() -> None:
    with pytest.raises(BacktestValidationError, match="iterable"):
        _engine(_FixedProvider(42)).run(_two_bars())


def test_provider_exception_wrapped() -> None:
    provider = _RaisingProvider()
    with pytest.raises(BacktestExecutionError, match="Decision provider failed") as excinfo:
        _engine(provider).run(_two_bars())
    assert isinstance(excinfo.value.__cause__, RuntimeError)
    assert provider.calls == 1


def test_provider_unknown_object_rejected() -> None:
    with pytest.raises(BacktestValidationError, match="Unknown intent"):
        _engine(_FixedProvider((object(),))).run(_two_bars())


def test_provider_multiple_intents_rejected() -> None:
    t0 = datetime(2026, 6, 1, tzinfo=UTC)
    enter = EnterIntent(
        intent_id="e1",
        decision_open_time=t0,
        direction=PositionDirection.LONG,
        quantity=Decimal("1.000"),
        stop_loss=Decimal("90"),
        take_profit=Decimal("150"),
    )
    exit_intent = ExitIntent(intent_id="x1", decision_open_time=t0)
    with pytest.raises(BacktestValidationError, match="At most one"):
        _engine(_FixedProvider((enter, exit_intent))).run(_two_bars())


def test_malformed_decision_time_runtime_type() -> None:
    with pytest.raises(BacktestValidationError, match="datetime"):
        EnterIntent(
            intent_id="e1",
            decision_open_time="2026-06-01T00:00:00Z",  # type: ignore[arg-type]
            direction=PositionDirection.LONG,
            quantity=Decimal("1.000"),
            stop_loss=Decimal("90"),
            take_profit=Decimal("150"),
        )


def test_naive_decision_time_rejected() -> None:
    with pytest.raises(BacktestValidationError, match="timezone-aware"):
        EnterIntent(
            intent_id="e1",
            decision_open_time=datetime(2026, 6, 1),
            direction=PositionDirection.LONG,
            quantity=Decimal("1.000"),
            stop_loss=Decimal("90"),
            take_profit=Decimal("150"),
        )


def test_nonzero_offset_decision_time_rejected() -> None:
    offset = timezone(timedelta(hours=5))
    with pytest.raises(BacktestValidationError, match="zero UTC offset"):
        EnterIntent(
            intent_id="e1",
            decision_open_time=datetime(2026, 6, 1, tzinfo=offset),
            direction=PositionDirection.LONG,
            quantity=Decimal("1.000"),
            stop_loss=Decimal("90"),
            take_profit=Decimal("150"),
        )


def test_invalid_quantity_runtime_type() -> None:
    with pytest.raises(BacktestValidationError, match="quantity"):
        EnterIntent(
            intent_id="e1",
            decision_open_time=datetime(2026, 6, 1, tzinfo=UTC),
            direction=PositionDirection.LONG,
            quantity="1.0",  # type: ignore[arg-type]
            stop_loss=Decimal("90"),
            take_profit=Decimal("150"),
        )


def test_invalid_stop_target_runtime_types() -> None:
    t0 = datetime(2026, 6, 1, tzinfo=UTC)
    with pytest.raises(BacktestValidationError, match="stop_loss"):
        EnterIntent(
            intent_id="e1",
            decision_open_time=t0,
            direction=PositionDirection.LONG,
            quantity=Decimal("1.000"),
            stop_loss=95,  # type: ignore[arg-type]
            take_profit=Decimal("150"),
        )
    with pytest.raises(BacktestValidationError, match="take_profit"):
        EnterIntent(
            intent_id="e1",
            decision_open_time=t0,
            direction=PositionDirection.LONG,
            quantity=Decimal("1.000"),
            stop_loss=Decimal("90"),
            take_profit=None,  # type: ignore[arg-type]
        )


def test_whitespace_intent_id_rejected() -> None:
    with pytest.raises(BacktestValidationError, match="intent_id"):
        ExitIntent(intent_id="  x  ", decision_open_time=datetime(2026, 6, 1, tzinfo=UTC))


def test_corrupted_intent_from_provider_sanitized() -> None:
    t0 = datetime(2026, 6, 1, tzinfo=UTC)
    enter = EnterIntent(
        intent_id="e1",
        decision_open_time=t0,
        direction=PositionDirection.LONG,
        quantity=Decimal("1.000"),
        stop_loss=Decimal("90"),
        take_profit=Decimal("150"),
    )
    object.__setattr__(enter, "quantity", "bad")

    class Provider:
        def on_bar_close(self, context: BacktestDecisionContext) -> object:
            return (enter,)

    with pytest.raises(BacktestValidationError):
        _engine(Provider()).run(_two_bars())


def test_scripted_empty_still_ok() -> None:
    result = _engine(ScriptedDecisionProvider({})).run(_two_bars())
    assert result.fills == ()
    assert result.summary.final_equity == Decimal("10000")
