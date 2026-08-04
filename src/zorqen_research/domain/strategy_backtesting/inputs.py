"""Factory-bound multi-timeframe backtest input bundles."""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass

from zorqen_research.domain.artifacts import sha256_hex
from zorqen_research.domain.candles import Candle
from zorqen_research.domain.market_data.alignment import (
    ContextAlignment,
    MultiContextAlignment,
    align_context_to_execution,
)
from zorqen_research.domain.market_data.derivation import derive_timeframe_plan
from zorqen_research.domain.market_data.errors import (
    AlignmentValidationError,
    ResamplingValidationError,
)
from zorqen_research.domain.market_data.hashes import hash_candle_tuple
from zorqen_research.domain.market_data.series import require_canonical_series
from zorqen_research.domain.strategy_backtesting.errors import StrategyBacktestValidationError
from zorqen_research.domain.strategy_definitions.instances import StrategyInstanceSpecification
from zorqen_research.domain.symbols import Symbol
from zorqen_research.domain.timeframes import Timeframe

_BUNDLE_SCHEMA = "1"


@dataclass(frozen=True, slots=True, init=False)
class ContextSeriesInput:
    """One verified context series bound to its definition warmup and alignment."""

    timeframe: Timeframe
    warmup_bars: int
    candles: tuple[Candle, ...]
    candle_count: int
    candle_sha256: str
    alignment: ContextAlignment

    def __init__(self, *args: object, **kwargs: object) -> None:
        msg = "ContextSeriesInput must be created via MultiTimeframeBacktestInput factory"
        raise StrategyBacktestValidationError(msg)

    @classmethod
    def _create(
        cls,
        *,
        timeframe: Timeframe,
        warmup_bars: int,
        candles: tuple[Candle, ...],
        candle_sha256: str,
        alignment: ContextAlignment,
    ) -> ContextSeriesInput:
        self = object.__new__(cls)
        object.__setattr__(self, "timeframe", timeframe)
        object.__setattr__(self, "warmup_bars", warmup_bars)
        object.__setattr__(self, "candles", candles)
        object.__setattr__(self, "candle_count", len(candles))
        object.__setattr__(self, "candle_sha256", candle_sha256)
        object.__setattr__(self, "alignment", alignment)
        return self


@dataclass(frozen=True, slots=True, init=False)
class MultiTimeframeBacktestInput:
    """Immutable strategy + execution + context identity for MTF backtests."""

    strategy_instance: StrategyInstanceSpecification
    strategy_instance_hash: str
    symbol: Symbol
    execution_timeframe: Timeframe
    execution_warmup_bars: int
    execution_candles: tuple[Candle, ...]
    execution_candle_count: int
    execution_candle_sha256: str
    contexts: tuple[ContextSeriesInput, ...]
    multi_context_alignment: MultiContextAlignment
    input_bundle_hash: str

    def __init__(self, *args: object, **kwargs: object) -> None:
        msg = "MultiTimeframeBacktestInput must be created via from_verified"
        raise StrategyBacktestValidationError(msg)

    @classmethod
    def from_verified(
        cls,
        *,
        strategy_instance: StrategyInstanceSpecification,
        symbol: Symbol,
        execution_candles: tuple[Candle, ...],
        context_series: Sequence[tuple[Timeframe, tuple[Candle, ...]]],
    ) -> MultiTimeframeBacktestInput:
        if not isinstance(strategy_instance, StrategyInstanceSpecification):
            msg = "strategy_instance must be a StrategyInstanceSpecification"
            raise StrategyBacktestValidationError(msg)
        if not isinstance(symbol, Symbol):
            msg = "symbol must be a Symbol"
            raise StrategyBacktestValidationError(msg)
        definition = strategy_instance.definition
        if not definition.context_requirements:
            msg = (
                "definitions without context requirements must use the single-timeframe "
                "backtest path; multi-timeframe runner rejected this definition"
            )
            raise StrategyBacktestValidationError(msg)
        if not isinstance(execution_candles, tuple):
            msg = "execution candles must be an immutable tuple"
            raise StrategyBacktestValidationError(msg)
        if not isinstance(context_series, tuple):
            msg = "context_series must be an immutable tuple"
            raise StrategyBacktestValidationError(msg)

        execution_timeframe = definition.execution_timeframe
        try:
            execution = require_canonical_series(
                execution_candles,
                timeframe=execution_timeframe,
                label="execution",
            )
        except ResamplingValidationError as exc:
            raise StrategyBacktestValidationError(str(exc)) from exc

        required = definition.context_requirements
        if len(context_series) != len(required):
            msg = "context series count must exactly match definition context requirements"
            raise StrategyBacktestValidationError(msg)

        context_inputs: list[ContextSeriesInput] = []
        alignments: list[ContextAlignment] = []
        for index, requirement in enumerate(required):
            entry = context_series[index]
            if not isinstance(entry, tuple) or len(entry) != 2:
                msg = "each context entry must be (Timeframe, candle tuple)"
                raise StrategyBacktestValidationError(msg)
            timeframe, candles = entry
            if timeframe is not requirement.timeframe:
                msg = (
                    "context timeframes must exactly match the definition order: "
                    f"expected {requirement.timeframe.value} at position {index}"
                )
                raise StrategyBacktestValidationError(msg)
            if not isinstance(candles, tuple):
                msg = f"context {timeframe.value} candles must be an immutable tuple"
                raise StrategyBacktestValidationError(msg)
            try:
                derive_timeframe_plan(execution_timeframe, timeframe)
            except ResamplingValidationError as exc:
                raise StrategyBacktestValidationError(str(exc)) from exc
            try:
                canonical = require_canonical_series(
                    candles, timeframe=timeframe, label=f"context:{timeframe.value}"
                )
            except ResamplingValidationError as exc:
                raise StrategyBacktestValidationError(str(exc)) from exc
            try:
                alignment = align_context_to_execution(
                    symbol=symbol,
                    execution_timeframe=execution_timeframe,
                    context_timeframe=timeframe,
                    execution_candles=execution,
                    context_candles=canonical,
                )
            except AlignmentValidationError as exc:
                raise StrategyBacktestValidationError(str(exc)) from exc
            digest = hash_candle_tuple(canonical)
            if digest != alignment.context_candle_sha256:
                msg = "context candle hash diverged from alignment binding"
                raise StrategyBacktestValidationError(msg)
            context_inputs.append(
                ContextSeriesInput._create(
                    timeframe=timeframe,
                    warmup_bars=requirement.warmup_bars,
                    candles=canonical,
                    candle_sha256=digest,
                    alignment=alignment,
                )
            )
            alignments.append(alignment)

        try:
            multi = MultiContextAlignment.from_alignments(tuple(alignments))
        except AlignmentValidationError as exc:
            raise StrategyBacktestValidationError(str(exc)) from exc

        execution_hash = hash_candle_tuple(execution)
        if execution_hash != multi.execution_candle_sha256:
            msg = "execution candle hash diverged from multi-context alignment"
            raise StrategyBacktestValidationError(msg)

        contexts = tuple(context_inputs)
        document = {
            "contexts": [
                {
                    "alignment_hash": item.alignment.alignment_hash,
                    "candle_count": item.candle_count,
                    "candle_sha256": item.candle_sha256,
                    "timeframe": item.timeframe.value,
                    "warmup_bars": item.warmup_bars,
                }
                for item in contexts
            ],
            "execution_candle_count": len(execution),
            "execution_candle_sha256": execution_hash,
            "execution_timeframe": execution_timeframe.value,
            "execution_warmup_bars": definition.execution_warmup_bars,
            "multi_context_alignment_hash": multi.alignment_hash,
            "schema_version": _BUNDLE_SCHEMA,
            "strategy_instance_hash": strategy_instance.instance_hash,
            "symbol": symbol.value,
        }
        bundle_hash = sha256_hex(
            json.dumps(
                document,
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            ).encode("utf-8")
        )

        self = object.__new__(cls)
        object.__setattr__(self, "strategy_instance", strategy_instance)
        object.__setattr__(self, "strategy_instance_hash", strategy_instance.instance_hash)
        object.__setattr__(self, "symbol", symbol)
        object.__setattr__(self, "execution_timeframe", execution_timeframe)
        object.__setattr__(self, "execution_warmup_bars", definition.execution_warmup_bars)
        object.__setattr__(self, "execution_candles", execution)
        object.__setattr__(self, "execution_candle_count", len(execution))
        object.__setattr__(self, "execution_candle_sha256", execution_hash)
        object.__setattr__(self, "contexts", contexts)
        object.__setattr__(self, "multi_context_alignment", multi)
        object.__setattr__(self, "input_bundle_hash", bundle_hash)
        return self
