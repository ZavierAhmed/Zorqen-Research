"""CLI for deterministic golden backtest verification."""

from __future__ import annotations

import argparse
import json
import sys

from zorqen_research.application.backtesting.golden import SCENARIOS, run_scenario
from zorqen_research.application.backtesting.golden_expectations import GoldenMismatchError
from zorqen_research.application.market_data.serialization import format_canonical_decimal
from zorqen_research.application.strategy_backtesting.goldens import (
    ALL_MTF_SCENARIO_NAMES,
    MtfGoldenMismatchError,
    run_mtf_scenario,
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
        result = run_scenario(name)
    except KeyError:
        return False, {"ok": False, "scenario": name, "error": "unknown_scenario"}
    except GoldenMismatchError as exc:
        return False, {
            "ok": False,
            "scenario": name,
            "error": "golden_mismatch",
            "detail": str(exc),
        }
    except Exception as exc:  # noqa: BLE001 — CLI boundary
        return False, {"ok": False, "scenario": name, "error": str(exc)}
    payload = {
        "ok": True,
        "scenario": name,
        "input_candle_count": result.summary.input_candle_count,
        "closed_trade_count": result.summary.closed_trade_count,
        "final_equity": format_canonical_decimal(result.summary.final_equity),
        "net_pnl": format_canonical_decimal(result.summary.net_pnl),
        "total_fees": format_canonical_decimal(result.summary.total_fees),
        "result_hash": result.summary.result_hash,
    }
    return True, payload


def _run_mtf_one(name: str) -> tuple[bool, dict[str, object]]:
    try:
        payload = run_mtf_scenario(name)
    except KeyError:
        return False, {"ok": False, "scenario": name, "error": "unknown_scenario"}
    except MtfGoldenMismatchError as exc:
        return False, {
            "ok": False,
            "scenario": name,
            "error": "golden_mismatch",
            "detail": str(exc),
        }
    except Exception as exc:  # noqa: BLE001 — CLI boundary
        return False, {"ok": False, "scenario": name, "error": str(exc)}
    return True, payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="zorqen-backtest",
        description="Deterministic golden backtest verification (no network/database)",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run-golden", help="Run one or all single-timeframe golden scenarios")
    run.add_argument("--scenario", required=True, help="Scenario name or 'all'")
    mtf = sub.add_parser(
        "run-mtf-golden",
        help="Run one or all multi-timeframe bridge golden scenarios",
    )
    mtf.add_argument("--scenario", required=True, help="Scenario name or 'all'")
    args = parser.parse_args(argv)

    if args.command == "run-golden":
        if args.scenario == "all":
            failures = 0
            for name in sorted(SCENARIOS):
                ok, payload = _run_one(name)
                print(json.dumps(payload, separators=(",", ":"), sort_keys=True))
                if not ok:
                    failures += 1
            return 0 if failures == 0 else 1
        ok, payload = _run_one(args.scenario)
        return _emit(payload, ok=ok)

    if args.command == "run-mtf-golden":
        if args.scenario == "all":
            failures = 0
            for name in ALL_MTF_SCENARIO_NAMES:
                ok, payload = _run_mtf_one(name)
                print(json.dumps(payload, separators=(",", ":"), sort_keys=True))
                if not ok:
                    failures += 1
            return 0 if failures == 0 else 1
        ok, payload = _run_mtf_one(args.scenario)
        return _emit(payload, ok=ok)

    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
