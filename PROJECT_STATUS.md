# Zorqen Research - Project Status

> This file records verified repository reality for handoff between coding agents. It must be updated in every milestone commit. Git, tests, and implementation remain authoritative when this file is stale or incorrect.

## 1. Project Identity

- Product: Zorqen Research
- Repository: `ZavierAhmed/Zorqen-Research`
- Default branch: `main`
- Current branch: `main`
- Previous verified commit (Milestone 0.3A): `9be07a73183469de4bae352624f0bfcafc377d4e`
- Milestone 0.3B base commit: `9be07a73183469de4bae352624f0bfcafc377d4e`
- Milestone result commit: current HEAD containing this status update.
- Exact SHA: report after commit.
- Master specification: `docs/specification/Zorqen_Research_Master_Specification_v0.1.pdf`
- Current environment: Windows development laptop
- Target deployment: Windows or Linux VPS
- Runtime principle: CPU-first; no mandatory GPU dependency
- Push state: confirm with `git status -sb` after commit (do not push unless instructed)

## 2. Product Purpose

Zorqen Research is a separate autonomous strategy-research and qualification platform. It will create controlled candidates, run deterministic testing and validation, apply hard gates and qualification scoring, and export qualified packages to MOMO Quant.

It does not connect to exchanges, place paper/live trades, approve live deployment, modify MOMO Quant, or use unrestricted strategy code generation in the MVP.

## 3. Initial Strategy Scope

Unchanged. Registry metadata only; executable baselines not defined.

## 4. Current Milestone

- Milestone: `0.3B` — Correct Docker Smoke Output Parsing and Root-Symlink Validation
- Status: Complete pending independent review
- Base: `9be07a73183469de4bae352624f0bfcafc377d4e`
- Defects corrected:
  - CI fixture step assumed pure JSON and did not explicitly build `dataset-fixture`
  - Artifact store resolved configured root before detecting that the root path itself was a symlink
- Implementation started: Yes
- Repository commit created: Yes (this milestone commit)

## 5. Latest Verified State

- Workflow builds `dataset-fixture` explicitly with Compose profile
- Fixture run uses `-T`; parser finds last valid `ok:true` JSON line; asserts expected manifest hash
- Dataset API step compares content hash to fixture result hash
- Failure diagnostics include `/tmp/fixture-output.log` plus compose logs
- Configured artifact root symlink rejected before resolve; unit + filesystem coverage
- Dataset fixture/APIs/migration behavior preserved from 0.3/0.3A
- Manifest hash unchanged: `5a0f0d0aacc3bc06969c4d45a38906a8d8a423ab449178b22fbf6a8abe81df80`

## 6–8. Product / Architecture / Research Engine

Unchanged from Milestone 0.3A. No network import, candle query, strategy, campaign, or MOMO work.

## 9. Outstanding Work

Awaiting independent review of Milestone 0.3B.
No later milestone is authorized.

## 10. Verification Evidence (Milestone 0.3B)

Commands actually executed:

```text
uv sync --frozen --all-extras
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest tests/unit -q                                          # 62 passed
uv run pytest tests/integration/test_artifact_filesystem.py -q       # 9 passed
uv run pytest tests/integration -q -m integration                    # 25 passed
alembic upgrade/downgrade round-trip through 0002 and base           # OK
uv run zorqen-dataset publish-fixture                                # created=true
uv run zorqen-dataset publish-fixture                                # created=false, same snapshot
uv run python -m zorqen_research.worker --check                      # OK
frontend npm ci / lint / test / build                                # 15 tests
docker compose --profile fixture build api worker migrate frontend dataset-fixture
docker compose up -d postgres migrate api worker frontend
docker compose --profile fixture run --rm --no-deps -T dataset-fixture
  → parsed last ok:true JSON; hash 5a0f0d0aacc3bc06969c4d45a38906a8d8a423ab449178b22fbf6a8abe81df80
nginx datasets list/detail/manifest hash match                       # OK
docker compose down -v
```

Manifest hash (unchanged):

`5a0f0d0aacc3bc06969c4d45a38906a8d8a423ab449178b22fbf6a8abe81df80`

GitHub Actions: not claimed until observed green after push (Ubuntu quality, Windows quality, PostgreSQL integration, Docker routing smoke).

## 11. Known Limitations

- Real root-symlink filesystem tests skip when OS denies symlink creation; unit branch coverage remains
- No later milestone authorized

## 12. Important Decisions

- Parse fixture CLI JSON from mixed Docker output (last valid `ok:true` object)
- Reject symlink artifact roots before `resolve`
- Do not claim CI green without observing GitHub Actions
