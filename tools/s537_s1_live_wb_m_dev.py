"""S #537 S1: opt-in original S49 DEV World runner with pinned WB/M owner code.

One original S49 qualify call, one existing native receiver/Action issuer.
Two callbacks only observe the already received probe / terminal owner batch.
No new LLM, S42/B0/L8, original source mutation or learning permission.
"""
from __future__ import annotations

import argparse
import asyncio
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Awaitable, Callable

from adapters.mineflayer.s537_s1_original_wb_m import S1WBMMatchedObserver

_M_PIN = "9afce6bde1079f8a42aaf3c4e515ef35fc6b0396"
_WB_PIN = "944db858186a4d9449946b6acdcb8c8e5998e071"


def _original_owner_module(
    *,
    root: Path, ref: str, relative: str, module_name: str,
) -> None:
    """Load exact pinned *original* sibling module, without merging branches."""
    if not root.is_absolute() or not root.is_dir() or root.is_symlink():
        raise ValueError("owner checkout root must exist, absolute, non-symlink")
    root = root.resolve(strict=True)
    checks = (
        ("rev-parse", "HEAD"),
        ("rev-parse", "--show-toplevel"),
        ("status", "--porcelain", "--untracked-files=no"),
    )
    outputs = []
    for command in checks:
        result = subprocess.run(
            ["git", "-C", str(root), *command],
            check=True, capture_output=True, text=True, timeout=10,
        )
        outputs.append(result.stdout.strip())
    if outputs != [ref, str(root), ""]:
        raise ValueError("owner checkout HEAD/tree not exact pinned clean source")
    filename = root / relative
    if not filename.is_file() or filename.is_symlink():
        raise ValueError("pinned module path absent or symlink")
    from experiments import __path__ as _m_package_path
    from relay_self import __path__ as _wb_package_path
    if not _m_package_path or not _wb_package_path:
        raise ValueError("existing Python namespace missing")
    spec = importlib.util.spec_from_file_location(module_name, filename)
    if spec is None or spec.loader is None:
        raise ValueError("cannot load pinned original module")
    original = sys.modules.get(module_name)
    if original is not None:
        if getattr(original, "__file__", None) != str(filename):
            raise ValueError("foreign preimported owner module")
        return
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(module_name, None)
        raise


def _read_report(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if type(value) is dict else {}
    except (OSError, ValueError, UnicodeError):
        return {}


async def run_s1_owner_dev(
    *,
    original_qualify: Callable[..., Awaitable[int]],
    report_path: Path,
    server_log: Path,
    observer: S1WBMMatchedObserver,
) -> tuple[int, dict[str, Any]]:
    """Exactly one S49 execution; never mask original S49 exit."""
    async def on_original_probe(reading: object) -> None:
        try:
            observer.observe(reading)
        except Exception as exc:
            observer.record_error(exc)  # Do not veto original physical Action.

    code = await original_qualify(
        report_path, server_log,
        live_probe=on_original_probe,
        completed_l0=observer.completed,
        completed_l0_dev=True,
    )
    source = _read_report(report_path)
    row = observer.readout
    pairs = source.get("source_pair_trace")
    original = source.get("original_completion_readback")
    source_join = (
        type(pairs) is list
        and type(original) is dict
        and type(row) is dict and row.get("status") == "RECORDED"
        and len(pairs) == len(row.get("wb_rows", []))
        and len(original.get("decisions", [])) == len(pairs)
        and all(
            type(pair) is dict and type(wb) is dict
            and type(decision) is dict
            and pair.get("event_seq") == decision.get("event_seq")
            and pair.get("probe_seq") == decision.get("probe_seq") == wb.get("probe_seq")
            and decision.get("request_id") == wb.get("request_id")
            for pair, wb, decision in zip(
                pairs, row["wb_rows"], original["decisions"], strict=True,
            )
        )
        and row.get("session_id") == source.get("session_id")
    )
    accepted = (
        type(code) is int and code == 0
        and source.get("status") == "PASS"
        and source.get("original_completion_observer") == "CALLBACK_RETURNED"
        and observer.completed_callbacks == 1
        and observer.errors == []
        and source_join
    )
    result = {
        "schema": "S537_S1_S49_WB_M_LIVE_DEV_V1",
        "status": "RECORDED" if accepted else "DEFERRED",
        "reason": (
            "same_original_session_wb_m_join"
            if accepted else "original_S49_or_WB_M_join_not_established"
        ),
        "s49_status": source.get("status", "UNKNOWN"),
        "s49_original_completion_observer": source.get(
            "original_completion_observer", "UNKNOWN",
        ),
        "s49_session_id": source.get("session_id"),
        "completed_callbacks": observer.completed_callbacks,
        "wb_observer_errors": list(observer.errors),
        "typed_join": row,
        "source_attested": False,
        "action_authority": False,
        "new_native_reads": 0,
        "new_model_calls": 0,
        "new_action_issues": 0,
        "learning_updates": 0,
        "energy_debits": 0,
        "qualification": "NO_GO",
        "science": "NOT_RUN",
    }
    return code, result


def main() -> int:
    parser = argparse.ArgumentParser(
        description="S #537 S1 original single-World WB/M join (DEV only)",
    )
    parser.add_argument("--m-owner-dir", required=True, type=Path)
    parser.add_argument("--wb-owner-dir", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--server-log", required=True, type=Path)
    parser.add_argument("--s1-report", required=True, type=Path)
    parser.add_argument("--live-world-dev", action="store_true")
    args = parser.parse_args()
    if not (
        args.live_world_dev
        and os.environ.get("S537_S1_LIVE_DEV_ONLY") == "1"
        and os.environ.get("S49_REAL_SERVER_CI") == "1"
        and os.environ.get("S49_COMPLETED_L0_DEV_ONLY") == "1"
        and not os.environ.get("NODE_OPTIONS")
    ):
        print(json.dumps({"status": "BLOCKED", "reason": "dev_gate_missing"}))
        return 2
    destinations = (args.report, args.server_log, args.s1_report)
    if (
        any(not path.is_absolute() or path.exists() or path.is_symlink()
            or not path.parent.is_dir() or path.parent.is_symlink()
            for path in destinations)
        or len({str(path.resolve()) for path in destinations}) != 3
    ):
        print(json.dumps({"status": "BLOCKED", "reason": "fresh_output_required"}))
        return 2
    try:
        _original_owner_module(
            root=args.m_owner_dir, ref=_M_PIN,
            relative="experiments/metabolism_s49_owner_admission.py",
            module_name="experiments.metabolism_s49_owner_admission",
        )
        _original_owner_module(
            root=args.wb_owner_dir, ref=_WB_PIN,
            relative="src/relay_self/self_cognition_slice.py",
            module_name="relay_self.self_cognition_slice",
        )
    except (OSError, ValueError, subprocess.SubprocessError, ImportError) as exc:
        print(json.dumps({
            "status": "BLOCKED", "reason": "pinned_original_owner_unavailable",
            "detail": type(exc).__name__,
        }))
        return 2

    from adapters.mineflayer.s49_normal_session_real_ci import qualify

    observer = S1WBMMatchedObserver(enabled=True)
    code, result = asyncio.run(run_s1_owner_dev(
        original_qualify=qualify,
        report_path=args.report, server_log=args.server_log,
        observer=observer,
    ))
    # Distinct report written only after original S49 has completed its
    # own cleanup. Never overwrite or amend its saved original report.
    args.s1_report.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "status": result["status"],
        "reason": result["reason"],
        "s1_report": str(args.s1_report),
    }))
    return 0 if code == 0 and result["status"] == "RECORDED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
