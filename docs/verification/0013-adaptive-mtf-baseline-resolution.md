# 0013 — Adaptive MTF Baseline Resolution

## Resolution

**Status: `RESOLVED`**

Pinned MOMO Quant commit: `766e31db73bbb130d12ba84f1568745210db6155`  
Inspection date: `2026-08-05`

## Why the illustration is not authoritative

The master-spec JSON under section 26 is an illustrative shape. Several fields differ from MOMO executable behavior (lookback 24 vs 20, retest 0.25/6 vs 0.35/8, atr_percentile vs ATR ratio, structure ATR buffer 0.35 vs stopBufferAtr 0.20). Zorqen freezes MOMO behavior rather than rewriting either system.

## Source discovery

Inspected at the pinned worktree without modifying MOMO:

| Role | Path | Blob SHA-1 |
| --- | --- | --- |
| Evaluator | `.../MomoAdaptive/MomoAdaptiveMtfTrendBreakoutEvaluator.cs` | `9c1048beeca8f8c51e625c37cb4baa2069febad5` |
| Plugin | `.../Implementations/MomoAdaptiveMultiTimeframeTrendBreakoutStrategy.cs` | `9efcdb39d1dcaf32d434eb255f24aa3b315f5730` |
| Rejection codes | `.../MomoAdaptive/MomoAdaptiveMtfRejectionCodes.cs` | `39c44584a761b938b9f1779947b473b5af01b0ef` |
| HTF support | `.../StrategyHigherTimeframeSupport.cs` | `95d08a747997ca5a096aace65364f23107b346d3` |
| Tests | `.../MomoAdaptiveMtfTrendBreakoutTests.cs` | `42ba2dd686b28a3fcdd164900b293eb18a6cff4c` |
| Preferred seed / warmup profile | `.../StrategyDataRequirementService.cs` | `ffe1e29c1aa6bd58af19ba7e8bd7e09d1b884845` |
| Fill timing | `.../Backtesting/BacktestEngine.cs` | `2da2fcf2abc9cd630341b1c7500321a61da94ea4` |
| Canonical seed | `.../Seeding/StrategyDataSeeder.cs` | `bdbbd846c03b1e7224d97f673f01a52494539e86` |

## Evidence hierarchy

1. `AUTHORITATIVE_EXECUTABLE`
2. `AUTHORITATIVE_TEST`
3. `AUTHORITATIVE_FROZEN_DEFINITION`
4. `INFORMATIONAL_DEFAULT` (annotates only; cannot alone satisfy protected semantics)
5. Illustration / legacy / missing

## Master-spec comparison (summary)

| Field | Result |
| --- | --- |
| higher 4h / exec 1h | MATCH as supported mapping; preferred seed 5m→1h DIFFERENT |
| EMA 50/200 | MATCH for HTF; LTF 20/50 DIFFERENT |
| lookback 24 | DIFFERENT (20) |
| requireClose | MATCH behavior; named param NOT_IMPLEMENTED |
| retest 0.25/6 | DIFFERENT (0.35/8); enabled flag NOT_IMPLEMENTED |
| atr_percentile 55 | NOT_IMPLEMENTED (ATR ratio gate) |
| structure_atr_buffer 0.35 | NOT_IMPLEMENTED (stopBufferAtr 0.20 on retest extreme) |
| rMultiple 2.5 | MATCH as fixedRewardRisk |

## Why provider implementation remains deferred

Baseline resolution freezes contracts and fixtures only. No Adaptive MTF decision provider, intents, or state machine is registered in Zorqen. Milestone 1.4 remains unauthorized until independent review of this milestone.

## Conditions before Milestone 1.4

- Independent review of Milestone 1.3
- Green GitHub checks for the 1.3 commit
- Provider work must consume the frozen contract, definition, and parity fixtures without inventing semantics
