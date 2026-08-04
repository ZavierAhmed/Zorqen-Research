"""Milestone 0.9C: seal history repr/str against future-candle leakage."""

from __future__ import annotations

import logging
from collections.abc import Iterator, Sequence
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from io import StringIO

from zorqen_research.application.backtesting.golden import default_policy
from zorqen_research.application.backtesting.provider import BacktestDecisionContext
from zorqen_research.application.market_data.goldens import build_source_series, make_candle
from zorqen_research.application.strategy_backtesting.feed import MultiTimeframeDecisionFeed
from zorqen_research.application.strategy_backtesting.goldens import (
    NoLookaheadProbeProvider,
    mtf_definition,
    run_no_lookahead_probe,
)
from zorqen_research.application.strategy_backtesting.provider import (
    MultiTimeframeBacktestDecisionContext,
)
from zorqen_research.application.strategy_backtesting.runner import MultiTimeframeBacktestRunner
from zorqen_research.application.strategy_definitions.serialization import build_instance
from zorqen_research.domain.backtesting.enums import PositionDirection
from zorqen_research.domain.backtesting.intents import EnterIntent
from zorqen_research.domain.candles import Candle
from zorqen_research.domain.strategy_backtesting.histories import (
    VisibleCandleHistory,
    _VerifiedHistorySource,
)
from zorqen_research.domain.strategy_backtesting.inputs import MultiTimeframeBacktestInput
from zorqen_research.domain.strategy_definitions.timeframes import TimeframeRequirement
from zorqen_research.domain.symbols import Symbol
from zorqen_research.domain.timeframes import Timeframe

SYM = Symbol(value="BTCUSDT")
START = datetime(2024, 1, 1, tzinfo=UTC)
FUTURE_OPEN = Decimal("888001.111")
FUTURE_HIGH = Decimal("888002.222")
FUTURE_LOW = Decimal("888000.000")
FUTURE_CLOSE = Decimal("888001.555")
FUTURE_VOLUME = Decimal("777777.777")
FUTURE_QUOTE = Decimal("666666.666")


class InstrumentedCandles(Sequence[Candle]):
    def __init__(self, items: tuple[Candle, ...]) -> None:
        self._items = items
        self.access_count = 0
        self.slice_count = 0
        self.iter_count = 0

    def __len__(self) -> int:
        return len(self._items)

    def __getitem__(self, key: int | slice) -> Candle | tuple[Candle, ...]:  # type: ignore[override]
        if isinstance(key, slice):
            self.slice_count += 1
            return self._items[key]
        self.access_count += 1
        return self._items[key]

    def __iter__(self) -> Iterator[Candle]:
        self.iter_count += 1
        for index in range(len(self._items)):
            yield self[index]


def _series_with_future_sentinels(
    *,
    timeframe: Timeframe,
    visible_count: int,
    future_count: int = 2,
) -> tuple[Candle, ...]:
    visible = build_source_series(
        start=START,
        timeframe=timeframe,
        count=visible_count,
        open_base=Decimal("100"),
    )
    step = visible[0].close_time - visible[0].open_time + timedelta(milliseconds=1)
    futures: list[Candle] = []
    for offset in range(future_count):
        open_time = visible[-1].open_time + step * (offset + 1)
        futures.append(
            make_candle(
                open_time,
                timeframe=timeframe,
                open=FUTURE_OPEN + Decimal(offset),
                high=FUTURE_HIGH + Decimal(offset),
                low=FUTURE_LOW + Decimal(offset),
                close=FUTURE_CLOSE + Decimal(offset),
                volume=FUTURE_VOLUME + Decimal(offset),
                quote_asset_volume=FUTURE_QUOTE + Decimal(offset),
                trade_count=900_000 + offset,
                taker_buy_base_volume=Decimal("0.5"),
                taker_buy_quote_volume=Decimal("5"),
            )
        )
    return visible + tuple(futures)


def _assert_no_future_leak(
    text: str,
    *,
    full_series: tuple[Candle, ...],
    visible_count: int,
) -> None:
    assert text == f"VisibleCandleHistory(visible_count={visible_count})" or (
        "VisibleCandleHistory(visible_count=" in text
    )
    for candle in full_series[visible_count:]:
        assert candle.open_time.isoformat() not in text
        assert candle.close_time.isoformat() not in text
        assert format(candle.open, "f") not in text
        assert format(candle.high, "f") not in text
        assert format(candle.low, "f") not in text
        assert format(candle.close, "f") not in text
        assert format(candle.volume, "f") not in text
        assert format(candle.quote_asset_volume, "f") not in text
    assert "Candle(" not in text
    assert "_source" not in text
    assert "888001" not in text
    assert "777777" not in text


def _assert_nested_no_future_timestamps(
    text: str,
    *,
    full_series: tuple[Candle, ...],
    visible_count: int,
) -> None:
    for candle in full_series[visible_count:]:
        assert candle.open_time.isoformat() not in text
        assert candle.close_time.isoformat() not in text
    assert "888001" not in text
    assert "777777" not in text


def test_history_repr_str_seal_and_formatting_paths() -> None:
    execution = _series_with_future_sentinels(timeframe=Timeframe.H1, visible_count=4)
    history = VisibleCandleHistory.from_prefix(execution, end_exclusive=4)
    texts = (
        repr(history),
        str(history),
        f"{history!r}",
        "%r" % (history,),  # noqa: UP031 — intentional percent-format path
        format(history, ""),
    )
    for text in texts:
        assert text == "VisibleCandleHistory(visible_count=4)"
        _assert_no_future_leak(text, full_series=execution, visible_count=4)

    stream = StringIO()
    logger = logging.getLogger("zorqen.mtf.repr.09c")
    logger.handlers.clear()
    handler = logging.StreamHandler(stream)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.info("history=%r", history)
    logged = stream.getvalue()
    assert "VisibleCandleHistory(visible_count=4)" in logged
    _assert_no_future_leak(
        logged[logged.index("VisibleCandleHistory") :],
        full_series=execution,
        visible_count=4,
    )

    source = _VerifiedHistorySource._bind_trusted(execution)
    assert repr(source) == "_VerifiedHistorySource()"
    assert str(source) == "_VerifiedHistorySource()"
    assert "888001" not in repr(source)
    assert "Candle(" not in repr(source)


def test_nested_view_and_context_repr_seal() -> None:
    definition = mtf_definition(
        execution_warmup=4,
        contexts=(TimeframeRequirement(timeframe=Timeframe.H4, warmup_bars=1),),
        definition_code="mtf_09c_repr",
    )
    instance = build_instance(definition, {"signal_strength": 1})
    std_execution = build_source_series(start=START, timeframe=Timeframe.H1, count=8)
    patched = list(std_execution[:4])
    for index, candle in enumerate(std_execution[4:]):
        patched.append(
            make_candle(
                candle.open_time,
                timeframe=Timeframe.H1,
                open=FUTURE_OPEN + Decimal(index),
                high=FUTURE_HIGH + Decimal(index),
                low=FUTURE_LOW + Decimal(index),
                close=FUTURE_CLOSE + Decimal(index),
                volume=FUTURE_VOLUME + Decimal(index),
                quote_asset_volume=FUTURE_QUOTE + Decimal(index),
                trade_count=900_000 + index,
            )
        )
    execution = tuple(patched)
    std_context = build_source_series(start=START, timeframe=Timeframe.H4, count=2)
    context = (
        std_context[0],
        make_candle(
            std_context[1].open_time,
            timeframe=Timeframe.H4,
            open=FUTURE_OPEN,
            high=FUTURE_HIGH,
            low=FUTURE_LOW,
            close=FUTURE_CLOSE,
            volume=FUTURE_VOLUME,
            quote_asset_volume=FUTURE_QUOTE,
            trade_count=900_050,
        ),
    )
    bundle = MultiTimeframeBacktestInput.from_verified(
        strategy_instance=instance,
        symbol=SYM,
        execution_candles=execution,
        context_series=((Timeframe.H4, context),),
    )
    feed = MultiTimeframeDecisionFeed.from_input(bundle)
    view = feed.view_at(3)
    assert len(view.execution_history) == 4
    assert view.contexts[0].visible_count == 1

    for text in (
        repr(view.execution_history),
        str(view.execution_history),
        f"{view.execution_history!r}",
        "%r" % (view.execution_history,),  # noqa: UP031 — intentional percent-format path
    ):
        _assert_no_future_leak(text, full_series=execution, visible_count=4)

    for text in (repr(view.contexts[0].history), str(view.contexts[0].history)):
        _assert_no_future_leak(text, full_series=context, visible_count=1)

    enhanced = MultiTimeframeBacktestDecisionContext(
        base=BacktestDecisionContext(
            candle=view.current_execution_candle,
            bar_index=3,
            symbol=SYM,
            timeframe=Timeframe.H1,
            position=None,
            realized_equity=Decimal("10000"),
            last_closed_trade=None,
            candles_processed=4,
        ),
        strategy_instance_hash=bundle.strategy_instance_hash,
        input_bundle_hash=bundle.input_bundle_hash,
        view=view,
    )
    for text in (
        repr(view.contexts[0]),
        repr(view),
        str(view),
        repr(enhanced),
        str(enhanced),
        f"{view!r}",
        f"{enhanced!r}",
    ):
        _assert_nested_no_future_timestamps(text, full_series=execution, visible_count=4)
        _assert_nested_no_future_timestamps(text, full_series=context, visible_count=1)


def test_history_repr_str_are_constant_time_and_source_access_free() -> None:
    candles = build_source_series(start=START, timeframe=Timeframe.H1, count=100_001)
    instrumented = InstrumentedCandles(candles)
    source = _VerifiedHistorySource._bind_trusted(candles)
    object.__setattr__(source, "_candles", instrumented)

    near_ten = VisibleCandleHistory._from_verified_source(source, end_exclusive=11)
    near_large = VisibleCandleHistory._from_verified_source(source, end_exclusive=100_001)

    baseline = (
        instrumented.access_count,
        instrumented.slice_count,
        instrumented.iter_count,
    )
    texts_ten = (
        repr(near_ten),
        str(near_ten),
        f"{near_ten!r}",
        "%r" % (near_ten,),  # noqa: UP031 — intentional percent-format path
    )
    after_ten = (
        instrumented.access_count,
        instrumented.slice_count,
        instrumented.iter_count,
    )
    texts_large = (
        repr(near_large),
        str(near_large),
        f"{near_large!r}",
        "%r" % (near_large,),  # noqa: UP031 — intentional percent-format path
    )
    after_large = (
        instrumented.access_count,
        instrumented.slice_count,
        instrumented.iter_count,
    )

    assert after_ten == baseline
    assert after_large == baseline
    assert all(text == "VisibleCandleHistory(visible_count=11)" for text in texts_ten)
    assert all(text == "VisibleCandleHistory(visible_count=100001)" for text in texts_large)


def test_provider_repr_probe_preserves_exact_close_hashes() -> None:
    payload = run_no_lookahead_probe()
    assert payload["ok"] is True
    assert payload["public_source_exposed"] is False
    assert payload["first_ready_index"] == 3
    assert payload["execution_visible_at_ready"] == 4
    assert payload["context_visible_at_ready"] == (1,)
    assert payload["closed_trade_count"] == 1
    assert (
        payload["input_bundle_hash"]
        == "1ef63eff5e42d00d2d3edabbc849a3f1f651929c3ba52abbc08fd64497794167"
    )
    assert (
        payload["envelope_hash"]
        == "8e5259d68e152ee3c1b0767ec372866ddcbb8b67eeae96175345e2512879b70d"
    )

    # Direct runner path with probe also succeeds.
    definition = mtf_definition(
        execution_warmup=4,
        contexts=(TimeframeRequirement(timeframe=Timeframe.H4, warmup_bars=1),),
        definition_code="mtf_exact_close",
    )
    instance = build_instance(definition, {"signal_strength": 1})
    execution = build_source_series(start=START, timeframe=Timeframe.H1, count=8)
    context = build_source_series(start=START, timeframe=Timeframe.H4, count=2)
    intent = EnterIntent(
        intent_id="mtf-exact-close",
        decision_open_time=execution[3].open_time,
        direction=PositionDirection.LONG,
        quantity=Decimal("1.000"),
        stop_loss=Decimal("50"),
        take_profit=Decimal("200"),
    )
    provider = NoLookaheadProbeProvider(
        first_ready_intent=(intent,),
        expected_execution_visible=4,
        expected_context_visible=(1,),
        full_execution=execution,
        full_contexts=(context,),
    )
    bundle = MultiTimeframeBacktestInput.from_verified(
        strategy_instance=instance,
        symbol=SYM,
        execution_candles=execution,
        context_series=((Timeframe.H4, context),),
    )
    envelope = MultiTimeframeBacktestRunner.run(
        input_bundle=bundle,
        policy=default_policy(),
        provider=provider,
    )
    assert provider.probe_ok is True
    assert provider.calls[0] == 3
    assert envelope.envelope_hash == (
        "8e5259d68e152ee3c1b0767ec372866ddcbb8b67eeae96175345e2512879b70d"
    )
