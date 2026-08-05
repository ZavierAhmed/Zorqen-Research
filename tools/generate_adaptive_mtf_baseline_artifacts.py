#!/usr/bin/env python3
"""Generate Adaptive MTF baseline contract, evidence, definition, and parity fixtures.

Ports AdaptiveDefaultFixtures from MOMO Quant MomoAdaptiveMtfTrendBreakoutTests.cs
(at pinned commit 766e31db73bbb130d12ba84f1568745210db6155) to deterministic CSV.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from zorqen_research.domain.artifacts import sha256_hex
from zorqen_research.domain.backtesting.enums import PositionDirection
from zorqen_research.domain.baselines.canonical import canonical_json_bytes
from zorqen_research.domain.strategy_definitions.canonical import (
    definition_to_document,
    serialize_definition,
)
from zorqen_research.domain.strategy_definitions.definitions import StrategyDefinition
from zorqen_research.domain.strategy_definitions.enums import DefinitionStatus
from zorqen_research.domain.strategy_definitions.parameters import (
    BooleanParameterDefinition,
    DecimalParameterDefinition,
    IntegerParameterDefinition,
)
from zorqen_research.domain.strategy_definitions.timeframes import TimeframeRequirement
from zorqen_research.domain.strategy_families import (
    ADAPTIVE_MTF_TREND_BREAKOUT_CODE,
    ADAPTIVE_MTF_TREND_BREAKOUT_ID,
)
from zorqen_research.domain.timeframes import Timeframe

ROOT = Path(__file__).resolve().parents[1]
BASELINE_DIR = ROOT / "baselines" / "adaptive_mtf_trend_breakout" / "v1"
FIXTURE_DIR = ROOT / "tests" / "fixtures" / "adaptive_mtf_trend_breakout" / "v1"

MOMO_COMMIT = "766e31db73bbb130d12ba84f1568745210db6155"
MOMO_REPO = "ZavierAhmed/MomoQuant"
INSPECTION_DATE = "2026-08-05"

EVALUATOR_BLOB = "9c1048beeca8f8c51e625c37cb4baa2069febad5"
PLUGIN_BLOB = "9efcdb39d1dcaf32d434eb255f24aa3b315f5730"
REJECTION_BLOB = "39c44584a761b938b9f1779947b473b5af01b0ef"
HTF_SUPPORT_BLOB = "95d08a747997ca5a096aace65364f23107b346d3"
TESTS_BLOB = "42ba2dd686b28a3fcdd164900b293eb18a6cff4c"
REQUIREMENT_BLOB = "ffe1e29c1aa6bd58af19ba7e8bd7e09d1b884845"
BACKTEST_BLOB = "2da2fcf2abc9cd630341b1c7500321a61da94ea4"
SEEDER_BLOB = "bdbbd846c03b1e7224d97f673f01a52494539e86"

EVALUATOR_PATH = (
    "src/backend/src/MomoQuant.Application/Strategies/MomoAdaptive/"
    "MomoAdaptiveMtfTrendBreakoutEvaluator.cs"
)
PLUGIN_PATH = (
    "src/backend/src/MomoQuant.Application/Strategies/Implementations/"
    "MomoAdaptiveMultiTimeframeTrendBreakoutStrategy.cs"
)
REJECTION_PATH = (
    "src/backend/src/MomoQuant.Application/Strategies/MomoAdaptive/MomoAdaptiveMtfRejectionCodes.cs"
)
HTF_PATH = "src/backend/src/MomoQuant.Application/Strategies/StrategyHigherTimeframeSupport.cs"
TESTS_PATH = "src/backend/tests/MomoQuant.UnitTests/Strategies/MomoAdaptiveMtfTrendBreakoutTests.cs"
REQUIREMENT_PATH = (
    "src/backend/src/MomoQuant.Application/Strategies/StrategyDataRequirementService.cs"
)
BACKTEST_PATH = "src/backend/src/MomoQuant.Application/Backtesting/BacktestEngine.cs"
SEEDER_PATH = "src/backend/src/MomoQuant.Persistence/Seeding/StrategyDataSeeder.cs"

DEFINITION_ID = "b8e4f1a0-2c3d-4e5f-9687-1a2b3c4d5e6f"
START = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)


@dataclass(frozen=True, slots=True)
class Candle:
    open_time: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    timeframe: str


def _d(value: float | int | str) -> Decimal:
    return Decimal(str(value))


def _add(
    ltf: list[Candle],
    htf: list[Candle],
    start: datetime,
    i: int,
    o: Decimal,
    h: Decimal,
    low: Decimal,
    c: Decimal,
    *,
    bearish_htf: bool = False,
) -> None:
    open_time = start + timedelta(minutes=i * 5)
    ltf.append(
        Candle(
            open_time=open_time,
            open=o,
            high=h,
            low=low,
            close=c,
            volume=_d(100 + i),
            timeframe="5m",
        )
    )
    if i % 12 == 11:
        htf_open = start + timedelta(minutes=(i - 11) * 5)
        htf.append(
            Candle(
                open_time=htf_open,
                open=(c + _d(50)) if bearish_htf else (c - _d(50)),
                high=h + _d(50),
                low=low - _d(50),
                close=(c - _d(30)) if bearish_htf else (c + _d(30)),
                volume=_d(1000),
                timeframe="1h",
            )
        )


def build_valid_long(
    start: datetime, price_scale: Decimal = Decimal("1")
) -> tuple[list[Candle], list[Candle]]:
    """Port of AdaptiveDefaultFixtures.BuildValidLong."""
    ltf: list[Candle] = []
    htf: list[Candle] = []
    mid = _d(40000) * price_scale
    base_atr = _d(200) * price_scale
    trend = _d(4) * price_scale

    for i in range(2700):
        mid += trend
        open_ = mid - base_atr * _d("0.1")
        close = mid + base_atr * _d("0.2")
        high = max(open_, close) + base_atr * _d("0.3")
        low = min(open_, close) - base_atr * _d("0.2")
        _add(ltf, htf, start, i, open_, high, low, close)

    box_top = mid + base_atr * _d("0.5")
    for j in range(40):
        mid += trend * (_d("2.5") if j >= 20 else _d("0.8"))
        atr = base_atr * _d("2.5") if j >= 24 else base_atr
        open_ = mid - atr * _d("0.15")
        close = mid + atr * _d("0.35")
        high = max(open_, close) + atr * _d("0.25")
        if j < 30:
            high = min(high, box_top + (_d(j) * trend * _d("0.1")))
        if 20 <= j < 30:
            high = min(high, mid + base_atr * _d("0.3"))
        low = min(open_, close) - atr * _d("0.2")
        _add(ltf, htf, start, len(ltf), open_, high, low, close)

    lookback_high = max(c.high for c in ltf[-20:])
    atr = base_atr * _d("2.2")
    open_ = lookback_high - atr * _d("0.05")
    close = lookback_high + atr * _d("0.45")
    _add(ltf, htf, start, len(ltf), open_, close + atr * _d("0.1"), open_ - atr * _d("0.2"), close)

    open_ = lookback_high + atr * _d("0.15")
    low = lookback_high - atr * _d("0.08")
    close = lookback_high + atr * _d("0.10")
    _add(ltf, htf, start, len(ltf), open_, open_ + atr * _d("0.1"), low, close)

    open_ = lookback_high + atr * _d("0.05")
    close = lookback_high + atr * _d("0.40")
    _add(ltf, htf, start, len(ltf), open_, close + atr * _d("0.05"), open_ - atr * _d("0.1"), close)

    return ltf, htf


def build_valid_short(
    start: datetime, price_scale: Decimal = Decimal("1")
) -> tuple[list[Candle], list[Candle]]:
    """Port of AdaptiveDefaultFixtures.BuildValidShort."""
    ltf: list[Candle] = []
    htf: list[Candle] = []
    mid = _d(60000) * price_scale
    base_atr = _d(200) * price_scale
    trend = _d(4) * price_scale

    for i in range(2700):
        mid -= trend
        open_ = mid + base_atr * _d("0.1")
        close = mid - base_atr * _d("0.2")
        high = max(open_, close) + base_atr * _d("0.2")
        low = min(open_, close) - base_atr * _d("0.3")
        _add(ltf, htf, start, i, open_, high, low, close, bearish_htf=True)

    box_bot = mid - base_atr * _d("0.5")
    for j in range(40):
        mid -= trend * (_d("2.5") if j >= 20 else _d("0.8"))
        atr = base_atr * _d("2.5") if j >= 24 else base_atr
        open_ = mid + atr * _d("0.15")
        close = mid - atr * _d("0.35")
        low = min(open_, close) - atr * _d("0.25")
        if j < 30:
            low = max(low, box_bot - (_d(j) * trend * _d("0.1")))
        if 20 <= j < 30:
            low = max(low, mid - base_atr * _d("0.3"))
        high = max(open_, close) + atr * _d("0.2")
        _add(ltf, htf, start, len(ltf), open_, high, low, close, bearish_htf=True)

    lookback_low = min(c.low for c in ltf[-20:])
    atr = base_atr * _d("2.2")
    open_ = lookback_low + atr * _d("0.05")
    close = lookback_low - atr * _d("0.45")
    _add(
        ltf,
        htf,
        start,
        len(ltf),
        open_,
        open_ + atr * _d("0.2"),
        close - atr * _d("0.1"),
        close,
        bearish_htf=True,
    )

    open_ = lookback_low - atr * _d("0.15")
    high = lookback_low + atr * _d("0.08")
    close = lookback_low - atr * _d("0.10")
    _add(
        ltf,
        htf,
        start,
        len(ltf),
        open_,
        high,
        close - atr * _d("0.1"),
        close,
        bearish_htf=True,
    )

    open_ = lookback_low - atr * _d("0.05")
    close = lookback_low - atr * _d("0.40")
    _add(
        ltf,
        htf,
        start,
        len(ltf),
        open_,
        open_ + atr * _d("0.1"),
        close - atr * _d("0.05"),
        close,
        bearish_htf=True,
    )

    return ltf, htf


def write_csv(path: Path, candles: list[Candle]) -> str:
    lines = ["open_time,open,high,low,close,volume"]
    for c in candles:
        ot = c.open_time.strftime("%Y-%m-%dT%H:%M:%SZ")
        lines.append(f"{ot},{c.open},{c.high},{c.low},{c.close},{c.volume}")
    raw = ("\n".join(lines) + "\n").encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    return sha256_hex(raw)


def write_json(path: Path, document: dict[object, object]) -> str:
    raw = canonical_json_bytes(document)  # type: ignore[arg-type]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    return sha256_hex(raw)


def build_contract() -> dict[str, object]:
    return {
        "authority": {
            "commit_sha": MOMO_COMMIT,
            "evidence_class": "AUTHORITATIVE_EXECUTABLE",
            "inspection_date": INSPECTION_DATE,
            "repository": MOMO_REPO,
            "source_blob_sha": EVALUATOR_BLOB,
            "source_file_path": EVALUATOR_PATH,
            "source_symbol_or_type": "MomoAdaptiveMtfTrendBreakoutEvaluator",
        },
        "baseline_code": "adaptive_mtf_trend_breakout_v1",
        "baseline_version": "1.0.0",
        "breakout_rule": {
            "adaptive_buffer": {
                "base_breakout_buffer_atr": "0.10",
                "formula": "clamp(base + (vol_ratio-1)*sensitivity, min, max)",
                "max_breakout_buffer_atr": "0.35",
                "min_breakout_buffer_atr": "0.05",
                "volatility_sensitivity": "0.15",
            },
            "current_bar_excluded_from_range": True,
            "equality_on_level": "close_must_exceed_level_strict",
            "lookback": 20,
            "long": "close > prior range high + adaptive ATR buffer distance",
            "price_field": "close",
            "range_construction": "max high / min low over lookback bars excluding breakout bar",
            "short": "close < prior range low - adaptive ATR buffer distance",
        },
        "family_code": ADAPTIVE_MTF_TREND_BREAKOUT_CODE,
        "family_id": str(ADAPTIVE_MTF_TREND_BREAKOUT_ID),
        "identity": {
            "canonical_portfolio": True,
            "display_name": "MOMO Adaptive Multi-Timeframe Trend Breakout",
            "enabled": True,
            "momo_strategy_code": "MOMO_ADAPTIVE_MTF_TREND_BREAKOUT",
            "production_status": "canonical_enabled",
            "version": "1.0.0",
        },
        "indicator_requirements": {
            "execution": [
                {"kind": "ema", "period": 20, "price_field": "close"},
                {"kind": "ema", "period": 50, "price_field": "close"},
                {"kind": "wilder_atr", "period": 14},
                {"kind": "wilder_atr", "period": 100},
                {"kind": "macd", "fast": 12, "signal": 9, "slow": 26},
            ],
            "higher_timeframe": [
                {"kind": "ema", "period": 50, "price_field": "close"},
                {"kind": "ema", "period": 200, "price_field": "close"},
            ],
            "notes": "Indicators are computed inside the evaluator from OHLC closes; no separate indicator plugin dependency.",
        },
        "master_spec_comparison": {
            "breakout.lookback_24": {
                "authoritative": "20",
                "illustrative": 24,
                "result": "DIFFERENT",
            },
            "breakout.requireClose": {
                "authoritative": "hardcoded close-beyond-level confirmation; named requireClose parameter absent",
                "illustrative": True,
                "result": "MATCH",
                "named_parameter": "NOT_IMPLEMENTED",
            },
            "retest.enabled": {
                "authoritative": "retest always required; no enabled flag",
                "illustrative": True,
                "result": "NOT_IMPLEMENTED",
            },
            "retest.maxBars_6": {
                "authoritative": 8,
                "illustrative": 6,
                "result": "DIFFERENT",
            },
            "retest.toleranceAtr_0.25": {
                "authoritative": "0.35",
                "illustrative": "0.25",
                "result": "DIFFERENT",
            },
            "stop.structure_atr_buffer_0.35": {
                "authoritative": "stop = retest extreme +/- stopBufferAtr(0.20)*retestEventAtr",
                "illustrative": "structure_atr_buffer 0.35",
                "result": "NOT_IMPLEMENTED",
            },
            "target.rMultiple_2.5": {
                "authoritative": "fixedRewardRisk 2.50",
                "illustrative": "2.5",
                "result": "MATCH",
            },
            "timeframes.higher_4h_exec_1h": {
                "authoritative": "supported AdaptiveHtfMapping/v1 pair H1->H4; preferred seed is 5m->1h",
                "illustrative": {"execution": "1h", "higher": "4h"},
                "preferred_seed": "DIFFERENT",
                "result": "MATCH",
            },
            "trend.ema_50_200": {
                "authoritative": "HTF EMA50/200 MATCH; LTF EMA20/50 DIFFERENT from naive 50/200 reading",
                "illustrative": {"fast": 50, "slow": 200},
                "result": "MATCH",
                "ltf_note": "DIFFERENT",
            },
            "volatility.atr_percentile_55": {
                "authoritative": "ATR14/ATR100 ratio gate in [1.00, 2.25]",
                "illustrative": {"minimum": 55, "type": "atr_percentile"},
                "result": "NOT_IMPLEMENTED",
            },
        },
        "outputs": {
            "direction": True,
            "entry_price": True,
            "fingerprint_dedupe": True,
            "reason_codes": True,
            "setup_object": True,
            "signal_emitted": True,
            "stop_price": True,
            "strength_min": "70",
            "target_price": True,
            "position_sizing": False,
        },
        "parameters": {
            "defaults_from": "MomoAdaptiveMtfTrendBreakoutEvaluator.GetDefaultParameterContract",
            "fixed_semantics": [
                "retest always required (no enabled flag)",
                "breakout confirmation uses close beyond level (no requireClose parameter)",
                "volatility uses ATR ratio not atr_percentile",
                "HTF candles only via SliceClosedThrough(evaluationCloseTimeUtc)",
                "entry at confirmation close; backtest fill at candleIndex+1",
            ],
            "items": [
                {
                    "default": 50,
                    "key": "htf_fast_ema_period",
                    "kind": "integer",
                    "momo_key": "htfFastEmaPeriod",
                    "researchable": True,
                },
                {
                    "default": 200,
                    "key": "htf_slow_ema_period",
                    "kind": "integer",
                    "momo_key": "htfSlowEmaPeriod",
                    "researchable": True,
                },
                {
                    "default": 5,
                    "key": "htf_slope_lookback",
                    "kind": "integer",
                    "momo_key": "htfSlopeLookback",
                    "researchable": True,
                },
                {
                    "default": 20,
                    "key": "ltf_fast_ema_period",
                    "kind": "integer",
                    "momo_key": "ltfFastEmaPeriod",
                    "researchable": True,
                },
                {
                    "default": 50,
                    "key": "ltf_slow_ema_period",
                    "kind": "integer",
                    "momo_key": "ltfSlowEmaPeriod",
                    "researchable": True,
                },
                {
                    "default": 20,
                    "key": "breakout_lookback",
                    "kind": "integer",
                    "momo_key": "breakoutLookback",
                    "researchable": True,
                },
                {
                    "default": 14,
                    "key": "fast_atr_period",
                    "kind": "integer",
                    "momo_key": "fastAtrPeriod",
                    "researchable": True,
                },
                {
                    "default": 100,
                    "key": "slow_atr_period",
                    "kind": "integer",
                    "momo_key": "slowAtrPeriod",
                    "researchable": True,
                },
                {
                    "default": "1.00",
                    "key": "min_volatility_ratio",
                    "kind": "decimal",
                    "momo_key": "minVolatilityRatio",
                    "researchable": True,
                },
                {
                    "default": "2.25",
                    "key": "max_volatility_ratio",
                    "kind": "decimal",
                    "momo_key": "maxVolatilityRatio",
                    "researchable": True,
                },
                {
                    "default": "0.10",
                    "key": "base_breakout_buffer_atr",
                    "kind": "decimal",
                    "momo_key": "baseBreakoutBufferAtr",
                    "researchable": True,
                },
                {
                    "default": "0.15",
                    "key": "volatility_sensitivity",
                    "kind": "decimal",
                    "momo_key": "volatilitySensitivity",
                    "researchable": True,
                },
                {
                    "default": "0.05",
                    "key": "min_breakout_buffer_atr",
                    "kind": "decimal",
                    "momo_key": "minBreakoutBufferAtr",
                    "researchable": True,
                },
                {
                    "default": "0.35",
                    "key": "max_breakout_buffer_atr",
                    "kind": "decimal",
                    "momo_key": "maxBreakoutBufferAtr",
                    "researchable": True,
                },
                {
                    "default": 12,
                    "key": "macd_fast",
                    "kind": "integer",
                    "momo_key": "macdFast",
                    "researchable": True,
                },
                {
                    "default": 26,
                    "key": "macd_slow",
                    "kind": "integer",
                    "momo_key": "macdSlow",
                    "researchable": True,
                },
                {
                    "default": 9,
                    "key": "macd_signal",
                    "kind": "integer",
                    "momo_key": "macdSignal",
                    "researchable": True,
                },
                {
                    "default": True,
                    "key": "require_histogram_expansion",
                    "kind": "boolean",
                    "momo_key": "requireHistogramExpansion",
                    "researchable": True,
                },
                {
                    "default": 8,
                    "key": "max_retest_bars",
                    "kind": "integer",
                    "momo_key": "maxRetestBars",
                    "researchable": True,
                },
                {
                    "default": "0.35",
                    "key": "retest_tolerance_atr",
                    "kind": "decimal",
                    "momo_key": "retestToleranceAtr",
                    "researchable": True,
                },
                {
                    "default": "1.00",
                    "key": "max_breakout_chase_atr",
                    "kind": "decimal",
                    "momo_key": "maxBreakoutChaseAtr",
                    "researchable": True,
                },
                {
                    "default": "0.20",
                    "key": "stop_buffer_atr",
                    "kind": "decimal",
                    "momo_key": "stopBufferAtr",
                    "researchable": True,
                },
                {
                    "default": "2.50",
                    "key": "fixed_reward_risk",
                    "kind": "decimal",
                    "momo_key": "fixedRewardRisk",
                    "researchable": True,
                },
                {
                    "default": "70",
                    "key": "min_strength",
                    "kind": "decimal",
                    "momo_key": "minStrength",
                    "researchable": True,
                },
            ],
            "protected_parameters": [
                "htf_fast_ema_period",
                "htf_slow_ema_period",
                "ltf_fast_ema_period",
                "ltf_slow_ema_period",
                "breakout_lookback",
                "fast_atr_period",
                "slow_atr_period",
                "max_retest_bars",
                "retest_tolerance_atr",
                "stop_buffer_atr",
                "fixed_reward_risk",
            ],
            "tunable_parameters": [
                "htf_slope_lookback",
                "min_volatility_ratio",
                "max_volatility_ratio",
                "base_breakout_buffer_atr",
                "volatility_sensitivity",
                "min_breakout_buffer_atr",
                "max_breakout_buffer_atr",
                "macd_fast",
                "macd_slow",
                "macd_signal",
                "require_histogram_expansion",
                "max_breakout_chase_atr",
                "min_strength",
            ],
            "validation_notes": "ValidateParameters requires positive periods, fast<slow for EMA/ATR/MACD, min_vol_ratio<=max, min_buffer<=max_buffer, non-negative ATR buffers/tolerances, fixedRewardRisk>0, minStrength in [0,100].",
        },
        "protected_semantics": {
            "direction": {
                "evidence_ids": [
                    "direction_long_short_symmetry",
                    "direction_valid_long_test",
                    "direction_valid_short_test",
                ],
                "resolved": True,
                "summary": "Long and short candidates from HTF alignment; both directions supported.",
            },
            "entry": {
                "evidence_ids": [
                    "entry_confirmation_close",
                    "entry_valid_long_prices",
                    "entry_valid_short_prices",
                ],
                "resolved": True,
                "summary": "Entry price equals confirmation candle close.",
            },
            "no_lookahead": {
                "evidence_ids": [
                    "no_lookahead_htf_slice",
                    "no_lookahead_htf_support",
                    "no_lookahead_pollution_tests",
                ],
                "resolved": True,
                "summary": "HTF series sliced closed-through evaluation close; incomplete HTF never consumed.",
            },
            "required_indicators": {
                "evidence_ids": [
                    "indicators_evaluator_defaults",
                    "indicators_default_contract_test",
                ],
                "resolved": True,
                "summary": "HTF EMA50/200 + slope; LTF EMA20/50; ATR14/100; MACD 12/26/9.",
            },
            "retest_state": {
                "evidence_ids": [
                    "retest_always_required",
                    "retest_expiration",
                    "retest_confirmation_rules",
                ],
                "resolved": True,
                "summary": "Retest always required within maxBars=8 with ATR tolerance 0.35; invalidation and expiration coded.",
            },
            "signal_timing": {
                "evidence_ids": [
                    "timing_bar_close_evaluate",
                    "timing_fill_next_open",
                    "timing_event_index_test",
                ],
                "resolved": True,
                "summary": "Evaluate at bar close; backtest FillAtCandleIndex = candleIndex+1 (next open).",
            },
            "stop": {
                "evidence_ids": [
                    "stop_retest_extreme_buffer",
                    "stop_valid_long_prices",
                    "stop_valid_short_prices",
                ],
                "resolved": True,
                "summary": "Stop = retest extreme +/- stopBufferAtr(0.20) * retest event-time ATR.",
            },
            "target": {
                "evidence_ids": [
                    "target_fixed_reward_risk",
                    "target_valid_long_prices",
                    "target_valid_short_prices",
                ],
                "resolved": True,
                "summary": "Target = entry +/- risk * fixedRewardRisk(2.50).",
            },
            "volatility_eligibility": {
                "evidence_ids": ["volatility_atr_ratio_gate", "volatility_defaults_test"],
                "resolved": True,
                "summary": "ATR14/ATR100 ratio must lie in [1.00, 2.25]; atr_percentile not implemented.",
            },
            "warmup": {
                "evidence_ids": ["warmup_compute_min_ltf", "warmup_htf_min", "warmup_profile_600"],
                "resolved": True,
                "summary": "Evaluator ComputeMinLtfBars=165; HTF min = htfSlow+htfSlope=205; data-requirement profile warmupCandles=600.",
            },
        },
        "resolution_status": "RESOLVED",
        "retest_rule": {
            "always_required": True,
            "confirmation_long": "bullish close > broken level",
            "confirmation_short": "bearish close < broken level",
            "enabled_parameter": "NOT_IMPLEMENTED",
            "invalidation": "close beyond level +/- tolerance ATR",
            "max_bars": 8,
            "tolerance_atr": "0.35",
            "touch_long": "low within level +/- tolerance*ATR",
            "touch_short": "high within level +/- tolerance*ATR",
        },
        "schema_version": "1",
        "source_files": [
            {
                "blob_sha": EVALUATOR_BLOB,
                "evidence_class": "AUTHORITATIVE_EXECUTABLE",
                "path": EVALUATOR_PATH,
                "role": "evaluator",
            },
            {
                "blob_sha": PLUGIN_BLOB,
                "evidence_class": "AUTHORITATIVE_EXECUTABLE",
                "path": PLUGIN_PATH,
                "role": "strategy_plugin",
            },
            {
                "blob_sha": REJECTION_BLOB,
                "evidence_class": "AUTHORITATIVE_EXECUTABLE",
                "path": REJECTION_PATH,
                "role": "rejection_codes",
            },
            {
                "blob_sha": HTF_SUPPORT_BLOB,
                "evidence_class": "AUTHORITATIVE_EXECUTABLE",
                "path": HTF_PATH,
                "role": "htf_support",
            },
            {
                "blob_sha": REQUIREMENT_BLOB,
                "evidence_class": "INFORMATIONAL_DEFAULT",
                "path": REQUIREMENT_PATH,
                "role": "preferred_seed_and_warmup_profile",
            },
            {
                "blob_sha": BACKTEST_BLOB,
                "evidence_class": "AUTHORITATIVE_EXECUTABLE",
                "path": BACKTEST_PATH,
                "role": "fill_timing",
            },
            {
                "blob_sha": SEEDER_BLOB,
                "evidence_class": "AUTHORITATIVE_FROZEN_DEFINITION",
                "path": SEEDER_PATH,
                "role": "canonical_enabled_seed",
            },
        ],
        "source_tests": [
            {
                "blob_sha": TESTS_BLOB,
                "evidence_class": "AUTHORITATIVE_TEST",
                "path": TESTS_PATH,
                "role": "default_contract_and_parity",
            }
        ],
        "state_machine": {
            "breakout_search": "scan recent bars for breakout then retest then confirmation",
            "duplicate_fingerprint": "reject DuplicateSetup when fingerprint already seen",
            "fingerprint_inputs": "strategyCode, symbolId, timeframe, direction, brokenLevel, breakoutIndex, retestIndex, candles",
            "regimes_allowed": ["Trending", "Breakout"],
        },
        "stop_rule": {
            "long": "retest_low - stopBufferAtr * retest_event_atr",
            "short": "retest_high + stopBufferAtr * retest_event_atr",
            "stop_buffer_atr": "0.20",
            "structure_reference": "retest extreme (not breakout structure ATR buffer 0.35)",
            "uses_confirmation_atr": False,
        },
        "target_rule": {
            "fixed_reward_risk": "2.50",
            "long": "entry + risk * fixedRewardRisk",
            "short": "entry - risk * fixedRewardRisk",
            "zero_or_negative_risk": "InvalidStop / InvalidTarget",
        },
        "timeframes": {
            "allowed_execution": ["5m", "15m", "1h", "4h"],
            "evaluator_min_ltf_bars": 165,
            "evaluator_min_ltf_formula": "max(slowAtr,ltfSlowEma)+breakoutLookback+maxRetestBars+macdSlow+macdSignal+2",
            "htf_availability": "SliceClosedThrough(evaluationCloseTimeUtc); incomplete HTF never consumed",
            "htf_mapping_contract": "AdaptiveHtfMapping/v1",
            "htf_warmup_bars": 205,
            "htf_warmup_formula": "htfSlowEmaPeriod + htfSlopeLookback",
            "mapping": {"15m": "4h", "1h": "4h", "4h": "1d", "5m": "1h"},
            "preferred_execution": "5m",
            "preferred_higher": "1h",
            "requirement_warmup_profile_bars": 600,
            "warmup_notes": "Definition uses evaluator ComputeMinLtfBars=165 and HTF warmup=205. StrategyDataRequirementService profile warmupCandles=600 is a data-loading profile, not the evaluator minimum.",
        },
        "timing": {
            "backtest_fill": "FillAtCandleIndex = candleIndex + 1 (next open)",
            "decision_point": "bar_close",
            "entry_price_source": "confirmation_candle_close",
            "intrabar": False,
        },
        "trend_rule": {
            "htf": {
                "equality": "strict inequalities",
                "fast_ema": 50,
                "long": "fast>slow AND slope>0 AND close>fast",
                "short": "fast<slow AND slope<0 AND close<fast",
                "slope_lookback": 5,
                "slow_ema": 200,
                "uses_latest_closed_htf": True,
            },
            "ltf": {
                "fast_ema": 20,
                "long": "exec fast EMA > slow EMA",
                "short": "exec fast EMA < slow EMA",
                "slow_ema": 50,
            },
            "macd": {
                "fast": 12,
                "histogram_expansion_required_by_default": True,
                "long": "histogram > 0 (and > previous when expansion required)",
                "short": "histogram < 0 (and < previous when expansion required)",
                "signal": 9,
                "slow": 26,
            },
        },
        "unresolved_items": [],
        "volatility_rule": {
            "atr_percentile": "NOT_IMPLEMENTED",
            "fast_atr_period": 14,
            "mandatory": True,
            "max_ratio": "2.25",
            "min_ratio": "1.00",
            "ratio_at_breakout_event": True,
            "slow_atr_period": 100,
            "type": "atr_ratio",
        },
    }


def build_evidence() -> dict[str, object]:
    def row(
        claim_id: str,
        claim: str,
        classification: str,
        file_path: str | None,
        blob_sha: str | None,
        symbol: str | None,
        line_or_member: str | None,
        supporting_test: str | None,
        notes: str,
    ) -> dict[str, object]:
        return {
            "blob_sha": blob_sha,
            "claim": claim,
            "claim_id": claim_id,
            "classification": classification,
            "commit_sha": MOMO_COMMIT,
            "file_path": file_path,
            "line_or_member_reference": line_or_member,
            "notes": notes,
            "repository": MOMO_REPO,
            "supporting_test": supporting_test,
            "symbol": symbol,
        }

    claims = [
        row(
            "direction_long_short_symmetry",
            "Evaluator builds long and short candidates with symmetric gates.",
            "AUTHORITATIVE_EXECUTABLE",
            EVALUATOR_PATH,
            EVALUATOR_BLOB,
            "TryBuildLongCandidate/TryBuildShortCandidate",
            "TryBuildLongCandidate;TryBuildShortCandidate",
            None,
            "Both directions are executable paths when HTF alignment allows.",
        ),
        row(
            "direction_valid_long_test",
            "Valid long fixture emits Long direction.",
            "AUTHORITATIVE_TEST",
            TESTS_PATH,
            TESTS_BLOB,
            "EvaluateAtCurrentCandle_ValidLong_WithExactDefaults",
            "EvaluateAtCurrentCandle_ValidLong_WithExactDefaults",
            "EvaluateAtCurrentCandle_ValidLong_WithExactDefaults",
            "Asserts TradeDirection.Long.",
        ),
        row(
            "direction_valid_short_test",
            "Valid short fixture emits Short direction.",
            "AUTHORITATIVE_TEST",
            TESTS_PATH,
            TESTS_BLOB,
            "EvaluateAtCurrentCandle_ValidShort_WithExactDefaults",
            "EvaluateAtCurrentCandle_ValidShort_WithExactDefaults",
            "EvaluateAtCurrentCandle_ValidShort_WithExactDefaults",
            "Asserts TradeDirection.Short.",
        ),
        row(
            "entry_confirmation_close",
            "Entry equals confirmation candle close.",
            "AUTHORITATIVE_EXECUTABLE",
            EVALUATOR_PATH,
            EVALUATOR_BLOB,
            "TryBuildLongCandidate",
            "var entry = candles[currentIndex].Close",
            None,
            "Same for short path.",
        ),
        row(
            "entry_valid_long_prices",
            "Valid long entry price is 51540.000.",
            "AUTHORITATIVE_TEST",
            TESTS_PATH,
            TESTS_BLOB,
            "EvaluateAtCurrentCandle_ValidLong_WithExactDefaults",
            "Assert.Equal(51540.000m, candidate.EntryPrice)",
            "EvaluateAtCurrentCandle_ValidLong_WithExactDefaults",
            "Frozen expected entry from AdaptiveDefaultFixtures.",
        ),
        row(
            "entry_valid_short_prices",
            "Valid short entry price is 48460.000.",
            "AUTHORITATIVE_TEST",
            TESTS_PATH,
            TESTS_BLOB,
            "EvaluateAtCurrentCandle_ValidShort_WithExactDefaults",
            "Assert.Equal(48460.000m, candidate.EntryPrice)",
            "EvaluateAtCurrentCandle_ValidShort_WithExactDefaults",
            "Frozen expected entry from AdaptiveDefaultFixtures.",
        ),
        row(
            "indicators_default_contract_test",
            "Default parameter contract matches EMA/ATR/MACD defaults.",
            "AUTHORITATIVE_TEST",
            TESTS_PATH,
            TESTS_BLOB,
            "GetDefaultParameterContract_MatchesExactDefaults",
            "GetDefaultParameterContract_MatchesExactDefaults",
            "GetDefaultParameterContract_MatchesExactDefaults",
            "Asserts periods 50/200/5/20/50/20/14/100 and MACD 12/26/9.",
        ),
        row(
            "indicators_evaluator_defaults",
            "Parameter defaults encode HTF/LTF EMA, ATR, and MACD periods.",
            "AUTHORITATIVE_EXECUTABLE",
            EVALUATOR_PATH,
            EVALUATOR_BLOB,
            "MomoAdaptiveMtfParameters",
            "MomoAdaptiveMtfParameters property initializers",
            None,
            "Consumed by ReadParameters and Compute* helpers.",
        ),
        row(
            "no_lookahead_htf_slice",
            "HTF candles are sliced closed-through evaluation close time.",
            "AUTHORITATIVE_EXECUTABLE",
            HTF_PATH,
            HTF_SUPPORT_BLOB,
            "SliceHigherTimeframeCandles",
            "HigherTimeframeCandleView.SliceClosedThrough",
            None,
            "Incomplete higher-timeframe candles are never consumed.",
        ),
        row(
            "no_lookahead_htf_support",
            "BuildContextHigherTimeframe uses evaluationCloseTimeUtc for Adaptive mapping.",
            "AUTHORITATIVE_EXECUTABLE",
            HTF_PATH,
            HTF_SUPPORT_BLOB,
            "BuildContextHigherTimeframe",
            "BuildContextHigherTimeframe",
            None,
            "Adaptive mapping only; general strategies do not load HTF bars.",
        ),
        row(
            "no_lookahead_pollution_tests",
            "Adaptive production LTF pollution tests assert HTF closed-through visibility.",
            "AUTHORITATIVE_TEST",
            "src/backend/tests/MomoQuant.UnitTests/Strategies/AdaptiveProductionLtfPollutionTests.cs",
            None,
            "AdaptiveProductionLtfPollutionTests",
            "AdaptiveProductionLtfPollutionTests",
            "AdaptiveProductionLtfPollutionTests",
            "Supports no-lookahead HTF visibility claims; blob not pinned in summary list.",
        ),
        row(
            "retest_always_required",
            "Retest search is mandatory before confirmation; no enabled flag.",
            "AUTHORITATIVE_EXECUTABLE",
            EVALUATOR_PATH,
            EVALUATOR_BLOB,
            "TryBuildLongCandidate",
            "retest search loop before confirmation",
            None,
            "Illustrative retest.enabled has no MOMO parameter.",
        ),
        row(
            "retest_confirmation_rules",
            "Long confirmation requires bullish close above level; short bearish below.",
            "AUTHORITATIVE_EXECUTABLE",
            EVALUATOR_PATH,
            EVALUATOR_BLOB,
            "IsLongConfirmation/IsShortConfirmation",
            "IsLongConfirmation;IsShortConfirmation",
            None,
            "Uses StrategyCandleHelper bullish/bearish helpers.",
        ),
        row(
            "retest_expiration",
            "Retest expires when currentIndex > breakoutIndex + MaxRetestBars.",
            "AUTHORITATIVE_EXECUTABLE",
            EVALUATOR_PATH,
            EVALUATOR_BLOB,
            "TryBuildLongCandidate",
            "RetestExpired when currentIndex > breakoutIndex + MaxRetestBars",
            None,
            "Default MaxRetestBars=8.",
        ),
        row(
            "signal_timing_unused_placeholder",
            "placeholder removed",
            "MISSING",
            None,
            None,
            None,
            None,
            None,
            "placeholder",
        ),
        row(
            "stop_retest_extreme_buffer",
            "Long stop = retestLow - StopBufferAtr * retestEventAtrFast.",
            "AUTHORITATIVE_EXECUTABLE",
            EVALUATOR_PATH,
            EVALUATOR_BLOB,
            "TryBuildLongCandidate",
            "var stop = retestLow - (settings.StopBufferAtr * retestEventAtrFast)",
            None,
            "Uses retest event-time ATR, not confirmation ATR.",
        ),
        row(
            "stop_valid_long_prices",
            "Valid long stop equals frozen MOMO assertion.",
            "AUTHORITATIVE_TEST",
            TESTS_PATH,
            TESTS_BLOB,
            "EvaluateAtCurrentCandle_ValidLong_WithExactDefaults",
            "Assert.Equal(51260.643226472988051101254046m, candidate.StopLoss)",
            "EvaluateAtCurrentCandle_ValidLong_WithExactDefaults",
            "Exact stop from authoritative test.",
        ),
        row(
            "stop_valid_short_prices",
            "Valid short stop equals frozen MOMO assertion.",
            "AUTHORITATIVE_TEST",
            TESTS_PATH,
            TESTS_BLOB,
            "EvaluateAtCurrentCandle_ValidShort_WithExactDefaults",
            "Assert.Equal(48739.356773527011948898745954m, candidate.StopLoss)",
            "EvaluateAtCurrentCandle_ValidShort_WithExactDefaults",
            "Exact stop from authoritative test.",
        ),
        row(
            "target_fixed_reward_risk",
            "Target uses FixedRewardRisk multiple of risk.",
            "AUTHORITATIVE_EXECUTABLE",
            EVALUATOR_PATH,
            EVALUATOR_BLOB,
            "TryComputeLongTarget/TryComputeShortTarget",
            "TryComputeLongTarget;TryComputeShortTarget",
            None,
            "Default FixedRewardRisk=2.50.",
        ),
        row(
            "target_valid_long_prices",
            "Valid long target equals frozen MOMO assertion.",
            "AUTHORITATIVE_TEST",
            TESTS_PATH,
            TESTS_BLOB,
            "EvaluateAtCurrentCandle_ValidLong_WithExactDefaults",
            "Assert.Equal(52238.391933817529872246864885m, candidate.TakeProfit)",
            "EvaluateAtCurrentCandle_ValidLong_WithExactDefaults",
            "Exact target from authoritative test.",
        ),
        row(
            "target_valid_short_prices",
            "Valid short target equals frozen MOMO assertion.",
            "AUTHORITATIVE_TEST",
            TESTS_PATH,
            TESTS_BLOB,
            "EvaluateAtCurrentCandle_ValidShort_WithExactDefaults",
            "Assert.Equal(47761.608066182470127753135115m, candidate.TakeProfit)",
            "EvaluateAtCurrentCandle_ValidShort_WithExactDefaults",
            "Exact target from authoritative test.",
        ),
        row(
            "timing_bar_close_evaluate",
            "Plugin evaluates on StrategyContext candles at current bar.",
            "AUTHORITATIVE_EXECUTABLE",
            PLUGIN_PATH,
            PLUGIN_BLOB,
            "MomoAdaptiveMultiTimeframeTrendBreakoutStrategy.Evaluate",
            "Evaluate",
            None,
            "Backtest engine supplies closed candle context.",
        ),
        row(
            "timing_event_index_test",
            "Frozen breakout/retest/confirmation indices and close times.",
            "AUTHORITATIVE_TEST",
            TESTS_PATH,
            TESTS_BLOB,
            "EvaluateAtCurrentCandle_EventTimeIndexes_AreStable",
            "expectedConfirmationCloseUtc = 2024-01-10T12:35:00Z",
            "EvaluateAtCurrentCandle_EventTimeIndexes_AreStable",
            "Confirms decision timing on confirmation bar close.",
        ),
        row(
            "timing_fill_next_open",
            "Backtest fill scheduled at candleIndex+1.",
            "AUTHORITATIVE_EXECUTABLE",
            BACKTEST_PATH,
            BACKTEST_BLOB,
            "BacktestEngine",
            "FillAtCandleIndex = candleIndex + 1",
            None,
            "Next-open fill semantics for emitted entries.",
        ),
        row(
            "volatility_atr_ratio_gate",
            "Breakout path requires ATR fast/slow ratio within min/max.",
            "AUTHORITATIVE_EXECUTABLE",
            EVALUATOR_PATH,
            EVALUATOR_BLOB,
            "TryBuildLongCandidate",
            "volRatio vs MinVolatilityRatio/MaxVolatilityRatio",
            None,
            "atr_percentile is not present in evaluator.",
        ),
        row(
            "volatility_defaults_test",
            "Defaults include minVolatilityRatio 1.00 and maxVolatilityRatio 2.25.",
            "AUTHORITATIVE_TEST",
            TESTS_PATH,
            TESTS_BLOB,
            "GetDefaultParameterContract_MatchesExactDefaults",
            "GetDefaultParameterContract_MatchesExactDefaults",
            "GetDefaultParameterContract_MatchesExactDefaults",
            "Ratio gate defaults asserted via ReadParameters.",
        ),
        row(
            "warmup_compute_min_ltf",
            "ComputeMinLtfBars formula yields 165 with defaults.",
            "AUTHORITATIVE_EXECUTABLE",
            EVALUATOR_PATH,
            EVALUATOR_BLOB,
            "ComputeMinLtfBars",
            "max(SlowAtr,LtfSlowEma)+BreakoutLookback+MaxRetestBars+MacdSlow+MacdSignal+2",
            None,
            "ComputeWarmupBars delegates to ComputeMinLtfBars.",
        ),
        row(
            "warmup_htf_min",
            "HTF minimum bars are HtfSlowEmaPeriod + HtfSlopeLookback (=205).",
            "AUTHORITATIVE_EXECUTABLE",
            EVALUATOR_PATH,
            EVALUATOR_BLOB,
            "EvaluateAtCurrentCandle",
            "minHtfBars = settings.HtfSlowEmaPeriod + settings.HtfSlopeLookback",
            None,
            "Insufficient HTF returns MtfDataUnavailable.",
        ),
        row(
            "warmup_profile_600",
            "StrategyDataRequirementService profile uses warmupCandles=600 for Adaptive.",
            "INFORMATIONAL_DEFAULT",
            REQUIREMENT_PATH,
            REQUIREMENT_BLOB,
            "RequirementProfile for MomoAdaptiveMultiTimeframeTrendBreakout",
            "warmupCandles: 600",
            None,
            "Data-loading profile; evaluator minimum remains 165. Preferred execution 5m documented here.",
        ),
    ]
    # Remove placeholder and sort
    claims = [c for c in claims if c["claim_id"] != "signal_timing_unused_placeholder"]
    claims.sort(key=lambda c: str(c["claim_id"]))
    return {
        "baseline_code": "adaptive_mtf_trend_breakout_v1",
        "baseline_version": "1.0.0",
        "claims": claims,
        "family_code": ADAPTIVE_MTF_TREND_BREAKOUT_CODE,
        "inspection_date": INSPECTION_DATE,
        "schema_version": "1",
    }


def build_definition(contract_hash: str) -> StrategyDefinition:
    def idef(
        key: str,
        display: str,
        desc: str,
        default: int,
        minimum: int,
        maximum: int,
        *,
        researchable: bool = True,
    ) -> IntegerParameterDefinition:
        return IntegerParameterDefinition(
            key=key,
            display_name=display,
            description=desc,
            researchable=researchable,
            default_value=default,
            minimum=minimum,
            maximum=maximum,
            step=1,
        )

    def ddef(
        key: str,
        display: str,
        desc: str,
        default: str,
        minimum: str | None,
        maximum: str | None,
        step: str | None,
        *,
        researchable: bool = True,
    ) -> DecimalParameterDefinition:
        return DecimalParameterDefinition(
            key=key,
            display_name=display,
            description=desc,
            researchable=researchable,
            default_value=Decimal(default),
            minimum=None if minimum is None else Decimal(minimum),
            maximum=None if maximum is None else Decimal(maximum),
            step=None if step is None else Decimal(step),
        )

    parameters = (
        ddef(
            "base_breakout_buffer_atr",
            "Base Breakout Buffer ATR",
            "Base adaptive breakout buffer in ATR units (MOMO baseBreakoutBufferAtr).",
            "0.10",
            "0",
            "2",
            "0.01",
        ),
        idef(
            "breakout_lookback",
            "Breakout Lookback",
            "Bars used for prior range high/low excluding breakout bar (MOMO breakoutLookback).",
            20,
            1,
            500,
        ),
        idef(
            "fast_atr_period",
            "Fast ATR Period",
            "Wilder ATR fast period (MOMO fastAtrPeriod).",
            14,
            1,
            500,
        ),
        ddef(
            "fixed_reward_risk",
            "Fixed Reward Risk",
            "Target multiple of risk (MOMO fixedRewardRisk).",
            "2.50",
            "0.01",
            "20",
            "0.01",
        ),
        idef(
            "htf_fast_ema_period",
            "HTF Fast EMA Period",
            "Higher-timeframe fast EMA period (MOMO htfFastEmaPeriod).",
            50,
            1,
            500,
        ),
        idef(
            "htf_slope_lookback",
            "HTF Slope Lookback",
            "Bars between HTF fast EMA samples for slope (MOMO htfSlopeLookback).",
            5,
            1,
            100,
        ),
        idef(
            "htf_slow_ema_period",
            "HTF Slow EMA Period",
            "Higher-timeframe slow EMA period (MOMO htfSlowEmaPeriod).",
            200,
            2,
            1000,
        ),
        idef(
            "ltf_fast_ema_period",
            "LTF Fast EMA Period",
            "Execution-timeframe fast EMA period (MOMO ltfFastEmaPeriod).",
            20,
            1,
            500,
        ),
        idef(
            "ltf_slow_ema_period",
            "LTF Slow EMA Period",
            "Execution-timeframe slow EMA period (MOMO ltfSlowEmaPeriod).",
            50,
            2,
            1000,
        ),
        idef(
            "macd_fast",
            "MACD Fast",
            "MACD fast EMA period (MOMO macdFast).",
            12,
            1,
            100,
        ),
        idef(
            "macd_signal",
            "MACD Signal",
            "MACD signal period (MOMO macdSignal).",
            9,
            1,
            100,
        ),
        idef(
            "macd_slow",
            "MACD Slow",
            "MACD slow EMA period (MOMO macdSlow).",
            26,
            2,
            200,
        ),
        ddef(
            "max_breakout_buffer_atr",
            "Max Breakout Buffer ATR",
            "Upper clamp for adaptive breakout buffer (MOMO maxBreakoutBufferAtr).",
            "0.35",
            "0",
            "5",
            "0.01",
        ),
        ddef(
            "max_breakout_chase_atr",
            "Max Breakout Chase ATR",
            "Maximum confirmation chase beyond broken level in ATR (MOMO maxBreakoutChaseAtr).",
            "1.00",
            "0",
            "20",
            "0.01",
        ),
        idef(
            "max_retest_bars",
            "Max Retest Bars",
            "Maximum bars after breakout to complete retest (MOMO maxRetestBars).",
            8,
            1,
            100,
        ),
        ddef(
            "max_volatility_ratio",
            "Max Volatility Ratio",
            "Maximum ATR14/ATR100 ratio (MOMO maxVolatilityRatio).",
            "2.25",
            "0.01",
            "20",
            "0.01",
        ),
        ddef(
            "min_breakout_buffer_atr",
            "Min Breakout Buffer ATR",
            "Lower clamp for adaptive breakout buffer (MOMO minBreakoutBufferAtr).",
            "0.05",
            "0",
            "5",
            "0.01",
        ),
        ddef(
            "min_strength",
            "Min Strength",
            "Minimum strength score in [0,100] (MOMO minStrength).",
            "70",
            "0",
            "100",
            "1",
        ),
        ddef(
            "min_volatility_ratio",
            "Min Volatility Ratio",
            "Minimum ATR14/ATR100 ratio (MOMO minVolatilityRatio).",
            "1.00",
            "0",
            "20",
            "0.01",
        ),
        BooleanParameterDefinition(
            key="require_histogram_expansion",
            display_name="Require Histogram Expansion",
            description="Require MACD histogram expansion vs prior bar (MOMO requireHistogramExpansion).",
            researchable=True,
            default_value=True,
        ),
        ddef(
            "retest_tolerance_atr",
            "Retest Tolerance ATR",
            "ATR tolerance for retest touch/invalidation (MOMO retestToleranceAtr).",
            "0.35",
            "0",
            "5",
            "0.01",
        ),
        idef(
            "slow_atr_period",
            "Slow ATR Period",
            "Wilder ATR slow period (MOMO slowAtrPeriod).",
            100,
            2,
            1000,
        ),
        ddef(
            "stop_buffer_atr",
            "Stop Buffer ATR",
            "ATR buffer beyond retest extreme for stop (MOMO stopBufferAtr).",
            "0.20",
            "0",
            "5",
            "0.01",
        ),
        ddef(
            "volatility_sensitivity",
            "Volatility Sensitivity",
            "Adaptive buffer sensitivity to volatility ratio (MOMO volatilitySensitivity).",
            "0.15",
            "0",
            "5",
            "0.01",
        ),
    )

    from uuid import UUID

    return StrategyDefinition(
        schema_version="1",
        definition_id=UUID(DEFINITION_ID),
        family_id=ADAPTIVE_MTF_TREND_BREAKOUT_ID,
        family_code=ADAPTIVE_MTF_TREND_BREAKOUT_CODE,
        definition_code="momo_adaptive_mtf_trend_breakout_v1",
        display_name="MOMO Adaptive Multi-Timeframe Trend Breakout v1",
        description=(
            "Approved Zorqen Research baseline definition bound to the pinned MOMO Quant "
            "Adaptive MTF evaluator at commit 766e31db73bbb130d12ba84f1568745210db6155. "
            "Does not implement a strategy provider."
        ),
        version="1.0.0",
        status=DefinitionStatus.APPROVED,
        execution_timeframe=Timeframe.M5,
        execution_warmup_bars=165,
        context_requirements=(TimeframeRequirement(timeframe=Timeframe.H1, warmup_bars=205),),
        supported_directions=(PositionDirection.LONG, PositionDirection.SHORT),
        parameters=parameters,
        source_spec_sha256=contract_hash,
    )


def write_fixtures() -> str:
    cases_meta: list[dict[str, object]] = []

    long_ltf, long_htf = build_valid_long(START)
    short_ltf, short_htf = build_valid_short(START)

    # Filter HTF to closed-through confirmation close (last LTF close).
    def closed_through(htf: list[Candle], evaluation_close: datetime) -> list[Candle]:
        return [c for c in htf if (c.open_time + timedelta(hours=1)) <= evaluation_close]

    long_confirm_close = long_ltf[-1].open_time + timedelta(minutes=5)
    short_confirm_close = short_ltf[-1].open_time + timedelta(minutes=5)
    long_htf_vis = closed_through(long_htf, long_confirm_close)
    short_htf_vis = closed_through(short_htf, short_confirm_close)

    long_dir = FIXTURE_DIR / "long_entry"
    short_dir = FIXTURE_DIR / "short_entry"

    long_exec_hash = write_csv(long_dir / "execution.csv", long_ltf)
    long_ctx_hash = write_csv(long_dir / "context_1h.csv", long_htf_vis)
    short_exec_hash = write_csv(short_dir / "execution.csv", short_ltf)
    short_ctx_hash = write_csv(short_dir / "context_1h.csv", short_htf_vis)

    long_expected = {
        "case_id": "long_entry",
        "decision_close_time": long_confirm_close.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "decision_open_time": long_ltf[-1].open_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "direction": "long",
        "entry_price": "51540",
        "fingerprint": "6046B1A38922BED1",
        "reason_code": "EntryConfirmed",
        "setup_state": "retest_confirmed",
        "signal_emitted": True,
        "stop_price": "51260.643226472988051101254046",
        "strength": "71.570666073762475131384281568",
        "target_price": "52238.391933817529872246864885",
        "visible_context_count": len(long_htf_vis),
        "visible_execution_count": len(long_ltf),
    }
    short_expected = {
        "case_id": "short_entry",
        "decision_close_time": short_confirm_close.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "decision_open_time": short_ltf[-1].open_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "direction": "short",
        "entry_price": "48460",
        "fingerprint": "F99C1578DBF02B61",
        "reason_code": "EntryConfirmed",
        "setup_state": "retest_confirmed",
        "signal_emitted": True,
        "stop_price": "48739.356773527011948898745954",
        "strength": "71.759963025343603377057197435",
        "target_price": "47761.608066182470127753135115",
        "visible_context_count": len(short_htf_vis),
        "visible_execution_count": len(short_ltf),
    }

    long_exp_hash = write_json(long_dir / "expected.json", long_expected)
    short_exp_hash = write_json(short_dir / "expected.json", short_expected)

    for case_id, exec_h, ctx_h, exp_h, test_name in (
        (
            "long_entry",
            long_exec_hash,
            long_ctx_hash,
            long_exp_hash,
            "EvaluateAtCurrentCandle_ValidLong_WithExactDefaults",
        ),
        (
            "short_entry",
            short_exec_hash,
            short_ctx_hash,
            short_exp_hash,
            "EvaluateAtCurrentCandle_ValidShort_WithExactDefaults",
        ),
    ):
        cases_meta.append(
            {
                "case_id": case_id,
                "context_csv_hash": ctx_h,
                "expected_hash": exp_h,
                "execution_csv_hash": exec_h,
                "provenance": {
                    "commit_sha": MOMO_COMMIT,
                    "fixture_builder": "tools/generate_adaptive_mtf_baseline_artifacts.py",
                    "repository": MOMO_REPO,
                    "source_test": test_name,
                    "source_test_file": TESTS_PATH,
                    "source_test_blob_sha": TESTS_BLOB,
                },
            }
        )

    cases_meta.sort(key=lambda c: str(c["case_id"]))
    manifest = {
        "baseline_code": "adaptive_mtf_trend_breakout_v1",
        "baseline_version": "1.0.0",
        "cases": cases_meta,
        "family_code": ADAPTIVE_MTF_TREND_BREAKOUT_CODE,
        "schema_version": "1",
    }
    return write_json(FIXTURE_DIR / "manifest.json", manifest)


def main() -> None:
    BASELINE_DIR.mkdir(parents=True, exist_ok=True)
    contract = build_contract()
    evidence = build_evidence()
    contract_hash = write_json(BASELINE_DIR / "baseline_contract.json", contract)
    evidence_hash = write_json(BASELINE_DIR / "source_evidence.json", evidence)

    definition = build_definition(contract_hash)
    def_doc = definition_to_document(definition)
    definition_hash = sha256_hex(serialize_definition(definition))
    write_json(BASELINE_DIR / "approved_definition.json", def_doc)

    fixture_hash = write_fixtures()

    # Sanity: entry prices from generated series should match MOMO assertions.
    long_ltf, _ = build_valid_long(START)
    short_ltf, _ = build_valid_short(START)
    assert long_ltf[-1].close == Decimal("51540"), long_ltf[-1].close
    assert short_ltf[-1].close == Decimal("48460"), short_ltf[-1].close
    assert len(long_ltf) == 2743
    assert long_ltf[-1].open_time == datetime(2024, 1, 10, 12, 30, 0, tzinfo=UTC)

    print(
        json.dumps(
            {
                "baseline_contract_hash": contract_hash,
                "source_evidence_hash": evidence_hash,
                "strategy_definition_hash": definition_hash,
                "fixture_manifest_hash": fixture_hash,
                "definition_id": DEFINITION_ID,
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
