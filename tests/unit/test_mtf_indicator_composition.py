"""Adversarial composition-input tests for Milestone 1.2."""

from __future__ import annotations

import pytest

from tests.unit.mtf_indicator_helpers import (
    SYMBOL,
    indicator_bundle_for,
    standard_composition,
    standard_mtf,
)
from zorqen_research.application.indicators.ema import ema_close
from zorqen_research.application.market_data.goldens import build_source_series
from zorqen_research.domain.indicator_views.bundles import IndicatorSeriesBundle
from zorqen_research.domain.indicators.inputs import IndicatorInput
from zorqen_research.domain.strategy_backtesting.errors import StrategyBacktestValidationError
from zorqen_research.domain.strategy_backtesting.indicator_composition import (
    MultiTimeframeIndicatorInput,
)
from zorqen_research.domain.strategy_backtesting.inputs import MultiTimeframeBacktestInput
from zorqen_research.domain.symbols import Symbol
from zorqen_research.domain.timeframes import Timeframe


def test_mtf_indicator_input_subclass_rejected() -> None:
    class Fake(MultiTimeframeBacktestInput):
        pass

    mtf, execution, _ = standard_mtf()
    fake = object.__new__(Fake)
    for name in (
        "strategy_instance",
        "strategy_instance_hash",
        "symbol",
        "execution_timeframe",
        "execution_warmup_bars",
        "execution_candles",
        "execution_candle_count",
        "execution_candle_sha256",
        "contexts",
        "multi_context_alignment",
        "input_bundle_hash",
    ):
        object.__setattr__(fake, name, getattr(mtf, name))
    exec_ind = indicator_bundle_for(execution, Timeframe.H1)
    with pytest.raises(StrategyBacktestValidationError, match="exact MultiTimeframeBacktestInput"):
        MultiTimeframeIndicatorInput.from_verified(
            input_bundle=fake,  # type: ignore[arg-type]
            execution_indicators=exec_ind,
            context_indicators=(None,),
        )


def test_mtf_indicator_forged_populated_mtf_rejected() -> None:
    mtf, execution, _ = standard_mtf()
    forged = object.__new__(MultiTimeframeBacktestInput)
    for name in (
        "strategy_instance",
        "strategy_instance_hash",
        "symbol",
        "execution_timeframe",
        "execution_warmup_bars",
        "execution_candles",
        "execution_candle_count",
        "execution_candle_sha256",
        "contexts",
        "multi_context_alignment",
    ):
        object.__setattr__(forged, name, getattr(mtf, name))
    object.__setattr__(forged, "input_bundle_hash", "ab" * 32)
    exec_ind = indicator_bundle_for(execution, Timeframe.H1)
    with pytest.raises(StrategyBacktestValidationError):
        MultiTimeframeIndicatorInput.from_verified(
            input_bundle=forged,
            execution_indicators=exec_ind,
            context_indicators=(None,),
        )


def test_mtf_indicator_mutable_list_and_tuple_subclass_rejected() -> None:
    mtf, execution, _ = standard_mtf()
    exec_ind = indicator_bundle_for(execution, Timeframe.H1)
    with pytest.raises(StrategyBacktestValidationError, match="exact tuple"):
        MultiTimeframeIndicatorInput.from_verified(
            input_bundle=mtf,
            execution_indicators=exec_ind,
            context_indicators=[None],  # type: ignore[arg-type]
        )

    class CtxTuple(tuple):
        pass

    with pytest.raises(StrategyBacktestValidationError, match="exact tuple"):
        MultiTimeframeIndicatorInput.from_verified(
            input_bundle=mtf,
            execution_indicators=exec_ind,
            context_indicators=CtxTuple((None,)),
        )


def test_mtf_indicator_context_slot_count_rejected() -> None:
    mtf, execution, _ = standard_mtf()
    exec_ind = indicator_bundle_for(execution, Timeframe.H1)
    with pytest.raises(StrategyBacktestValidationError, match="length"):
        MultiTimeframeIndicatorInput.from_verified(
            input_bundle=mtf,
            execution_indicators=exec_ind,
            context_indicators=(),
        )
    with pytest.raises(StrategyBacktestValidationError, match="length"):
        MultiTimeframeIndicatorInput.from_verified(
            input_bundle=mtf,
            execution_indicators=exec_ind,
            context_indicators=(None, None),
        )


def test_mtf_indicator_swapped_context_bundles_rejected() -> None:
    from tests.unit.mtf_indicator_helpers import START
    from zorqen_research.application.strategy_backtesting.goldens import mtf_definition
    from zorqen_research.application.strategy_definitions.serialization import build_instance
    from zorqen_research.domain.strategy_definitions.timeframes import TimeframeRequirement

    definition = mtf_definition(
        execution_warmup=4,
        contexts=(
            TimeframeRequirement(timeframe=Timeframe.H4, warmup_bars=1),
            TimeframeRequirement(timeframe=Timeframe.D1, warmup_bars=1),
        ),
        definition_code="mtf_ind_swap",
    )
    instance = build_instance(definition, {"signal_strength": 1})
    execution = build_source_series(start=START, timeframe=Timeframe.H1, count=24)
    c4 = build_source_series(start=START, timeframe=Timeframe.H4, count=6)
    c1d = build_source_series(start=START, timeframe=Timeframe.D1, count=1)
    mtf = MultiTimeframeBacktestInput.from_verified(
        strategy_instance=instance,
        symbol=SYMBOL,
        execution_candles=execution,
        context_series=((Timeframe.H4, c4), (Timeframe.D1, c1d)),
    )
    h4_bundle = indicator_bundle_for(c4, Timeframe.H4)
    d1_bundle = indicator_bundle_for(c1d, Timeframe.D1)
    with pytest.raises(StrategyBacktestValidationError, match="timeframe"):
        MultiTimeframeIndicatorInput.from_verified(
            input_bundle=mtf,
            execution_indicators=None,
            context_indicators=(d1_bundle, h4_bundle),
        )


def test_mtf_indicator_wrong_symbol_timeframe_count_hash_identity() -> None:
    mtf, execution, context = standard_mtf()
    # Wrong symbol
    other_symbol = Symbol(value="ETHUSDT")
    wrong_symbol_input = IndicatorInput.from_verified(
        symbol=other_symbol,
        timeframe=Timeframe.H1,
        candles=execution,
    )
    wrong_symbol = IndicatorSeriesBundle.from_verified(
        indicator_input=wrong_symbol_input,
        series=(ema_close(wrong_symbol_input, 1),),
    )
    with pytest.raises(StrategyBacktestValidationError, match="symbol"):
        MultiTimeframeIndicatorInput.from_verified(
            input_bundle=mtf,
            execution_indicators=wrong_symbol,
            context_indicators=(None,),
        )

    # Wrong timeframe (H4 candles as execution indicators)
    wrong_tf = indicator_bundle_for(context, Timeframe.H4)
    with pytest.raises(StrategyBacktestValidationError, match="timeframe"):
        MultiTimeframeIndicatorInput.from_verified(
            input_bundle=mtf,
            execution_indicators=wrong_tf,
            context_indicators=(None,),
        )

    # Wrong count: shorter series on H1
    short = build_source_series(
        start=mtf.execution_candles[0].open_time,
        timeframe=Timeframe.H1,
        count=4,
    )
    wrong_count = indicator_bundle_for(short, Timeframe.H1)
    with pytest.raises(StrategyBacktestValidationError, match="candle count|candle hash"):
        MultiTimeframeIndicatorInput.from_verified(
            input_bundle=mtf,
            execution_indicators=wrong_count,
            context_indicators=(None,),
        )


def test_mtf_indicator_correct_hash_wrong_tuple_identity_rejected() -> None:
    mtf, execution, _ = standard_mtf()
    # Rebuild equal candles as a new tuple (same content/hash, different identity).
    twin = build_source_series(
        start=execution[0].open_time,
        timeframe=Timeframe.H1,
        count=len(execution),
    )
    assert twin is not execution
    from zorqen_research.domain.market_data.hashes import hash_candle_tuple

    assert hash_candle_tuple(twin) == hash_candle_tuple(execution)
    twin_bundle = indicator_bundle_for(twin, Timeframe.H1)
    with pytest.raises(StrategyBacktestValidationError, match="exact MTF candle tuple"):
        MultiTimeframeIndicatorInput.from_verified(
            input_bundle=mtf,
            execution_indicators=twin_bundle,
            context_indicators=(None,),
        )


def test_mtf_indicator_cross_slot_placement_rejected() -> None:
    mtf, execution, context = standard_mtf()
    exec_as_context = indicator_bundle_for(execution, Timeframe.H1)
    with pytest.raises(StrategyBacktestValidationError, match="timeframe"):
        MultiTimeframeIndicatorInput.from_verified(
            input_bundle=mtf,
            execution_indicators=None,
            context_indicators=(exec_as_context,),
        )
    context_as_exec = indicator_bundle_for(context, Timeframe.H4)
    with pytest.raises(StrategyBacktestValidationError, match="timeframe"):
        MultiTimeframeIndicatorInput.from_verified(
            input_bundle=mtf,
            execution_indicators=context_as_exec,
            context_indicators=(None,),
        )


def test_mtf_indicator_caller_modified_and_forged_bundle_rejected() -> None:
    mtf, execution, _ = standard_mtf()
    valid = indicator_bundle_for(execution, Timeframe.H1)
    forged = object.__new__(IndicatorSeriesBundle)
    for name in IndicatorSeriesBundle.__slots__:
        object.__setattr__(forged, name, getattr(valid, name))
    object.__setattr__(forged, "bundle_hash", "ff" * 32)
    with pytest.raises(StrategyBacktestValidationError):
        MultiTimeframeIndicatorInput.from_verified(
            input_bundle=mtf,
            execution_indicators=forged,
            context_indicators=(None,),
        )


def test_mtf_indicator_no_configured_bundles_rejected() -> None:
    mtf, _, _ = standard_mtf()
    with pytest.raises(StrategyBacktestValidationError, match="at least one"):
        MultiTimeframeIndicatorInput.from_verified(
            input_bundle=mtf,
            execution_indicators=None,
            context_indicators=(None,),
        )


def test_mtf_indicator_direct_construction_blocked() -> None:
    with pytest.raises(StrategyBacktestValidationError):
        MultiTimeframeIndicatorInput(  # type: ignore[call-arg]
            indicator_composition_hash="aa" * 32
        )


def test_mtf_indicator_valid_composition_retains_rebuilt() -> None:
    composition = standard_composition()
    assert composition.execution_indicators is not None
    assert composition.indicator_composition_hash
    again = MultiTimeframeIndicatorInput.from_verified(
        input_bundle=composition.input_bundle,
        execution_indicators=composition.execution_indicators,
        context_indicators=composition.context_indicators,
    )
    assert again.indicator_composition_hash == composition.indicator_composition_hash
