"""Indicator-aware wrapper around StrategyBacktestEnvelope."""

from __future__ import annotations

import json
from dataclasses import dataclass

from zorqen_research.domain.artifacts import sha256_hex
from zorqen_research.domain.backtesting.policy import BacktestPolicy
from zorqen_research.domain.backtesting.results import BacktestResult
from zorqen_research.domain.strategy_backtesting.errors import StrategyBacktestValidationError
from zorqen_research.domain.strategy_backtesting.indicator_composition import (
    MultiTimeframeIndicatorInput,
)
from zorqen_research.domain.strategy_backtesting.results import StrategyBacktestEnvelope

_INDICATOR_ENVELOPE_SCHEMA = "1"


@dataclass(frozen=True, slots=True, init=False)
class IndicatorStrategyBacktestEnvelope:
    """Binds a base MTF envelope to indicator composition provenance."""

    schema_version: str
    base: StrategyBacktestEnvelope
    indicator_composition_hash: str
    indicator_aware_envelope_hash: str

    def __init__(self, *args: object, **kwargs: object) -> None:
        msg = "IndicatorStrategyBacktestEnvelope must be created via from_run"
        raise StrategyBacktestValidationError(msg)

    @classmethod
    def from_run(
        cls,
        *,
        composition: MultiTimeframeIndicatorInput,
        policy: BacktestPolicy,
        result: BacktestResult,
        provider_invocation_count: int,
        warmup_skipped_decision_count: int,
    ) -> IndicatorStrategyBacktestEnvelope:
        if type(composition) is not MultiTimeframeIndicatorInput:
            msg = "composition must be an exact MultiTimeframeIndicatorInput"
            raise StrategyBacktestValidationError(msg)
        base = StrategyBacktestEnvelope.from_run(
            input_bundle=composition.input_bundle,
            policy=policy,
            result=result,
            provider_invocation_count=provider_invocation_count,
            warmup_skipped_decision_count=warmup_skipped_decision_count,
        )
        if base.input_bundle_hash != composition.input_bundle.input_bundle_hash:
            msg = "base envelope input_bundle_hash does not match composition"
            raise StrategyBacktestValidationError(msg)
        composition_hash = composition.indicator_composition_hash
        digest = sha256_hex(
            json.dumps(
                {
                    "base_envelope_hash": base.envelope_hash,
                    "indicator_composition_hash": composition_hash,
                    "schema_version": _INDICATOR_ENVELOPE_SCHEMA,
                },
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            ).encode("utf-8")
        )
        self = object.__new__(cls)
        object.__setattr__(self, "schema_version", _INDICATOR_ENVELOPE_SCHEMA)
        object.__setattr__(self, "base", base)
        object.__setattr__(self, "indicator_composition_hash", composition_hash)
        object.__setattr__(self, "indicator_aware_envelope_hash", digest)
        return self
