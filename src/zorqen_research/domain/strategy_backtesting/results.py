"""Factory-bound strategy backtest result envelope."""

from __future__ import annotations

import json
from dataclasses import dataclass

from zorqen_research.domain.artifacts import sha256_hex
from zorqen_research.domain.backtesting.policy import BacktestPolicy
from zorqen_research.domain.backtesting.results import BacktestResult
from zorqen_research.domain.strategy_backtesting.errors import StrategyBacktestValidationError
from zorqen_research.domain.strategy_backtesting.inputs import MultiTimeframeBacktestInput

_ENVELOPE_SCHEMA = "1"


@dataclass(frozen=True, slots=True, init=False)
class StrategyBacktestEnvelope:
    """Binds strategy/market-data identity to an unchanged BacktestResult."""

    strategy_instance_hash: str
    input_bundle_hash: str
    execution_candle_sha256: str
    multi_context_alignment_hash: str
    policy_hash: str
    backtest_result_hash: str
    result: BacktestResult
    provider_invocation_count: int
    warmup_skipped_decision_count: int
    envelope_hash: str

    def __init__(self, *args: object, **kwargs: object) -> None:
        msg = "StrategyBacktestEnvelope must be created via from_run"
        raise StrategyBacktestValidationError(msg)

    @classmethod
    def from_run(
        cls,
        *,
        input_bundle: MultiTimeframeBacktestInput,
        policy: BacktestPolicy,
        result: BacktestResult,
        provider_invocation_count: int,
        warmup_skipped_decision_count: int,
    ) -> StrategyBacktestEnvelope:
        if not isinstance(input_bundle, MultiTimeframeBacktestInput):
            msg = "input_bundle must be a MultiTimeframeBacktestInput"
            raise StrategyBacktestValidationError(msg)
        if not isinstance(policy, BacktestPolicy):
            msg = "policy must be a BacktestPolicy"
            raise StrategyBacktestValidationError(msg)
        if not isinstance(result, BacktestResult):
            msg = "result must be a BacktestResult"
            raise StrategyBacktestValidationError(msg)
        if type(provider_invocation_count) is not int or isinstance(
            provider_invocation_count, bool
        ):
            msg = "provider_invocation_count must be a real int"
            raise StrategyBacktestValidationError(msg)
        if type(warmup_skipped_decision_count) is not int or isinstance(
            warmup_skipped_decision_count, bool
        ):
            msg = "warmup_skipped_decision_count must be a real int"
            raise StrategyBacktestValidationError(msg)
        if provider_invocation_count < 0 or warmup_skipped_decision_count < 0:
            msg = "invocation and warmup-skip counts must be non-negative"
            raise StrategyBacktestValidationError(msg)
        if (
            provider_invocation_count + warmup_skipped_decision_count
            != input_bundle.execution_candle_count
        ):
            msg = (
                "provider_invocation_count + warmup_skipped_decision_count "
                "must equal execution_candle_count"
            )
            raise StrategyBacktestValidationError(msg)

        # Deferred import keeps CSV/policy hashing on the application contract.
        from zorqen_research.application.backtesting.serialization import hash_policy

        policy_digest = hash_policy(policy)
        if result.summary.policy_hash != policy_digest:
            msg = "result policy_hash does not match the supplied policy"
            raise StrategyBacktestValidationError(msg)
        if result.summary.input_candle_hash != input_bundle.execution_candle_sha256:
            msg = "result input_candle_hash does not match the input bundle execution hash"
            raise StrategyBacktestValidationError(msg)

        strategy_instance_hash = input_bundle.strategy_instance_hash
        input_bundle_hash = input_bundle.input_bundle_hash
        execution_candle_sha256 = input_bundle.execution_candle_sha256
        multi_context_alignment_hash = input_bundle.multi_context_alignment.alignment_hash
        backtest_result_hash = result.summary.result_hash
        digest = sha256_hex(
            json.dumps(
                {
                    "backtest_result_hash": backtest_result_hash,
                    "execution_candle_sha256": execution_candle_sha256,
                    "input_bundle_hash": input_bundle_hash,
                    "multi_context_alignment_hash": multi_context_alignment_hash,
                    "policy_hash": policy_digest,
                    "provider_invocation_count": provider_invocation_count,
                    "schema_version": _ENVELOPE_SCHEMA,
                    "strategy_instance_hash": strategy_instance_hash,
                    "warmup_skipped_decision_count": warmup_skipped_decision_count,
                },
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            ).encode("utf-8")
        )
        self = object.__new__(cls)
        object.__setattr__(self, "strategy_instance_hash", strategy_instance_hash)
        object.__setattr__(self, "input_bundle_hash", input_bundle_hash)
        object.__setattr__(self, "execution_candle_sha256", execution_candle_sha256)
        object.__setattr__(self, "multi_context_alignment_hash", multi_context_alignment_hash)
        object.__setattr__(self, "policy_hash", policy_digest)
        object.__setattr__(self, "backtest_result_hash", backtest_result_hash)
        object.__setattr__(self, "result", result)
        object.__setattr__(self, "provider_invocation_count", provider_invocation_count)
        object.__setattr__(self, "warmup_skipped_decision_count", warmup_skipped_decision_count)
        object.__setattr__(self, "envelope_hash", digest)
        return self
