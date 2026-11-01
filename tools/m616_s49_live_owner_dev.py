"""M-only S49 actual-owner callback consumer. Default OFF, strictly passive.

Uses the ORIGINAL pinned S49 qualify(completed_l0=...) hook after native
S16 closures. This wrapper does not issue Actions, probes or model requests.
Actual World execution requires operator grant and explicit CLI/env gates.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path
from typing import Any, Awaitable, Callable

from tools.m616_s49_owner_bootstrap import (
    S49OwnerBootstrapRejected,
    bootstrap_original_s49_owner,
)


class M616OriginalS49CompletedTap:
    """Original Python batch owner admission. Never catches a physical Action."""

    def __init__(self, *, enabled: bool = False) -> None:
        if type(enabled) is not bool:
            raise ValueError("explicit owner DEV opt-in must be boolean")
        from experiments.metabolism_s49_owner_admission import S49MAdmissionLease

        self.lease = S49MAdmissionLease(enabled=enabled, max_batches=1)
        self.readout: dict[str, object] | None = None
        self.observed_callbacks = 0

    def __call__(self, original_batch: object) -> None:
        if not self.lease.enabled:
            return
        from experiments.metabolism_s49_owner_admission import (
            bounded_s49_m_admission_row,
        )

        self.observed_callbacks += 1
        result = self.lease.admit_batch(original_batch)
        # Deliberately avoid saving original World/Body/Action Python objects.
        self.readout = bounded_s49_m_admission_row(result)


async def run_original_s49_with_m_readback(
    *,
    original_qualify: Callable[..., Awaitable[int]],
    report_path: Path,
    server_log: Path,
    tap: M616OriginalS49CompletedTap,
) -> tuple[int, dict[str, Any]]:
    """CALL original S49 only once; M does not change its return/Action flow.

    Exact original S49 callable must be imported from pinned original owner.
    Caller is responsible for DEV operator/environment gates and fresh paths.
    """
    if not isinstance(tap, M616OriginalS49CompletedTap) or not tap.lease.enabled:
        raise ValueError("M live source readback was not explicitly enabled")

    code = await original_qualify(
        report_path,
        server_log,
        completed_l0=tap,
        completed_l0_dev=True,
    )
    try:
        s_report = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError):
        s_report = {}
    row = tap.readout
    original_saved = s_report.get("original_completion_readback")
    readback = original_saved if isinstance(original_saved, dict) else {}
    accepted = (
        type(code) is int and code == 0
        and s_report.get("status") == "PASS"
        and s_report.get("original_completion_observer") == "CALLBACK_RETURNED"
        and isinstance(row, dict) and row.get("status") == "RECORDED"
        and row.get("kind") == "ORIGINAL_PYTHON_BATCH"
        and s_report.get("session_id") == row.get("session_id")
        and readback.get("step_count") == row.get("step_count")
        and readback.get("wait_count") == row.get("wait_count")
        and readback.get("outcome_count") == row.get("outcome_count")
        and tap.observed_callbacks == 1
    )
    return code, {
        "schema": "M_S49_LIVE_ORIGINAL_BATCH_DEV_V1",
        "status": "RECORDED" if accepted else "DEFERRED",
        "reason": ("original_callback_source_matched"
                   if accepted else "s49_owner_or_m_callback_not_admitted"),
        "s49_owner_report_status": s_report.get("status"),
        "original_callbacks_observed": tap.observed_callbacks,
        "m_admission": row,
        "source_attested": False,
        "action_authority": False,
        "new_native_reads": 0,
        "new_model_calls": 0,
        "new_action_issues": 0,
        "learning_updates": 0,
        "energy_debits": 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="M #616 original S49 single-run read-only live DEV"
    )
    parser.add_argument("--s49-owner-dir", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--server-log", type=Path, required=True)
    parser.add_argument("--m-report", type=Path, required=True)
    parser.add_argument("--live-world-dev", action="store_true")
    args = parser.parse_args()

    # The World is forbidden unless all gates and fresh M evidence destination
    # are verified BEFORE loading/running the original owner.
    if not (
        args.live_world_dev
        and os.environ.get("M616_S49_LIVE_DEV_ONLY") == "1"
        and os.environ.get("S49_REAL_SERVER_CI") == "1"
        and os.environ.get("S49_COMPLETED_L0_DEV_ONLY") == "1"
        and not os.environ.get("NODE_OPTIONS")
    ):
        print(json.dumps({"status": "BLOCKED", "reason": "missing_explicit_dev_grant_gates"}))
        return 2
    if any(p.exists() for p in (args.report, args.server_log, args.m_report)):
        print(json.dumps({"status": "BLOCKED", "reason": "evidence_destination_exists"}))
        return 2
    if len({p.resolve() for p in (args.report, args.server_log, args.m_report)}) != 3:
        print(json.dumps({"status": "BLOCKED", "reason": "evidence_paths_overlap"}))
        return 2
    try:
        bootstrap_original_s49_owner(args.s49_owner_dir)
    except S49OwnerBootstrapRejected:
        print(json.dumps({"status": "BLOCKED", "reason": "original_s49_checkout_unverified"}))
        return 2

    # Import this once after pinning source; no alternative S/Action issuer.
    from adapters.mineflayer.s49_normal_session_real_ci import qualify

    tap = M616OriginalS49CompletedTap(enabled=True)
    s_rc, result = asyncio.run(run_original_s49_with_m_readback(
        original_qualify=qualify,
        report_path=args.report, server_log=args.server_log,
        tap=tap,
    ))
    # This M diagnostic is a separate append-only output, never altering S49.
    args.m_report.parent.mkdir(parents=True, exist_ok=True)
    with args.m_report.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, ensure_ascii=False, sort_keys=True, allow_nan=False)
        stream.write("\n")
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False))
    return 0 if s_rc == 0 and result["status"] == "RECORDED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
