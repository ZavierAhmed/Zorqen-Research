"""Prefix-only indicator hash chain tests."""

from __future__ import annotations

import hashlib
from decimal import Decimal, getcontext

from tests.unit.indicator_helpers import indicator_input_from_specs
from zorqen_research.application.indicator_views.feed import IndicatorDecisionFeed
from zorqen_research.application.indicator_views.prefix_hashes import (
    build_prefix_header_bytes,
    canonical_value_token,
    compute_prefix_hash_chain,
)
from zorqen_research.application.indicators.ema import ema_close
from zorqen_research.application.market_data.serialization import format_canonical_decimal
from zorqen_research.domain.indicator_views.bundles import IndicatorSeriesBundle
from zorqen_research.domain.indicator_views.keys import IndicatorSeriesKey
from zorqen_research.domain.indicators.enums import IndicatorCode
from zorqen_research.domain.indicators.math_policy import default_math_policy


def test_zero_and_one_value_prefix_and_undefined_token() -> None:
    assert canonical_value_token(None) == b"null"
    key = IndicatorSeriesKey.from_verified(
        indicator_code=IndicatorCode.EMA_CLOSE,
        parameters={"period": 3},
    )
    indicator_input = indicator_input_from_specs(
        (
            ("10", "11", "9", "10"),
            ("11", "12", "10", "11"),
            ("12", "13", "11", "12"),
        )
    )
    series = ema_close(indicator_input, 3)
    chain = compute_prefix_hash_chain(
        symbol=indicator_input.symbol,
        timeframe=indicator_input.timeframe,
        series_key=key,
        math_policy=series.math_policy,
        values=series.values,
    )
    header = build_prefix_header_bytes(
        symbol=indicator_input.symbol,
        timeframe=indicator_input.timeframe,
        series_key=key,
        math_policy=series.math_policy,
    )
    assert chain[0] == hashlib.sha256(header).hexdigest()
    assert len(chain) == len(series.values) + 1
    h1 = hashlib.sha256(
        bytes.fromhex(chain[0]) + b"\n" + canonical_value_token(series.values[0])
    ).hexdigest()
    assert chain[1] == h1
    assert series.values[0] is None


def test_signed_zero_token_and_decimal_context_independence() -> None:
    assert canonical_value_token(Decimal("-0")) == b"0"
    assert format_canonical_decimal(Decimal("-0")) == "0"
    key = IndicatorSeriesKey.from_verified(
        indicator_code=IndicatorCode.EMA_CLOSE,
        parameters={"period": 2},
    )
    values = (None, Decimal("1"), Decimal("-0"), Decimal("2"))
    policy = default_math_policy()
    indicator_input = indicator_input_from_specs(
        (
            ("10", "11", "9", "10"),
            ("11", "12", "10", "11"),
            ("12", "13", "11", "12"),
            ("13", "14", "12", "13"),
        )
    )
    baseline = compute_prefix_hash_chain(
        symbol=indicator_input.symbol,
        timeframe=indicator_input.timeframe,
        series_key=key,
        math_policy=policy,
        values=values,
    )
    ctx = getcontext()
    previous = (ctx.prec, ctx.rounding, ctx.Emax, ctx.Emin)
    try:
        ctx.prec = 2
        ctx.rounding = "ROUND_DOWN"
        ctx.Emax = 5
        ctx.Emin = -5
        attacked = compute_prefix_hash_chain(
            symbol=indicator_input.symbol,
            timeframe=indicator_input.timeframe,
            series_key=key,
            math_policy=policy,
            values=values,
        )
    finally:
        ctx.prec, ctx.rounding, ctx.Emax, ctx.Emin = previous
    assert attacked == baseline


def test_future_mutation_and_append_independence() -> None:
    prefix = (
        ("10", "11", "9", "10"),
        ("11", "12", "10", "11"),
        ("12", "13", "11", "12"),
        ("13", "14", "12", "13"),
    )
    base_input = indicator_input_from_specs(prefix)
    mutated_input = indicator_input_from_specs(prefix[:3] + (("90", "91", "89", "90"),))
    appended_input = indicator_input_from_specs(prefix + (("20", "21", "19", "20"),))
    base = IndicatorSeriesBundle.from_verified(
        indicator_input=base_input,
        series=(ema_close(base_input, 3),),
    )
    mutated = IndicatorSeriesBundle.from_verified(
        indicator_input=mutated_input,
        series=(ema_close(mutated_input, 3),),
    )
    appended = IndicatorSeriesBundle.from_verified(
        indicator_input=appended_input,
        series=(ema_close(appended_input, 3),),
    )
    # Prefix views through shared earlier candles: base vs appended at index 3.
    base_view = IndicatorDecisionFeed.from_bundle(base).view_at(3)
    appended_view = IndicatorDecisionFeed.from_bundle(appended).view_at(3)
    assert base_view.decision_view_hash == appended_view.decision_view_hash
    assert base_view.items[0].visible_prefix_hash == appended_view.items[0].visible_prefix_hash
    assert base.series[0].result_hash != appended.series[0].result_hash
    # Mutation of candle after shared prefix changes later hashes but not earlier bar.
    shared = IndicatorDecisionFeed.from_bundle(base).view_at(2)
    mutated_shared = IndicatorDecisionFeed.from_bundle(mutated).view_at(2)
    assert shared.decision_view_hash == mutated_shared.decision_view_hash
    assert base.bundle_hash != mutated.bundle_hash


def test_visible_value_and_metadata_change_alter_hash() -> None:
    key_a = IndicatorSeriesKey.from_verified(
        indicator_code=IndicatorCode.EMA_CLOSE,
        parameters={"period": 2},
    )
    key_b = IndicatorSeriesKey.from_verified(
        indicator_code=IndicatorCode.EMA_CLOSE,
        parameters={"period": 3},
    )
    policy = default_math_policy()
    indicator_input = indicator_input_from_specs(
        (("10", "11", "9", "10"), ("11", "12", "10", "11"))
    )
    chain_a = compute_prefix_hash_chain(
        symbol=indicator_input.symbol,
        timeframe=indicator_input.timeframe,
        series_key=key_a,
        math_policy=policy,
        values=(None, Decimal("1")),
    )
    chain_b = compute_prefix_hash_chain(
        symbol=indicator_input.symbol,
        timeframe=indicator_input.timeframe,
        series_key=key_a,
        math_policy=policy,
        values=(None, Decimal("2")),
    )
    chain_c = compute_prefix_hash_chain(
        symbol=indicator_input.symbol,
        timeframe=indicator_input.timeframe,
        series_key=key_b,
        math_policy=policy,
        values=(None, Decimal("1")),
    )
    assert chain_a[2] != chain_b[2]
    assert chain_a[0] != chain_c[0]
    assert chain_a[0] == chain_b[0]


def test_cross_platform_canonical_header_bytes() -> None:
    key = IndicatorSeriesKey.from_verified(
        indicator_code=IndicatorCode.TRUE_RANGE,
        parameters={},
    )
    indicator_input = indicator_input_from_specs((("10", "11", "9", "10"),))
    header = build_prefix_header_bytes(
        symbol=indicator_input.symbol,
        timeframe=indicator_input.timeframe,
        series_key=key,
        math_policy=default_math_policy(),
    )
    assert b"\r" not in header
    assert header.startswith(b"{")
    assert b'"indicator_code":"true_range"' in header
