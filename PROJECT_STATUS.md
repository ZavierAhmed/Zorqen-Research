# Zorqen Research - Project Status

> This file records verified repository reality for handoff between coding agents. It must be updated in every milestone commit. Git, tests, and implementation remain authoritative when this file is stale or incorrect.

## 1. Project Identity

- Product: Zorqen Research
- Repository: `ZavierAhmed/Zorqen-Research`
- Default branch: `main`
- Current branch: `main`
- Previous verified commit (Milestone 0.6B): `b48ef6b9a7ef4c4325f34c5102dccf86c93e6f74`
- Milestone 0.7 base commit: `b48ef6b9a7ef4c4325f34c5102dccf86c93e6f74`
- Milestone result commit: current HEAD containing this status update.
- Exact SHA: report after commit.
- Master specification: `docs/specification/Zorqen_Research_Master_Specification_v0.1.pdf`
- Current environment: Windows development laptop
- Target deployment: Windows or Linux VPS
- Runtime principle: CPU-first; no mandatory GPU dependency
- Push state: confirm with `git status -sb` after commit (do not push unless instructed)

## 2. Product Purpose

Unchanged. Research qualification only; no account/trading APIs.

## 3. Initial Strategy Scope

Family metadata remains seeded for Adaptive MTF Trend Breakout (primary) and Support and Resistance (secondary). Milestone 0.7 adds the immutable definition schema only — no executable strategy algorithms.

## 4. Current Milestone

- Milestone: `0.7` — Immutable Strategy Definition and Parameter Schema
- Status: Complete pending independent review
- Base: `b48ef6b9a7ef4c4325f34c5102dccf86c93e6f74`
- Work completed:
  - Domain models for definitions, typed parameters, timeframes, directions, parameter sets, instances
  - Exact seeded family ID/code binding via `SEEDED_FAMILY_PAIRS`
  - Strict JSON parser (BOM/UTF-8/duplicates/unknown fields/size/NaN)
  - Canonical serialization and definition/parameter-set/instance hashes
  - `zorqen-strategy` CLI (`validate-definition`, `bind-parameters`)
  - Draft test fixtures (not production baselines)
  - ADR 0007 + requirement traceability + red-team documentation
- Implementation started: Yes
- Repository commit created: Yes (this milestone commit)

## 5. Latest Verified State

Fixture manifest hash:
`5a0f0d0aacc3bc06969c4d45a38906a8d8a423ab449178b22fbf6a8abe81df80`

Mocked import hashes:
- normalized_sha256: `e54d56e814276e63574c57a66c6776bf3add0827c8401f354362695a34933159`
- content_hash: `ac9762134a0eb1f24b3dd9012df72f01ad19d4c1aa628188fcd6265195c3fc6e`

Golden result hashes (unchanged):

```text
end-of-data:           28931b0cc74a136963be0d503742e7c04fc3e5df744f9d007350560f93f430c3
explicit-exit:         3d1134fb7ce251828cd8b4dd8840eac1b8a39c373df425d79d6692d40b840a1c
long-stop:             4b6b354b6f67af1aa06756b68513a2cc5a81066ba03a9c2d19bd939b733f1e02
long-target:           964dac42d637c0802a847ca5b63dec08c033d6234cbde71fff2b88c886a68a38
pending-final-entry:   e8721eab0f82f7ec9d43c0568c7f929deea2be6b4cd9ec1e84ebef1d5056a766
same-bar-stop-first:   a9273a5972f6bbae9dc9443385a2d3076dfc2a7549699e4a803e5899e2f928a6
short-target:          b342b5be8e4943a1bf82abbe26e3329424447515062df4e728154e47dea71c7d
```

## 6–8. Product / Architecture / Research Engine

No strategy algorithms, indicators, provider factories, definition persistence/API/UI, campaigns, candidates, scoring, MOMO, or trading. Milestone 0.8 is not started.

## 9. Outstanding Work

Awaiting independent review of Milestone 0.7.
No later milestone is authorized until then.

## 10. Verification Evidence (Milestone 0.7)

Commands actually executed:

```text
uv sync --frozen --all-extras
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest tests/unit -k strategy_definition -q                 # 83 passed
uv run pytest tests/unit -q                                         # 386 passed
uv run pytest tests/integration/test_artifact_filesystem.py -q      # 9 passed
uv run pytest tests/integration -q -m integration                   # 34 passed
uv run pytest tests/integration/test_candle_query.py -q             # 5 passed
alembic upgrade/downgrade round-trip (0001/0002/0003 only; no new migration)
uv run zorqen-backtest run-golden --scenario all                    # twice, identical
uv run zorqen-strategy validate-definition --file .../example_definition_v1.json  # ok
uv run zorqen-strategy bind-parameters ...                          # ok
uv run zorqen-strategy validate-definition --file missing.json      # exit 1
uv run python -m zorqen_research.worker --check                     # OK
frontend npm ci / lint / test --run / build                         # 15 tests
docker compose down -v; build; up; nginx routes live/ready/families/datasets # 200
```

Traceability: `docs/verification/0007-strategy-definition-traceability.md` (0 NOT TESTED)  
GitHub Actions: unknown until push (do not push unless instructed).

## 11. Known Defects and Limitations

- Definition schema is not persisted and has no HTTP API
- No executable Adaptive MTF or Support/Resistance implementation
- No provider factory linking definitions to the backtest kernel
- Existing backtest/kernel limitations unchanged

## 12. Next Authorized Work

None until Milestone 0.7 is independently accepted.
