"""CLI for deterministic indicator golden verification."""

from __future__ import annotations

import argparse
import json
import sys

from zorqen_research.application.indicators.goldens import (
    ALL_SCENARIO_NAMES,
    IndicatorGoldenMismatchError,
    run_scenario,
)


def _emit(payload: dict[str, object], *, ok: bool) -> int:
    text = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    if ok:
        print(text)
        return 0
    print(text, file=sys.stderr)
    return 1


def _run_one(name: str) -> tuple[bool, dict[str, object]]:
    try:
        return True, run_scenario(name)
    except KeyError:
        return False, {"ok": False, "scenario": name, "error": "unknown_scenario"}
    except IndicatorGoldenMismatchError as exc:
        return False, {
            "ok": False,
            "scenario": name,
            "error": "golden_mismatch",
            "detail": str(exc),
        }
    except Exception as exc:  # noqa: BLE001 — CLI boundary
        return False, {"ok": False, "scenario": name, "error": str(exc)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="zorqen-indicators",
        description="Verify frozen indicator golden values and hashes (no network/DB)",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    verify = sub.add_parser("verify-golden", help="Verify one or all golden scenarios")
    verify.add_argument("--scenario", required=True)
    args = parser.parse_args(argv)
    if args.command != "verify-golden":
        return 2
    if args.scenario == "all":
        exit_code = 0
        for name in ALL_SCENARIO_NAMES:
            ok, payload = _run_one(name)
            print(json.dumps(payload, separators=(",", ":"), sort_keys=True))
            if not ok:
                exit_code = 1
        return exit_code
    ok, payload = _run_one(args.scenario)
    return _emit(payload, ok=ok)


if __name__ == "__main__":
    raise SystemExit(main())
