"""Deterministic single-symbol backtest execution engine."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, replace
from datetime import timedelta
from decimal import Decimal

from zorqen_research.application.backtesting import serialization as result_serialization
from zorqen_research.application.backtesting.provider import (
    BacktestDecisionContext,
    BacktestDecisionProvider,
)
from zorqen_research.application.market_data.ranges import is_aligned
from zorqen_research.application.market_data.serialization import serialize_candles_csv
from zorqen_research.domain.artifacts import sha256_hex
from zorqen_research.domain.backtesting.enums import (
    FillReason,
    FillSide,
    LiquidityRole,
    PositionDirection,
    SameBarExitPolicy,
)
from zorqen_research.domain.backtesting.errors import (
    BacktestExecutionError,
    BacktestValidationError,
)
from zorqen_research.domain.backtesting.execution import FillRecord, PositionSnapshot
from zorqen_research.domain.backtesting.intents import (
    BacktestIntent,
    EnterIntent,
    ExitIntent,
)
from zorqen_research.domain.backtesting.math_rules import (
    apply_buy_slippage,
    apply_sell_slippage,
    compute_fee,
    normalize_buy_fill,
    normalize_long_stop,
    normalize_long_target,
    normalize_sell_fill,
    normalize_short_stop,
    normalize_short_target,
    require_positive_price,
)
from zorqen_research.domain.backtesting.policy import BacktestPolicy
from zorqen_research.domain.backtesting.results import (
    BacktestResult,
    BacktestSummary,
    UnfilledIntentRecord,
)
from zorqen_research.domain.backtesting.trades import ClosedTrade
from zorqen_research.domain.candles import Candle
from zorqen_research.domain.symbols import Symbol
from zorqen_research.domain.timeframes import Timeframe, timeframe_duration


@dataclass(slots=True)
class _OpenPosition:
    snapshot: PositionSnapshot
    entry_fill: FillRecord
    same_bar_ambiguity_used: bool = False


class BacktestEngine:
    """
    Pure in-memory bar-based simulator.

    Per-candle event order:
    1. Activate and execute any pending market intent at candle open.
    2. Apply adverse slippage.
    3. Charge the applicable taker fee.
    4. Validate newly opened position brackets against actual fill.
    5. Evaluate protective stop and target during the candle.
    6. Close the position when a protective level triggers.
    7. Record fills, realized P&L and equity.
    8. Call the decision provider at candle close.
    9. Validate returned intents.
    10. Queue valid intent for the next candle.
    """

    def __init__(
        self,
        *,
        symbol: Symbol,
        timeframe: Timeframe,
        policy: BacktestPolicy,
        provider: BacktestDecisionProvider,
    ) -> None:
        self._symbol = symbol
        self._timeframe = timeframe
        self._policy = policy
        self._provider = provider

    def run(
        self,
        candles: Sequence[Candle],
        *,
        expected_input_hash: str | None = None,
    ) -> BacktestResult:
        candle_tuple = self._validate_candles(candles)
        input_hash = sha256_hex(serialize_candles_csv(candle_tuple))
        if expected_input_hash is not None and expected_input_hash != input_hash:
            msg = "Input candle hash does not match expected hash"
            raise BacktestValidationError(msg)

        equity = self._policy.initial_equity
        equity_curve: list[Decimal] = [equity]
        fills: list[FillRecord] = []
        trades: list[ClosedTrade] = []
        unfilled: list[UnfilledIntentRecord] = []
        position: _OpenPosition | None = None
        pending: BacktestIntent | None = None
        fill_seq = 0
        trade_seq = 0
        position_seq = 0

        for bar_index, candle in enumerate(candle_tuple):
            # Steps 1-4: pending market intent at open.
            if pending is not None:
                if isinstance(pending, EnterIntent):
                    if position is not None:
                        msg = "Cannot enter while a position is open"
                        raise BacktestExecutionError(msg)
                    fill_seq += 1
                    position_seq += 1
                    entry_fill, opened, equity = self._execute_entry(
                        intent=pending,
                        candle=candle,
                        bar_index=bar_index,
                        fill_seq=fill_seq,
                        position_seq=position_seq,
                        equity=equity,
                    )
                    fills.append(entry_fill)
                    equity_curve.append(equity)
                    position = opened
                elif isinstance(pending, ExitIntent):
                    if position is None:
                        msg = "Cannot exit while flat"
                        raise BacktestExecutionError(msg)
                    fill_seq += 1
                    trade_seq += 1
                    exit_fill, trade, equity = self._execute_exit(
                        position=position,
                        intent_id=pending.intent_id,
                        candle=candle,
                        bar_index=bar_index,
                        fill_seq=fill_seq,
                        trade_seq=trade_seq,
                        reason=FillReason.EXPLICIT_EXIT,
                        reference_price=candle.open,
                        equity=equity,
                        same_bar_ambiguity_used=False,
                    )
                    fills.append(exit_fill)
                    trades.append(trade)
                    equity_curve.append(equity)
                    position = None
                pending = None

            # Steps 5-7: protective exits (including same bar as entry).
            if position is not None:
                trigger = self._evaluate_protective(position.snapshot, candle)
                if trigger is not None:
                    reason, reference, ambiguity = trigger
                    fill_seq += 1
                    trade_seq += 1
                    exit_fill, trade, equity = self._execute_exit(
                        position=position,
                        intent_id=None,
                        candle=candle,
                        bar_index=bar_index,
                        fill_seq=fill_seq,
                        trade_seq=trade_seq,
                        reason=reason,
                        reference_price=reference,
                        equity=equity,
                        same_bar_ambiguity_used=ambiguity,
                    )
                    fills.append(exit_fill)
                    trades.append(trade)
                    equity_curve.append(equity)
                    position = None

            # Steps 8-10: decision at close.
            context = BacktestDecisionContext(
                candle=candle,
                bar_index=bar_index,
                symbol=self._symbol,
                timeframe=self._timeframe,
                position=None if position is None else position.snapshot,
                realized_equity=equity,
                last_closed_trade=trades[-1] if trades else None,
                candles_processed=bar_index + 1,
            )
            intents = self._invoke_provider(context)
            pending = self._validate_and_select_intent(
                intents,
                decision_open_time=candle.open_time,
                has_position=position is not None,
                has_pending=False,
            )

        # End of data.
        if pending is not None:
            unfilled.append(
                UnfilledIntentRecord(
                    intent=pending,
                    reason="no_next_candle",
                )
            )
            pending = None

        if position is not None:
            if not self._policy.force_close_at_end:
                msg = "Backtest ended with an open position and force_close_at_end=false"
                raise BacktestExecutionError(msg)
            final = candle_tuple[-1]
            fill_seq += 1
            trade_seq += 1
            exit_fill, trade, equity = self._execute_exit(
                position=position,
                intent_id=None,
                candle=final,
                bar_index=len(candle_tuple) - 1,
                fill_seq=fill_seq,
                trade_seq=trade_seq,
                reason=FillReason.END_OF_DATA,
                reference_price=final.close,
                equity=equity,
                same_bar_ambiguity_used=False,
            )
            fills.append(exit_fill)
            trades.append(trade)
            equity_curve.append(equity)
            position = None

        policy_hash = result_serialization.hash_policy(self._policy)
        summary_without_hash = self._build_summary(
            equity=equity,
            equity_curve=tuple(equity_curve),
            fills=tuple(fills),
            trades=tuple(trades),
            unfilled_count=len(unfilled),
            input_candle_count=len(candle_tuple),
            input_candle_hash=input_hash,
            policy_hash=policy_hash,
            result_hash="",
        )
        result = BacktestResult(
            symbol=self._symbol,
            timeframe=self._timeframe,
            policy=self._policy,
            fills=tuple(fills),
            trades=tuple(trades),
            unfilled_intents=tuple(unfilled),
            equity_curve=tuple(equity_curve),
            summary=summary_without_hash,
        )
        result_hash = result_serialization.hash_result(result)
        summary = replace(summary_without_hash, result_hash=result_hash)
        return BacktestResult(
            symbol=result.symbol,
            timeframe=result.timeframe,
            policy=result.policy,
            fills=result.fills,
            trades=result.trades,
            unfilled_intents=result.unfilled_intents,
            equity_curve=result.equity_curve,
            summary=summary,
        )

    def _validate_candles(self, candles: Sequence[Candle]) -> tuple[Candle, ...]:
        if not candles:
            msg = "Candle sequence must be non-empty"
            raise BacktestValidationError(msg)
        out: list[Candle] = []
        duration = timeframe_duration(self._timeframe)
        for index, candle in enumerate(candles):
            if not isinstance(candle, Candle):
                msg = "Every item must be a canonical Candle"
                raise BacktestValidationError(msg)
            if not is_aligned(candle.open_time, self._timeframe):
                msg = f"Candle open_time is not aligned at index {index}"
                raise BacktestValidationError(msg)
            expected_close = candle.open_time + duration - timedelta(milliseconds=1)
            if candle.close_time != expected_close:
                msg = f"Candle close_time convention mismatch at index {index}"
                raise BacktestValidationError(msg)
            if out:
                expected_open = out[-1].open_time + duration
                if candle.open_time == out[-1].open_time:
                    msg = f"Duplicate open_time at index {index}"
                    raise BacktestValidationError(msg)
                if candle.open_time < out[-1].open_time:
                    msg = f"Out-of-order open_time at index {index}"
                    raise BacktestValidationError(msg)
                if candle.open_time != expected_open:
                    msg = f"Gap in candle sequence at index {index}"
                    raise BacktestValidationError(msg)
            out.append(candle)
        return tuple(out)

    def _invoke_provider(self, context: BacktestDecisionContext) -> tuple[object, ...]:
        try:
            raw = self._provider.on_bar_close(context)
        except (BacktestValidationError, BacktestExecutionError):
            raise
        except Exception as exc:
            msg = "Decision provider failed"
            raise BacktestExecutionError(msg) from exc
        return self._coerce_provider_output(raw)

    def _coerce_provider_output(self, raw: object) -> tuple[object, ...]:
        if raw is None:
            msg = "Decision provider must return a sequence of intents, not None"
            raise BacktestValidationError(msg)
        if isinstance(raw, (str, bytes, bytearray)):
            msg = "Decision provider must return a sequence of intents, not a string/bytes"
            raise BacktestValidationError(msg)
        try:
            iterator = iter(raw)  # type: ignore[call-overload]
        except TypeError as exc:
            msg = "Decision provider must return an iterable sequence of intents"
            raise BacktestValidationError(msg) from exc
        try:
            return tuple(iterator)
        except TypeError as exc:
            msg = "Decision provider returned a non-materializable sequence"
            raise BacktestValidationError(msg) from exc

    def _validate_and_select_intent(
        self,
        intents: tuple[object, ...] | Sequence[object],
        *,
        decision_open_time: object,
        has_position: bool,
        has_pending: bool,
    ) -> BacktestIntent | None:
        items = tuple(intents)
        if len(items) > 1:
            msg = "At most one intent may be returned per decision event"
            raise BacktestValidationError(msg)
        if not items:
            return None
        intent = items[0]
        try:
            if isinstance(intent, EnterIntent):
                intent.validate_for_policy(self._policy)
                if intent.decision_open_time != decision_open_time:
                    msg = "Enter intent decision_open_time must match the decision candle"
                    raise BacktestValidationError(msg)
                if has_position:
                    msg = "Entry rejected while a position is open"
                    raise BacktestValidationError(msg)
                if has_pending:
                    msg = "Entry rejected while an intent is already pending"
                    raise BacktestValidationError(msg)
                return intent
            if isinstance(intent, ExitIntent):
                intent.validate()
                if intent.decision_open_time != decision_open_time:
                    msg = "Exit intent decision_open_time must match the decision candle"
                    raise BacktestValidationError(msg)
                if not has_position:
                    msg = "Exit rejected while flat"
                    raise BacktestValidationError(msg)
                return intent
        except BacktestValidationError:
            raise
        except (AttributeError, TypeError) as exc:
            msg = "Invalid intent object from decision provider"
            raise BacktestValidationError(msg) from exc
        msg = "Unknown intent type"
        raise BacktestValidationError(msg)

    def _execute_entry(
        self,
        *,
        intent: EnterIntent,
        candle: Candle,
        bar_index: int,
        fill_seq: int,
        position_seq: int,
        equity: Decimal,
    ) -> tuple[FillRecord, _OpenPosition, Decimal]:
        is_buy = intent.direction is PositionDirection.LONG
        slipped = (
            apply_buy_slippage(candle.open, self._policy.market_slippage_bps)
            if is_buy
            else apply_sell_slippage(candle.open, self._policy.market_slippage_bps)
        )
        fill_price = (
            normalize_buy_fill(slipped, self._policy.tick_size)
            if is_buy
            else normalize_sell_fill(slipped, self._policy.tick_size)
        )
        fill_price = require_positive_price(fill_price, field="entry_fill_price")
        intent.validate_brackets_against_fill(fill_price)
        notional = abs(fill_price * intent.quantity)
        if notional < self._policy.minimum_notional:
            msg = "Entry notional is below minimum_notional"
            raise BacktestValidationError(msg)
        fee = compute_fee(fill_price, intent.quantity, self._policy.taker_fee_bps)
        if intent.direction is PositionDirection.LONG:
            stop = normalize_long_stop(intent.stop_loss, self._policy.tick_size)
            target = normalize_long_target(intent.take_profit, self._policy.tick_size)
        else:
            stop = normalize_short_stop(intent.stop_loss, self._policy.tick_size)
            target = normalize_short_target(intent.take_profit, self._policy.tick_size)
        stop = require_positive_price(stop, field="stop_loss")
        target = require_positive_price(target, field="take_profit")
        # Re-check brackets after protective tick normalization.
        if intent.direction is PositionDirection.LONG:
            if not (stop < fill_price < target):
                msg = "Normalized long brackets are invalid relative to fill"
                raise BacktestValidationError(msg)
        elif not (target < fill_price < stop):
            msg = "Normalized short brackets are invalid relative to fill"
            raise BacktestValidationError(msg)

        position_id = f"pos-{position_seq:06d}"
        fill = FillRecord(
            fill_id=f"fill-{fill_seq:06d}",
            intent_id=intent.intent_id,
            position_id=position_id,
            bar_index=bar_index,
            fill_time=candle.open_time,
            side=FillSide.BUY if is_buy else FillSide.SELL,
            direction=intent.direction,
            reason=FillReason.MARKET_ENTRY,
            reference_price=candle.open,
            fill_price=fill_price,
            quantity=intent.quantity,
            notional=notional,
            fee=fee,
            liquidity_role=LiquidityRole.TAKER,
            tick_normalized=fill_price != slipped,
        )
        snapshot = PositionSnapshot(
            position_id=position_id,
            entry_intent_id=intent.intent_id,
            direction=intent.direction,
            quantity=intent.quantity,
            entry_decision_time=intent.decision_open_time,
            entry_fill_time=candle.open_time,
            entry_price=fill_price,
            entry_fee=fee,
            stop_loss=stop,
            take_profit=target,
            entry_bar_index=bar_index,
        )
        # Accounting: deduct entry fee immediately; gross P&L applied only on exit.
        new_equity = equity - fee
        return fill, _OpenPosition(snapshot=snapshot, entry_fill=fill), new_equity

    def _execute_exit(
        self,
        *,
        position: _OpenPosition,
        intent_id: str | None,
        candle: Candle,
        bar_index: int,
        fill_seq: int,
        trade_seq: int,
        reason: FillReason,
        reference_price: Decimal,
        equity: Decimal,
        same_bar_ambiguity_used: bool,
    ) -> tuple[FillRecord, ClosedTrade, Decimal]:
        snap = position.snapshot
        is_buy = snap.direction is PositionDirection.SHORT  # covering short
        slipped = (
            apply_buy_slippage(reference_price, self._policy.market_slippage_bps)
            if is_buy
            else apply_sell_slippage(reference_price, self._policy.market_slippage_bps)
        )
        fill_price = (
            normalize_buy_fill(slipped, self._policy.tick_size)
            if is_buy
            else normalize_sell_fill(slipped, self._policy.tick_size)
        )
        fill_price = require_positive_price(fill_price, field="exit_fill_price")
        fee = compute_fee(fill_price, snap.quantity, self._policy.taker_fee_bps)
        notional = abs(fill_price * snap.quantity)
        if snap.direction is PositionDirection.LONG:
            gross = (fill_price - snap.entry_price) * snap.quantity
        else:
            gross = (snap.entry_price - fill_price) * snap.quantity
        net = gross - snap.entry_fee - fee
        fill = FillRecord(
            fill_id=f"fill-{fill_seq:06d}",
            intent_id=intent_id,
            position_id=snap.position_id,
            bar_index=bar_index,
            fill_time=(candle.close_time if reason is FillReason.END_OF_DATA else candle.open_time),
            side=FillSide.BUY if is_buy else FillSide.SELL,
            direction=snap.direction,
            reason=reason,
            reference_price=reference_price,
            fill_price=fill_price,
            quantity=snap.quantity,
            notional=notional,
            fee=fee,
            liquidity_role=LiquidityRole.TAKER,
            tick_normalized=fill_price != slipped,
        )

        trade = ClosedTrade(
            trade_id=f"trade-{trade_seq:06d}",
            position_id=snap.position_id,
            direction=snap.direction,
            quantity=snap.quantity,
            entry_fill_id=position.entry_fill.fill_id,
            exit_fill_id=fill.fill_id,
            entry_time=snap.entry_fill_time,
            exit_time=fill.fill_time,
            entry_price=snap.entry_price,
            exit_price=fill_price,
            stop_loss=snap.stop_loss,
            take_profit=snap.take_profit,
            exit_reason=reason,
            entry_fee=snap.entry_fee,
            exit_fee=fee,
            total_fees=snap.entry_fee + fee,
            gross_pnl=gross,
            net_pnl=net,
            bars_held=bar_index - snap.entry_bar_index,
            same_bar_ambiguity_used=same_bar_ambiguity_used,
        )
        # Equity: entry fee already deducted; apply gross and deduct exit fee.
        new_equity = equity + gross - fee
        return fill, trade, new_equity

    def _evaluate_protective(
        self,
        snapshot: PositionSnapshot,
        candle: Candle,
    ) -> tuple[FillReason, Decimal, bool] | None:
        if snapshot.direction is PositionDirection.LONG:
            stop_hit = candle.low <= snapshot.stop_loss
            target_hit = candle.high >= snapshot.take_profit
        else:
            stop_hit = candle.high >= snapshot.stop_loss
            target_hit = candle.low <= snapshot.take_profit

        if stop_hit and target_hit:
            if self._policy.same_bar_exit_policy is not SameBarExitPolicy.STOP_FIRST:
                msg = "Unsupported same-bar exit policy"
                raise BacktestExecutionError(msg)
            return FillReason.STOP_LOSS, snapshot.stop_loss, True
        if stop_hit:
            return FillReason.STOP_LOSS, snapshot.stop_loss, False
        if target_hit:
            return FillReason.TAKE_PROFIT, snapshot.take_profit, False
        return None

    def _build_summary(
        self,
        *,
        equity: Decimal,
        equity_curve: tuple[Decimal, ...],
        fills: tuple[FillRecord, ...],
        trades: tuple[ClosedTrade, ...],
        unfilled_count: int,
        input_candle_count: int,
        input_candle_hash: str,
        policy_hash: str,
        result_hash: str,
    ) -> BacktestSummary:
        gross = sum((t.gross_pnl for t in trades), Decimal("0"))
        net = sum((t.net_pnl for t in trades), Decimal("0"))
        fees = sum((f.fee for f in fills), Decimal("0"))
        wins = sum(1 for t in trades if t.net_pnl > 0)
        losses = sum(1 for t in trades if t.net_pnl < 0)
        flats = sum(1 for t in trades if t.net_pnl == 0)
        return BacktestSummary(
            initial_equity=self._policy.initial_equity,
            final_equity=equity,
            gross_pnl=gross,
            net_pnl=net,
            total_fees=fees,
            closed_trade_count=len(trades),
            winning_trade_count=wins,
            losing_trade_count=losses,
            breakeven_trade_count=flats,
            forced_close_count=sum(1 for t in trades if t.exit_reason is FillReason.END_OF_DATA),
            stop_loss_count=sum(1 for t in trades if t.exit_reason is FillReason.STOP_LOSS),
            take_profit_count=sum(1 for t in trades if t.exit_reason is FillReason.TAKE_PROFIT),
            explicit_exit_count=sum(1 for t in trades if t.exit_reason is FillReason.EXPLICIT_EXIT),
            unfilled_intent_count=unfilled_count,
            max_realized_equity_drawdown=_max_drawdown(equity_curve),
            input_candle_count=input_candle_count,
            input_candle_hash=input_candle_hash,
            policy_hash=policy_hash,
            result_hash=result_hash,
        )


def _max_drawdown(curve: tuple[Decimal, ...]) -> Decimal:
    peak = curve[0]
    max_dd = Decimal("0")
    for value in curve:
        if value > peak:
            peak = value
        dd = peak - value
        if dd > max_dd:
            max_dd = dd
    return max_dd
