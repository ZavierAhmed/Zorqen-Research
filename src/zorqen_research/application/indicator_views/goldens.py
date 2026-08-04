"""Frozen literal golden expectations for indicator decision views.

Literal constants only — do not invoke production feed logic to derive
expected hashes or values at import time.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from zorqen_research.application.indicator_views.feed import IndicatorDecisionFeed
from zorqen_research.application.indicators.ema import ema_close
from zorqen_research.application.indicators.volatility import wilder_atr
from zorqen_research.application.market_data.serialization import format_canonical_decimal
from zorqen_research.domain.candles import Candle
from zorqen_research.domain.indicator_views.bundles import IndicatorSeriesBundle
from zorqen_research.domain.indicator_views.errors import IndicatorViewValidationError
from zorqen_research.domain.indicator_views.histories import VisibleIndicatorHistory
from zorqen_research.domain.indicators.enums import IndicatorCode
from zorqen_research.domain.indicators.inputs import IndicatorInput
from zorqen_research.domain.symbols import Symbol
from zorqen_research.domain.timeframes import Timeframe, timeframe_duration

SYMBOL = Symbol(value="BTCUSDT")
TIMEFRAME = Timeframe.M1

_START = datetime(2024, 1, 1, tzinfo=UTC)
_STEP = timeframe_duration(TIMEFRAME)


def make_candle(
    open_time: datetime,
    *,
    open: str,
    high: str,
    low: str,
    close: str,
) -> Candle:
    return Candle(
        open_time=open_time,
        open=Decimal(open),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
        volume=Decimal("1"),
        close_time=open_time + _STEP - timedelta(milliseconds=1),
        quote_asset_volume=Decimal("10"),
        trade_count=1,
        taker_buy_base_volume=Decimal("0.4"),
        taker_buy_quote_volume=Decimal("4"),
    )


def _series(specs: tuple[tuple[str, str, str, str], ...]) -> tuple[Candle, ...]:
    return tuple(
        make_candle(
            _START + index * _STEP,
            open=open_,
            high=high,
            low=low,
            close=close,
        )
        for index, (open_, high, low, close) in enumerate(specs)
    )


WARMUP_CANDLES = _series(
    (
        ("10", "11", "9", "10"),
        ("11", "12", "10", "11"),
        ("12", "13", "11", "12"),
        ("13", "14", "12", "13"),
        ("14", "15", "13", "14"),
        ("15", "16", "14", "15"),
    )
)

MULTI_EMA_CANDLES = _series(
    (
        ("10", "11", "9", "10"),
        ("11", "12", "10", "11"),
        ("12", "13", "11", "12"),
        ("13", "14", "12", "13"),
        ("14", "15", "13", "14"),
    )
)

FUTURE_PREFIX = (
    ("10", "11", "9", "10"),
    ("11", "12", "10", "11"),
    ("12", "13", "11", "12"),
    ("13", "14", "12", "13"),
)
FUTURE_A_CANDLES = _series(
    FUTURE_PREFIX
    + (
        ("20", "21", "19", "20"),
        ("21", "22", "20", "21"),
    )
)
FUTURE_B_CANDLES = _series(
    FUTURE_PREFIX
    + (
        ("99", "100", "98", "99"),
        ("1", "2", "0", "1"),
    )
)


@dataclass(frozen=True, slots=True)
class WarmupBarExpectation:
    bar_index: int
    visible_count: int
    overall_ready: bool
    decision_view_hash: str
    ema_ready: bool
    ema_visible_count: int
    ema_defined_visible_count: int
    ema_latest: str | None
    ema_prefix_hash: str
    atr_ready: bool
    atr_visible_count: int
    atr_defined_visible_count: int
    atr_latest: str | None
    atr_prefix_hash: str


WARMUP_BUNDLE_HASH = "b9e4c70816cf3118632fbeb1274b52a1b70fedc1bb92b0f514ac442a59e94e7a"

WARMUP_BARS: tuple[WarmupBarExpectation, ...] = (
    WarmupBarExpectation(
        bar_index=0,
        visible_count=1,
        overall_ready=False,
        decision_view_hash="7e8bd170c81439b9e700a56fe8a05465370eae69951151d71213681c2f7011c8",
        ema_ready=False,
        ema_visible_count=1,
        ema_defined_visible_count=0,
        ema_latest=None,
        ema_prefix_hash="1c0701708551e2082cb88dd3ee394f35ce0a24b24442fb942c2fa9906fea6556",
        atr_ready=False,
        atr_visible_count=1,
        atr_defined_visible_count=0,
        atr_latest=None,
        atr_prefix_hash="c9a046510ffd7133899b92c2c3e55846ce36af065e165a0f1a7656a52b0c8951",
    ),
    WarmupBarExpectation(
        bar_index=2,
        visible_count=3,
        overall_ready=False,
        decision_view_hash="08f7528074639cc8c1c11c0fa10157590c4eb2aa715715b15c34acad9e3eb6ec",
        ema_ready=False,
        ema_visible_count=3,
        ema_defined_visible_count=0,
        ema_latest=None,
        ema_prefix_hash="29f6c2838e0d88d5524d21e047e7c8df7e3d2299334d90f9438d12e7959253d9",
        atr_ready=True,
        atr_visible_count=3,
        atr_defined_visible_count=1,
        atr_latest="2",
        atr_prefix_hash="d2de1aefbf94a43137362e55228b0c86bb722014d9d3dc469452b82355086496",
    ),
    WarmupBarExpectation(
        bar_index=3,
        visible_count=4,
        overall_ready=True,
        decision_view_hash="b5df80fbb92a71f0b8b01c93cfb08baaf88abccbab39945e0103482a11a48928",
        ema_ready=True,
        ema_visible_count=4,
        ema_defined_visible_count=1,
        ema_latest="11.5",
        ema_prefix_hash="36286646d445ffa10fdb5977f0664bf60f3e9cd9c5c1c7a6fb2180755641254e",
        atr_ready=True,
        atr_visible_count=4,
        atr_defined_visible_count=2,
        atr_latest="2",
        atr_prefix_hash="268089bf8c09f6d98e70ce2d7dcaf70a0abd82ff66d43b0c82ccdd3ef5c9e4d4",
    ),
    WarmupBarExpectation(
        bar_index=5,
        visible_count=6,
        overall_ready=True,
        decision_view_hash="aaecdb9c79d1d2649ed37087bcbc3a3652f1e4e7466b4a315efe1a104479a847",
        ema_ready=True,
        ema_visible_count=6,
        ema_defined_visible_count=3,
        ema_latest="13.5",
        ema_prefix_hash="1abc82978d6bfca627c5f56ef10f6fc53b20a15de6f60bf929a1251ea2e084d9",
        atr_ready=True,
        atr_visible_count=6,
        atr_defined_visible_count=4,
        atr_latest="2",
        atr_prefix_hash="845323ac6a90c3cf1c502b4f9cc2573d7ec0bb8e22016b8f312f1f5351ca037d",
    ),
)

MULTI_EMA_BUNDLE_HASH = "6bf1290f021bd5ccf03ec1f8faecbbef8af9286642e83551d10d09751a8a45cf"
MULTI_EMA_BAR_INDEX = 4
MULTI_EMA_DECISION_VIEW_HASH = "8607acdd9b9cf776a804df7e0fcf71bd6cb06140938d2f336f9fa906041c96e2"
MULTI_EMA_PERIOD_2_PREFIX = "9fd6276cc36fb8fa6975a7f3180f90a789bb1beabc78604d907a6d836fa274e0"
MULTI_EMA_PERIOD_4_PREFIX = "809b17c1feb953bc29db672e73701f3e211e234e3db9c1c408a6a3a4337b4876"
MULTI_EMA_PERIOD_2_LATEST = "13.5"
MULTI_EMA_PERIOD_4_LATEST = "12.5"

FUTURE_A_BUNDLE_HASH = "608b2dc2a90a097e8a18b3521cf88f1198c0058b0cc08119ed95e7c5b629edea"
FUTURE_B_BUNDLE_HASH = "858c3d7e2cb2a279165c11a09c9184ef40fb99bdd080a2dc7f42dc975a264dae"
FUTURE_BAR_INDEX = 3
FUTURE_DECISION_VIEW_HASH = "b5df80fbb92a71f0b8b01c93cfb08baaf88abccbab39945e0103482a11a48928"
FUTURE_EMA_PREFIX = "36286646d445ffa10fdb5977f0664bf60f3e9cd9c5c1c7a6fb2180755641254e"
FUTURE_ATR_PREFIX = "268089bf8c09f6d98e70ce2d7dcaf70a0abd82ff66d43b0c82ccdd3ef5c9e4d4"

BOUNDED_ACCESS_REPORT = {
    "public_source_exposed": False,
    "future_index_blocked": True,
    "slice_bounded": True,
    "iteration_bounded": True,
    "repr_safe": True,
    "str_safe": True,
}

ALL_SCENARIO_NAMES: tuple[str, ...] = (
    "warmup-progression",
    "multiple-ema-keys",
    "future-independence",
    "bounded-access",
)


class IndicatorViewGoldenMismatchError(Exception):
    """Raised when a computed indicator view diverges from frozen literals."""


def _latest_text(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return format_canonical_decimal(value)


def _warmup_bundle() -> IndicatorSeriesBundle:
    indicator_input = IndicatorInput.from_verified(
        symbol=SYMBOL,
        timeframe=TIMEFRAME,
        candles=WARMUP_CANDLES,
    )
    return IndicatorSeriesBundle.from_verified(
        indicator_input=indicator_input,
        series=(
            ema_close(indicator_input, 4),
            wilder_atr(indicator_input, 3),
        ),
    )


def _check_warmup_bar(
    *,
    expected: WarmupBarExpectation,
    feed: IndicatorDecisionFeed,
    bundle_hash: str,
) -> dict[str, object]:
    view = feed.view_at(expected.bar_index)
    ema = view.require(IndicatorCode.EMA_CLOSE, period=4)
    atr = view.require(IndicatorCode.WILDER_ATR, period=3)
    if view.visible_count != expected.visible_count:
        msg = "visible_count mismatch"
        raise IndicatorViewGoldenMismatchError(msg)
    if view.overall_ready != expected.overall_ready:
        msg = "overall_ready mismatch"
        raise IndicatorViewGoldenMismatchError(msg)
    if view.decision_view_hash != expected.decision_view_hash:
        msg = "decision_view_hash mismatch"
        raise IndicatorViewGoldenMismatchError(msg)
    if ema.ready != expected.ema_ready or atr.ready != expected.atr_ready:
        msg = "item ready mismatch"
        raise IndicatorViewGoldenMismatchError(msg)
    if ema.visible_count != expected.ema_visible_count:
        msg = "ema visible_count mismatch"
        raise IndicatorViewGoldenMismatchError(msg)
    if atr.visible_count != expected.atr_visible_count:
        msg = "atr visible_count mismatch"
        raise IndicatorViewGoldenMismatchError(msg)
    if ema.defined_visible_count != expected.ema_defined_visible_count:
        msg = "ema defined_visible_count mismatch"
        raise IndicatorViewGoldenMismatchError(msg)
    if atr.defined_visible_count != expected.atr_defined_visible_count:
        msg = "atr defined_visible_count mismatch"
        raise IndicatorViewGoldenMismatchError(msg)
    if _latest_text(ema.latest) != expected.ema_latest:
        msg = "ema latest mismatch"
        raise IndicatorViewGoldenMismatchError(msg)
    if _latest_text(atr.latest) != expected.atr_latest:
        msg = "atr latest mismatch"
        raise IndicatorViewGoldenMismatchError(msg)
    if ema.visible_prefix_hash != expected.ema_prefix_hash:
        msg = "ema prefix-hash mismatch"
        raise IndicatorViewGoldenMismatchError(msg)
    if atr.visible_prefix_hash != expected.atr_prefix_hash:
        msg = "atr prefix-hash mismatch"
        raise IndicatorViewGoldenMismatchError(msg)
    return {
        "ok": True,
        "scenario": "warmup-progression",
        "bundle_hash": bundle_hash,
        "bar_index": expected.bar_index,
        "visible_count": view.visible_count,
        "overall_ready": view.overall_ready,
        "decision_view_hash": view.decision_view_hash,
        "item_prefix_hashes": {
            "ema_close": ema.visible_prefix_hash,
            "wilder_atr": atr.visible_prefix_hash,
        },
    }


def _run_warmup_progression() -> dict[str, object]:
    bundle = _warmup_bundle()
    if bundle.bundle_hash != WARMUP_BUNDLE_HASH:
        msg = "bundle_hash mismatch"
        raise IndicatorViewGoldenMismatchError(msg)
    feed = IndicatorDecisionFeed.from_bundle(bundle)
    payloads = [
        _check_warmup_bar(expected=expected, feed=feed, bundle_hash=bundle.bundle_hash)
        for expected in WARMUP_BARS
    ]
    return {
        "ok": True,
        "scenario": "warmup-progression",
        "bundle_hash": bundle.bundle_hash,
        "bar_index": WARMUP_BARS[-1].bar_index,
        "visible_count": WARMUP_BARS[-1].visible_count,
        "overall_ready": WARMUP_BARS[-1].overall_ready,
        "decision_view_hash": WARMUP_BARS[-1].decision_view_hash,
        "item_prefix_hashes": payloads[-1]["item_prefix_hashes"],
        "bars_verified": len(payloads),
    }


def _run_multiple_ema_keys() -> dict[str, object]:
    indicator_input = IndicatorInput.from_verified(
        symbol=SYMBOL,
        timeframe=TIMEFRAME,
        candles=MULTI_EMA_CANDLES,
    )
    # Intentionally unordered construction — bundle must canonicalize.
    bundle = IndicatorSeriesBundle.from_verified(
        indicator_input=indicator_input,
        series=(
            ema_close(indicator_input, 4),
            ema_close(indicator_input, 2),
        ),
    )
    if bundle.bundle_hash != MULTI_EMA_BUNDLE_HASH:
        msg = "bundle_hash mismatch"
        raise IndicatorViewGoldenMismatchError(msg)
    if bundle.series_keys[0].parameters != (("period", 2),):
        msg = "canonical key order mismatch"
        raise IndicatorViewGoldenMismatchError(msg)
    if bundle.series_keys[1].parameters != (("period", 4),):
        msg = "canonical key order mismatch"
        raise IndicatorViewGoldenMismatchError(msg)
    if bundle.series_keys[0].key_hash == bundle.series_keys[1].key_hash:
        msg = "EMA period keys must be distinct"
        raise IndicatorViewGoldenMismatchError(msg)
    feed = IndicatorDecisionFeed.from_bundle(bundle)
    view = feed.view_at(MULTI_EMA_BAR_INDEX)
    if view.decision_view_hash != MULTI_EMA_DECISION_VIEW_HASH:
        msg = "decision_view_hash mismatch"
        raise IndicatorViewGoldenMismatchError(msg)
    period2 = view.require(IndicatorCode.EMA_CLOSE, period=2)
    period4 = view.require(IndicatorCode.EMA_CLOSE, period=4)
    if period2.visible_prefix_hash != MULTI_EMA_PERIOD_2_PREFIX:
        msg = "period-2 prefix-hash mismatch"
        raise IndicatorViewGoldenMismatchError(msg)
    if period4.visible_prefix_hash != MULTI_EMA_PERIOD_4_PREFIX:
        msg = "period-4 prefix-hash mismatch"
        raise IndicatorViewGoldenMismatchError(msg)
    if _latest_text(period2.latest) != MULTI_EMA_PERIOD_2_LATEST:
        msg = "period-2 latest mismatch"
        raise IndicatorViewGoldenMismatchError(msg)
    if _latest_text(period4.latest) != MULTI_EMA_PERIOD_4_LATEST:
        msg = "period-4 latest mismatch"
        raise IndicatorViewGoldenMismatchError(msg)
    return {
        "ok": True,
        "scenario": "multiple-ema-keys",
        "bundle_hash": bundle.bundle_hash,
        "bar_index": MULTI_EMA_BAR_INDEX,
        "visible_count": view.visible_count,
        "overall_ready": view.overall_ready,
        "decision_view_hash": view.decision_view_hash,
        "item_prefix_hashes": {
            "ema_close_period_2": period2.visible_prefix_hash,
            "ema_close_period_4": period4.visible_prefix_hash,
        },
    }


def _future_bundle(candles: tuple[Candle, ...]) -> IndicatorSeriesBundle:
    indicator_input = IndicatorInput.from_verified(
        symbol=SYMBOL,
        timeframe=TIMEFRAME,
        candles=candles,
    )
    return IndicatorSeriesBundle.from_verified(
        indicator_input=indicator_input,
        series=(
            ema_close(indicator_input, 4),
            wilder_atr(indicator_input, 3),
        ),
    )


def _run_future_independence() -> dict[str, object]:
    bundle_a = _future_bundle(FUTURE_A_CANDLES)
    bundle_b = _future_bundle(FUTURE_B_CANDLES)
    if bundle_a.bundle_hash != FUTURE_A_BUNDLE_HASH:
        msg = "future-A bundle_hash mismatch"
        raise IndicatorViewGoldenMismatchError(msg)
    if bundle_b.bundle_hash != FUTURE_B_BUNDLE_HASH:
        msg = "future-B bundle_hash mismatch"
        raise IndicatorViewGoldenMismatchError(msg)
    if bundle_a.bundle_hash == bundle_b.bundle_hash:
        msg = "future bundles must diverge"
        raise IndicatorViewGoldenMismatchError(msg)
    if bundle_a.series[0].result_hash == bundle_b.series[0].result_hash:
        msg = "future EMA result hashes must diverge"
        raise IndicatorViewGoldenMismatchError(msg)
    feed_a = IndicatorDecisionFeed.from_bundle(bundle_a)
    feed_b = IndicatorDecisionFeed.from_bundle(bundle_b)
    view_a = feed_a.view_at(FUTURE_BAR_INDEX)
    view_b = feed_b.view_at(FUTURE_BAR_INDEX)
    if view_a.decision_view_hash != FUTURE_DECISION_VIEW_HASH:
        msg = "decision_view_hash mismatch"
        raise IndicatorViewGoldenMismatchError(msg)
    if view_a.decision_view_hash != view_b.decision_view_hash:
        msg = "earlier decision-view hashes must match"
        raise IndicatorViewGoldenMismatchError(msg)
    ema_a = view_a.require(IndicatorCode.EMA_CLOSE, period=4)
    ema_b = view_b.require(IndicatorCode.EMA_CLOSE, period=4)
    atr_a = view_a.require(IndicatorCode.WILDER_ATR, period=3)
    atr_b = view_b.require(IndicatorCode.WILDER_ATR, period=3)
    if (
        ema_a.visible_prefix_hash != FUTURE_EMA_PREFIX
        or ema_b.visible_prefix_hash != FUTURE_EMA_PREFIX
    ):
        msg = "ema prefix-hash mismatch"
        raise IndicatorViewGoldenMismatchError(msg)
    if (
        atr_a.visible_prefix_hash != FUTURE_ATR_PREFIX
        or atr_b.visible_prefix_hash != FUTURE_ATR_PREFIX
    ):
        msg = "atr prefix-hash mismatch"
        raise IndicatorViewGoldenMismatchError(msg)
    if tuple(ema_a.history) != tuple(ema_b.history):
        msg = "earlier visible values must match"
        raise IndicatorViewGoldenMismatchError(msg)
    return {
        "ok": True,
        "scenario": "future-independence",
        "bundle_hash": bundle_a.bundle_hash,
        "bar_index": FUTURE_BAR_INDEX,
        "visible_count": view_a.visible_count,
        "overall_ready": view_a.overall_ready,
        "decision_view_hash": view_a.decision_view_hash,
        "item_prefix_hashes": {
            "ema_close": ema_a.visible_prefix_hash,
            "wilder_atr": atr_a.visible_prefix_hash,
        },
        "alternate_bundle_hash": bundle_b.bundle_hash,
    }


def _run_bounded_access() -> dict[str, object]:
    bundle = _warmup_bundle()
    feed = IndicatorDecisionFeed.from_bundle(bundle)
    view = feed.view_at(2)
    item = view.require(IndicatorCode.EMA_CLOSE, period=4)
    history = item.history

    public_source_exposed = hasattr(history, "values") or hasattr(history, "source")
    public_source_exposed = public_source_exposed or hasattr(history, "series")
    public_source_exposed = public_source_exposed or hasattr(history, "to_tuple")
    public_source_exposed = public_source_exposed or hasattr(history, "all")
    public_source_exposed = public_source_exposed or hasattr(history, "full")

    future_index_blocked = False
    try:
        _ = history[3]
    except IndexError:
        future_index_blocked = True

    sliced = history[0:10]
    assert isinstance(sliced, tuple)
    slice_bounded = len(sliced) == 3 and all(value is None for value in sliced)

    iterated = tuple(history)
    iteration_bounded = len(iterated) == 3

    text_repr = repr(history)
    text_str = str(history)
    sentinel = "999999.123456789"
    # Future sentinel is not present in this warmup series; ensure bounds text
    # never leaks source length or full result hash either.
    repr_safe = (
        "visible_count=3" in text_repr
        and "latest_defined=false" in text_repr
        and sentinel not in text_repr
        and bundle.series[0].result_hash not in text_repr
        and str(len(bundle.series[0].values)) not in text_repr.replace("visible_count=3", "")
    )
    str_safe = text_str == text_repr and sentinel not in text_str

    direct_blocked = False
    try:
        VisibleIndicatorHistory()
    except IndicatorViewValidationError:
        direct_blocked = True

    report = {
        "public_source_exposed": public_source_exposed,
        "future_index_blocked": future_index_blocked,
        "slice_bounded": slice_bounded,
        "iteration_bounded": iteration_bounded,
        "repr_safe": repr_safe and direct_blocked,
        "str_safe": str_safe,
    }
    if report != BOUNDED_ACCESS_REPORT:
        msg = f"bounded-access report mismatch: {report!r}"
        raise IndicatorViewGoldenMismatchError(msg)
    return {
        "ok": True,
        "scenario": "bounded-access",
        "bundle_hash": bundle.bundle_hash,
        "bar_index": 2,
        "visible_count": view.visible_count,
        "overall_ready": view.overall_ready,
        "decision_view_hash": view.decision_view_hash,
        "item_prefix_hashes": {
            "ema_close": item.visible_prefix_hash,
        },
        "bounded_access_report": report,
    }


def run_scenario(name: str) -> dict[str, object]:
    if name == "warmup-progression":
        return _run_warmup_progression()
    if name == "multiple-ema-keys":
        return _run_multiple_ema_keys()
    if name == "future-independence":
        return _run_future_independence()
    if name == "bounded-access":
        return _run_bounded_access()
    raise KeyError(name)
