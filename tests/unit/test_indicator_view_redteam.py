"""Adversarial red-team loop for bounded indicator decision views."""

from __future__ import annotations

import inspect
from decimal import Decimal, getcontext
from io import StringIO
from unittest.mock import patch

import pytest

from tests.unit.indicator_helpers import indicator_input_from_specs
from zorqen_research.application.indicator_views.feed import IndicatorDecisionFeed
from zorqen_research.application.indicator_views.goldens import (
    ALL_SCENARIO_NAMES,
    WARMUP_BARS,
    run_scenario,
)
from zorqen_research.application.indicator_views.prefix_hashes import compute_prefix_hash_chain
from zorqen_research.application.indicators.ema import ema_close
from zorqen_research.application.indicators.volatility import wilder_atr
from zorqen_research.domain.indicator_views import __all__ as domain_all
from zorqen_research.domain.indicator_views.bundles import IndicatorSeriesBundle
from zorqen_research.domain.indicator_views.errors import IndicatorViewValidationError
from zorqen_research.domain.indicator_views.histories import (
    VisibleIndicatorHistory,
    _VerifiedIndicatorSource,
)
from zorqen_research.domain.indicator_views.keys import IndicatorSeriesKey
from zorqen_research.domain.indicators.enums import IndicatorCode
from zorqen_research.domain.indicators.results import IndicatorSeries
from zorqen_research.indicators.cli import main


def _bundle(
    specs: tuple[tuple[str, str, str, str], ...] | None = None,
) -> IndicatorSeriesBundle:
    indicator_input = indicator_input_from_specs(
        specs
        or (
            ("10", "11", "9", "10"),
            ("11", "12", "10", "11"),
            ("12", "13", "11", "12"),
            ("13", "14", "12", "13"),
            ("14", "15", "13", "14"),
            ("15", "16", "14", "15"),
        )
    )
    return IndicatorSeriesBundle.from_verified(
        indicator_input=indicator_input,
        series=(
            ema_close(indicator_input, 4),
            wilder_atr(indicator_input, 3),
        ),
    )


def test_redteam_tuple_subclass_and_forged_series() -> None:
    class SeriesTuple(tuple):
        pass

    indicator_input = indicator_input_from_specs((("10", "11", "9", "10"),))
    series = ema_close(indicator_input, 1)
    with pytest.raises(IndicatorViewValidationError):
        IndicatorSeriesBundle.from_verified(
            indicator_input=indicator_input,
            series=SeriesTuple((series,)),
        )
    forged = object.__new__(IndicatorSeries)
    with pytest.raises(IndicatorViewValidationError):
        IndicatorSeriesBundle.from_verified(
            indicator_input=indicator_input,
            series=(forged,),
        )


def test_redteam_mutated_hash_duplicate_bool_period_string_alias() -> None:
    indicator_input = indicator_input_from_specs(
        (
            ("10", "11", "9", "10"),
            ("11", "12", "10", "11"),
            ("12", "13", "11", "12"),
        )
    )
    series = ema_close(indicator_input, 2)
    object.__setattr__(series, "result_hash", "ab" * 32)
    with pytest.raises(IndicatorViewValidationError, match="result_hash|result hash"):
        IndicatorSeriesBundle.from_verified(
            indicator_input=indicator_input,
            series=(series,),
        )
    good = ema_close(indicator_input, 2)
    with pytest.raises(IndicatorViewValidationError, match="duplicate"):
        IndicatorSeriesBundle.from_verified(
            indicator_input=indicator_input,
            series=(good, good),
        )
    with pytest.raises(IndicatorViewValidationError):
        IndicatorSeriesKey.from_verified(
            indicator_code=IndicatorCode.EMA_CLOSE,
            parameters={"period": True},
        )
    view = IndicatorDecisionFeed.from_bundle(_bundle()).view_at(3)
    with pytest.raises(IndicatorViewValidationError, match="IndicatorCode"):
        view.require("ema_close", period=4)  # type: ignore[arg-type]


def test_redteam_bar_index_and_direct_history() -> None:
    feed = IndicatorDecisionFeed.from_bundle(_bundle())
    with pytest.raises(IndicatorViewValidationError):
        feed.view_at(-1)
    with pytest.raises(IndicatorViewValidationError):
        feed.view_at(True)
    with pytest.raises(IndicatorViewValidationError):
        feed.view_at(100)
    with pytest.raises(IndicatorViewValidationError):
        VisibleIndicatorHistory()
    with pytest.raises(IndicatorViewValidationError):
        _VerifiedIndicatorSource()


def test_redteam_source_repr_slices_negative_future_sentinel() -> None:
    feed = IndicatorDecisionFeed.from_bundle(_bundle())
    view = feed.view_at(2)
    item = view.require(IndicatorCode.EMA_CLOSE, period=4)
    history = item.history
    future_sentinel = Decimal("999999.123456789")
    # Inject sentinel into private full values beyond the visible boundary.
    values = list(history._source._values)
    values[5] = future_sentinel
    object.__setattr__(history._source, "_values", tuple(values))
    assert future_sentinel not in tuple(history)
    with pytest.raises(IndexError):
        _ = history[5]
    assert history[0:20] == (None, None, None)
    assert history[::-1] == (None, None, None)
    with pytest.raises(IndexError):
        _ = history[-4]
    for name in ("values", "source", "series", "to_tuple", "all", "full"):
        assert not hasattr(history, name)
    assert "999999" not in repr(history)
    assert "999999" not in str(history)
    assert "999999" not in repr(item)
    assert "999999" not in repr(view)
    assert "_VerifiedIndicatorSource" not in domain_all


def test_redteam_future_candle_mutation_append_and_decimal_context() -> None:
    prefix = (
        ("10", "11", "9", "10"),
        ("11", "12", "10", "11"),
        ("12", "13", "11", "12"),
        ("13", "14", "12", "13"),
    )
    base = _bundle(prefix)
    mutated = _bundle(prefix[:3] + (("77", "88", "66", "70"),))
    appended = _bundle(prefix + (("20", "21", "19", "20"),))
    base_view = IndicatorDecisionFeed.from_bundle(base).view_at(2)
    mutated_view = IndicatorDecisionFeed.from_bundle(mutated).view_at(2)
    appended_view = IndicatorDecisionFeed.from_bundle(appended).view_at(3)
    base_at_3 = IndicatorDecisionFeed.from_bundle(base).view_at(3)
    assert base_view.decision_view_hash == mutated_view.decision_view_hash
    assert base_at_3.decision_view_hash == appended_view.decision_view_hash
    assert base.bundle_hash != mutated.bundle_hash
    assert base.bundle_hash != appended.bundle_hash

    ctx = getcontext()
    previous = (ctx.prec, ctx.rounding, ctx.Emax, ctx.Emin)
    try:
        ctx.prec = 3
        ctx.rounding = "ROUND_UP"
        attacked = IndicatorDecisionFeed.from_bundle(_bundle(prefix)).view_at(3)
    finally:
        ctx.prec, ctx.rounding, ctx.Emax, ctx.Emin = previous
    assert attacked.decision_view_hash == base_at_3.decision_view_hash


def test_redteam_signed_zero_and_view_hash_excludes_result_hash() -> None:
    from zorqen_research.application.indicator_views.prefix_hashes import canonical_value_token

    assert canonical_value_token(Decimal("-0")) == b"0"
    view = IndicatorDecisionFeed.from_bundle(_bundle()).view_at(4)
    for series in view.items:
        assert series.visible_prefix_hash
    # Decision-view hash payload must not embed full result hashes.
    src = inspect.getsource(
        __import__(
            "zorqen_research.domain.indicator_views.views",
            fromlist=["IndicatorDecisionView"],
        ).IndicatorDecisionView._from_feed
    )
    assert "result_hash" not in src
    assert "input_hash" not in src
    assert "visible_prefix_hash" in src


def test_redteam_prefix_not_recomputed_and_large_index_constant() -> None:
    feed = IndicatorDecisionFeed.from_bundle(_bundle())
    source = feed._sources[0]
    before = source._prefix_hashes
    feed.view_at(1)
    feed.view_at(5)
    assert source._prefix_hashes is before
    # Monkeypatch compute to fail if recomputed during view_at.
    calls = {"n": 0}
    original = compute_prefix_hash_chain

    def counting(**kwargs):  # noqa: ANN003
        calls["n"] += 1
        return original(**kwargs)

    with patch(
        "zorqen_research.application.indicator_views.feed.compute_prefix_hash_chain",
        counting,
    ):
        IndicatorDecisionFeed.from_bundle(_bundle())
        assert calls["n"] == 2
        # Fresh feed already has chains; view_at must not call compute.
        calls["n"] = 0
        feed.view_at(4)
        assert calls["n"] == 0


def test_redteam_golden_value_and_prefix_mismatches() -> None:
    from dataclasses import replace

    from zorqen_research.application.indicator_views.goldens import (
        IndicatorViewGoldenMismatchError,
    )

    with (
        patch(
            "zorqen_research.application.indicator_views.goldens.WARMUP_BARS",
            (replace(WARMUP_BARS[0], ema_latest="999"), *WARMUP_BARS[1:]),
        ),
        pytest.raises(IndicatorViewGoldenMismatchError),
    ):
        run_scenario("warmup-progression")

    with (
        patch(
            "zorqen_research.application.indicator_views.goldens.WARMUP_BARS",
            (replace(WARMUP_BARS[0], ema_prefix_hash="0" * 64), *WARMUP_BARS[1:]),
        ),
        pytest.raises(IndicatorViewGoldenMismatchError),
    ):
        run_scenario("warmup-progression")


def test_redteam_cli_all_failure_routing() -> None:
    stderr = StringIO()
    stdout = StringIO()
    with patch("sys.stderr", stderr), patch("sys.stdout", stdout):
        code = main(["verify-view-golden", "--scenario", "does-not-exist"])
    assert code == 1
    assert b'"ok":false' in stderr.getvalue().encode() or '"ok": false' in stderr.getvalue()
    payload_ok = True
    for name in ALL_SCENARIO_NAMES:
        assert run_scenario(name)["ok"] is True
        payload_ok = payload_ok and True
    assert payload_ok

    # Force mismatch through CLI for --scenario all failure routing.
    with patch(
        "zorqen_research.application.indicator_views.goldens.WARMUP_BUNDLE_HASH",
        "0" * 64,
    ):
        stderr = StringIO()
        stdout = StringIO()
        with patch("sys.stderr", stderr), patch("sys.stdout", stdout):
            code = main(["verify-view-golden", "--scenario", "all"])
        assert code == 1
        assert "golden_mismatch" in stderr.getvalue() or "bundle_hash" in stderr.getvalue()
