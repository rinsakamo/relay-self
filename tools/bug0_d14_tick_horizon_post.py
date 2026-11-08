"""D14 independent post: Paper-owned 10000-tick horizon is not survival learning.

The original D8/D12 audit remains independent. Natural zero, no-new-spawn,
Self death, and absence of autonomous Actions must never be forged as progress.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from tools.bug0_d12_third_intent_rearm_post import audit_d12
from tools.bug0_d14_tick_horizon_world import _field
from tools.bug0_d6_multigen_world import _uuid


class D14TickHorizonAuditRejected(ValueError):
    """Missing original tick/World/owner evidence."""


def audit_horizon(report: dict, paper_log: str, parent_audit: dict) -> dict:
    if (
        not isinstance(report, dict) or not isinstance(paper_log, str)
        or report.get("status") != "PASS_DEV"
        or report.get("d14_tick_horizon_proven") is not True
        or report.get("d14_tick_horizon_optin") is not True
        or report.get("d14_tick_horizon_requested") != 10000
        or report.get("d14_self_continuous_action_policy_enabled") is not False
        or report.get("d14_additional_native_actions") != 0
        or report.get("d14_l2_calls") != 0
        or report.get("d14_learning_updates") != 0
        or report.get("node_exit") != 0
        or report.get("java_exit") != 0
        or report.get("cleanup_done") is not True
        or parent_audit.get("status") not in ("PASS_DEV", "NOT_EXERCISED")
    ):
        raise D14TickHorizonAuditRejected("ORIGINAL_WORLD_STATUS_OR_INDEPENDENT_PARENT_INVALID")
    start = [
        line for line in paper_log.splitlines()
        if "RSELF_ENDURANCE_START world=" in line
    ]
    end = [
        line for line in paper_log.splitlines()
        if "RSELF_ENDURANCE_LIMIT world=" in line
    ]
    samples = [
        line for line in paper_log.splitlines()
        if "RSELF_ENDURANCE_SAMPLE world=" in line
    ]
    if len(start) != 1 or len(end) != 1 or len(samples) != 49:
        raise D14TickHorizonAuditRejected("MISSING_OR_DUPLICATE_PAPER_CLOCK")
    st = _field(start[0], "start_tick")
    en = _field(end[0], "observed_tick")
    world = _uuid(start[0], "world")
    if (
        en - st != 10000
        or _field(start[0], "stop_tick") != en
        or _field(end[0], "end_tick") != en
        or _field(end[0], "start_tick") != st
        or _field(end[0], "elapsed_ticks") != 10000
        or _uuid(end[0], "world") != world
        or "stop_new_spawns=true no_forced_death=true" not in end[0]
        or report.get("d14_tick_horizon", {}).get("source_original_start") != start[0]
        or report.get("d14_tick_horizon", {}).get("source_original_end") != end[0]
        or report["d14_tick_horizon"].get("world_uuid") != world
        or report["d14_tick_horizon"].get("world_ticks") != 10000
        or report["d14_tick_horizon"].get("end_tick") != en
        or report["d14_tick_horizon"].get("original_s49_action_count")
            != report.get("d14_start_action_count")
        or report["d14_tick_horizon"].get("native_new_actions_issued_by_horizon") != 0
        or report.get("real_model_calls") != 0
        or report.get("learning_updated") is not False
    ):
        raise D14TickHorizonAuditRejected("PAPER_TIMELINE_OR_OWNER_END_INCONSISTENT")
    for index, line in enumerate(samples, 1):
        if (
            _field(line, "elapsed_ticks") != 200 * index
            or _field(line, "tick") != st + 200 * index
            or _uuid(line, "world") != world
            or _field(line, "generation") < 1
        ):
            raise D14TickHorizonAuditRejected("WORLD_SAMPLE_NOT_MONOTONIC")
    if "RSELF_RESPAWN_FAULT" in paper_log or "RSELF_NATURAL_DROP_FAULT" in paper_log:
        raise D14TickHorizonAuditRejected("WORLD_FAULT_PRESENT")
    if any(
        "RSELF_RESPAWN_SPAWN world=" in line
        and _field(line, "tick") >= en
        for line in paper_log.splitlines()
    ):
        raise D14TickHorizonAuditRejected("SPAWN_AFTER_WORLD_LIMIT")
    if report.get("session_id") != report.get("d12_third_rearm", {}).get(
        "session_id", report.get("session_id")
    ):
        raise D14TickHorizonAuditRejected("NATIVE_SESSION_CHANGED")
    return {
        "status": "PASS_DEV",
        "classification": "D14_10000_REAL_WORLD_TICKS_OBSERVED_PASS",
        "world_uuid": world,
        "start_tick": st, "end_tick": en, "world_ticks": en - st,
        "world_owned_respawn_rule_ticks": 600,
        "paper_heartbeat_count": len(samples),
        "native_heartbeat_count": len(report.get("d14_heartbeat_observations", [])),
        "parent_d12_status": parent_audit["status"],
        "parent_d12_classification": parent_audit["classification"],
        "third_and_later_S49_action_loop": "NOT_IMPLEMENTED",
        "Self_autonomous_long_survival": False,
        "l2_calls": 0, "learning_updates": 0,
        "new_physical_actions_from_horizon": 0,
        "qualification": "NO_GO", "science": "NOT_RUN",
    }


def main() -> None:
    p = argparse.ArgumentParser()
    for key in ("report", "server-log", "nonmotion-fence",
                "motion-fence", "s50-sidecar", "out"):
        p.add_argument("--" + key, required=True, type=Path)
    args = p.parse_args()
    report = json.loads(args.report.read_text(encoding="utf8"))
    log = args.server_log.read_text(encoding="utf8")
    parent = audit_d12(
        report, log, nonmotion_path=args.nonmotion_fence,
        motion_path=args.motion_fence,
        s50_jsonl=args.s50_sidecar.read_text(encoding="utf8"),
    )
    result = audit_horizon(report, log, parent)
    args.out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf8")
    print(result["classification"])


if __name__ == "__main__":
    main()
