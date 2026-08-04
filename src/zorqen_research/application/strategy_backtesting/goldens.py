"""Frozen multi-timeframe backtest bridge golden scenarios.

Literal expected hashes only — do not derive golden hashes by invoking the
production runner at module import time.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from zorqen_research.application.backtesting.golden import default_policy
from zorqen_research.application.market_data.goldens import build_source_series, make_candle
from zorqen_research.application.strategy_backtesting.feed import MultiTimeframeDecisionFeed
from zorqen_research.application.strategy_backtesting.provider import (
    MultiTimeframeBacktestDecisionContext,
)
from zorqen_research.application.strategy_backtesting.runner import MultiTimeframeBacktestRunner
from zorqen_research.application.strategy_definitions.serialization import build_instance
from zorqen_research.domain.backtesting.enums import PositionDirection
from zorqen_research.domain.backtesting.errors import (
    BacktestExecutionError,
    BacktestValidationError,
)
from zorqen_research.domain.backtesting.intents import BacktestIntent, EnterIntent
from zorqen_research.domain.backtesting.policy import BacktestPolicy
from zorqen_research.domain.candles import Candle
from zorqen_research.domain.strategy_backtesting.inputs import MultiTimeframeBacktestInput
from zorqen_research.domain.strategy_backtesting.results import StrategyBacktestEnvelope
from zorqen_research.domain.strategy_definitions.definitions import StrategyDefinition
from zorqen_research.domain.strategy_definitions.enums import DefinitionStatus
from zorqen_research.domain.strategy_definitions.parameters import IntegerParameterDefinition
from zorqen_research.domain.strategy_definitions.timeframes import TimeframeRequirement
from zorqen_research.domain.strategy_families import (
    ADAPTIVE_MTF_TREND_BREAKOUT_CODE,
    ADAPTIVE_MTF_TREND_BREAKOUT_ID,
)
from zorqen_research.domain.symbols import Symbol
from zorqen_research.domain.timeframes import Timeframe

SYMBOL = Symbol(value="BTCUSDT")
START = datetime(2024, 1, 1, tzinfo=UTC)


def mtf_definition(
    *,
    execution_warmup: int,
    contexts: tuple[TimeframeRequirement, ...],
    directions: tuple[PositionDirection, ...] = (PositionDirection.LONG, PositionDirection.SHORT),
    definition_code: str = "mtf_bridge_golden",
    param_default: int = 1,
) -> StrategyDefinition:
    return StrategyDefinition(
        schema_version="1",
        definition_id=UUID("22222222-2222-4222-8222-222222222222"),
        family_id=ADAPTIVE_MTF_TREND_BREAKOUT_ID,
        family_code=ADAPTIVE_MTF_TREND_BREAKOUT_CODE,
        definition_code=definition_code,
        display_name="MTF Bridge Golden",
        description="Test-only multi-timeframe bridge definition.",
        version="0.1.0",
        status=DefinitionStatus.DRAFT,
        execution_timeframe=Timeframe.H1,
        execution_warmup_bars=execution_warmup,
        context_requirements=contexts,
        supported_directions=directions,
        parameters=(
            IntegerParameterDefinition(
                key="signal_strength",
                display_name="Signal Strength",
                description="Golden-only integer parameter",
                researchable=False,
                default_value=param_default,
                minimum=1,
                maximum=10,
                step=1,
            ),
        ),
        source_spec_sha256=None,
    )


class ScriptedMtfProvider:
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
        context: MultiTimeframeBacktestDecisionContext,
    ) -> tuple[BacktestIntent, ...]:
        self.calls.append(context.view.execution_bar_index)
        if context.view.execution_bar_index in self._by_bar:
            return self._by_bar[context.view.execution_bar_index]
        if self._first_ready is not None and not self._emitted_first:
            self._emitted_first = True
            return self._first_ready
        return ()


@dataclass(frozen=True, slots=True)
class MtfGoldenExpectation:
    scenario: str
    strategy_instance_hash: str
    input_bundle_hash: str
    execution_candle_hash: str
    alignment_hash: str
    backtest_result_hash: str
    envelope_hash: str
    provider_invocation_count: int
    warmup_skipped_count: int
    closed_trade_count: int
    first_ready_index: int | None = None
    context_visible_counts_at_ready: tuple[int, ...] | None = None
    controlled_failure: bool = False
    # Context sensitivity extras
    altered_context_hash: str | None = None
    altered_bundle_hash: str | None = None
    altered_envelope_hash: str | None = None


class MtfGoldenMismatchError(Exception):
    """Golden expectation mismatch."""


def _enter_long(*, decision_open: datetime, intent_id: str) -> EnterIntent:
    return EnterIntent(
        intent_id=intent_id,
        decision_open_time=decision_open,
        direction=PositionDirection.LONG,
        quantity=Decimal("1.000"),
        stop_loss=Decimal("50"),
        take_profit=Decimal("200"),
        label="mtf-long",
    )


def _enter_short(*, decision_open: datetime, intent_id: str) -> EnterIntent:
    return EnterIntent(
        intent_id=intent_id,
        decision_open_time=decision_open,
        direction=PositionDirection.SHORT,
        quantity=Decimal("1.000"),
        stop_loss=Decimal("200"),
        take_profit=Decimal("50"),
        label="mtf-short",
    )


def _run_envelope(
    *,
    definition: StrategyDefinition,
    execution: tuple[Candle, ...],
    contexts: tuple[tuple[Timeframe, tuple[Candle, ...]], ...],
    provider: ScriptedMtfProvider,
    policy: BacktestPolicy | None = None,
    signal_strength: int = 1,
) -> tuple[MultiTimeframeBacktestInput, StrategyBacktestEnvelope]:
    instance = build_instance(definition, {"signal_strength": signal_strength})
    bundle = MultiTimeframeBacktestInput.from_verified(
        strategy_instance=instance,
        symbol=SYMBOL,
        execution_candles=execution,
        context_series=contexts,
    )
    envelope = MultiTimeframeBacktestRunner.run(
        input_bundle=bundle,
        policy=policy or default_policy(),
        provider=provider,
    )
    return bundle, envelope


def _payload(
    *,
    expectation: MtfGoldenExpectation,
    bundle: MultiTimeframeBacktestInput,
    envelope: StrategyBacktestEnvelope,
) -> dict[str, object]:
    return {
        "ok": True,
        "scenario": expectation.scenario,
        "strategy_instance_hash": bundle.strategy_instance_hash,
        "input_bundle_hash": bundle.input_bundle_hash,
        "execution_candle_hash": bundle.execution_candle_sha256,
        "alignment_hash": bundle.multi_context_alignment.alignment_hash,
        "backtest_result_hash": envelope.backtest_result_hash,
        "envelope_hash": envelope.envelope_hash,
        "provider_invocation_count": envelope.provider_invocation_count,
        "warmup_skipped_count": envelope.warmup_skipped_decision_count,
        "closed_trade_count": envelope.result.summary.closed_trade_count,
    }


def _assert_envelope(
    expectation: MtfGoldenExpectation,
    bundle: MultiTimeframeBacktestInput,
    envelope: StrategyBacktestEnvelope,
) -> dict[str, object]:
    checks = (
        (
            bundle.strategy_instance_hash,
            expectation.strategy_instance_hash,
            "strategy_instance_hash",
        ),
        (bundle.input_bundle_hash, expectation.input_bundle_hash, "input_bundle_hash"),
        (
            bundle.execution_candle_sha256,
            expectation.execution_candle_hash,
            "execution_candle_hash",
        ),
        (
            bundle.multi_context_alignment.alignment_hash,
            expectation.alignment_hash,
            "alignment_hash",
        ),
        (envelope.backtest_result_hash, expectation.backtest_result_hash, "backtest_result_hash"),
        (envelope.envelope_hash, expectation.envelope_hash, "envelope_hash"),
        (
            envelope.provider_invocation_count,
            expectation.provider_invocation_count,
            "provider_invocation_count",
        ),
        (
            envelope.warmup_skipped_decision_count,
            expectation.warmup_skipped_count,
            "warmup_skipped_count",
        ),
        (
            envelope.result.summary.closed_trade_count,
            expectation.closed_trade_count,
            "closed_trade_count",
        ),
    )
    for actual, expected, label in checks:
        if actual != expected:
            msg = f"{expectation.scenario}: {label} mismatch"
            raise MtfGoldenMismatchError(msg)
    return _payload(expectation=expectation, bundle=bundle, envelope=envelope)


MTF_GOLDENS: dict[str, MtfGoldenExpectation] = {
    "exact-close-readiness": MtfGoldenExpectation(
        scenario="exact-close-readiness",
        strategy_instance_hash="4787e5aed25fc47e1d1d1068de1beb919b94d809f2cb2b7d604625641db324d1",
        input_bundle_hash="1ef63eff5e42d00d2d3edabbc849a3f1f651929c3ba52abbc08fd64497794167",
        execution_candle_hash="43077aac3637c792ac96df9c2441d08b9a5af09b861b0318d8e60a152aead315",
        alignment_hash="7fb35c893491d96770e2e2beb3c8082bfe74b6c3389db3f4a6ea990a78700a7a",
        backtest_result_hash="966418dd3fb45a8695b171d4cfca92029f94dd7cb208178761002d62f65a0b19",
        envelope_hash="8e5259d68e152ee3c1b0767ec372866ddcbb8b67eeae96175345e2512879b70d",
        provider_invocation_count=5,
        warmup_skipped_count=3,
        closed_trade_count=1,
        first_ready_index=3,
        context_visible_counts_at_ready=(1,),
    ),
    "context-unavailable": MtfGoldenExpectation(
        scenario="context-unavailable",
        strategy_instance_hash="1f46f741225b377c0e825357a3651f7205fd3c20ecf1771116bb3894bd264224",
        input_bundle_hash="2033a31ab9a1d33a15a29ff6cebd178198ffc681855302937c69d6e2e1dc020b",
        execution_candle_hash="744cad7a2f105d58cbaa7bdaf079dc4859b83fc454816e09b395a8c90fef2da9",
        alignment_hash="2a0f96ef8ded73ef65dd161f60eb414967f3e92e26bb59c072a1f900bf4d64d7",
        backtest_result_hash="e2a8ead750c260d1a687c5dc28f1622969fc4f811909d6c89c429b0c6408dde1",
        envelope_hash="908c85b8bdfd7d76ac7bcc3d5ba7ddf452e366971c6245a346b590afb2732737",
        provider_invocation_count=0,
        warmup_skipped_count=3,
        closed_trade_count=0,
    ),
    "two-contexts": MtfGoldenExpectation(
        scenario="two-contexts",
        strategy_instance_hash="c5af63d423e7ecda825b2ec419c88d2b7ac2b2aca406b77a1cbb5523d52d29ab",
        input_bundle_hash="3f4bf5675a65362736c1a98ae190e843272a6778afcb0830dfb65c1ac605152b",
        execution_candle_hash="12ad15d6cf957b337720019aa4766687fb643e163394b001621c5c0d38f96abd",
        alignment_hash="1ced7609616bfc7e79039cd8ac9cbead378c7feffbeeec5db4bda3b7174f48ac",
        backtest_result_hash="57205bfc878dc07b5e092aeb97c1eabb8770a29f1988fba8937efef8e9249826",
        envelope_hash="c0945d5d2609c958a2cdae155e65606e59233a6fc6c03ec6906bc8065bfa0d94",
        provider_invocation_count=1,
        warmup_skipped_count=23,
        closed_trade_count=0,
        first_ready_index=23,
        context_visible_counts_at_ready=(6, 1),
    ),
    "direction-restriction": MtfGoldenExpectation(
        scenario="direction-restriction",
        strategy_instance_hash="",
        input_bundle_hash="",
        execution_candle_hash="",
        alignment_hash="",
        backtest_result_hash="",
        envelope_hash="",
        provider_invocation_count=1,
        warmup_skipped_count=3,
        closed_trade_count=0,
        first_ready_index=3,
        controlled_failure=True,
    ),
    "context-sensitivity": MtfGoldenExpectation(
        scenario="context-sensitivity",
        strategy_instance_hash="9903057ca2105cbbb47a06e824ba9e4e7e818bb4431ff9cbe956174f6b0bd9c6",
        input_bundle_hash="62d87377e7d20355a59cda3555c50b86dda889f3dc3a6fe7b0b73e1d2f013b3b",
        execution_candle_hash="43077aac3637c792ac96df9c2441d08b9a5af09b861b0318d8e60a152aead315",
        alignment_hash="7fb35c893491d96770e2e2beb3c8082bfe74b6c3389db3f4a6ea990a78700a7a",
        backtest_result_hash="4dd3b3988f646ab53e6569d62c90426011b89a05317d7cf2c7b3800a6a625391",
        envelope_hash="e64fcdc08370513239c1b78c2b1b9b1b9541841de6d281c9765b605eabbbb982",
        provider_invocation_count=5,
        warmup_skipped_count=3,
        closed_trade_count=1,
        altered_context_hash="7c164b94a2d9b99a75b34979f13fc90b64b6efd6dd76afc9957d3e98d6ec9214",
        altered_bundle_hash="1a107a395a4d45408ae6bd90699539e9b1faec6f92838434560c839c101a78d9",
        altered_envelope_hash="3e20e4bcc1286dbc788c450ae83e843571d79a1908bdbc8488a925338c7ebcbb",
    ),
}

ALL_MTF_SCENARIO_NAMES: tuple[str, ...] = tuple(sorted(MTF_GOLDENS))


def run_exact_close_readiness() -> dict[str, object]:
    expectation = MTF_GOLDENS["exact-close-readiness"]
    definition = mtf_definition(
        execution_warmup=4,
        contexts=(TimeframeRequirement(timeframe=Timeframe.H4, warmup_bars=1),),
        definition_code="mtf_exact_close",
    )
    execution = build_source_series(start=START, timeframe=Timeframe.H1, count=8)
    context = build_source_series(start=START, timeframe=Timeframe.H4, count=2)
    intent = _enter_long(decision_open=execution[3].open_time, intent_id="mtf-exact-close")
    provider = ScriptedMtfProvider(first_ready_intent=(intent,))
    bundle, envelope = _run_envelope(
        definition=definition,
        execution=execution,
        contexts=((Timeframe.H4, context),),
        provider=provider,
    )
    feed = MultiTimeframeDecisionFeed.from_input(bundle)
    view = feed.view_at(3)
    if expectation.first_ready_index != 3 or not view.overall_ready:
        msg = "exact-close-readiness: first ready index mismatch"
        raise MtfGoldenMismatchError(msg)
    if tuple(item.visible_count for item in view.contexts) != (1,):
        msg = "exact-close-readiness: context visible counts mismatch"
        raise MtfGoldenMismatchError(msg)
    if provider.calls[0] != 3:
        msg = "exact-close-readiness: provider called too early"
        raise MtfGoldenMismatchError(msg)
    return _assert_envelope(expectation, bundle, envelope)


def run_context_unavailable() -> dict[str, object]:
    expectation = MTF_GOLDENS["context-unavailable"]
    definition = mtf_definition(
        execution_warmup=1,
        contexts=(TimeframeRequirement(timeframe=Timeframe.H4, warmup_bars=1),),
        definition_code="mtf_context_unavailable",
    )
    execution = build_source_series(start=START, timeframe=Timeframe.H1, count=3)
    context = build_source_series(start=START, timeframe=Timeframe.H4, count=1)
    provider = ScriptedMtfProvider()
    bundle, envelope = _run_envelope(
        definition=definition,
        execution=execution,
        contexts=((Timeframe.H4, context),),
        provider=provider,
    )
    if provider.calls:
        msg = "context-unavailable: provider must not be invoked"
        raise MtfGoldenMismatchError(msg)
    return _assert_envelope(expectation, bundle, envelope)


def run_two_contexts() -> dict[str, object]:
    expectation = MTF_GOLDENS["two-contexts"]
    definition = mtf_definition(
        execution_warmup=4,
        contexts=(
            TimeframeRequirement(timeframe=Timeframe.H4, warmup_bars=1),
            TimeframeRequirement(timeframe=Timeframe.D1, warmup_bars=1),
        ),
        definition_code="mtf_two_contexts",
    )
    execution = build_source_series(start=START, timeframe=Timeframe.H1, count=24)
    c4 = build_source_series(start=START, timeframe=Timeframe.H4, count=6)
    c1d = build_source_series(start=START, timeframe=Timeframe.D1, count=1)
    intent = _enter_long(decision_open=execution[23].open_time, intent_id="mtf-two-ctx")
    provider = ScriptedMtfProvider(first_ready_intent=(intent,))
    bundle, envelope = _run_envelope(
        definition=definition,
        execution=execution,
        contexts=((Timeframe.H4, c4), (Timeframe.D1, c1d)),
        provider=provider,
    )
    feed = MultiTimeframeDecisionFeed.from_input(bundle)
    first_ready: int | None = None
    visible: tuple[int, ...] | None = None
    for index in range(bundle.execution_candle_count):
        view = feed.view_at(index)
        if view.overall_ready:
            first_ready = index
            visible = tuple(item.visible_count for item in view.contexts)
            break
    if first_ready != expectation.first_ready_index:
        msg = "two-contexts: first ready index mismatch"
        raise MtfGoldenMismatchError(msg)
    if visible != expectation.context_visible_counts_at_ready:
        msg = "two-contexts: context visible counts mismatch"
        raise MtfGoldenMismatchError(msg)
    return _assert_envelope(expectation, bundle, envelope)


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


def run_direction_restriction() -> dict[str, object]:
    expectation = MTF_GOLDENS["direction-restriction"]
    definition = mtf_definition(
        execution_warmup=4,
        contexts=(TimeframeRequirement(timeframe=Timeframe.H4, warmup_bars=1),),
        directions=(PositionDirection.LONG,),
        definition_code="mtf_long_only",
    )
    if definition.supported_directions != (PositionDirection.LONG,):
        msg = "direction-restriction: definition must be long-only"
        raise MtfGoldenMismatchError(msg)
    execution = build_source_series(start=START, timeframe=Timeframe.H1, count=8)
    context = build_source_series(start=START, timeframe=Timeframe.H4, count=2)
    intent = _enter_short(decision_open=execution[3].open_time, intent_id="mtf-short-denied")
    if intent.direction is not PositionDirection.SHORT:
        msg = "direction-restriction: provider must return a short entry"
        raise MtfGoldenMismatchError(msg)
    provider = ScriptedMtfProvider(first_ready_intent=(intent,))
    instance = build_instance(definition, {"signal_strength": 1})
    bundle = MultiTimeframeBacktestInput.from_verified(
        strategy_instance=instance,
        symbol=SYMBOL,
        execution_candles=execution,
        context_series=((Timeframe.H4, context),),
    )
    feed = MultiTimeframeDecisionFeed.from_input(bundle)
    if not feed.view_at(expectation.first_ready_index or 3).overall_ready:
        msg = "direction-restriction: provider must first become ready at expected bar"
        raise MtfGoldenMismatchError(msg)
    try:
        MultiTimeframeBacktestRunner.run(
            input_bundle=bundle,
            policy=default_policy(),
            provider=provider,
        )
    except BacktestExecutionError as exc:
        if "Decision provider failed" not in str(exc):
            msg = "direction-restriction: public exception must be sanitized engine error"
            raise MtfGoldenMismatchError(msg) from exc
        if not _cause_chain_has_unsupported_direction(exc):
            msg = "direction-restriction: cause chain missing unsupported-direction failure"
            raise MtfGoldenMismatchError(msg) from exc
        if provider.calls != [expectation.first_ready_index]:
            msg = "direction-restriction: provider must be called exactly once at first ready bar"
            raise MtfGoldenMismatchError(msg) from exc
        return {
            "ok": True,
            "scenario": expectation.scenario,
            "controlled_failure": True,
            "provider_invocation_count": len(provider.calls),
            "first_ready_index": expectation.first_ready_index,
            "error_code": "unsupported_direction",
            "warmup_skipped_count": expectation.warmup_skipped_count,
            "closed_trade_count": 0,
            "strategy_instance_hash": None,
            "input_bundle_hash": None,
            "execution_candle_hash": None,
            "alignment_hash": None,
            "backtest_result_hash": None,
            "envelope_hash": None,
        }
    msg = "direction-restriction: expected controlled failure with no result envelope"
    raise MtfGoldenMismatchError(msg)


def run_context_sensitivity() -> dict[str, object]:
    expectation = MTF_GOLDENS["context-sensitivity"]
    definition = mtf_definition(
        execution_warmup=4,
        contexts=(TimeframeRequirement(timeframe=Timeframe.H4, warmup_bars=1),),
        definition_code="mtf_context_sensitivity",
    )
    execution = build_source_series(start=START, timeframe=Timeframe.H1, count=8)
    context_a = build_source_series(start=START, timeframe=Timeframe.H4, count=2)
    tweaked = list(context_a)
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
    intent = _enter_long(decision_open=execution[3].open_time, intent_id="mtf-sensitivity")
    bundle_a, env_a = _run_envelope(
        definition=definition,
        execution=execution,
        contexts=((Timeframe.H4, context_a),),
        provider=ScriptedMtfProvider(first_ready_intent=(intent,)),
    )
    bundle_b, env_b = _run_envelope(
        definition=definition,
        execution=execution,
        contexts=((Timeframe.H4, context_b),),
        provider=ScriptedMtfProvider(first_ready_intent=(intent,)),
    )
    if bundle_a.execution_candle_sha256 != expectation.execution_candle_hash:
        msg = "context-sensitivity: execution hash mismatch"
        raise MtfGoldenMismatchError(msg)
    if bundle_a.execution_candle_sha256 != bundle_b.execution_candle_sha256:
        msg = "context-sensitivity: execution hash must be unchanged"
        raise MtfGoldenMismatchError(msg)
    if bundle_a.contexts[0].candle_sha256 == bundle_b.contexts[0].candle_sha256:
        msg = "context-sensitivity: context hash must change"
        raise MtfGoldenMismatchError(msg)
    if bundle_b.contexts[0].candle_sha256 != expectation.altered_context_hash:
        msg = "context-sensitivity: altered context hash mismatch"
        raise MtfGoldenMismatchError(msg)
    if bundle_a.input_bundle_hash == bundle_b.input_bundle_hash:
        msg = "context-sensitivity: bundle hash must change"
        raise MtfGoldenMismatchError(msg)
    if bundle_b.input_bundle_hash != expectation.altered_bundle_hash:
        msg = "context-sensitivity: altered bundle hash mismatch"
        raise MtfGoldenMismatchError(msg)
    if env_a.envelope_hash == env_b.envelope_hash:
        msg = "context-sensitivity: envelope hash must change"
        raise MtfGoldenMismatchError(msg)
    if env_a.envelope_hash != expectation.envelope_hash:
        msg = "context-sensitivity: baseline envelope hash mismatch"
        raise MtfGoldenMismatchError(msg)
    if env_b.envelope_hash != expectation.altered_envelope_hash:
        msg = "context-sensitivity: altered envelope hash mismatch"
        raise MtfGoldenMismatchError(msg)
    if bundle_a.strategy_instance_hash != expectation.strategy_instance_hash:
        msg = "context-sensitivity: strategy_instance_hash mismatch"
        raise MtfGoldenMismatchError(msg)
    if bundle_a.input_bundle_hash != expectation.input_bundle_hash:
        msg = "context-sensitivity: baseline bundle hash mismatch"
        raise MtfGoldenMismatchError(msg)
    if env_a.backtest_result_hash != expectation.backtest_result_hash:
        msg = "context-sensitivity: backtest_result_hash mismatch"
        raise MtfGoldenMismatchError(msg)
    return {
        "ok": True,
        "scenario": expectation.scenario,
        "strategy_instance_hash": bundle_a.strategy_instance_hash,
        "input_bundle_hash": bundle_a.input_bundle_hash,
        "execution_candle_hash": bundle_a.execution_candle_sha256,
        "alignment_hash": bundle_a.multi_context_alignment.alignment_hash,
        "backtest_result_hash": env_a.backtest_result_hash,
        "envelope_hash": env_a.envelope_hash,
        "provider_invocation_count": env_a.provider_invocation_count,
        "warmup_skipped_count": env_a.warmup_skipped_decision_count,
        "closed_trade_count": env_a.result.summary.closed_trade_count,
        "altered_bundle_hash": bundle_b.input_bundle_hash,
        "altered_envelope_hash": env_b.envelope_hash,
    }


def run_mtf_scenario(name: str) -> dict[str, object]:
    if name == "exact-close-readiness":
        return run_exact_close_readiness()
    if name == "context-unavailable":
        return run_context_unavailable()
    if name == "two-contexts":
        return run_two_contexts()
    if name == "direction-restriction":
        return run_direction_restriction()
    if name == "context-sensitivity":
        return run_context_sensitivity()
    raise KeyError(name)
