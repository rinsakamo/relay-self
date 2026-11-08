"""D14 independent post: Paper-owned 10000-tick horizon is not survival learning.

The original D8/D12 audit remains independent. Natural zero, no-new-spawn,
Self death, and absence of autonomous Actions must never be forged as progress.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from relay_self.c1_physical_action_fence import OriginalS49PhysicalFence
from relay_self.s49_nonmotion_physical_fence import OriginalS49NonMotionFence
from tools.bug0_d6_multigen_world import _uuid
from tools.bug0_d12_third_intent_rearm_post import audit_d12
from tools.bug0_d14_tick_horizon_world import _field


class D14TickHorizonAuditRejected(ValueError):
    """Missing original tick/World/owner evidence."""


def audit_closed_original_action_failure(
    report: dict, *, nonmotion_path: Path, motion_path: Path,
) -> dict:
    """Original EAT/pickup path failed, but every issued S49 Action is terminal."""
    if (
        report.get("status") != "FAIL"
        or report.get("d14_prior_owner_action_failure") != report.get("failure")
        or report.get("d14_action_failure_does_not_end_world") is not True
        or report.get("original_action_issuer") != "S49"
        or report.get("real_world_started") is not True
        or report.get("real_model_calls") != 0
        or report.get("learning_updated") is not False
    ):
        raise D14TickHorizonAuditRejected("NOT_A_CLOSED_ORIGINAL_ACTION_REJECTION")
    non = OriginalS49NonMotionFence.restore(
        nonmotion_path, self_id="s49-original-self",
    )
    motion = OriginalS49PhysicalFence.restore(
        motion_path, self_id="s49-original-self",
    )
    non.require_clear()
    motion.require_clear()
    expected_non = report.get("s49_actions")
    expected_motion = report.get("d6_original_s49_move_actions", [])
    if (
        not isinstance(expected_non, list)
        or not isinstance(expected_motion, list)
        or len(non.actions) != len(expected_non)
        or len(motion.actions) != len(expected_motion)
        or not expected_non
        or report.get("nonmotion_fence", {}).get("sha256") != non.sha256
        or report.get("motion_fence", {}).get("sha256") != motion.sha256
    ):
        raise D14TickHorizonAuditRejected("SOURCE_OWNER_JOURNAL_COUNT_OR_SHA_MISMATCH")
    sid = report.get("session_id")
    if (
        type(sid) is not str or not sid
        or any(
            row.get("session_id") != sid
            or row.get("action_id") != prior.get("action_id")
            or row.get("status") != "S16_OUTCOME"
            or row.get("terminal") != "outcome"
            for row, prior in zip(non.actions, expected_non)
        )
        or any(
            row.get("session_id") != sid
            or row.get("action_id") != prior.get("action_id")
            or row.get("status") != "S16_OUTCOME"
            or row.get("terminal_state") != "outcome"
            for row, prior in zip(motion.actions, expected_motion)
        )
    ):
        raise D14TickHorizonAuditRejected("UNQUALIFIED_ISSUED_ORIGINAL_S49_TERMINAL")
    ids = [row["action_id"] for row in (*non.actions, *motion.actions)]
    if len(ids) != len(set(ids)) or report.get("d14_start_action_count") != len(ids):
        raise D14TickHorizonAuditRejected("ISSUED_ACTION_REUSE_OR_WRONG_COUNT")
    return {
        "status": "SOURCE_INCOMPLETE",
        "classification": "D14_D8_FOOD_ROUTE_REJECTED_ALL_ORIGINAL_ACTIONS_S16_CLOSED",
        "original_action_count": len(ids),
        "prior_failure": report["failure"],
    }


def audit_horizon(report: dict, paper_log: str, parent_audit: dict) -> dict:
    if (
        not isinstance(report, dict) or not isinstance(paper_log, str)
        or report.get("status") not in ("PASS_DEV", "FAIL")
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
        or parent_audit.get("status") not in (
            "PASS_DEV", "NOT_EXERCISED", "SOURCE_INCOMPLETE"
        )
        or (report.get("status") == "FAIL"
            and parent_audit.get("status") != "SOURCE_INCOMPLETE")
        or (report.get("status") == "PASS_DEV"
            and parent_audit.get("status") == "SOURCE_INCOMPLETE")
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
        "legacy_original_action_path_complete": (
            parent_audit["status"] != "SOURCE_INCOMPLETE"
        ),
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
    if report.get("status") == "FAIL":
        parent = audit_closed_original_action_failure(
            report, nonmotion_path=args.nonmotion_fence,
            motion_path=args.motion_fence,
        )
    else:
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
