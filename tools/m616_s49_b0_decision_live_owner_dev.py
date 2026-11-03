"""M #616 single original S49 session + S14 planned + B0 decision-only.

One physical S49 owner call. S49 creates real owner B0Decision and SelfBody
view from its *existing* probes. B0 remains an unadvanced experimental
MetabolismConfig ledger; no WorldTick-qualified energy accounting/debit.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path
from typing import Any, Awaitable, Callable

from experiments.metabolism_s49_b0_original_decision_only import (
    M616B0DecisionLease,
    bounded_m_b0_original_decision_row,
)
from tools.m616_s49_s14_live_owner_dev import (
    M616S14LiveTap,
    run_s49_s14_with_m_readback,
)
from tools.m616_s49_b0_decision_owner_bootstrap import (
    B0OwnerBootstrapRejected,
    bootstrap_original_s49_b0_decision_owner,
)


class M616B0DecisionLiveTap:
    def __init__(self, *, enabled: bool = False) -> None:
        if type(enabled) is not bool:
            raise ValueError("boolean B0 DEV tap option required")
        self.s14 = M616S14LiveTap(enabled=enabled)
        self.b0_lease = M616B0DecisionLease(enabled=enabled)
        self.b0_calls = 0
        self.b0_original: object | None = None

    def on_original_b0(self, original: object) -> None:
        self.b0_calls += 1
        self.b0_original = original if self.b0_calls == 1 else None


async def run_original_s49_with_m_b0_readback(
    *,
    original_qualify: Callable[..., Awaitable[int]],
    report_path: Path,
    server_log: Path,
    tap: M616B0DecisionLiveTap,
) -> tuple[int, dict[str, Any]]:
    if (
        not isinstance(tap, M616B0DecisionLiveTap)
        or not tap.s14.original.lease.enabled
        or not tap.b0_lease.enabled
    ):
        raise ValueError("original B0 DEV witness is default OFF")

    async def call_original_once(
        path: Path, log: Path, *,
        completed_l0: Callable[[object], None],
        completed_l0_dev: bool,
        completed_planned: Callable[[object], None],
        completed_planned_dev: bool,
    ) -> int:
        return await original_qualify(
            path, log,
            completed_l0=completed_l0,
            completed_l0_dev=completed_l0_dev,
            completed_planned=completed_planned,
            completed_planned_dev=completed_planned_dev,
            completed_b0_decisions=tap.on_original_b0,
            completed_b0_decisions_dev=True,
        )

    s49_rc, s14_result = await run_s49_s14_with_m_readback(
        original_qualify=call_original_once,
        report_path=report_path,
        server_log=server_log,
        tap=tap.s14,
    )
    try:
        original_saved = json.loads(report_path.read_text(encoding="utf-8"))
        if type(original_saved) is not dict:
            original_saved = {}
    except (OSError, ValueError, UnicodeError):
        original_saved = {}

    m_b0_observation = tap.b0_lease.admit(
        original_l0=tap.s14.original_l0,
        original_planned=tap.s14.original_planned,
        original_b0=tap.b0_original,
        m_admission_row=tap.s14.original.readout,
        m_s16_row=tap.s14.original.original_s16_receipts,
        m_planned_row=s14_result.get("m_original_s14_planned"),
    )
    m_b0 = bounded_m_b0_original_decision_row(m_b0_observation)
    s_b0 = original_saved.get("original_b0_decision_readback")
    source_b0 = (
        isinstance(s_b0, dict)
        and s_b0.get("schema") == "S49_ORIGINAL_B0_DECISION_ONLY_DEV_V1"
        and s_b0.get("status") == "RECORDED"
        and s_b0.get("session_id") == m_b0.get("session_id")
        and s_b0.get("decision_count") == m_b0.get("decision_count")
        and s_b0.get("decision_probe_seqs") == [
            d.get("probe_seq") for d in m_b0.get("decisions", [])
        ]
        and s_b0.get("decision_kinds") == [
            d.get("b0_kind") for d in m_b0.get("decisions", [])
        ]
        and s_b0.get("energy_debits") == m_b0.get("energy_debits") == 0
        and s_b0.get("energy_transitions") == m_b0.get("energy_transition_count") == 0
        and s_b0.get("food_credits") == m_b0.get("food_credits") == 0
    )
    accepted = (
        type(s49_rc) is int and s49_rc == 0
        and s14_result.get("status") == "RECORDED"
        and original_saved.get("status") == "PASS"
        and original_saved.get("node_exit") == 0
        and original_saved.get("server_exit") == 0
        and original_saved.get("original_b0_decision_observer") == "CALLBACK_RETURNED"
        and tap.b0_calls == 1
        and m_b0.get("status") == "RECORDED"
        and m_b0.get("decision_count") == s14_result["m_admission"]["step_count"]
        and source_b0
    )
    return s49_rc, {
        "schema": "M_S49_B0_DECISION_ONLY_LIVE_DEV_V1",
        "status": "RECORDED" if accepted else "DEFERRED",
        "reason": (
            "original_b0_decision_and_s14_s16_same_session"
            if accepted else "original_b0_decision_or_cleanup_unverified"
        ),
        "s49_owner_status": original_saved.get("status"),
        "original_b0_callbacks": tap.b0_calls,
        "m_s14_original_join": s14_result,
        "m_original_b0_decision_only": m_b0,
        "source_attested": False, "action_authority": False,
        "true_world_energy": "UNKNOWN_NO_PHYSICAL_ENERGY_TICK",
        "b0_owner_model_energy": "UNADVANCED_INITIAL_STATE_NOT_PHYSICAL_COST",
        "s42_owner_receipt": "NOT_SUPPLIED_BY_B0_DECISION_ONLY",
        "l8_owner_receipt": "NOT_SUPPLIED_BY_B0_DECISION_ONLY",
        "new_native_reads": 0, "new_model_calls": 0,
        "new_action_issues": 0, "learning_updates": 0,
        "energy_debits": 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="M #616 S49 original B0 owner decision-only, one World DEV"
    )
    parser.add_argument("--s49-owner-dir", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--server-log", type=Path, required=True)
    parser.add_argument("--m-report", type=Path, required=True)
    parser.add_argument("--live-world-dev", action="store_true")
    args = parser.parse_args()
    required = (
        args.live_world_dev
        and os.environ.get("M616_S49_LIVE_DEV_ONLY") == "1"
        and os.environ.get("M616_S14_PLANNED_LIVE_DEV_ONLY") == "1"
        and os.environ.get("M616_B0_DECISION_LIVE_DEV_ONLY") == "1"
        and os.environ.get("S49_REAL_SERVER_CI") == "1"
        and os.environ.get("S49_COMPLETED_L0_DEV_ONLY") == "1"
        and os.environ.get("S49_COMPLETED_PLANNED_DEV_ONLY") == "1"
        and os.environ.get("S49_B0_DECISION_WITNESS_DEV_ONLY") == "1"
        and not os.environ.get("NODE_OPTIONS")
    )
    if not required:
        print(json.dumps({"status": "BLOCKED", "reason": "missing_b0_dev_gates"}))
        return 2
    if (
        len({p.resolve() for p in (args.report, args.server_log, args.m_report)}) != 3
        or any(p.exists() for p in (args.report, args.server_log, args.m_report))
    ):
        print(json.dumps({"status": "BLOCKED", "reason": "reused_evidence_path"}))
        return 2
    try:
        bootstrap_original_s49_b0_decision_owner(args.s49_owner_dir)
    except B0OwnerBootstrapRejected:
        print(json.dumps({"status": "BLOCKED", "reason": "wrong_original_b0_owner"}))
        return 2
    from adapters.mineflayer.s49_normal_session_real_ci import qualify

    rc, result = asyncio.run(run_original_s49_with_m_b0_readback(
        original_qualify=qualify, report_path=args.report,
        server_log=args.server_log, tap=M616B0DecisionLiveTap(enabled=True),
    ))
    args.m_report.parent.mkdir(parents=True, exist_ok=True)
    with args.m_report.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, ensure_ascii=False, sort_keys=True, allow_nan=False)
        stream.write("\n")
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False))
    return 0 if rc == 0 and result["status"] == "RECORDED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
