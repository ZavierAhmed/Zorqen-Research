# Zorqen Research - Project Status

> This file records verified repository reality for handoff between coding agents. It must be updated in every milestone commit. Git, tests, and implementation remain authoritative when this file is stale or incorrect.

## 1. Project Identity

- Product: Zorqen Research
- Repository: `ZavierAhmed/Zorqen-Research`
- Default branch: `main`
- Current branch: `main`
- Previous verified commit (Milestone 0.7B): `1ff0ea988a92b0c385912325d92b6b075b635e6b`
- Milestone 0.8 base commit: `1ff0ea988a92b0c385912325d92b6b075b635e6b`
- Milestone result commit: current HEAD containing this status update (exact SHA after commit).
- Master specification: `docs/specification/Zorqen_Research_Master_Specification_v0.1.pdf`
- Current environment: Windows development laptop
- Target deployment: Windows or Linux VPS
- Runtime principle: CPU-first; no mandatory GPU dependency
- Push / GitHub state: report from final `git status -sb` and Actions after push; milestone incomplete until all four checks are green. Do not push unless instructed.

## 2. Product Purpose

Unchanged. Research qualification only; no account/trading APIs.

## 3. Initial Strategy Scope

Family metadata remains seeded. Milestone 0.8 adds pure resampling/alignment only — no executable strategy algorithms.

## 4. Current Milestone

- Milestone: `0.8` — Deterministic Candle Resampling and Multi-Timeframe Alignment
- Status: Complete pending independent review and all four GitHub checks green after push
- Base: `1ff0ea988a92b0c385912325d92b6b075b635e6b`
- Work completed:
  - Exact timeframe derivation plans (`TimeframeDerivationPlan`)
  - Strict complete-bucket resampling + immutable `ResampledCandleSeries`
  - No-lookahead single/multi context alignment + alignment hash
  - Frozen goldens + `zorqen-timeframes verify-golden` CLI
  - ADR 0008 + traceability 0008 (0 NOT TESTED)
- Implementation started: Yes
- Repository commit created: Yes (this milestone commit)

## 5. Latest Verified State

Fixture manifest hash:
`5a0f0d0aacc3bc06969c4d45a38906a8d8a423ab449178b22fbf6a8abe81df80`

Mocked import hashes:
- normalized_sha256: `e54d56e814276e63574c57a66c6776bf3add0827c8401f354362695a34933159`
- content_hash: `ac9762134a0eb1f24b3dd9012df72f01ad19d4c1aa628188fcd6265195c3fc6e`

Golden backtest hashes (unchanged):

```text
28931b0cc74a136963be0d503742e7c04fc3e5df744f9d007350560f93f430c3
3d1134fb7ce251828cd8b4dd8840eac1b8a39c373df425d79d6692d40b840a1c
4b6b354b6f67af1aa06756b68513a2cc5a81066ba03a9c2d19bd939b733f1e02
964dac42d637c0802a847ca5b63dec08c033d6234cbde71fff2b88c886a68a38
e8721eab0f82f7ec9d43c0568c7f929deea2be6b4cd9ec1e84ebef1d5056a766
a9273a5972f6bbae9dc9443385a2d3076dfc2a7549699e4a803e5899e2f928a6
b342b5be8e4943a1bf82abbe26e3329424447515062df4e728154e47dea71c7d
```

Example strategy definition hash (unchanged):
`eb98cec1aa7c862514fa3fca8878769b38a28fa98d96b4c9bb49d41b51dc08f4`

Frozen resampling target hashes:

```text
1m→5m:  56c28d9a685c7e36ea8c0c511ec41630bf58d567c00f7f99f3d3e8ad68f8db94
3m→15m: 11d98ca40e25366fd268c7220b3b3cd1639d019e328863e0f8917bbcdd514940
15m→1h: 50a6b2ddd1bc888e9d9bbc49e222025528a34b2f07773d168cc0c2929306af04
1h→4h:  7762636a0bafc047b942ad51623cb5d40aae6ae389c256e47b9aac11028f76a7
4h→1d:  6a3800671b847193f484959759964fbecbb72ce5e6a96a35e2b49cb636c70b23
1d→1w:  522ca23a8e8b5b400dd78de03a396421af980f5a91bff06085c751634b743a80
```

Multi-context alignment hash (`1h` + `4h`/`1d`):
`30abad8971a01b39c3a8579e9929c42f56fc168b4694885834ab911c9b1f904e`

## 6–8. Product / Architecture / Research Engine

No strategy algorithms, indicators, provider/backtest context wiring, definition persistence/API/UI, campaigns, scoring, MOMO, or trading. Milestone 0.9 is not started.

## 9. Outstanding Work

Awaiting independent review of Milestone 0.8 and confirmation that all four GitHub checks are green after push.

## 10. Verification Evidence (Milestone 0.8)

Commands actually executed:

```text
uv sync --frozen --all-extras
uv run ruff check .                                            # All checks passed
uv run ruff format --check .                                   # 193 files already formatted
uv run mypy src                                                # Success: 116 source files
uv run pytest tests/unit -k "resampl or alignment or timeframe" -q
                                                               # 51 passed, 392 deselected
uv run pytest tests/unit -q                                    # 443 passed
uv run pytest tests/integration/test_artifact_filesystem.py -q # 9 passed
uv run pytest tests/integration -q -m integration              # 34 passed
uv run pytest tests/integration/test_candle_query.py -q        # 5 passed
alembic downgrade base / upgrade head                          # 0001/0002/0003 only; no new migration
uv run zorqen-backtest run-golden --scenario all               # twice, byte-identical
uv run zorqen-timeframes verify-golden --scenario all          # twice, byte-identical
uv run python -m zorqen_research.worker --check                # PostgreSQL reachable
frontend npm ci / lint / test --run / build                    # eslint ok; 15 passed; build ok
docker compose build + up; nginx live/ready/families/datasets  # 200; fixture hash preserved
Linux container (node:22-bookworm): quality.yml sequence       # ruff/mypy; 443 unit; frontend 15 + build
```

Traceability: `docs/verification/0008-timeframe-resampling-traceability.md` — **NOT TESTED: 0**

GitHub Actions: unknown until push.

## 11. Known Defects and Limitations

- Resampling is in-memory only; no derivative dataset persistence
- Backtest provider context is not yet multi-timeframe aware
- No executable Adaptive MTF / Support-Resistance implementation

## 12. Next Authorized Work

None until Milestone 0.8 is independently accepted. Milestone 0.9 is not authorized.
