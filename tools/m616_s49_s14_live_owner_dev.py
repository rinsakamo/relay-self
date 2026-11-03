"""M #616: original S49 L0/S16 plus S #701 S14 planned passive join.

One original S49 qualify() invocation and two independent S-owned callbacks.
The S49 and M #683 source reports are not rewritten. No model, native reads,
Actions, learning or energy debt is introduced by this observer.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path
from typing import Any, Awaitable, Callable

from experiments.metabolism_s49_s14_planned_owner_join import (
    M616S14PlannedLease,
    bounded_m_s14_planned_row,
)
from tools.m616_s49_live_owner_dev import M616OriginalS49CompletedTap
from tools.m616_s49_s14_owner_bootstrap import (
    S14OwnerBootstrapRejected,
    bootstrap_original_s14_owner,
)


class M616S14LiveTap:
    def __init__(self, *, enabled: bool = False) -> None:
        if type(enabled) is not bool:
            raise ValueError("S14 DEV tap enabled must be boolean")
        self.original = M616OriginalS49CompletedTap(enabled=enabled)
        self.planned_lease = M616S14PlannedLease(enabled=enabled)
        self.original_calls = 0
        self.planned_calls = 0
        self.original_l0: object | None = None
        self.original_planned: object | None = None

    def on_original_l0(self, source: object) -> None:
        self.original_calls += 1
        if self.original_calls == 1:
            self.original_l0 = source
        else:
            self.original_l0 = None
        self.original(source)

    def on_original_planned(self, source: object) -> None:
        self.planned_calls += 1
        # Do not use an earlier source once a duplicate callback was observed.
        self.original_planned = source if self.planned_calls == 1 else None


async def run_s49_s14_with_m_readback(
    *,
    original_qualify: Callable[..., Awaitable[int]],
    report_path: Path,
    server_log: Path,
    tap: M616S14LiveTap,
) -> tuple[int, dict[str, Any]]:
    if (
        not isinstance(tap, M616S14LiveTap)
        or not tap.original.lease.enabled
        or not tap.planned_lease.enabled
    ):
        raise ValueError("original S49 and M S14 source observer must be DEV-enabled")

    code = await original_qualify(
        report_path,
        server_log,
        completed_l0=tap.on_original_l0,
        completed_l0_dev=True,
        completed_planned=tap.on_original_planned,
        completed_planned_dev=True,
    )
    try:
        saved = json.loads(report_path.read_text(encoding="utf-8"))
        if type(saved) is not dict:
            saved = {}
    except (OSError, UnicodeError, ValueError):
        saved = {}

    m_admission = tap.original.readout
    m_s16 = tap.original.original_s16_receipts
    observed = tap.planned_lease.admit(
        original_l0=tap.original_l0,
        original_planned=tap.original_planned,
        m_admission_row=m_admission,
        m_s16_row=m_s16,
    )
    m_planned = bounded_m_s14_planned_row(observed)
    s_plan = saved.get("original_planned_readback")
    s_l0 = saved.get("original_completion_readback")
    native = saved.get("actual_native_actions")
    m_actions = m_planned.get("actions")
    s_actions = s_plan.get("actions") if isinstance(s_plan, dict) else None

    same_planned = (
        isinstance(s_plan, dict) and s_plan.get("status") == "RECORDED"
        and s_plan.get("schema") == "S49_ORIGINAL_S14_PLANNED_POSTACTION_DEV_V1"
        and s_plan.get("session_id") == m_planned.get("session_id")
        and s_plan.get("wait_epoch_count") == 0
        and s_plan.get("move_epoch_count") == m_planned.get("move_epoch_count")
        and isinstance(s_actions, list) and isinstance(m_actions, list)
        and len(s_actions) == len(m_actions)
        and all(
            isinstance(sa, dict) and isinstance(ma, dict)
            and all(sa.get(k) == ma.get(k) for k in (
                "action_id", "event_seq", "probe_seq", "s16_after_seq",
            ))
            and sa.get("planned_cognition_requested") is False
            and sa.get("original_plan") == "MOVE_AWAY"
            and sa.get("original_admission") == "admitted"
            for sa, ma in zip(s_actions, m_actions)
        )
    )
    same_actions = (
        isinstance(native, list) and isinstance(m_actions, list)
        and isinstance(m_s16, dict)
        and isinstance(m_s16.get("actions"), list)
        and len(native) == len(m_actions) == len(m_s16["actions"])
        and all(
            isinstance(n, dict) and isinstance(ma, dict) and isinstance(sr, dict)
            and n.get("action") == ma.get("action_id") == sr.get("action_id")
            and n.get("event_seq") == ma.get("event_seq") == sr.get("event_seq")
            and n.get("probe_seq") == ma.get("probe_seq") == sr.get("probe_seq")
            and n.get("terminal") == "outcome"
            and sr.get("s16_after_seq") == ma.get("s16_after_seq")
            and n.get("movement_m") == sr.get("movement_m")
            for n, ma, sr in zip(native, m_actions, m_s16["actions"])
        )
    )
    accepted = (
        type(code) is int and code == 0 and saved.get("status") == "PASS"
        and saved.get("node_exit") == 0
        and saved.get("server_exit") == 0
        and tap.original_calls == 1 and tap.planned_calls == 1
        and tap.original.observed_callbacks == 1
        and saved.get("original_completion_observer") == "CALLBACK_RETURNED"
        and saved.get("original_planned_observer") == "CALLBACK_RETURNED"
        and isinstance(m_admission, dict) and m_admission.get("status") == "RECORDED"
        and m_admission.get("kind") == "ORIGINAL_PYTHON_BATCH"
        and isinstance(m_s16, dict) and m_s16.get("status") == "RECORDED"
        and m_planned.get("status") == "RECORDED"
        and isinstance(s_l0, dict)
        and s_l0.get("session_id") == saved.get("session_id")
        and s_l0.get("step_count") == m_admission.get("step_count")
        and s_l0.get("wait_count") == m_admission.get("wait_count")
        and s_l0.get("outcome_count") == m_admission.get("outcome_count")
        and m_planned.get("session_id") == m_admission.get("session_id")
        and m_s16.get("session_id") == m_admission.get("session_id")
        and m_planned.get("move_epoch_count") == m_admission.get("outcome_count")
        and same_planned and same_actions
    )
    return code, {
        "schema": "M_S49_S14_LIVE_ORIGINAL_PLANNED_DEV_V1",
        "status": "RECORDED" if accepted else "DEFERRED",
        "reason": (
            "original_s49_s14_s16_join" if accepted
            else "original_owner_or_cleanup_or_planned_join_not_admitted"
        ),
        "s49_owner_status": saved.get("status"),
        "original_l0_callbacks": tap.original_calls,
        "original_planned_callbacks": tap.planned_calls,
        "m_admission": m_admission,
        "m_original_s16_receipts": m_s16,
        "m_original_s14_planned": m_planned,
        "source_attested": False,
        "action_authority": False,
        "s42_owner_receipt": "NOT_SUPPLIED_BY_S49_S14_PLANNED_CALLBACK",
        "b0_owner_receipt": "NOT_SUPPLIED_BY_S49_S14_PLANNED_CALLBACK",
        "l8_owner_receipt": "NOT_SUPPLIED_BY_S49_S14_PLANNED_CALLBACK",
        "model_usage": "UNKNOWN_NO_MODEL_METER",
        "metabolic_energy": "UNKNOWN_NO_B0_OWNER",
        "l8_learning": "UNKNOWN_NO_L8_OWNER",
        "new_native_reads": 0, "new_model_calls": 0,
        "new_action_issues": 0, "learning_updates": 0,
        "energy_debits": 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="M #616 pinned original S14 post-Action live DEV"
    )
    parser.add_argument("--s49-owner-dir", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--server-log", type=Path, required=True)
    parser.add_argument("--m-report", type=Path, required=True)
    parser.add_argument("--live-world-dev", action="store_true")
    args = parser.parse_args()
    gates = (
        args.live_world_dev
        and os.environ.get("M616_S49_LIVE_DEV_ONLY") == "1"
        and os.environ.get("M616_S14_PLANNED_LIVE_DEV_ONLY") == "1"
        and os.environ.get("S49_REAL_SERVER_CI") == "1"
        and os.environ.get("S49_COMPLETED_L0_DEV_ONLY") == "1"
        and os.environ.get("S49_COMPLETED_PLANNED_DEV_ONLY") == "1"
        and not os.environ.get("NODE_OPTIONS")
    )
    if not gates:
        print(json.dumps({"status": "BLOCKED", "reason": "missing_explicit_dev_gates"}))
        return 2
    if (
        len({p.resolve() for p in (args.report, args.server_log, args.m_report)}) != 3
        or any(p.exists() for p in (args.report, args.server_log, args.m_report))
    ):
        print(json.dumps({"status": "BLOCKED", "reason": "evidence_path_reused"}))
        return 2
    try:
        bootstrap_original_s14_owner(args.s49_owner_dir)
    except S14OwnerBootstrapRejected:
        print(json.dumps({"status": "BLOCKED", "reason": "wrong_original_s14_owner"}))
        return 2

    from adapters.mineflayer.s49_normal_session_real_ci import qualify

    code, result = asyncio.run(run_s49_s14_with_m_readback(
        original_qualify=qualify, report_path=args.report,
        server_log=args.server_log, tap=M616S14LiveTap(enabled=True),
    ))
    args.m_report.parent.mkdir(parents=True, exist_ok=True)
    with args.m_report.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, ensure_ascii=False, sort_keys=True, allow_nan=False)
        stream.write("\n")
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False))
    return 0 if code == 0 and result["status"] == "RECORDED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
