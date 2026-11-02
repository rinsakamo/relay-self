"""S #537 S2-A DEV: S49 + S1 original WB/M, with prior-S16 L2 read port.

The model is NOT called. This installs only the original Action executor's
existing post-S16 read-only hook and the existing native probe callback.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import subprocess
from pathlib import Path
from typing import Awaitable, Callable

from adapters.mineflayer.normal_action import observe_closed_native_actions
from adapters.mineflayer.s537_s2a_l2_read_port import S2ASourceBoundObserver
from tools.s537_s1_live_wb_m_dev import (
    _M_PIN,
    _WB_PIN,
    _original_owner_module,
    run_s1_owner_dev,
)


async def run_s2a_original_dev(
    *,
    original_qualify: Callable[..., Awaitable[int]],
    report_path: Path,
    server_log: Path,
    observer: S2ASourceBoundObserver,
) -> tuple[int, dict[str, object]]:
    """One S49 run; owner completion and host-ordered input are separate."""
    with observe_closed_native_actions(observer.observe_closed):
        rc, s1 = await run_s1_owner_dev(
            original_qualify=original_qualify, report_path=report_path,
            server_log=server_log, observer=observer,
        )
    try:
        s2a = observer.s2a_readout()
    except (ValueError, AttributeError, TypeError, KeyError):
        s2a = {"status": "DEFERRED", "reason": "SOURCE_READOUT_REJECTED"}
    accepted = (
        type(rc) is int and rc == 0
        and s1.get("status") == "RECORDED"
        and s2a.get("status") == "RECORDED"
    )
    return rc, {
        "schema": "S537_S2A_HOST_READONLY_DEV_V1",
        "status": "RECORDED" if accepted else "DEFERRED",
        "reason": (
            "same_S49_WB_M_and_ordered_prior_S16_no_L2"
            if accepted else "source_or_callback_not_admitted"
        ),
        "s49_s1_status": s1.get("status", "UNKNOWN"),
        "s1_session_id": s1.get("s49_session_id"),
        "s1": s1,
        "s2a": s2a,
        "model_calls": 0,
        "s60_submissions": 0,
        "source_attested": False,
        "action_authority": False,
        "learning_authority": False,
        "qualification": "NO_GO",
        "science": "NOT_RUN",
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="S2-A original S49 + WB/M + previous S16 read-only (DEV)",
    )
    parser.add_argument("--m-owner-dir", type=Path, required=True)
    parser.add_argument("--wb-owner-dir", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--server-log", type=Path, required=True)
    parser.add_argument("--s2a-report", type=Path, required=True)
    parser.add_argument("--live-world-dev", action="store_true")
    args = parser.parse_args()
    if not (
        args.live_world_dev
        and os.environ.get("S537_S2A_LIVE_DEV_ONLY") == "1"
        and os.environ.get("S49_REAL_SERVER_CI") == "1"
        and os.environ.get("S49_COMPLETED_L0_DEV_ONLY") == "1"
        and not os.environ.get("NODE_OPTIONS")
    ):
        print(json.dumps({"status": "BLOCKED", "reason": "s2a_dev_gate_missing"}))
        return 2
    files = (args.report, args.server_log, args.s2a_report)
    if (
        any(
            not p.is_absolute() or p.is_symlink() or p.exists()
            or not p.parent.is_dir() or p.parent.is_symlink()
            for p in files
        )
        or len({str(p.resolve()) for p in files}) != 3
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

    observer = S2ASourceBoundObserver(enabled=True)
    rc, result = asyncio.run(run_s2a_original_dev(
        original_qualify=qualify, report_path=args.report,
        server_log=args.server_log, observer=observer,
    ))
    args.s2a_report.write_text(
        json.dumps(result, ensure_ascii=True, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "status": result["status"],
        "s2a_report": str(args.s2a_report),
    }))
    return 0 if rc == 0 and result["status"] == "RECORDED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
