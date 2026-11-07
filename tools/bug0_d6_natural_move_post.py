"""D6-D independent original Paper / original S49 ATTACK+MOVE dual-fence audit.

Separate provenance: Paper death+natural ItemSpawn/Pickup UUID, native
ATTACK/S15 MOVE/rotten-flesh inventory, original S49 supervisor and two
non-atomic durable pre-ISSUE journals. No self EAT or survival claim.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from relay_self.c1_physical_action_fence import OriginalS49PhysicalFence
from relay_self.s49_nonmotion_physical_fence import OriginalS49NonMotionFence

UUID = r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}"
INITIAL = re.compile(
    rf"RSELF_RESPAWN_INITIAL world=(?P<world>{UUID}) "
    rf"entity=(?P<zombie>{UUID}) generation=1 tick=(?P<tick>\d+)"
)
DEATH = re.compile(
    rf"RSELF_NATURAL_DROP_DEATH world=(?P<world>{UUID}) "
    rf"zombie=(?P<zombie>{UUID}) tick=(?P<tick>\d+) "
    rf"rotten_count=(?P<count>\d+) killer=(?P<killer>{UUID}) "
    r"source=ACTUAL_PAPER_ENTITY_DEATH_DROPS killer_is_relay_self=true"
)
RESPAWN_DEATH = re.compile(
    rf"RSELF_RESPAWN_DEATH world=(?P<world>{UUID}) "
    rf"entity=(?P<zombie>{UUID}) generation=1 "
    rf"tick=(?P<tick>\d+) due_tick=(?P<due>\d+) "
    rf"paper_drops=(?P<count>\d+) killer=(?P<killer>{UUID})"
)
SPAWN = re.compile(
    rf"RSELF_NATURAL_DROP_SPAWN world=(?P<world>{UUID}) "
    rf"zombie=(?P<zombie>{UUID}) item=(?P<item>{UUID}) "
    rf"tick=(?P<tick>\d+) rotten_count=(?P<count>\d+) "
    r"source=ACTUAL_PAPER_ITEM_SPAWN_NEAR_DEATH"
)
PICKUP = re.compile(
    rf"RSELF_NATURAL_DROP_PICKUP world=(?P<world>{UUID}) "
    rf"zombie=(?P<zombie>{UUID}) item=(?P<item>{UUID}) "
    rf"player=(?P<player>{UUID}) tick=(?P<tick>\d+) "
    rf"rotten_count=(?P<count>\d+) source=ACTUAL_PAPER_ITEM_PICKUP"
)
RESPAWN = re.compile(
    rf"RSELF_RESPAWN_SPAWN world=(?P<world>{UUID}) "
    rf"entity=(?P<zombie>{UUID}) generation=2 tick=(?P<tick>\d+)"
)


class D6DNaturalAuditRejected(ValueError):
    """Inconsistent World, original S49 physical outcome or provenance."""


def _one(source: str, regex: re.Pattern[str]) -> dict[str, str]:
    values = [m.groupdict() for m in regex.finditer(source)]
    if len(values) != 1:
        raise D6DNaturalAuditRejected(
            f"original Paper expected one {regex.pattern[:45]}"
        )
    return values[0]


def audit(
    original_log: str, report: dict,
    nonmotion_path: Path, motion_path: Path,
) -> dict:
    if (
        not isinstance(report, dict)
        or report.get("status") != "PASS_DEV"
        or report.get("cleanup_done") is not True
        or report.get("node_exit") != 0
        or report.get("java_exit") != 0
        or report.get("real_world_started") is not True
        or report.get("self_eat") is not False
        or report.get("original_action_issuer") != "S49"
        or report.get("operator_staged_no_ai") is not True
        or report.get("d6_operator_zombie_staged_behind_m") != 2.2
        or report.get("d6_native_orientation_optin") is not True
        or report.get("d6_no_hunger_intervention") is not True
        or report.get("self_goal_selected_autonomously") is not False
        or report.get("real_model_calls") != 0
        or report.get("learning_updated") is not False
        or report.get("d4_self_eat_issued") is not False
        or report.get("d4_eat_terminal") not in (
            "NOT_ISSUED", "NOT_ISSUED_AFTER_MOVE",
        )
        or "effect give RelaySelf minecraft:hunger 70 20 true"
           in report.get("operator_world_staging", ())
        or "rselfstagefood" in original_log
        or "RSELF_LOOT_STAGED" in original_log
        or "RSELF_NATURAL_DROP_FAULT" in original_log
        or "RSELF_RESPAWN_FAULT" in original_log
    ):
        raise D6DNaturalAuditRejected("D6 natural World identity or scope invalid")
    initial = _one(original_log, INITIAL)
    death = _one(original_log, DEATH)
    rdeath = _one(original_log, RESPAWN_DEATH)
    respawn = _one(original_log, RESPAWN)
    if (
        initial["world"] != death["world"]
        or initial["world"] != rdeath["world"]
        or initial["world"] != respawn["world"]
        or initial["zombie"] != death["zombie"]
        or initial["zombie"] != rdeath["zombie"]
        or initial["zombie"] == respawn["zombie"]
        or death["killer"] != rdeath["killer"]
        or int(initial["tick"]) >= int(death["tick"])
        or death["tick"] != rdeath["tick"]
        or int(rdeath["due"]) - int(death["tick"]) != 600
        or int(respawn["tick"]) != int(rdeath["due"])
        or death["count"] != rdeath["count"]
    ):
        raise D6DNaturalAuditRejected("Paper first death / owner / 600tick mismatch")
    amount = int(death["count"])
    if not 0 <= amount <= 2:
        raise D6DNaturalAuditRejected("unqualified true random natural loot count")
    nonmotion = OriginalS49NonMotionFence.restore(
        nonmotion_path, self_id="s49-original-self",
    )
    motion = OriginalS49PhysicalFence.restore(
        motion_path, self_id="s49-original-self",
    )
    nonmotion.require_clear()
    motion.require_clear()
    sid = report.get("session_id")
    attacks = report.get("s49_actions")
    moves = report.get("d6_original_s49_move_actions", [])
    if (
        type(sid) is not str or not sid
        or not isinstance(attacks, list) or not 1 <= len(attacks) <= 8
        or not isinstance(moves, list)
        or report.get("attack_count") != len(attacks)
        or len(nonmotion.actions) != len(attacks)
        or len(motion.actions) != len(moves)
        or report.get("d4_combat_closed_action_count") != len(attacks)
        or report.get("d4_final_action_count") != len(attacks) + len(moves)
        or report.get("d4_final_supervisor_open_count") != 0
        or report.get("nonmotion_fence", {}).get("sha256") != nonmotion.sha256
        or report.get("motion_fence", {}).get("sha256") != motion.sha256
        or report.get("nonmotion_fence", {}).get("unresolved") is not False
        or report.get("motion_fence", {}).get("unresolved") is not False
    ):
        raise D6DNaturalAuditRejected("original S49 Action and dual C1 fence count invalid")
    last_attack_seq = -1
    attack_ids: list[str] = []
    for physical, row in zip(nonmotion.actions, attacks):
        if (
            physical.get("kind") != "ATTACK"
            or physical.get("status") != "S16_OUTCOME"
            or physical.get("session_id") != sid
            or physical.get("action_id") != row.get("action_id")
            or physical.get("intent_id") != "escape-threat"
            or row.get("session_id") != sid
            or row.get("target_entity_id")
            != report.get("native_initial", {}).get("zombie_entity_id")
            or row.get("terminal") != "outcome"
            or row.get("ack") != "applied"
            or not (
                last_attack_seq < row.get("previous_seq", -1)
                < row.get("admitted_seq", -1)
                < row.get("effect_seq", -1)
                < row.get("after_seq", -1)
            )
        ):
            raise D6DNaturalAuditRejected("original S49 ATTACK/native ledger mismatch")
        last_attack_seq = row["after_seq"]
        attack_ids.append(row["action_id"])
    gain = report.get("d4_native_before")
    if (
        not isinstance(gain, dict)
        or gain.get("rotten_flesh") != 0
        or gain.get("session_id") != sid
        or report.get("real_rotten_flesh_count") != amount
        or report.get("d4_natural_count") != amount
    ):
        raise D6DNaturalAuditRejected("pre-kill Self inventory or true Paper amount mismatch")
    item = None
    if amount:
        item, pickup = _one(original_log, SPAWN), _one(original_log, PICKUP)
        if (
            item["world"] != initial["world"] or pickup["world"] != initial["world"]
            or item["zombie"] != initial["zombie"]
            or pickup["zombie"] != initial["zombie"]
            or item["item"] != pickup["item"]
            or item["count"] != pickup["count"]
            or int(item["count"]) != amount
            or pickup["player"] != death["killer"]
            or not int(death["tick"]) <= int(item["tick"]) < int(pickup["tick"])
            or int(pickup["tick"]) >= int(respawn["tick"])
            or report.get("classification")
            != "D6_NATURAL_DROP_ORIGINAL_S49_ATTACK_MOVE_PICKUP_PASS"
            or report.get("self_move_to_loot") is not True
            or report.get("d4_self_move_for_item") is not True
            or report.get("d4_pickup_passive") is not False
            or report.get("d6_d_paper_pickup_absent_before_move") is not True
            or report.get("d6_d_same_attack_move_supervisor") is not True
            or report.get("d6_d_original_attack_action_ids_before_move")
            != sorted(attack_ids)
            or report.get("d6_d_original_count_before_move") != len(attacks)
            or report.get("d6_d_no_postmove_eat_grant") is not True
            or report.get("d6_post_move_eat_fenced") is not True
            or report.get("d6_eat_after_move") is not False
            or report.get("d6_item_origin") != "ACTUAL_PAPER_ZOMBIE_DEATH_EVENT"
            or report.get("d6_original_move_count") != len(moves)
            or not 1 <= len(moves) <= 4
            or report.get("d6_item_native_id") != moves[0].get("item_entity_id")
            or report.get("d4_native_after_pickup", {}).get("rotten_flesh") != amount
        ):
            raise D6DNaturalAuditRejected("natural spawn/pickup or original MOVE proof absent")
        last_move_seq = last_attack_seq
        for persisted, move in zip(motion.actions, moves):
            if (
                persisted.get("status") != "S16_OUTCOME"
                or persisted.get("action_ref") != "MOVE_BACKWARD"
                or persisted.get("session_id") != sid
                or persisted.get("intent_id") != "escape-threat"
                or persisted.get("action_id") != move.get("action_id")
                or persisted.get("decision_seq") != move.get("decision_seq")
                or persisted.get("decision_request_id") != move.get("decision_request_id")
                or persisted.get("before_seq") != move.get("s15_before_seq")
                or persisted.get("dispatch_seq") != move.get("s15_dispatch_seq")
                or persisted.get("cleanup_seq") != move.get("s15_clear_seq")
                or persisted.get("after_seq") != move.get("s15_after_seq")
                or persisted.get("movement_m") != move.get("movement_m")
                or move.get("item_entity_id") != report["d6_item_native_id"]
                or move.get("terminal") != "outcome"
                or move.get("food_identity_verified_by_entity") is not False
                or move.get("pickup_verified_by_move_alone") is not False
                or not (
                    last_move_seq < move.get("decision_seq", -1)
                    < move.get("s15_before_seq", -1)
                    < move.get("s15_dispatch_seq", -1)
                    < move.get("s15_clear_seq", -1)
                    < move.get("s15_after_seq", -1)
                )
                or not (
                    move.get("target_distance_before_m", 0)
                    > move.get("target_distance_after_m", -1) + 0.05
                )
            ):
                raise D6DNaturalAuditRejected("original S49 C1 physical item MOVE mismatch")
            last_move_seq = move["s15_after_seq"]
        if report["d4_native_after_pickup"]["seq"] <= last_move_seq:
            raise D6DNaturalAuditRejected("native inventory not confirmed after real MOVE")
    else:
        if (
            SPAWN.search(original_log) or PICKUP.search(original_log)
            or report.get("classification") != "D6_NATURAL_ZERO_LOOT_NO_MOVE"
            or report.get("self_move_to_loot") is not False
            or moves or motion.actions
            or report.get("d4_self_eat_issued") is not False
            or report.get("d4_native_after_zero", {}).get("rotten_flesh") != 0
        ):
            raise D6DNaturalAuditRejected("zero natural loot cannot mint Self MOVE/pickup")
    return {
        "classification": report["classification"],
        "status": "PASS_DEV",
        "paper_world_uuid": initial["world"],
        "original_zombie_uuid": initial["zombie"],
        "paper_relay_self_killer_uuid": death["killer"],
        "death_tick": int(death["tick"]),
        "respawn_tick": int(respawn["tick"]),
        "actual_natural_rotten_flesh_count": amount,
        "paper_item_uuid": item["item"] if item else None,
        "paper_item_spawn_and_pickup": bool(item),
        "original_s49_attack_action_ids": attack_ids,
        "original_s49_move_action_ids": [m["action_id"] for m in moves],
        "same_original_supervisor": bool(item),
        "nonmotion_fence_sha256": nonmotion.sha256,
        "motion_fence_sha256": motion.sha256,
        "dual_fences_atomic": False,
        "operator_staged_low_health_no_ai_zombie": True,
        "operator_staged_item": False,
        "post_move_eat_authorized": False,
        "second_complete_cycle": False,
        "unlimited_survival_proven": False,
        "qualification": "NO_GO",
        "science": "NOT_RUN",
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--report", type=Path, required=True)
    p.add_argument("--server-log", type=Path, required=True)
    p.add_argument("--nonmotion-fence", type=Path, required=True)
    p.add_argument("--motion-fence", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    row = audit(
        args.server_log.read_text(encoding="utf8"),
        json.loads(args.report.read_text(encoding="utf8")),
        args.nonmotion_fence, args.motion_fence,
    )
    args.out.write_text(json.dumps(row, sort_keys=True, indent=2) + "\n",
                        encoding="utf8")
    print(row["classification"])


if __name__ == "__main__":
    main()
