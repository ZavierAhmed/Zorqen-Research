"""Decision-provider boundary and intrinsic intent validation tests."""

from __future__ import annotations

from collections.abc import Iterator
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


def _valid_enter(decision_time: datetime | None = None) -> EnterIntent:
    t0 = decision_time or datetime(2026, 6, 1, tzinfo=UTC)
    return EnterIntent(
        intent_id="e1",
        decision_open_time=t0,
        direction=PositionDirection.LONG,
        quantity=Decimal("1.000"),
        stop_loss=Decimal("90"),
        take_profit=Decimal("150"),
    )


class _FixedProvider:
    def __init__(self, value: object) -> None:
        self.value = value
        self.calls = 0

    def on_bar_close(self, context: BacktestDecisionContext) -> object:
        self.calls += 1
        return self.value


class _RaisingProvider:
    def __init__(self, exc: BaseException) -> None:
        self.exc = exc
        self.calls = 0

    def on_bar_close(self, context: BacktestDecisionContext) -> object:
        self.calls += 1
        raise self.exc


@pytest.mark.parametrize(
    "exc",
    [
        RuntimeError("provider boom"),
        ValueError("bad value"),
        TypeError("bad type"),
        BacktestValidationError("provider validation"),
        BacktestExecutionError("provider execution"),
    ],
)
def test_provider_exceptions_always_wrapped(exc: BaseException) -> None:
    provider = _RaisingProvider(exc)
    with pytest.raises(BacktestExecutionError, match="^Decision provider failed$") as excinfo:
        _engine(provider).run(_two_bars())
    assert excinfo.value.__cause__ is exc
    assert str(excinfo.value) == "Decision provider failed"
    assert provider.calls == 1


def test_provider_not_called_again_after_failure() -> None:
    provider = _RaisingProvider(RuntimeError("boom"))
    with pytest.raises(BacktestExecutionError, match="Decision provider failed"):
        _engine(provider).run(_two_bars())
    assert provider.calls == 1


def test_empty_tuple_succeeds() -> None:
    result = _engine(_FixedProvider(())).run(_two_bars())
    assert result.fills == ()
    assert result.summary.final_equity == Decimal("10000")


def test_one_item_tuple_succeeds() -> None:
    t0 = datetime(2026, 6, 1, tzinfo=UTC)
    enter = _valid_enter(t0)
    calls = {"n": 0}

    class Provider:
        def on_bar_close(self, context: BacktestDecisionContext) -> object:
            calls["n"] += 1
            if context.bar_index == 0:
                return (enter,)
            return ()

    result = _engine(Provider()).run(_two_bars())
    assert result.fills[0].intent_id == "e1"
    assert result.fills[0].reason.value == "market_entry"
    assert calls["n"] == 2


def test_two_item_tuple_rejected() -> None:
    t0 = datetime(2026, 6, 1, tzinfo=UTC)
    enter = _valid_enter(t0)
    exit_intent = ExitIntent(intent_id="x1", decision_open_time=t0)
    with pytest.raises(BacktestValidationError, match="At most one"):
        _engine(_FixedProvider((enter, exit_intent))).run(_two_bars())


@pytest.mark.parametrize(
    "value",
    [
        None,
        42,
        "not-intents",
        b"bytes",
        bytearray(b"bytes"),
        {"intent": "no"},
        {1, 2},
        [_valid_enter()],
    ],
)
def test_non_tuple_containers_rejected(value: object) -> None:
    provider = _FixedProvider(value)
    with pytest.raises(BacktestValidationError, match="tuple of intents"):
        _engine(provider).run(_two_bars())
    assert provider.calls == 1


def test_generator_rejected_without_consumption() -> None:
    consumed: list[int] = []

    def gen() -> Iterator[EnterIntent]:
        consumed.append(1)
        yield _valid_enter()

    provider = _FixedProvider(gen())
    with pytest.raises(BacktestValidationError, match="tuple of intents"):
        _engine(provider).run(_two_bars())
    assert consumed == []
    assert provider.calls == 1


def test_infinite_generator_rejected_immediately() -> None:
    def infinite() -> Iterator[int]:
        while True:
            yield 1

    provider = _FixedProvider(infinite())
    with pytest.raises(BacktestValidationError, match="tuple of intents"):
        _engine(provider).run(_two_bars())
    assert provider.calls == 1


def test_provider_unknown_object_rejected() -> None:
    with pytest.raises(BacktestValidationError, match="Unknown intent"):
        _engine(_FixedProvider((object(),))).run(_two_bars())


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
    enter = _valid_enter(t0)
    object.__setattr__(enter, "quantity", "bad")

    class Provider:
        def on_bar_close(self, context: BacktestDecisionContext) -> object:
            return (enter,)

    with pytest.raises(BacktestValidationError):
        _engine(Provider()).run(_two_bars())


def test_failure_produces_no_fills_or_trades() -> None:
    provider = _RaisingProvider(RuntimeError("boom"))
    with pytest.raises(BacktestExecutionError):
        _engine(provider).run(_two_bars())
    assert provider.calls == 1
    ok = _engine(ScriptedDecisionProvider({})).run(_two_bars())
    assert ok.fills == ()
    assert ok.trades == ()


def test_scripted_empty_still_ok() -> None:
    result = _engine(ScriptedDecisionProvider({})).run(_two_bars())
    assert result.fills == ()
    assert result.summary.final_equity == Decimal("10000")
