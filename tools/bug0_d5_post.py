"""Independent read-only D5 audit: D4 full proof + next Intent one S49 Action.

This proves the second physical ATTACK, not a second kill/loot/eat cycle.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from tools.bug0_d4_post import audit as audit_d4


class D5OriginalAuditRejected(ValueError):
    pass


def audit(log: str, report: dict) -> dict:
    if (
        not isinstance(report, dict)
        or report.get("status") != "PASS_DEV"
        or report.get("classification") != "D5_REAL_S49_SECOND_INTENT_ATTACK_PASS"
        or report.get("node_exit") != 0
        or report.get("java_exit") != 0
        or report.get("cleanup_done") is not True
        or report.get("d5_second_experience_completed") is not False
        or report.get("d5_second_kill_attested") is not False
        or report.get("d5_self_move_to_loot") is not False
    ):
        raise D5OriginalAuditRejected("D5 final status or evidence scope invalid")
    # The real D4 prefix remains intact: D5 emits no second death/drop.
    # Reuse D4's established Paper, native pickup, EAT and tick audit
    # against the exact same original log, with only its scope label restored.
    first_eat = report.get("d4_natural_food_pickup_eat_proven")
    if type(first_eat) is not bool:
        raise D5OriginalAuditRejected("missing original D4 conditional EAT outcome")
    original_d4 = dict(
        report,
        classification=(
            "D4_REAL_NATURAL_LOOT_PICKUP_S49_EAT_AND_RESPAWN_PASS"
            if first_eat else "D4_GENUINE_ZERO_LOOT_NO_EAT_RESPAWN_PASS"
        ),
    )
    try:
        d4 = audit_d4(log, original_d4)
    except (ValueError, KeyError, TypeError) as exc:
        raise D5OriginalAuditRejected("first real D4 experience unqualified") from exc
    a = report.get("d5_second_action")
    e = report.get("d5_rearm")
    n = report.get("d5_new_zombie_native")
    first = report.get("s49_actions")
    last = (first or [])[-1] if isinstance(first, list) and first else {}
    old_count = report.get("d4_final_action_count")
    new_id = report.get("native_respawn", {}).get("zombie_entity_id")
    old_id = report.get("native_initial", {}).get("zombie_entity_id")
    sid = report.get("session_id")
    commands = report.get("d5_operator_world_staging")
    if (
        not isinstance(a, dict)
        or not isinstance(e, dict)
        or not isinstance(n, dict)
        or not isinstance(last, dict)
        or type(old_count) is not int or old_count < 2
        or type(new_id) is not int or type(old_id) is not int
        or old_id == new_id
        or e.get("session_id") != sid
        or e.get("next_epoch") != 2
        or e.get("completed_intent_id") != "escape-threat"
        or e.get("next_intent_id") != "bug0-d5-second-zombie-encounter"
        or e.get("completed_action_count") != old_count
        or e.get("previous_zombie_entity_id") != old_id
        or e.get("next_zombie_entity_id") != new_id
        or not e.get("next_source")
        or e.get("physically_issued") is not False
        or n.get("session_id") != sid
        or n.get("zombie_entity_id") != new_id
        or n.get("source") != e.get("next_source")
        or n.get("truncated") is not False
        or type(n.get("candidate_count")) is not int
        or n.get("candidate_count") < 1
        or not n.get("request_id")
        or type(n.get("seq")) is not int
        or n["seq"] <= report.get("native_respawn", {}).get("seq", -1)
        or not isinstance(commands, list)
        or len(commands) != 2
        or not commands[0].startswith("execute at RelaySelf run tp ")
        or not commands[1].startswith("data merge entity ")
    ):
        raise D5OriginalAuditRejected("fresh native rearm/new-generation source invalid")
    if (
        a.get("intent_id") != e["next_intent_id"]
        or a.get("session_id") != sid
        or a.get("target_entity_id") != new_id
        or not a.get("action_id")
        or a["action_id"] in {x.get("action_id") for x in first}
        or a.get("terminal") != "outcome"
        or a.get("ack") != "applied"
        or any(type(a.get(k)) is not int for k in (
            "previous_seq", "admitted_seq", "effect_seq", "after_seq"
        ))
        or not (
            last["after_seq"] < n["seq"] < a["previous_seq"]
            < a["admitted_seq"] < a["effect_seq"] < a["after_seq"]
        )
        or report.get("d5_owner_total_action_count") != old_count + 1
        or report.get("d5_supervisor_open_count") != 0
        or report.get("d5_retained_old_actions") is not True
        or report.get("d5_same_supervisor_identity") is not True
    ):
        raise D5OriginalAuditRejected("second Intent PROPOSE/ISSUE/OUTCOME invalid")
    return {
        **d4,
        "classification": "D5_REAL_S49_SECOND_INTENT_ATTACK_PASS",
        "same_session_id": sid,
        "same_supervisor": True,
        "old_intent_action_count": old_count,
        "first_real_food_eaten": first_eat,
        "first_world_zero_loot_valid": not first_eat,
        "new_intent_id": a["intent_id"],
        "new_zombie_entity_id": new_id,
        "new_action_id": a["action_id"],
        "new_action_outcome": a["terminal"],
        "second_intent_attack_proven": True,
        "second_experience_cycle_completed": False,
        "second_kill_pickup_eat_proven": False,
        "self_move_to_loot_proven": False,
        "unlimited_survival_proven": False,
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--server-log", type=Path, required=True)
    p.add_argument("--report", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    result = audit(
        args.server_log.read_text(encoding="utf8"),
        json.loads(args.report.read_text(encoding="utf8")),
    )
    args.out.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n",
                        encoding="utf8")
    print(result["classification"])


if __name__ == "__main__":
    main()
