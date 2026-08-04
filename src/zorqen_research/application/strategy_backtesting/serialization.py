"""Canonical serialization helpers for MTF strategy backtest envelopes."""

from __future__ import annotations

import json

from zorqen_research.domain.strategy_backtesting.errors import StrategyBacktestValidationError
from zorqen_research.domain.strategy_backtesting.results import StrategyBacktestEnvelope


def serialize_envelope_identity(envelope: StrategyBacktestEnvelope) -> bytes:
    """Canonical JSON identity bytes (no candle bodies / no result ledger)."""
    if not isinstance(envelope, StrategyBacktestEnvelope):
        msg = "envelope must be a StrategyBacktestEnvelope"
        raise StrategyBacktestValidationError(msg)
    document = {
        "backtest_result_hash": envelope.backtest_result_hash,
        "envelope_hash": envelope.envelope_hash,
        "execution_candle_sha256": envelope.execution_candle_sha256,
        "input_bundle_hash": envelope.input_bundle_hash,
        "multi_context_alignment_hash": envelope.multi_context_alignment_hash,
        "policy_hash": envelope.policy_hash,
        "provider_invocation_count": envelope.provider_invocation_count,
        "schema_version": "1",
        "strategy_instance_hash": envelope.strategy_instance_hash,
        "warmup_skipped_decision_count": envelope.warmup_skipped_decision_count,
    }
    return json.dumps(
        document,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
