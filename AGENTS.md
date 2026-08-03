# Zorqen Research - Coding Agent Rules

## Purpose

This file contains permanent instructions for every coding agent working in this repository. Current implementation state belongs in `PROJECT_STATUS.md`.

## Authority order

1. Verified repository code and passing tests at the authoritative commit.
2. The Zorqen Research Master Specification.
3. `PROJECT_STATUS.md` for current verified state.
4. This file for permanent working rules.
5. The active milestone prompt for exact authorized scope.

Never trust a completion report when code, tests, Git history, or logs contradict it.

## Product boundary

Zorqen Research may create controlled candidates, run deterministic historical and validation tests, retain or discard experiments under frozen policies, and export qualified packages to MOMO Quant.

It must not connect to an exchange, store trading credentials, place paper/live orders, approve its own production use, modify MOMO Quant, bypass independent verification, or silently widen scope.

## Initial strategy scope

1. Adaptive Multi-Timeframe Trend Breakout - primary.
2. Support and Resistance - secondary.

Do not invent baseline logic. Baselines must come from an authoritative implementation or an explicitly approved formal specification.

## Required development loop

Repeat until every milestone gate passes:

1. Inspect repository state, branch, authoritative commit, tests, and documentation.
2. Compare the milestone with actual implementation.
3. Plan the smallest coherent change inside authorized scope.
4. Implement it.
5. Run targeted tests and inspect logs.
6. Correct failures, warnings, incomplete criteria, and regressions.
7. Repeat targeted verification.
8. Run the required broader verification.
9. Audit the final diff against scope, exclusions, architecture, and security.
10. Update `PROJECT_STATUS.md` with commands and results that actually occurred.
11. Commit only after verification.
12. Stop after the authorized milestone.

A successful build alone is not completion.

## Git rules

- Work from the exact base commit named in the milestone prompt.
- Record branch and base before editing.
- Keep each milestone or corrective milestone in one intentional commit unless explicitly instructed otherwise.
- Do not mix unrelated cleanup into milestone work.
- Do not rewrite verified history without explicit authorization.
- Keep secrets, databases, logs, caches, datasets, and runtime artifacts out of Git.
- The worktree must be clean when completion is declared.
- Commit messages must include the milestone identifier and a precise description.

## Required inspection before coding

Read in this order:

1. `README.md`
2. `AGENTS.md`
3. `PROJECT_STATUS.md`
4. Active milestone prompt
5. Relevant tests
6. Relevant implementation files
7. Relevant architecture decisions and contracts

Record the relevant equivalents of:

```bash
git status
git branch --show-current
git log -5 --oneline
git diff <last-verified-commit>..HEAD
```

## Testing rules

- Add or update tests with implementation.
- Prefer deterministic fixtures and explicit assertions.
- Run targeted tests first, then broader suites.
- Inspect logs even when commands exit successfully.
- Database changes require clean-database and upgrade-path verification.
- Candidate/evaluator work requires temporal-leakage and determinism tests.
- Cross-engine work requires parity fixtures.
- Never weaken, delete, skip, or ignore tests merely to pass.

## Research-integrity rules

- Market-data snapshots, evaluator logic, campaign policies, and hidden holdouts are immutable during a campaign.
- Candidate logic must not access future candles or hidden information.
- Hard rejection gates execute before weighted scoring.
- High score cannot compensate for leakage, invalid data, excessive drawdown, insufficient samples, non-determinism, or parity failure.
- Identical inputs must reproduce identical outputs within documented tolerances.
- Every retained experiment preserves complete provenance and rationale.

## Architecture and security

- CPU-first; no mandatory GPU dependency in the MVP.
- Support Windows development and Windows/Linux VPS deployment.
- Use configuration and `pathlib`; never hardcode drive paths.
- Start as a modular monolith with separate API and worker processes.
- Never commit secrets or add exchange credentials/connectivity.
- MVP candidate definitions must not execute arbitrary operating-system commands.
- Treat data or artifact hash mismatches as integrity failures.

## Documentation and handoff

Before each milestone commit, update `PROJECT_STATUS.md` with the current milestone, branch, authoritative commit, work completed/remaining, commands actually run, exact test/build/migration results, known defects and limitations, important decisions, and next authorized work.

If any required gate failed, report the milestone as incomplete.
