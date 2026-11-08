"""Independent R4 Paper + original S49 journal audit (no new authority).

The original physical nonmotion fence is a separate durable source. A typed
S16 receipt is not zombie death, causal learning or sustained survival.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from relay_self.s49_nonmotion_physical_fence import OriginalS49NonMotionFence
from tools.bug0_d14_natural_world import (
    NATURAL_PLUGIN_CONFIG,
    NaturalPaperTimeline,
    marker_kind,
    natural_properties,
)


class D14NaturalActiveAuditRejected(ValueError):
    """Forged Paper, changed natural World, action, or incomplete original fence."""


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit_active(
    report: dict[str, Any], paper_original: str, derivative: str,
    fence: OriginalS49NonMotionFence,
    *, original_sha: str, derivative_sha: str,
) -> dict[str, Any]:
    if (
        report.get("status") != "PASS_DEV"
        or report.get("classification")
            != "DEV_D14_R4_NATURAL_ACTIVE_S49_SOURCE_OBSERVED"
        or report.get("cleanup_done") is not True
        or report.get("node_exit") != 0 or report.get("java_exit") != 0
        or report.get("paper_original_sha256") != original_sha
        or report.get("derivative_journal_sha256") != derivative_sha
        or report.get("plugin_config") != NATURAL_PLUGIN_CONFIG
        or report.get("world_config") != "NATURAL_SURVIVAL"
        or report.get("server_properties")
            != natural_properties(report.get("server_properties", ""))
        or report.get("s49_physical_issuer")
            != "ORIGINAL_NORMAL_SESSION_ACTION_EXECUTOR"
        or report.get("operator_commands") != []
        or report.get("staged_hunger_effect") is not False
        or report.get("staged_zombie_no_ai") is not False
        or report.get("staged_zombie_low_health") is not False
        or report.get("staged_enemy_teleport") is not False
        or report.get("natural_mob_spawning_unchanged") is not True
        or report.get("managed_respawn_after_real_death_ticks") != 600
        or report.get("world_daylight_behavior") != "VANILLA"
        or any(report.get(k) != 0 for k in (
            "model_posts", "learning_updates", "skill_installs",
            "c1_intent_experiences",
        ))
        or report.get("move_admission") != "NOT_CONNECTED_IN_R4"
        or report.get("intent_rearm") != "NOT_CONNECTED_IN_R4"
    ):
        raise D14NaturalActiveAuditRejected("WORLD_OR_OWNER_SOURCE_NOT_QUALIFIED")

    timeline = NaturalPaperTimeline()
    original_rows = []
    for line in paper_original.splitlines():
        kind = marker_kind(line)
        if kind is not None:
            timeline.admit(kind, line)
            original_rows.append((kind, line))
    result = timeline.finish()
    if (
        result != report.get("result")
        or timeline.source_summary() != report.get("paper_source")
    ):
        raise D14NaturalActiveAuditRejected("WORLD_CLOCK_OR_TERMINAL_INCONSISTENT")

    derived_paper = []
    native_count = 0
    life_decisions = []
    life_actions = []
    for line in derivative.splitlines():
        try:
            e = json.loads(line)
        except json.JSONDecodeError as exc:
            raise D14NaturalActiveAuditRejected("BROKEN_APPEND_ONLY_JOURNAL") from exc
        if e.get("record_type") != "D14_R3_DERIVATIVE_SOURCE_REFERENCE":
            raise D14NaturalActiveAuditRejected("DERIVATIVE_RECORD_TYPE_CHANGED")
        kind = e.get("kind")
        if kind in ("LIFE_DECISION", "LIFE_ACTION", "LIFE_READBACK_FAILED"):
            if e.get("original_paper_line") != "":
                raise D14NaturalActiveAuditRejected("LIFE_EVENT_FORGED_PAPER_LINE")
            observed = e.get("native_observation")
            if not isinstance(observed, dict):
                raise D14NaturalActiveAuditRejected("LIFE_EVENT_WITHOUT_NATIVE_SOURCE")
            if kind == "LIFE_DECISION":
                life_decisions.append(observed)
            elif kind == "LIFE_ACTION":
                life_actions.append(observed)
            continue
        if kind in ("NATIVE_OBSERVATION", "NATIVE_OBSERVATION_FAILED"):
            if kind == "NATIVE_OBSERVATION":
                native_count += 1
            continue
        if marker_kind(e.get("original_paper_line", "")) != kind:
            raise D14NaturalActiveAuditRejected("DERIVATIVE_PAPER_KIND_CHANGED")
        derived_paper.append((kind, e["original_paper_line"]))
    if (
        derived_paper != original_rows
        or native_count != len(report.get("native_snapshots", []))
        or len(life_decisions) != report.get("life_decision_count")
        or len(life_actions) != report.get("life_outcome_count")
    ):
        raise D14NaturalActiveAuditRejected("DERIVATIVE_PAPER_OR_LIFE_COUNT_MISMATCH")

    last_cycle = 0
    last_seq = -1
    session = report.get("original_s49_session_id")
    intent_id = report.get("original_s49_intent_id")
    if not session or session != report.get("native_session_id") or not intent_id:
        raise D14NaturalActiveAuditRejected("ORIGINAL_S49_SESSION_ID_UNBOUND")
    for event in life_decisions:
        if (
            type(event.get("cycle")) is not int
            or not last_cycle < event["cycle"] <= 64
            or event.get("session_id") != session
            or event.get("intent_id") != intent_id
            or type(event.get("native_seq")) is not int
            or type(event.get("previous_seq")) is not int
            or not last_seq < event["previous_seq"] < event["native_seq"]
            or type(event.get("native_request_id")) is not str
            or not event["native_request_id"]
            or event.get("source") != "NATIVE_BODY_WORLD_CURRENT_NOT_GLOBAL_TRUTH"
        ):
            raise D14NaturalActiveAuditRejected("LIFE_NATIVE_SEQUENCE_OR_INTENT_REPLAY")
        last_cycle, last_seq = event["cycle"], event["native_seq"]

    fence.require_clear()
    rows = fence.actions
    if (
        fence.self_id != "s49-original-self"
        or fence.sha256 != report.get("original_s49_fence_sha256")
        or len(rows) != report.get("new_s49_actions")
        or len(rows) != len(life_actions)
        or report.get("original_s49_supervisor_open") != 0
        or report.get("original_s49_fence_unresolved") is not False
        or report.get("original_s49_fence_action_ids")
            != [row["action_id"] for row in rows]
    ):
        raise D14NaturalActiveAuditRejected("ORIGINAL_S49_FENCE_OR_OUTCOME_MISMATCH")
    seen = set()
    for event, row in zip(life_actions, rows):
        if (
            row["status"] != "S16_OUTCOME"
            or row["terminal"] != "outcome"
            or row["session_id"] != session
            or row["intent_id"] != intent_id
            or row["action_id"] in seen
            or event.get("action_id") != row["action_id"]
            or event.get("kind") != row["kind"]
            or event.get("terminal") != "outcome"
            or event.get("session_id") != session
            or event.get("original_fence_sha256") is None
        ):
            raise D14NaturalActiveAuditRejected("ORIGINAL_ACTION_NOT_SOURCE_VERIFIED")
        seen.add(row["action_id"])
    return {
        "status": "PASS_DEV",
        "classification": "D14_R4_NATURAL_WORLD_ORIGINAL_S49_SOURCE_AUDITED",
        "world_uuid": timeline.source_summary()["world_uuid"],
        "observed_world_ticks": result["elapsed_ticks"],
        "eventual_reason": result["terminal_reason"],
        "reached_10000_ticks": result["outcome"] == "WORLD_TICK_LIMIT_REACHED",
        "self_died_before_limit": result["self_died_before_limit"],
        "life_decisions": len(life_decisions),
        "original_s49_actions": len(rows),
        "original_s49_s16_outcomes": len(rows),
        "original_s49_action_kinds": [row["kind"] for row in rows],
        "original_s49_fence_sha256": fence.sha256,
        "c1_intent_experiences_committed": 0,
        "learning_updates": 0,
        "long_run_autonomous_self_proven": False,
        "qualification": "NO_GO", "science": "NOT_RUN",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    for name in ("report", "server-log", "event-journal", "nonmotion-fence", "out"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    report = json.loads(args.report.read_text(encoding="utf8"))
    fence = OriginalS49NonMotionFence.restore(
        args.nonmotion_fence, self_id="s49-original-self",
    )
    outcome = audit_active(
        report,
        args.server_log.read_text(encoding="utf8"),
        args.event_journal.read_text(encoding="utf8"),
        fence, original_sha=_sha(args.server_log),
        derivative_sha=_sha(args.event_journal),
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("x", encoding="utf8") as out:
        json.dump(outcome, out, sort_keys=True, indent=2)
        out.write("\n")
    print(outcome["classification"], outcome["eventual_reason"])


if __name__ == "__main__":
    main()
