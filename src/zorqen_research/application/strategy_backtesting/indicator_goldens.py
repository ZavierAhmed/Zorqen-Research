"""Frozen multi-timeframe + indicator composition golden scenarios.

Literal expected hashes only — do not derive golden hashes by invoking the
production runner at module import time.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from zorqen_research.application.backtesting.golden import default_policy
from zorqen_research.application.indicators.ema import ema_close
from zorqen_research.application.indicators.extrema import rolling_highest, rolling_lowest
from zorqen_research.application.indicators.volatility import wilder_atr
from zorqen_research.application.market_data.goldens import build_source_series, make_candle
from zorqen_research.application.strategy_backtesting.goldens import (
    _enter_long,
    _enter_short,
    mtf_definition,
)
from zorqen_research.application.strategy_backtesting.indicator_feed import (
    MultiTimeframeIndicatorDecisionFeed,
)
from zorqen_research.application.strategy_backtesting.indicator_provider import (
    MultiTimeframeIndicatorBacktestDecisionContext,
)
from zorqen_research.application.strategy_backtesting.indicator_runner import (
    MultiTimeframeIndicatorBacktestRunner,
)
from zorqen_research.application.strategy_definitions.serialization import build_instance
from zorqen_research.domain.backtesting.enums import PositionDirection
from zorqen_research.domain.backtesting.errors import (
    BacktestExecutionError,
    BacktestValidationError,
)
from zorqen_research.domain.backtesting.intents import BacktestIntent
from zorqen_research.domain.candles import Candle
from zorqen_research.domain.indicator_views.bundles import IndicatorSeriesBundle
from zorqen_research.domain.indicators.enums import IndicatorCode
from zorqen_research.domain.indicators.inputs import IndicatorInput
from zorqen_research.domain.strategy_backtesting.indicator_composition import (
    MultiTimeframeIndicatorInput,
)
from zorqen_research.domain.strategy_backtesting.inputs import MultiTimeframeBacktestInput
from zorqen_research.domain.strategy_definitions.definitions import StrategyDefinition
from zorqen_research.domain.strategy_definitions.timeframes import TimeframeRequirement
from zorqen_research.domain.symbols import Symbol
from zorqen_research.domain.timeframes import Timeframe

SYMBOL = Symbol(value="BTCUSDT")
START = datetime(2024, 1, 1, tzinfo=UTC)


class ScriptedMtfIndicatorProvider:
    """Golden/test utility only — not a production strategy provider."""

    def __init__(
        self,
        *,
        intents_by_bar: dict[int, tuple[BacktestIntent, ...]] | None = None,
        first_ready_intent: tuple[BacktestIntent, ...] | None = None,
    ) -> None:
        self._by_bar = intents_by_bar or {}
        self._first_ready = first_ready_intent
        self._emitted_first = False
        self.calls: list[int] = []

    def on_bar_close(
        self,
        context: MultiTimeframeIndicatorBacktestDecisionContext,
    ) -> tuple[BacktestIntent, ...]:
        self.calls.append(context.view.base_view.execution_bar_index)
        index = context.view.base_view.execution_bar_index
        if index in self._by_bar:
            return self._by_bar[index]
        if self._first_ready is not None and not self._emitted_first:
            self._emitted_first = True
            return self._first_ready
        return ()


@dataclass(frozen=True, slots=True)
class MtfIndicatorGoldenExpectation:
    scenario: str
    first_ready_index: int
    candle_ready_before_indicator: bool
    composition_hash: str
    provider_visible_hash: str
    execution_decision_view_hash: str | None
    context_decision_view_hashes: tuple[str | None, ...]
    indicator_aware_envelope_hash: str
    base_envelope_hash: str
    backtest_result_hash: str
    provider_invocation_count: int
    warmup_skipped_count: int
    closed_trade_count: int
    strategy_instance_hash: str
    mtf_input_bundle_hash: str
    controlled_failure: bool = False


class MtfIndicatorGoldenMismatchError(Exception):
    """Raised when a computed MTF-indicator golden diverges from frozen literals."""


def _indicator_bundle(
    *,
    candles: tuple[Candle, ...],
    timeframe: Timeframe,
    builders: tuple[object, ...],
) -> IndicatorSeriesBundle:
    indicator_input = IndicatorInput.from_verified(
        symbol=SYMBOL,
        timeframe=timeframe,
        candles=candles,
    )
    series = tuple(builder(indicator_input) for builder in builders)  # type: ignore[operator]
    return IndicatorSeriesBundle.from_verified(
        indicator_input=indicator_input,
        series=series,
    )


def _mtf_bundle(
    *,
    definition: StrategyDefinition,
    execution: tuple[Candle, ...],
    contexts: tuple[tuple[Timeframe, tuple[Candle, ...]], ...],
) -> MultiTimeframeBacktestInput:
    instance = build_instance(definition, {"signal_strength": 1})
    return MultiTimeframeBacktestInput.from_verified(
        strategy_instance=instance,
        symbol=SYMBOL,
        execution_candles=execution,
        context_series=contexts,
    )


def _cause_chain_has_unsupported_direction(exc: BaseException) -> bool:
    current: BaseException | None = exc
    seen: set[int] = set()
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        if isinstance(current, BacktestValidationError):
            text = str(current)
            if "not supported by the strategy definition" in text and "short" in text:
                return True
        current = current.__cause__ or current.__context__
    return False


# ---------------------------------------------------------------------------
# Frozen literals (computed offline once; never derived at import).
# ---------------------------------------------------------------------------

GOLDENS: dict[str, MtfIndicatorGoldenExpectation] = {
    "execution-indicator-warmup": MtfIndicatorGoldenExpectation(
        scenario="execution-indicator-warmup",
        first_ready_index=5,
        candle_ready_before_indicator=True,
        composition_hash="09c42366069a9be625274a0829314b986a714a66417a088794335cfb06015e01",
        provider_visible_hash="3f10ab0915fdbf64972c3a66be48a63e35d8a8723de8f83a4b80097ba70ac511",
        execution_decision_view_hash=(
            "1a9689672bd16c18f0f9a419d0f993b8b397677a85a42c668dd0064d1421019a"
        ),
        context_decision_view_hashes=(None,),
        indicator_aware_envelope_hash=(
            "9b197291e0da4dbe3a16c8266f8868272217911a883ca6b7d39f0515412ebaae"
        ),
        base_envelope_hash="7c640e619671cb5fc6acadd6c449e445d5d78adafbcb17709e573d8bc8e3759a",
        backtest_result_hash="2d6ce9c103d477967a1eff119ed35f1fc919e1d9db085695cc210a38c3dc9f2f",
        provider_invocation_count=5,
        warmup_skipped_count=5,
        closed_trade_count=1,
        strategy_instance_hash=("c3dea846ee64efc3f929d7b49c71db8693e66ca20ce1806b914fc3381aa2c434"),
        mtf_input_bundle_hash="3a045fccae131f9b6db520886183dc005ec0758e831950ba5c76b3510b247ca2",
    ),
    "exact-close-context-indicator": MtfIndicatorGoldenExpectation(
        scenario="exact-close-context-indicator",
        first_ready_index=3,
        candle_ready_before_indicator=False,
        composition_hash="65d5ebe74797553994e29ac7538bd745fefd6f2e9959949e2f92322cf9e5e93c",
        provider_visible_hash="3aceb55c71f99176f9dc7ee525230db60faa313638989ceefad885104dc4f6f9",
        execution_decision_view_hash=None,
        context_decision_view_hashes=(
            "e68692b4c8e3f007e097f41b168874a5ac4581be9ff6a13b4b52791f7337ab58",
        ),
        indicator_aware_envelope_hash=(
            "b4fcff2a65ac6906d99b44adc45a3a8639d173af044d026bd516a20604e89370"
        ),
        base_envelope_hash="865f0a5de018a09ee8cbdfa5c98af5007aaa367fced2196435750623e92bbb65",
        backtest_result_hash="3b13d44742c17a57e3ec94497e05bc83835743ed082017f81e7680781b9bf29e",
        provider_invocation_count=5,
        warmup_skipped_count=3,
        closed_trade_count=1,
        strategy_instance_hash=("858e2d8bb1a7f96a4fb74219f96ac7db7a77592ee23afd408ee02354a995826b"),
        mtf_input_bundle_hash="046b18c049377cb8af21b48a2f425ae6c70a07199eb6ce378598170b68fb76a0",
    ),
    "multiple-indicators-duplicate-codes": MtfIndicatorGoldenExpectation(
        scenario="multiple-indicators-duplicate-codes",
        first_ready_index=23,
        candle_ready_before_indicator=False,
        composition_hash="2f33951f3fe5d9e503d93415f4cdb05159dc227ac23d0d246705b667aab61209",
        provider_visible_hash="49b53235fe68dc8c4e53b0d6eaf92c5a20b50a21da7234e64b90601e19703445",
        execution_decision_view_hash=(
            "e17ee4282bbb9632af2e681a2e388ad0de9050f37f264eba9e5cff193aa40dba"
        ),
        context_decision_view_hashes=(
            "a4659a390d2cae203682c5f7dc3157a4ae6e1619fbdb3a2a992ade4de002a7ae",
            "81d9add75d04a7d5d444a888ee6787cb6cfa8a41fcc59bf7719b0bb5e9c9dc1e",
        ),
        indicator_aware_envelope_hash=(
            "7b8f23240704620b7183492eb5d80a39df923fb07d56e7a9739e4929278c070e"
        ),
        base_envelope_hash="285213f4bb73ebbe1fcbc21feb9c101ec5f35d6b6048719adafc7c7107492095",
        backtest_result_hash="d6d97f92dedd11c9a59fcac2ab937e3c70face07b9281263de5207f669c8fa09",
        provider_invocation_count=1,
        warmup_skipped_count=23,
        closed_trade_count=0,
        strategy_instance_hash=("0ed2f73a1b7b08fe9e2bd18995f94b171db5f9322f23ba18b4e1a21741f24d05"),
        mtf_input_bundle_hash="0749f09e9745d89966576e6275fd576e3792645cbef359550993c4d2152bea96",
    ),
    "optional-indicator-slots": MtfIndicatorGoldenExpectation(
        scenario="optional-indicator-slots",
        first_ready_index=23,
        candle_ready_before_indicator=False,
        composition_hash="7e054d5cf92b87749147a3640871c4862c9596b50a8f654cd608ad572eb69979",
        provider_visible_hash="d224257963bc9394053aaf6a4502d74f7a6718bea78648c3a5b5315513609d95",
        execution_decision_view_hash=None,
        context_decision_view_hashes=(
            "a4659a390d2cae203682c5f7dc3157a4ae6e1619fbdb3a2a992ade4de002a7ae",
            None,
        ),
        indicator_aware_envelope_hash=(
            "3b7121378bb3b36d6c0eb277ae949fa1e33bc604a0cb4f7bc74b3b6f96a4e8aa"
        ),
        base_envelope_hash="5f8c3917e0614b9625af783d28e46907fed495140fc5f49947a94420d3a5506b",
        backtest_result_hash="1acd509994b38468d71a3f7898f2e1bceee8257407a1e1f74feb80248dc94151",
        provider_invocation_count=1,
        warmup_skipped_count=23,
        closed_trade_count=0,
        strategy_instance_hash=("99411487353509e26446b7b6e74d3c85b0b02ca08b0808067296657511bf677d"),
        mtf_input_bundle_hash="02c92369709018dea41b8c2ee4b45c792487fe294c9eeddbe1ff08ea6b8cf307",
    ),
    "direction-restriction": MtfIndicatorGoldenExpectation(
        scenario="direction-restriction",
        first_ready_index=3,
        candle_ready_before_indicator=False,
        composition_hash="ee58944e0fbcae5cff93d2c1223b024d1e78f98272941e8121f6329b953c2321",
        provider_visible_hash="9c3ef10fe6498fad983ded2737700f103fbee8e6763826d7763a11669185f984",
        execution_decision_view_hash=(
            "7452add6115addc2792600a9676a6cd24dc3cb4c897fcd93f9e64890588fdd30"
        ),
        context_decision_view_hashes=(None,),
        indicator_aware_envelope_hash="",
        base_envelope_hash="",
        backtest_result_hash="",
        provider_invocation_count=1,
        warmup_skipped_count=3,
        closed_trade_count=0,
        strategy_instance_hash="",
        mtf_input_bundle_hash="",
        controlled_failure=True,
    ),
    "composition-identity-sensitivity": MtfIndicatorGoldenExpectation(
        scenario="composition-identity-sensitivity",
        first_ready_index=3,
        candle_ready_before_indicator=False,
        composition_hash="45e20876acf86c6421cdfd8af97cd7e682ec2edacf2a43e0591c458111c1c7aa",
        provider_visible_hash="",
        execution_decision_view_hash=None,
        context_decision_view_hashes=(),
        indicator_aware_envelope_hash=(
            "a2b113145cc7d39ad1ee6909198321f5d3e7edcadbca2258310791096dceddff"
        ),
        base_envelope_hash="",
        backtest_result_hash="",
        provider_invocation_count=5,
        warmup_skipped_count=3,
        closed_trade_count=1,
        strategy_instance_hash="",
        mtf_input_bundle_hash="",
    ),
}

ALL_MTF_INDICATOR_SCENARIO_NAMES: tuple[str, ...] = tuple(sorted(GOLDENS))

# Frozen alternate composition hashes for scenario F (sensitivity).
F_PERIOD_COMPOSITION_HASH = "d24d89e46f1c4404345847cb603b516251f6ad9c1fc0f55d706b5fdf51036602"
F_CODE_COMPOSITION_HASH = "0ee95434fccd273280d2668934caef12cba43b45b01a88802328c7059691d945"
F_PLACEMENT_COMPOSITION_HASH = "92c82b58003dcd3a33f99716cabc185d649cf35e51cef7476de84468d3ce0809"
F_VALUES_COMPOSITION_HASH = "c38661a49d1a714dd8b3be23a4baac1a759eb651b4ebfb3cd7dd196eb1888a26"
F_SLOT0_COMPOSITION_HASH = "f1ac665ae99a7d7dead6bd3acd63b5ebd9881f626613a408468d6867f1bf9370"
F_SLOT1_COMPOSITION_HASH = "605271c221206bc938b5e666a4f56c3ef314868e5bc5ce2959d7649bbd93ffd3"
F_NONE_VS_INCLUDED_COMPOSITION_HASH = (
    "db5e456824f4bd19e1df8634889d5d5056e3a6eec9fff5bb984bddcf6e0da6ec"
)


def _assert_hashes(
    expectation: MtfIndicatorGoldenExpectation,
    *,
    composition: MultiTimeframeIndicatorInput,
    view_provider_hash: str | None,
    execution_decision_hash: str | None,
    context_hashes: tuple[str | None, ...],
    envelope_hash: str | None,
    base_envelope_hash: str | None,
    result_hash: str | None,
    provider_invocation_count: int | None,
    warmup_skipped_count: int | None,
    closed_trade_count: int | None,
) -> None:
    if composition.indicator_composition_hash != expectation.composition_hash:
        msg = f"{expectation.scenario}: composition_hash mismatch"
        raise MtfIndicatorGoldenMismatchError(msg)
    if (
        expectation.strategy_instance_hash
        and composition.input_bundle.strategy_instance_hash != expectation.strategy_instance_hash
    ):
        msg = f"{expectation.scenario}: strategy_instance_hash mismatch"
        raise MtfIndicatorGoldenMismatchError(msg)
    if expectation.mtf_input_bundle_hash and (
        composition.input_bundle.input_bundle_hash != expectation.mtf_input_bundle_hash
    ):
        msg = f"{expectation.scenario}: mtf_input_bundle_hash mismatch"
        raise MtfIndicatorGoldenMismatchError(msg)
    if (
        view_provider_hash is not None
        and expectation.provider_visible_hash
        and view_provider_hash != expectation.provider_visible_hash
    ):
        msg = f"{expectation.scenario}: provider_visible_hash mismatch"
        raise MtfIndicatorGoldenMismatchError(msg)
    if (
        execution_decision_hash != expectation.execution_decision_view_hash
        and (
            expectation.execution_decision_view_hash is not None
            or execution_decision_hash is not None
        )
        and expectation.scenario != "composition-identity-sensitivity"
    ):
        msg = f"{expectation.scenario}: execution_decision_view_hash mismatch"
        raise MtfIndicatorGoldenMismatchError(msg)
    if expectation.context_decision_view_hashes and (
        context_hashes != expectation.context_decision_view_hashes
    ):
        msg = f"{expectation.scenario}: context_decision_view_hashes mismatch"
        raise MtfIndicatorGoldenMismatchError(msg)
    if (
        envelope_hash is not None
        and expectation.indicator_aware_envelope_hash
        and envelope_hash != expectation.indicator_aware_envelope_hash
    ):
        msg = f"{expectation.scenario}: indicator_aware_envelope_hash mismatch"
        raise MtfIndicatorGoldenMismatchError(msg)
    if (
        base_envelope_hash is not None
        and expectation.base_envelope_hash
        and base_envelope_hash != expectation.base_envelope_hash
    ):
        msg = f"{expectation.scenario}: base_envelope_hash mismatch"
        raise MtfIndicatorGoldenMismatchError(msg)
    if (
        result_hash is not None
        and expectation.backtest_result_hash
        and result_hash != expectation.backtest_result_hash
    ):
        msg = f"{expectation.scenario}: backtest_result_hash mismatch"
        raise MtfIndicatorGoldenMismatchError(msg)
    if (
        provider_invocation_count is not None
        and provider_invocation_count != expectation.provider_invocation_count
    ):
        msg = f"{expectation.scenario}: provider_invocation_count mismatch"
        raise MtfIndicatorGoldenMismatchError(msg)
    if (
        warmup_skipped_count is not None
        and warmup_skipped_count != expectation.warmup_skipped_count
    ):
        msg = f"{expectation.scenario}: warmup_skipped_count mismatch"
        raise MtfIndicatorGoldenMismatchError(msg)
    if closed_trade_count is not None and closed_trade_count != expectation.closed_trade_count:
        msg = f"{expectation.scenario}: closed_trade_count mismatch"
        raise MtfIndicatorGoldenMismatchError(msg)


def _payload(
    *,
    expectation: MtfIndicatorGoldenExpectation,
    composition: MultiTimeframeIndicatorInput,
    first_ready_index: int,
    provider_visible_hash: str | None = None,
    envelope_hash: str | None = None,
) -> dict[str, object]:
    return {
        "ok": True,
        "scenario": expectation.scenario,
        "first_ready_index": first_ready_index,
        "indicator_composition_hash": composition.indicator_composition_hash,
        "provider_visible_indicator_hash": provider_visible_hash,
        "indicator_aware_envelope_hash": envelope_hash,
        "provider_invocation_count": expectation.provider_invocation_count,
        "warmup_skipped_count": expectation.warmup_skipped_count,
        "closed_trade_count": expectation.closed_trade_count,
    }


def run_execution_indicator_warmup() -> dict[str, object]:
    expectation = GOLDENS["execution-indicator-warmup"]
    definition = mtf_definition(
        execution_warmup=4,
        contexts=(TimeframeRequirement(timeframe=Timeframe.H4, warmup_bars=1),),
        definition_code="mtf_ind_exec_warmup",
    )
    execution = build_source_series(start=START, timeframe=Timeframe.H1, count=10)
    context = build_source_series(start=START, timeframe=Timeframe.H4, count=3)
    mtf = _mtf_bundle(
        definition=definition,
        execution=execution,
        contexts=((Timeframe.H4, context),),
    )
    exec_ind = _indicator_bundle(
        candles=execution,
        timeframe=Timeframe.H1,
        builders=(lambda inp: ema_close(inp, 6),),
    )
    composition = MultiTimeframeIndicatorInput.from_verified(
        input_bundle=mtf,
        execution_indicators=exec_ind,
        context_indicators=(None,),
    )
    feed = MultiTimeframeIndicatorDecisionFeed.from_composition(composition)
    candle_ready: int | None = None
    first_ready: int | None = None
    ready_view = None
    for index in range(mtf.execution_candle_count):
        view = feed.view_at(index)
        if candle_ready is None and view.base_view.overall_ready:
            candle_ready = index
            if view.execution_indicators_ready or view.overall_ready:
                msg = "execution-indicator-warmup: candle ready must precede EMA readiness"
                raise MtfIndicatorGoldenMismatchError(msg)
        if view.overall_ready:
            first_ready = index
            ready_view = view
            break
    if first_ready != expectation.first_ready_index:
        msg = "execution-indicator-warmup: first_ready_index mismatch"
        raise MtfIndicatorGoldenMismatchError(msg)
    if candle_ready is None or candle_ready >= first_ready:
        msg = "execution-indicator-warmup: candle readiness must precede composed readiness"
        raise MtfIndicatorGoldenMismatchError(msg)
    assert ready_view is not None
    intent = _enter_long(
        decision_open=execution[first_ready].open_time,
        intent_id="mtf-ind-exec-warmup",
    )
    provider = ScriptedMtfIndicatorProvider(first_ready_intent=(intent,))
    envelope = MultiTimeframeIndicatorBacktestRunner.run(
        composition=composition,
        policy=default_policy(),
        provider=provider,
    )
    if provider.calls[0] != first_ready:
        msg = "execution-indicator-warmup: provider invoked too early"
        raise MtfIndicatorGoldenMismatchError(msg)
    _assert_hashes(
        expectation,
        composition=composition,
        view_provider_hash=ready_view.provider_visible_indicator_hash,
        execution_decision_hash=ready_view.execution_indicator_view.decision_view_hash
        if ready_view.execution_indicator_view is not None
        else None,
        context_hashes=tuple(
            None if slot.indicator_view is None else slot.indicator_view.decision_view_hash
            for slot in ready_view.context_indicator_views
        ),
        envelope_hash=envelope.indicator_aware_envelope_hash,
        base_envelope_hash=envelope.base.envelope_hash,
        result_hash=envelope.base.backtest_result_hash,
        provider_invocation_count=envelope.base.provider_invocation_count,
        warmup_skipped_count=envelope.base.warmup_skipped_decision_count,
        closed_trade_count=envelope.base.result.summary.closed_trade_count,
    )
    return _payload(
        expectation=expectation,
        composition=composition,
        first_ready_index=first_ready,
        provider_visible_hash=ready_view.provider_visible_indicator_hash,
        envelope_hash=envelope.indicator_aware_envelope_hash,
    )


def run_exact_close_context_indicator() -> dict[str, object]:
    expectation = GOLDENS["exact-close-context-indicator"]
    definition = mtf_definition(
        execution_warmup=4,
        contexts=(TimeframeRequirement(timeframe=Timeframe.H4, warmup_bars=1),),
        definition_code="mtf_ind_exact_close",
    )
    execution = build_source_series(start=START, timeframe=Timeframe.H1, count=8)
    context = build_source_series(start=START, timeframe=Timeframe.H4, count=2)
    mtf = _mtf_bundle(
        definition=definition,
        execution=execution,
        contexts=((Timeframe.H4, context),),
    )
    ctx_ind = _indicator_bundle(
        candles=context,
        timeframe=Timeframe.H4,
        builders=(lambda inp: ema_close(inp, 1),),
    )
    composition = MultiTimeframeIndicatorInput.from_verified(
        input_bundle=mtf,
        execution_indicators=None,
        context_indicators=(ctx_ind,),
    )
    feed = MultiTimeframeIndicatorDecisionFeed.from_composition(composition)
    before = feed.view_at(2)
    if before.base_view.contexts[0].latest_closed_index is not None:
        msg = "exact-close-context-indicator: context must be unavailable before exact close"
        raise MtfIndicatorGoldenMismatchError(msg)
    if before.context_indicator_views[0].indicator_view is not None:
        msg = "exact-close-context-indicator: context indicator must be None before close"
        raise MtfIndicatorGoldenMismatchError(msg)
    if before.overall_ready:
        msg = "exact-close-context-indicator: composed view must not be ready before close"
        raise MtfIndicatorGoldenMismatchError(msg)

    ready_view = feed.view_at(3)
    if ready_view.base_view.contexts[0].latest_closed_index != 0:
        msg = "exact-close-context-indicator: latest_closed_index must be 0 at exact close"
        raise MtfIndicatorGoldenMismatchError(msg)
    slot = ready_view.context_indicator_views[0]
    if slot.indicator_view is None or slot.indicator_view.bar_index != 0:
        msg = "exact-close-context-indicator: context indicator must use latest_closed_index"
        raise MtfIndicatorGoldenMismatchError(msg)
    if slot.indicator_view.bar_index == ready_view.base_view.execution_bar_index:
        msg = "exact-close-context-indicator: must not index context by execution bar"
        raise MtfIndicatorGoldenMismatchError(msg)
    if not ready_view.overall_ready:
        msg = "exact-close-context-indicator: must be ready at exact close"
        raise MtfIndicatorGoldenMismatchError(msg)

    intent = _enter_long(decision_open=execution[3].open_time, intent_id="mtf-ind-exact-close")
    provider = ScriptedMtfIndicatorProvider(first_ready_intent=(intent,))
    envelope = MultiTimeframeIndicatorBacktestRunner.run(
        composition=composition,
        policy=default_policy(),
        provider=provider,
    )
    if provider.calls[0] != 3:
        msg = "exact-close-context-indicator: provider first call index mismatch"
        raise MtfIndicatorGoldenMismatchError(msg)
    _assert_hashes(
        expectation,
        composition=composition,
        view_provider_hash=ready_view.provider_visible_indicator_hash,
        execution_decision_hash=None,
        context_hashes=(slot.indicator_view.decision_view_hash,),
        envelope_hash=envelope.indicator_aware_envelope_hash,
        base_envelope_hash=envelope.base.envelope_hash,
        result_hash=envelope.base.backtest_result_hash,
        provider_invocation_count=envelope.base.provider_invocation_count,
        warmup_skipped_count=envelope.base.warmup_skipped_decision_count,
        closed_trade_count=envelope.base.result.summary.closed_trade_count,
    )
    return _payload(
        expectation=expectation,
        composition=composition,
        first_ready_index=3,
        provider_visible_hash=ready_view.provider_visible_indicator_hash,
        envelope_hash=envelope.indicator_aware_envelope_hash,
    )


def run_multiple_indicators_duplicate_codes() -> dict[str, object]:
    expectation = GOLDENS["multiple-indicators-duplicate-codes"]
    definition = mtf_definition(
        execution_warmup=4,
        contexts=(
            TimeframeRequirement(timeframe=Timeframe.H4, warmup_bars=1),
            TimeframeRequirement(timeframe=Timeframe.D1, warmup_bars=1),
        ),
        definition_code="mtf_ind_multi",
    )
    execution = build_source_series(start=START, timeframe=Timeframe.H1, count=24)
    c4 = build_source_series(start=START, timeframe=Timeframe.H4, count=6)
    c1d = build_source_series(start=START, timeframe=Timeframe.D1, count=1)
    mtf = _mtf_bundle(
        definition=definition,
        execution=execution,
        contexts=((Timeframe.H4, c4), (Timeframe.D1, c1d)),
    )
    exec_ind = _indicator_bundle(
        candles=execution,
        timeframe=Timeframe.H1,
        builders=(lambda inp: ema_close(inp, 2), lambda inp: ema_close(inp, 4)),
    )
    atr = _indicator_bundle(
        candles=c4,
        timeframe=Timeframe.H4,
        builders=(lambda inp: wilder_atr(inp, 2),),
    )
    extrema = _indicator_bundle(
        candles=c1d,
        timeframe=Timeframe.D1,
        builders=(
            lambda inp: rolling_highest(inp, 1),
            lambda inp: rolling_lowest(inp, 1),
        ),
    )
    composition = MultiTimeframeIndicatorInput.from_verified(
        input_bundle=mtf,
        execution_indicators=exec_ind,
        context_indicators=(atr, extrema),
    )
    feed = MultiTimeframeIndicatorDecisionFeed.from_composition(composition)
    first_ready: int | None = None
    ready_view = None
    for index in range(mtf.execution_candle_count):
        view = feed.view_at(index)
        if view.overall_ready:
            first_ready = index
            ready_view = view
            break
    if first_ready != expectation.first_ready_index or ready_view is None:
        msg = "multiple-indicators-duplicate-codes: first_ready_index mismatch"
        raise MtfIndicatorGoldenMismatchError(msg)
    assert ready_view.execution_indicator_view is not None
    period_2 = ready_view.execution_indicator_view.require(IndicatorCode.EMA_CLOSE, period=2)
    period_4 = ready_view.execution_indicator_view.require(IndicatorCode.EMA_CLOSE, period=4)
    if period_2.series_key.parameters != (("period", 2),):
        msg = "multiple-indicators-duplicate-codes: EMA period 2 lookup failed"
        raise MtfIndicatorGoldenMismatchError(msg)
    if period_4.series_key.parameters != (("period", 4),):
        msg = "multiple-indicators-duplicate-codes: EMA period 4 lookup failed"
        raise MtfIndicatorGoldenMismatchError(msg)
    codes = [item.indicator_code.value for item in ready_view.execution_indicator_view.items]
    if codes != ["ema_close", "ema_close"]:
        msg = "multiple-indicators-duplicate-codes: canonical EMA ordering mismatch"
        raise MtfIndicatorGoldenMismatchError(msg)

    intent = _enter_long(
        decision_open=execution[first_ready].open_time,
        intent_id="mtf-ind-multi",
    )
    provider = ScriptedMtfIndicatorProvider(first_ready_intent=(intent,))
    envelope = MultiTimeframeIndicatorBacktestRunner.run(
        composition=composition,
        policy=default_policy(),
        provider=provider,
    )
    _assert_hashes(
        expectation,
        composition=composition,
        view_provider_hash=ready_view.provider_visible_indicator_hash,
        execution_decision_hash=ready_view.execution_indicator_view.decision_view_hash,
        context_hashes=tuple(
            None if slot.indicator_view is None else slot.indicator_view.decision_view_hash
            for slot in ready_view.context_indicator_views
        ),
        envelope_hash=envelope.indicator_aware_envelope_hash,
        base_envelope_hash=envelope.base.envelope_hash,
        result_hash=envelope.base.backtest_result_hash,
        provider_invocation_count=envelope.base.provider_invocation_count,
        warmup_skipped_count=envelope.base.warmup_skipped_decision_count,
        closed_trade_count=envelope.base.result.summary.closed_trade_count,
    )
    return _payload(
        expectation=expectation,
        composition=composition,
        first_ready_index=first_ready,
        provider_visible_hash=ready_view.provider_visible_indicator_hash,
        envelope_hash=envelope.indicator_aware_envelope_hash,
    )


def run_optional_indicator_slots() -> dict[str, object]:
    expectation = GOLDENS["optional-indicator-slots"]
    definition = mtf_definition(
        execution_warmup=4,
        contexts=(
            TimeframeRequirement(timeframe=Timeframe.H4, warmup_bars=1),
            TimeframeRequirement(timeframe=Timeframe.D1, warmup_bars=1),
        ),
        definition_code="mtf_ind_optional",
    )
    execution = build_source_series(start=START, timeframe=Timeframe.H1, count=24)
    c4 = build_source_series(start=START, timeframe=Timeframe.H4, count=6)
    c1d = build_source_series(start=START, timeframe=Timeframe.D1, count=1)
    mtf = _mtf_bundle(
        definition=definition,
        execution=execution,
        contexts=((Timeframe.H4, c4), (Timeframe.D1, c1d)),
    )
    atr = _indicator_bundle(
        candles=c4,
        timeframe=Timeframe.H4,
        builders=(lambda inp: wilder_atr(inp, 2),),
    )
    composition = MultiTimeframeIndicatorInput.from_verified(
        input_bundle=mtf,
        execution_indicators=None,
        context_indicators=(atr, None),
    )
    feed = MultiTimeframeIndicatorDecisionFeed.from_composition(composition)
    # Before ATR is defined on the first closed H4 bar, configured slot blocks.
    early = feed.view_at(3)
    if early.base_view.contexts[0].latest_closed_index != 0:
        msg = "optional-indicator-slots: expected first H4 close at execution bar 3"
        raise MtfIndicatorGoldenMismatchError(msg)
    if early.context_indicator_views[0].ready:
        msg = "optional-indicator-slots: ATR period 2 must block at first H4 bar"
        raise MtfIndicatorGoldenMismatchError(msg)
    if not early.context_indicator_views[1].ready:
        msg = "optional-indicator-slots: unconfigured slot must not block"
        raise MtfIndicatorGoldenMismatchError(msg)
    if early.overall_ready:
        msg = "optional-indicator-slots: configured ATR must block overall readiness"
        raise MtfIndicatorGoldenMismatchError(msg)

    first_ready: int | None = None
    ready_view = None
    for index in range(mtf.execution_candle_count):
        view = feed.view_at(index)
        if view.overall_ready:
            first_ready = index
            ready_view = view
            break
    if first_ready != expectation.first_ready_index or ready_view is None:
        msg = "optional-indicator-slots: first_ready_index mismatch"
        raise MtfIndicatorGoldenMismatchError(msg)
    if ready_view.execution_indicator_view is not None:
        msg = "optional-indicator-slots: execution indicators must be unconfigured"
        raise MtfIndicatorGoldenMismatchError(msg)
    if ready_view.context_indicator_views[1].configured:
        msg = "optional-indicator-slots: second context must remain unconfigured"
        raise MtfIndicatorGoldenMismatchError(msg)

    intent = _enter_long(
        decision_open=execution[first_ready].open_time,
        intent_id="mtf-ind-optional",
    )
    provider = ScriptedMtfIndicatorProvider(first_ready_intent=(intent,))
    envelope = MultiTimeframeIndicatorBacktestRunner.run(
        composition=composition,
        policy=default_policy(),
        provider=provider,
    )
    _assert_hashes(
        expectation,
        composition=composition,
        view_provider_hash=ready_view.provider_visible_indicator_hash,
        execution_decision_hash=None,
        context_hashes=tuple(
            None if slot.indicator_view is None else slot.indicator_view.decision_view_hash
            for slot in ready_view.context_indicator_views
        ),
        envelope_hash=envelope.indicator_aware_envelope_hash,
        base_envelope_hash=envelope.base.envelope_hash,
        result_hash=envelope.base.backtest_result_hash,
        provider_invocation_count=envelope.base.provider_invocation_count,
        warmup_skipped_count=envelope.base.warmup_skipped_decision_count,
        closed_trade_count=envelope.base.result.summary.closed_trade_count,
    )
    return _payload(
        expectation=expectation,
        composition=composition,
        first_ready_index=first_ready,
        provider_visible_hash=ready_view.provider_visible_indicator_hash,
        envelope_hash=envelope.indicator_aware_envelope_hash,
    )


def run_direction_restriction() -> dict[str, object]:
    expectation = GOLDENS["direction-restriction"]
    definition = mtf_definition(
        execution_warmup=4,
        contexts=(TimeframeRequirement(timeframe=Timeframe.H4, warmup_bars=1),),
        directions=(PositionDirection.LONG,),
        definition_code="mtf_ind_long_only",
    )
    execution = build_source_series(start=START, timeframe=Timeframe.H1, count=8)
    context = build_source_series(start=START, timeframe=Timeframe.H4, count=2)
    mtf = _mtf_bundle(
        definition=definition,
        execution=execution,
        contexts=((Timeframe.H4, context),),
    )
    exec_ind = _indicator_bundle(
        candles=execution,
        timeframe=Timeframe.H1,
        builders=(lambda inp: ema_close(inp, 1),),
    )
    composition = MultiTimeframeIndicatorInput.from_verified(
        input_bundle=mtf,
        execution_indicators=exec_ind,
        context_indicators=(None,),
    )
    feed = MultiTimeframeIndicatorDecisionFeed.from_composition(composition)
    ready_view = feed.view_at(expectation.first_ready_index)
    if not ready_view.overall_ready:
        msg = "direction-restriction: composed view must be ready before failure"
        raise MtfIndicatorGoldenMismatchError(msg)
    if composition.indicator_composition_hash != expectation.composition_hash:
        msg = "direction-restriction: composition_hash mismatch"
        raise MtfIndicatorGoldenMismatchError(msg)
    if ready_view.provider_visible_indicator_hash != expectation.provider_visible_hash:
        msg = "direction-restriction: provider_visible_hash mismatch"
        raise MtfIndicatorGoldenMismatchError(msg)
    assert ready_view.execution_indicator_view is not None
    if (
        ready_view.execution_indicator_view.decision_view_hash
        != expectation.execution_decision_view_hash
    ):
        msg = "direction-restriction: execution_decision_view_hash mismatch"
        raise MtfIndicatorGoldenMismatchError(msg)

    intent = _enter_short(
        decision_open=execution[expectation.first_ready_index].open_time,
        intent_id="mtf-ind-direction",
    )
    provider = ScriptedMtfIndicatorProvider(first_ready_intent=(intent,))
    try:
        MultiTimeframeIndicatorBacktestRunner.run(
            composition=composition,
            policy=default_policy(),
            provider=provider,
        )
    except BacktestExecutionError as exc:
        if "Decision provider failed" not in str(exc):
            msg = "direction-restriction: public exception must be sanitized engine error"
            raise MtfIndicatorGoldenMismatchError(msg) from exc
        if not _cause_chain_has_unsupported_direction(exc):
            msg = "direction-restriction: cause chain missing unsupported-direction failure"
            raise MtfIndicatorGoldenMismatchError(msg) from exc
        if provider.calls != [expectation.first_ready_index]:
            msg = "direction-restriction: provider must be called once at first ready bar"
            raise MtfIndicatorGoldenMismatchError(msg) from exc
        return {
            "ok": True,
            "scenario": expectation.scenario,
            "controlled_failure": True,
            "first_ready_index": expectation.first_ready_index,
            "provider_invocation_count": len(provider.calls),
            "error_code": "unsupported_direction",
            "indicator_composition_hash": composition.indicator_composition_hash,
            "closed_trade_count": 0,
        }
    msg = "direction-restriction: expected controlled failure with no result envelope"
    raise MtfIndicatorGoldenMismatchError(msg)


def run_composition_identity_sensitivity() -> dict[str, object]:
    expectation = GOLDENS["composition-identity-sensitivity"]
    definition = mtf_definition(
        execution_warmup=4,
        contexts=(TimeframeRequirement(timeframe=Timeframe.H4, warmup_bars=1),),
        definition_code="mtf_ind_sensitivity",
    )
    execution = build_source_series(start=START, timeframe=Timeframe.H1, count=8)
    context = build_source_series(start=START, timeframe=Timeframe.H4, count=2)
    mtf = _mtf_bundle(
        definition=definition,
        execution=execution,
        contexts=((Timeframe.H4, context),),
    )
    baseline_exec = _indicator_bundle(
        candles=execution,
        timeframe=Timeframe.H1,
        builders=(lambda inp: ema_close(inp, 4),),
    )
    baseline = MultiTimeframeIndicatorInput.from_verified(
        input_bundle=mtf,
        execution_indicators=baseline_exec,
        context_indicators=(None,),
    )
    intent = _enter_long(decision_open=execution[3].open_time, intent_id="mtf-ind-sensitivity")
    env_baseline = MultiTimeframeIndicatorBacktestRunner.run(
        composition=baseline,
        policy=default_policy(),
        provider=ScriptedMtfIndicatorProvider(first_ready_intent=(intent,)),
    )
    if baseline.indicator_composition_hash != expectation.composition_hash:
        msg = "composition-identity-sensitivity: baseline composition_hash mismatch"
        raise MtfIndicatorGoldenMismatchError(msg)
    if env_baseline.indicator_aware_envelope_hash != expectation.indicator_aware_envelope_hash:
        msg = "composition-identity-sensitivity: baseline envelope_hash mismatch"
        raise MtfIndicatorGoldenMismatchError(msg)

    period_change = MultiTimeframeIndicatorInput.from_verified(
        input_bundle=mtf,
        execution_indicators=_indicator_bundle(
            candles=execution,
            timeframe=Timeframe.H1,
            builders=(lambda inp: ema_close(inp, 3),),
        ),
        context_indicators=(None,),
    )
    code_change = MultiTimeframeIndicatorInput.from_verified(
        input_bundle=mtf,
        execution_indicators=_indicator_bundle(
            candles=execution,
            timeframe=Timeframe.H1,
            builders=(lambda inp: wilder_atr(inp, 4),),
        ),
        context_indicators=(None,),
    )
    placement = MultiTimeframeIndicatorInput.from_verified(
        input_bundle=mtf,
        execution_indicators=None,
        context_indicators=(
            _indicator_bundle(
                candles=context,
                timeframe=Timeframe.H4,
                builders=(lambda inp: ema_close(inp, 4),),
            ),
        ),
    )
    tweaked = list(context)
    tweaked[0] = make_candle(
        tweaked[0].open_time,
        timeframe=Timeframe.H4,
        open=Decimal("999"),
        high=Decimal("1000"),
        low=Decimal("998"),
        close=Decimal("999.5"),
        volume=Decimal("9"),
        quote_asset_volume=Decimal("90"),
        trade_count=9,
        taker_buy_base_volume=Decimal("0.5"),
        taker_buy_quote_volume=Decimal("5"),
    )
    context_b = tuple(tweaked)
    mtf_b = _mtf_bundle(
        definition=definition,
        execution=execution,
        contexts=((Timeframe.H4, context_b),),
    )
    values_change = MultiTimeframeIndicatorInput.from_verified(
        input_bundle=mtf_b,
        execution_indicators=_indicator_bundle(
            candles=execution,
            timeframe=Timeframe.H1,
            builders=(lambda inp: ema_close(inp, 4),),
        ),
        context_indicators=(None,),
    )
    none_vs = MultiTimeframeIndicatorInput.from_verified(
        input_bundle=mtf,
        execution_indicators=None,
        context_indicators=(
            _indicator_bundle(
                candles=context,
                timeframe=Timeframe.H4,
                builders=(lambda inp: ema_close(inp, 1),),
            ),
        ),
    )

    definition2 = mtf_definition(
        execution_warmup=4,
        contexts=(
            TimeframeRequirement(timeframe=Timeframe.H4, warmup_bars=1),
            TimeframeRequirement(timeframe=Timeframe.D1, warmup_bars=1),
        ),
        definition_code="mtf_ind_slot",
    )
    execution2 = build_source_series(start=START, timeframe=Timeframe.H1, count=24)
    c4 = build_source_series(start=START, timeframe=Timeframe.H4, count=6)
    c1d = build_source_series(start=START, timeframe=Timeframe.D1, count=1)
    mtf2 = _mtf_bundle(
        definition=definition2,
        execution=execution2,
        contexts=((Timeframe.H4, c4), (Timeframe.D1, c1d)),
    )
    slot0 = MultiTimeframeIndicatorInput.from_verified(
        input_bundle=mtf2,
        execution_indicators=None,
        context_indicators=(
            _indicator_bundle(
                candles=c4,
                timeframe=Timeframe.H4,
                builders=(lambda inp: wilder_atr(inp, 2),),
            ),
            None,
        ),
    )
    slot1 = MultiTimeframeIndicatorInput.from_verified(
        input_bundle=mtf2,
        execution_indicators=None,
        context_indicators=(
            None,
            _indicator_bundle(
                candles=c1d,
                timeframe=Timeframe.D1,
                builders=(lambda inp: rolling_highest(inp, 1),),
            ),
        ),
    )

    checks = (
        (period_change.indicator_composition_hash, F_PERIOD_COMPOSITION_HASH, "period"),
        (code_change.indicator_composition_hash, F_CODE_COMPOSITION_HASH, "code"),
        (placement.indicator_composition_hash, F_PLACEMENT_COMPOSITION_HASH, "placement"),
        (values_change.indicator_composition_hash, F_VALUES_COMPOSITION_HASH, "values"),
        (slot0.indicator_composition_hash, F_SLOT0_COMPOSITION_HASH, "slot0"),
        (slot1.indicator_composition_hash, F_SLOT1_COMPOSITION_HASH, "slot1"),
        (
            none_vs.indicator_composition_hash,
            F_NONE_VS_INCLUDED_COMPOSITION_HASH,
            "none_vs_included",
        ),
    )
    for actual, expected, label in checks:
        if actual != expected:
            msg = f"composition-identity-sensitivity: {label} composition_hash mismatch"
            raise MtfIndicatorGoldenMismatchError(msg)
        if actual == baseline.indicator_composition_hash:
            msg = f"composition-identity-sensitivity: {label} must change composition hash"
            raise MtfIndicatorGoldenMismatchError(msg)
    if slot0.indicator_composition_hash == slot1.indicator_composition_hash:
        msg = "composition-identity-sensitivity: context slot placement must change hash"
        raise MtfIndicatorGoldenMismatchError(msg)

    env_period = MultiTimeframeIndicatorBacktestRunner.run(
        composition=period_change,
        policy=default_policy(),
        provider=ScriptedMtfIndicatorProvider(first_ready_intent=(intent,)),
    )
    if env_period.indicator_aware_envelope_hash == env_baseline.indicator_aware_envelope_hash:
        msg = "composition-identity-sensitivity: envelope hash must change with period"
        raise MtfIndicatorGoldenMismatchError(msg)

    return {
        "ok": True,
        "scenario": expectation.scenario,
        "indicator_composition_hash": baseline.indicator_composition_hash,
        "indicator_aware_envelope_hash": env_baseline.indicator_aware_envelope_hash,
        "altered_period_composition_hash": period_change.indicator_composition_hash,
        "altered_code_composition_hash": code_change.indicator_composition_hash,
        "altered_placement_composition_hash": placement.indicator_composition_hash,
        "altered_values_composition_hash": values_change.indicator_composition_hash,
        "altered_slot0_composition_hash": slot0.indicator_composition_hash,
        "altered_slot1_composition_hash": slot1.indicator_composition_hash,
        "altered_none_vs_composition_hash": none_vs.indicator_composition_hash,
        "provider_invocation_count": env_baseline.base.provider_invocation_count,
        "warmup_skipped_count": env_baseline.base.warmup_skipped_decision_count,
        "closed_trade_count": env_baseline.base.result.summary.closed_trade_count,
    }


def run_mtf_indicator_scenario(name: str) -> dict[str, object]:
    if name == "execution-indicator-warmup":
        return run_execution_indicator_warmup()
    if name == "exact-close-context-indicator":
        return run_exact_close_context_indicator()
    if name == "multiple-indicators-duplicate-codes":
        return run_multiple_indicators_duplicate_codes()
    if name == "optional-indicator-slots":
        return run_optional_indicator_slots()
    if name == "direction-restriction":
        return run_direction_restriction()
    if name == "composition-identity-sensitivity":
        return run_composition_identity_sensitivity()
    raise KeyError(name)
