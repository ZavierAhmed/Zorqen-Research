"""Canonical serialization and hashing for backtest results."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from zorqen_research.application.market_data.serialization import format_canonical_decimal
from zorqen_research.domain.artifacts import sha256_hex
from zorqen_research.domain.backtesting.execution import FillRecord
from zorqen_research.domain.backtesting.intents import BacktestIntent, EnterIntent, ExitIntent
from zorqen_research.domain.backtesting.policy import BacktestPolicy
from zorqen_research.domain.backtesting.results import (
    BacktestResult,
    BacktestSummary,
)
from zorqen_research.domain.backtesting.trades import ClosedTrade


def _iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _dec(value: Decimal) -> str:
    return format_canonical_decimal(value)


def policy_to_document(policy: BacktestPolicy) -> dict[str, Any]:
    return {
        "force_close_at_end": policy.force_close_at_end,
        "initial_equity": _dec(policy.initial_equity),
        "market_slippage_bps": _dec(policy.market_slippage_bps),
        "minimum_notional": _dec(policy.minimum_notional),
        "minimum_quantity": _dec(policy.minimum_quantity),
        "quantity_step": _dec(policy.quantity_step),
        "same_bar_exit_policy": policy.same_bar_exit_policy.value,
        "taker_fee_bps": _dec(policy.taker_fee_bps),
        "tick_size": _dec(policy.tick_size),
    }


def hash_policy(policy: BacktestPolicy) -> str:
    payload = json.dumps(
        policy_to_document(policy),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return sha256_hex(payload)


def _intent_document(intent: BacktestIntent) -> dict[str, Any]:
    if isinstance(intent, EnterIntent):
        return {
            "decision_open_time": _iso(intent.decision_open_time),
            "direction": intent.direction.value,
            "intent_id": intent.intent_id,
            "intent_type": intent.intent_type.value,
            "label": intent.label,
            "quantity": _dec(intent.quantity),
            "stop_loss": _dec(intent.stop_loss),
            "take_profit": _dec(intent.take_profit),
        }
    assert isinstance(intent, ExitIntent)
    return {
        "decision_open_time": _iso(intent.decision_open_time),
        "intent_id": intent.intent_id,
        "intent_type": intent.intent_type.value,
        "label": intent.label,
    }


def _fill_document(fill: FillRecord) -> dict[str, Any]:
    return {
        "bar_index": fill.bar_index,
        "direction": fill.direction.value,
        "fee": _dec(fill.fee),
        "fill_id": fill.fill_id,
        "fill_price": _dec(fill.fill_price),
        "fill_time": _iso(fill.fill_time),
        "intent_id": fill.intent_id,
        "liquidity_role": fill.liquidity_role.value,
        "notional": _dec(fill.notional),
        "position_id": fill.position_id,
        "quantity": _dec(fill.quantity),
        "reason": fill.reason.value,
        "reference_price": _dec(fill.reference_price),
        "side": fill.side.value,
        "tick_normalized": fill.tick_normalized,
    }


def _trade_document(trade: ClosedTrade) -> dict[str, Any]:
    return {
        "bars_held": trade.bars_held,
        "direction": trade.direction.value,
        "entry_fee": _dec(trade.entry_fee),
        "entry_fill_id": trade.entry_fill_id,
        "entry_price": _dec(trade.entry_price),
        "entry_time": _iso(trade.entry_time),
        "exit_fee": _dec(trade.exit_fee),
        "exit_fill_id": trade.exit_fill_id,
        "exit_price": _dec(trade.exit_price),
        "exit_reason": trade.exit_reason.value,
        "exit_time": _iso(trade.exit_time),
        "gross_pnl": _dec(trade.gross_pnl),
        "net_pnl": _dec(trade.net_pnl),
        "position_id": trade.position_id,
        "quantity": _dec(trade.quantity),
        "same_bar_ambiguity_used": trade.same_bar_ambiguity_used,
        "stop_loss": _dec(trade.stop_loss),
        "take_profit": _dec(trade.take_profit),
        "total_fees": _dec(trade.total_fees),
        "trade_id": trade.trade_id,
    }


def _summary_document(summary: BacktestSummary, *, include_result_hash: bool) -> dict[str, Any]:
    doc = {
        "breakeven_trade_count": summary.breakeven_trade_count,
        "closed_trade_count": summary.closed_trade_count,
        "explicit_exit_count": summary.explicit_exit_count,
        "final_equity": _dec(summary.final_equity),
        "forced_close_count": summary.forced_close_count,
        "gross_pnl": _dec(summary.gross_pnl),
        "initial_equity": _dec(summary.initial_equity),
        "input_candle_count": summary.input_candle_count,
        "input_candle_hash": summary.input_candle_hash,
        "losing_trade_count": summary.losing_trade_count,
        "max_realized_equity_drawdown": _dec(summary.max_realized_equity_drawdown),
        "net_pnl": _dec(summary.net_pnl),
        "policy_hash": summary.policy_hash,
        "stop_loss_count": summary.stop_loss_count,
        "take_profit_count": summary.take_profit_count,
        "total_fees": _dec(summary.total_fees),
        "unfilled_intent_count": summary.unfilled_intent_count,
        "winning_trade_count": summary.winning_trade_count,
    }
    if include_result_hash:
        doc["result_hash"] = summary.result_hash
    return doc


def result_to_document(
    result: BacktestResult, *, include_result_hash: bool = True
) -> dict[str, Any]:
    return {
        "equity_curve": [_dec(v) for v in result.equity_curve],
        "fills": [_fill_document(item) for item in result.fills],
        "policy": policy_to_document(result.policy),
        "summary": _summary_document(result.summary, include_result_hash=include_result_hash),
        "symbol": result.symbol.value,
        "timeframe": result.timeframe.value,
        "trades": [_trade_document(item) for item in result.trades],
        "unfilled_intents": [
            {"intent": _intent_document(item.intent), "reason": item.reason}
            for item in result.unfilled_intents
        ],
    }


def serialize_result(result: BacktestResult, *, include_result_hash: bool = True) -> bytes:
    document = result_to_document(result, include_result_hash=include_result_hash)
    return json.dumps(
        document,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def hash_result(result: BacktestResult) -> str:
    """Hash logical result excluding volatile/circular result_hash field."""
    return sha256_hex(serialize_result(result, include_result_hash=False))
