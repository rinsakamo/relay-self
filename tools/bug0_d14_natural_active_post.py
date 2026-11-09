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

from relay_self.c1_physical_action_fence import OriginalS49PhysicalFence
from relay_self.s49_nonmotion_physical_fence import OriginalS49NonMotionFence
from tools.bug0_d14_natural_world import (
    NATURAL_PLUGIN_CONFIG,
    R10_PLUGIN_CONFIG,
    R11_PLUGIN_CONFIG,
    R11_WORLD_TICKS,
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
    motion_fence: OriginalS49PhysicalFence | None = None,
) -> dict[str, Any]:
    r6 = report.get("classification") == (
        "DEV_D14_R6_NATURAL_ORIGINAL_S49_MOTION_SOURCE_OBSERVED"
    )
    r10 = report.get("r10_initial_sword_opt_in") is True
    r11 = report.get("r11_natural_day_opt_in") is True
    if (r6 and motion_fence is None) or (not r6 and motion_fence is not None):
        raise D14NaturalActiveAuditRejected("R6_MOTION_FENCE_SCOPE_MISMATCH")
    if (
        report.get("status") != "PASS_DEV"
        or report.get("classification") not in (
            "DEV_D14_R6_NATURAL_ORIGINAL_S49_MOTION_SOURCE_OBSERVED",
            "DEV_D14_R4_NATURAL_ACTIVE_S49_SOURCE_OBSERVED",
        )
        or report.get("cleanup_done") is not True
        or report.get("node_exit") != 0 or report.get("java_exit") != 0
        or report.get("paper_original_sha256") != original_sha
        or report.get("derivative_journal_sha256") != derivative_sha
        or report.get("plugin_config") != (
            R11_PLUGIN_CONFIG if r11 else
            R10_PLUGIN_CONFIG if r10 else NATURAL_PLUGIN_CONFIG
        )
        or (r11 and (
            not r10 or report.get("requested_paper_horizon_ticks") != R11_WORLD_TICKS
        ))
        or (r10 and report.get("r10_operator_initial_equipment")
            != "VANILLA_STONE_SWORD_MAIN_HAND_ONE_PAPER_INITIAL_GRANT")
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
        or report.get("move_admission") != (
            "R6_ORIGINAL_S49_NATIVE_ENTITIES_S14_DURABLE_FENCE"
            if r6 else "NOT_CONNECTED_IN_R4"
        )
        or (r6 and report.get("stop_settling")
            != "R6_S15_CLEAR_ACK_ONLY_PHYSICAL_STOP_UNATTESTED")
        or report.get("intent_rearm") != "NOT_CONNECTED_IN_R4"
    ):
        raise D14NaturalActiveAuditRejected("WORLD_OR_OWNER_SOURCE_NOT_QUALIFIED")

    timeline = NaturalPaperTimeline(
        horizon_ticks=R11_WORLD_TICKS if r11 else 10000,
    )
    original_rows = []
    # Paper console lines can contain carriage returns before the marker.
    # The live reader preserves those bytes within each LF-delimited line.
    for line in paper_original.split("\n"):
        kind = marker_kind(line)
        if kind is not None:
            timeline.admit(kind, line)
            original_rows.append((kind, line))
    result = timeline.finish()
    # The R10 operator-provided sword is a real Paper-logged world input,
    # not an S49 Action and not a naturally crafted item. Reject duplicate
    # or reordered equipment, source spoofing, and any sword without opt-in.
    equipment_lines = [
        x for x in paper_original.split("\n")
        if "RSELF_R10_INITIAL_STONE_SWORD world=" in x
    ]
    if r10:
        source = timeline.source_summary()
        equipped = equipment_lines[0] if len(equipment_lines) == 1 else ""
        first_initial = timeline.initial[0] if timeline.initial else ""
        if (
            len(equipment_lines) != 1
            or not first_initial
            or paper_original.find(equipped) > paper_original.find(first_initial)
            or "world=" + source["world_uuid"] not in equipped
            or not all(fragment in equipped for fragment in (
                " item=STONE_SWORD count=1 hand=MAIN_HAND",
                " source=PAPER_OPERATOR_INITIAL_ONLY",
                " physics=VANILLA no_auto_attack=true",
            ))
            or not any(
                "RSELF_R10_SOURCE_READY " in line
                for line in paper_original.split("\n")
            )
        ):
            raise D14NaturalActiveAuditRejected(
                "R10_INITIAL_EQUIPMENT_PAPER_SOURCE_NOT_ATTESTED"
            )
    elif equipment_lines:
        raise D14NaturalActiveAuditRejected(
            "R10_STONE_SWORD_WITHOUT_OPERATOR_OPT_IN"
        )
    if (
        result != report.get("result")
        or timeline.source_summary() != report.get("paper_source")
    ):
        raise D14NaturalActiveAuditRejected("WORLD_CLOCK_OR_TERMINAL_INCONSISTENT")

    derived_paper = []
    native_count = 0
    life_decisions = []
    life_actions = []
    native_safe_stops = []
    preceding_native_errors = 0
    last_original_sample = None
    paper_terminal_seen = False
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
        if kind in ("NATIVE_OBSERVATION", "NATIVE_OBSERVATION_FAILED",
                    "NATIVE_SAFE_STOP"):
            if kind == "NATIVE_OBSERVATION":
                native_count += 1
                preceding_native_errors = 0
            elif kind == "NATIVE_OBSERVATION_FAILED":
                preceding_native_errors += 1
            else:
                record = e.get("native_observation")
                if (
                    len(native_safe_stops) != 0
                    or paper_terminal_seen
                    or preceding_native_errors < 2
                    or not isinstance(record, dict)
                    or type(record.get("consecutive_failures")) is not int
                    or record["consecutive_failures"] < 2
                    or record.get("reason")
                        != "NATIVE_READBACK_UNAVAILABLE_ACTION_STOP"
                    or record.get("after_sample") != e.get("original_paper_line")
                    or e.get("original_paper_line") != last_original_sample
                    or marker_kind(e.get("original_paper_line", "")) != "SAMPLE"
                    or e.get("original_paper_line") not in [
                        row for kind0, row in original_rows if kind0 == "SAMPLE"
                    ]
                ):
                    raise D14NaturalActiveAuditRejected(
                        "NATIVE_SAFE_STOP_WITHOUT_TWO_PAPER_BOUND_FAILURES"
                    )
                native_safe_stops.append(record)
            continue
        if marker_kind(e.get("original_paper_line", "")) != kind:
            raise D14NaturalActiveAuditRejected("DERIVATIVE_PAPER_KIND_CHANGED")
        derived_paper.append((kind, e["original_paper_line"]))
        if kind == "SAMPLE":
            last_original_sample = e["original_paper_line"]
        elif kind in ("LIMIT", "TERMINAL"):
            paper_terminal_seen = True
    if (
        derived_paper != original_rows
        or native_count != len(report.get("native_snapshots", []))
        or len(life_decisions) != report.get("life_decision_count")
        or len(life_actions) != report.get("life_outcome_count")
        or native_safe_stops != (
            [report["native_observation_safe_stop"]]
            if "native_observation_safe_stop" in report else []
        )
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
            or not last_cycle < event["cycle"] <= (4096 if r11 else 1024)
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
        if r11 and (
            event.get("r11_item_type_from_native") != "UNKNOWN"
            or event.get("r11_item_approach_authorization") != "NOT_CONNECTED"
            or not isinstance(event.get("r11_native_dropped_item_candidates"), list)
            or any(
                type(item.get("entity_id")) is not int
                or type(item.get("distance")) not in (int, float)
                or item["distance"] < 0
                for item in event["r11_native_dropped_item_candidates"]
                if isinstance(item, dict)
            )
            or any(
                not isinstance(item, dict)
                for item in event["r11_native_dropped_item_candidates"]
            )
            or (
                event.get("r11_native_rotten_inventory_delta_since_last_decision")
                is not None
                and type(event["r11_native_rotten_inventory_delta_since_last_decision"])
                is not int
            )
        ):
            raise D14NaturalActiveAuditRejected(
                "R11_NATIVE_ITEM_READ_ONLY_PROJECTION_UNQUALIFIED"
            )
        last_cycle, last_seq = event["cycle"], event["native_seq"]

    fence.require_clear()
    rows = fence.actions
    moves = ()
    if r6:
        assert motion_fence is not None
        motion_fence.require_clear()
        moves = motion_fence.actions
        if (
            motion_fence.self_id != "s49-original-self"
            or motion_fence.sha256 != report.get("original_s49_move_fence_sha256")
            or report.get("original_s49_move_fence_unresolved") is not False
            or report.get("original_s49_move_fence_action_ids")
                != [item["action_id"] for item in moves]
            or report.get("original_s49_post_move_settling_unqualified")
                is not bool(moves)
            or type(report.get("r6_native_entities_event_count")) is not int
            or report["r6_native_entities_event_count"] < len(moves)
        ):
            raise D14NaturalActiveAuditRejected("ORIGINAL_MOVE_FENCE_LINEAGE_NOT_ATTESTED")
    if (
        fence._body.get("self_id") != "s49-original-self"
        or fence.sha256 != report.get("original_s49_fence_sha256")
        or len(rows) + len(moves) != report.get("new_s49_actions")
        or len(rows) + len(moves) != len(life_actions)
        or report.get("original_s49_supervisor_open") != 0
        or report.get("original_s49_fence_unresolved") is not False
        or report.get("original_s49_fence_action_ids")
            != [row["action_id"] for row in rows]
    ):
        raise D14NaturalActiveAuditRejected("ORIGINAL_S49_FENCE_OR_OUTCOME_MISMATCH")
    nonmotion_by_id = {row["action_id"]: row for row in rows}
    motion_by_id = {row["action_id"]: row for row in moves}
    if set(nonmotion_by_id) & set(motion_by_id):
        raise D14NaturalActiveAuditRejected("CROSS_FENCE_ACTION_ID_REPLAY")
    seen = set()
    for event in life_actions:
        action_id = event.get("action_id")
        kind = event.get("kind")
        if (
            not isinstance(action_id, str) or action_id in seen
            or event.get("terminal") != "outcome"
            or event.get("session_id") != session
        ):
            raise D14NaturalActiveAuditRejected("ORIGINAL_ACTION_ID_OR_TERMINAL_REPLAY")
        if kind in ("ATTACK", "EAT"):
            row = nonmotion_by_id.get(action_id)
            if (
                row is None
                or row["status"] != "S16_OUTCOME"
                or row["terminal"] != "outcome"
                or row["session_id"] != session
                or row["intent_id"] != intent_id
                or row["kind"] != kind
                or event.get("original_fence_sha256") is None
                or event.get("native_admitted_seq") != row["probe_seq"]
            ):
                raise D14NaturalActiveAuditRejected(
                    "ORIGINAL_NONMOTION_ACTION_NOT_SOURCE_VERIFIED"
                )
        elif r6 and kind == "MOVE_AWAY":
            row = motion_by_id.get(action_id)
            if (
                row is None
                or row["status"] != "S16_OUTCOME"
                or row["terminal_state"] != "outcome"
                or row["action_ref"] != "MOVE_BACKWARD"
                or row["session_id"] != session
                or row["intent_id"] != intent_id
                or event.get("native_admitted_seq") != row["decision_seq"]
                or event.get("native_event_seq") is None
                or type(event["native_event_seq"]) is not int
                or not 0 <= event["native_event_seq"] < row["decision_seq"]
                or event.get("movement_m") != row["movement_m"]
                or event.get("original_move_fence_sha256") is None
                or event.get("s15_clear_ack") != "ORIGINAL"
                or event.get("effective_physical_stop") != "UNATTESTED"
                or event.get("post_move_eat_granted") is not False
                or report.get("stop_settling")
                    != "R6_S15_CLEAR_ACK_ONLY_PHYSICAL_STOP_UNATTESTED"
            ):
                raise D14NaturalActiveAuditRejected(
                    "ORIGINAL_MOTION_ACTION_OR_STOP_SOURCE_NOT_VERIFIED"
                )
        else:
            raise D14NaturalActiveAuditRejected("UNSUPPORTED_ORIGINAL_ACTION_KIND")
        seen.add(action_id)
    if seen != set(nonmotion_by_id) | set(motion_by_id):
        raise D14NaturalActiveAuditRejected("ORIGINAL_ACTION_JOURNAL_LINEAGE_MISSING")
    return {
        "status": "PASS_DEV",
        "classification": (
            "D14_R6_NATURAL_WORLD_S49_SOURCE_CONSISTENCY_AUDITED"
            if r6 else "D14_R4_NATURAL_WORLD_ORIGINAL_S49_SOURCE_AUDITED"
        ),
        "world_uuid": timeline.source_summary()["world_uuid"],
        "observed_world_ticks": result["elapsed_ticks"],
        "eventual_reason": result["terminal_reason"],
        "reached_10000_ticks": (
            not r11 and result["outcome"] == "WORLD_TICK_LIMIT_REACHED"
        ),
        "r11_natural_day_opt_in": r11,
        "r11_observed_horizon_ticks": result["elapsed_ticks"],
        "r11_full_day_survival_observed": (
            r11 and result["outcome"] == "WORLD_TICK_LIMIT_REACHED"
            and result["elapsed_ticks"] == R11_WORLD_TICKS
        ),
        "r11_native_item_candidate_decisions": sum(
            bool(e.get("r11_native_dropped_item_candidates"))
            for e in life_decisions
        ) if r11 else 0,
        "r11_native_positive_rotten_inventory_deltas": [
            e["r11_native_rotten_inventory_delta_since_last_decision"]
            for e in life_decisions
            if r11 and type(e.get("r11_native_rotten_inventory_delta_since_last_decision")) is int
            and e["r11_native_rotten_inventory_delta_since_last_decision"] > 0
        ],
        "r11_item_approach_action_granted": False,
        "self_died_before_limit": result["self_died_before_limit"],
        "life_decisions": len(life_decisions),
        "native_safe_stops": len(native_safe_stops),
        "active_l0_stopped_after_native_loss": bool(native_safe_stops),
        "original_s49_actions": len(rows) + len(moves),
        "original_s49_s16_outcomes": len(rows) + len(moves),
        "original_s49_motion_actions": len(moves),
        "original_s49_action_kinds": [e["kind"] for e in life_actions],
        "original_s49_fence_sha256": fence.sha256,
        "original_s49_motion_fence_sha256": (
            motion_fence.sha256 if motion_fence is not None else None
        ),
        "native_entity_event_independently_attested": False,
        "effective_physical_stop_attested": False,
        "r10_operator_initial_stone_sword_attested": r10,
        "r10_paper_damage_event_count_source_only": sum(
            "RSELF_R10_ZOMBIE_DAMAGE source=PAPER_ENTITY_DAMAGE_MONITOR" in row
            for row in paper_original.split("\n")
        ) if r10 else 0,
        "r10_paper_self_damage_event_count_source_only": sum(
            "RSELF_R10_SELF_DAMAGE source=PAPER_ENTITY_DAMAGE_MONITOR" in row
            for row in paper_original.split("\n")
        ) if r10 else 0,
        "r10_damage_caused_by_specific_s49_action_attested": False,
        "c1_intent_experiences_committed": 0,
        "learning_updates": 0,
        "long_run_autonomous_self_proven": False,
        "qualification": "NO_GO", "science": "NOT_RUN",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    for name in ("report", "server-log", "event-journal", "nonmotion-fence", "out"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--motion-fence", type=Path)
    args = parser.parse_args()
    report = json.loads(args.report.read_text(encoding="utf8"))
    fence = OriginalS49NonMotionFence.restore(
        args.nonmotion_fence, self_id="s49-original-self",
    )
    outcome = audit_active(
        report,
        args.server_log.read_bytes().decode("utf8"),
        args.event_journal.read_text(encoding="utf8"),
        fence, original_sha=_sha(args.server_log),
        derivative_sha=_sha(args.event_journal),
        motion_fence=(
            OriginalS49PhysicalFence.restore(
                args.motion_fence, self_id="s49-original-self",
            )
            if args.motion_fence is not None else None
        ),
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("x", encoding="utf8") as out:
        json.dump(outcome, out, sort_keys=True, indent=2)
        out.write("\n")
    print(outcome["classification"], outcome["eventual_reason"])


if __name__ == "__main__":
    main()
