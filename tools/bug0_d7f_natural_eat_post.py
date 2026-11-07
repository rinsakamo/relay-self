"""Independent D7-F real Paper natural item + original S49/S51 physical EAT audit.

No live permission is derived from this offline review. Original S49 was
the only physical issuer. Qualification is DEV_ONLY, not SCIENCE.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from adapters.mineflayer.d7_live_staged_stop import CONTROL_KEYS
from relay_self.c1_physical_action_fence import OriginalS49PhysicalFence
from relay_self.s49_nonmotion_physical_fence import OriginalS49NonMotionFence
from tools.bug0_d6_multigen_post import require_vanilla_paper_loot
from tools.bug0_d6_natural_move_post import (
    DEATH,
    INITIAL,
    PICKUP,
    RESPAWN,
    RESPAWN_DEATH,
    SPAWN,
    _one,
)
from tools.bug0_d7_paper_server_tick_post import (
    SOURCE,
    TICK_MARK,
    _fields,
    _inputs_off,
    _integer,
    _number,
)
from tools.bug0_d7e_staged_move_eat_post import native_integral_food


class D7FNaturalAuditRejected(ValueError):
    """Actual natural zombie source or original physical EAT unqualified."""


def audit(
    log: str, report: dict, client: str, *,
    nonmotion_path: Path, motion_path: Path,
) -> dict:
    if (
        not isinstance(log, str)
        or not isinstance(report, dict)
        or not isinstance(client, str)
        or report.get("status") != "PASS_DEV"
        or report.get("cleanup_done") is not True
        or report.get("node_exit") != 0 or report.get("java_exit") != 0
        or report.get("real_world_started") is not True
        or report.get("original_action_issuer") != "S49"
        or report.get("operator_staged_no_ai") is not True
        or report.get("d7f_live_eat_optin") is not True
        or report.get("d7f_operator_hunger_effect_dev") is not True
        or report.get("d6_no_hunger_intervention") is not False
        or report.get("real_model_calls") != 0
        or report.get("learning_updated") is not False
        or "RSELF_NATURAL_DROP_FAULT" in log
        or "RSELF_RESPAWN_FAULT" in log
        or "RSELF_LOOT_STAGED" in log
        or "rselfstagefood" in log
    ):
        raise D7FNaturalAuditRejected("D7-F real natural World/issuer scope invalid")
    require_vanilla_paper_loot(log)
    initial, death = _one(log, INITIAL), _one(log, DEATH)
    rdeath, respawn = _one(log, RESPAWN_DEATH), _one(log, RESPAWN)
    if (
        initial["world"] != death["world"]
        or initial["world"] != rdeath["world"]
        or initial["world"] != respawn["world"]
        or initial["zombie"] != death["zombie"]
        or initial["zombie"] != rdeath["zombie"]
        or initial["zombie"] == respawn["zombie"]
        or death["killer"] != rdeath["killer"]
        or death["tick"] != rdeath["tick"]
        or int(rdeath["due"]) != int(death["tick"]) + 600
        or int(respawn["tick"]) != int(rdeath["due"])
    ):
        raise D7FNaturalAuditRejected("true Paper killer/death/600tick respawn mismatch")
    count = int(death["count"])
    sid = report.get("session_id")
    attack = report.get("s49_actions")
    moves = report.get("d6_original_s49_move_actions", [])
    positive = count == 1
    if (
        not 0 <= count <= 2 or not isinstance(sid, str) or not sid
        or not isinstance(attack, list) or not 1 <= len(attack) <= 8
        or not isinstance(moves, list)
        or report.get("attack_count") != len(attack)
        or report.get("real_rotten_flesh_count") != count
        or report.get("d4_natural_count") != count
        or report.get("d4_native_before", {}).get("rotten_flesh") != 0
        or report.get("d4_final_supervisor_open_count") != 0
        or report.get("motion_fence", {}).get("unresolved") is not False
        or report.get("nonmotion_fence", {}).get("unresolved") is not False
    ):
        raise D7FNaturalAuditRejected("original source amount/Action/session invalid")
    nonmotion = OriginalS49NonMotionFence.restore(
        nonmotion_path, self_id="s49-original-self",
    )
    motion = OriginalS49PhysicalFence.restore(
        motion_path, self_id="s49-original-self",
    )
    nonmotion.require_clear()
    motion.require_clear()
    if (
        report["motion_fence"]["sha256"] != motion.sha256
        or report["nonmotion_fence"]["sha256"] != nonmotion.sha256
        or len(motion.actions) != len(moves)
        or len(nonmotion.actions) != len(attack) + int(positive and report.get("self_eat") is True)
    ):
        raise D7FNaturalAuditRejected("original source-bound physical ledgers invalid")
    for row, pers in zip(attack, nonmotion.actions):
        if (
            pers.get("kind") != "ATTACK"
            or pers.get("status") != "S16_OUTCOME"
            or pers.get("session_id") != sid
            or pers.get("action_id") != row.get("action_id")
            or row.get("terminal") != "outcome"
            or row.get("ack") != "applied"
        ):
            raise D7FNaturalAuditRejected("S49 original physical ATTACK ledger mismatched")
    if count > 0:
        spawn, picked = _one(log, SPAWN), _one(log, PICKUP)
        if (
            spawn["item"] != picked["item"]
            or spawn["zombie"] != initial["zombie"]
            or picked["zombie"] != initial["zombie"]
            or spawn["world"] != initial["world"]
            or picked["world"] != initial["world"]
            or picked["player"] != death["killer"]
            or int(spawn["count"]) != count
            or int(picked["count"]) != count
            or not int(death["tick"]) <= int(spawn["tick"]) < int(picked["tick"]) < int(respawn["tick"])
            or report.get("d4_paper_item_spawn", "").find(spawn["item"]) < 0
            or report.get("d4_paper_item_pickup", "").find(spawn["item"]) < 0
            or report.get("d4_native_after_pickup", {}).get("rotten_flesh") != count
            or report.get("d4_self_move_for_item") is not True
            or report.get("d4_pickup_passive") is not False
            or report.get("d6_item_origin") != "ACTUAL_PAPER_ZOMBIE_DEATH_EVENT"
            or report.get("d6_d_same_attack_move_supervisor") is not True
            or not 1 <= len(moves) <= 4
        ):
            raise D7FNaturalAuditRejected("true Paper natural UUID spawn/pickup/move absent")
        for persisted, move in zip(motion.actions, moves):
            if (
                persisted.get("status") != "S16_OUTCOME"
                or persisted.get("action_ref") != "MOVE_BACKWARD"
                or persisted.get("session_id") != sid
                or persisted.get("action_id") != move.get("action_id")
                or persisted.get("cleanup_seq") != move.get("s15_clear_seq")
                or persisted.get("after_seq") != move.get("s15_after_seq")
                or move.get("terminal") != "outcome"
                or not move.get("target_distance_before_m", 0)
                    > move.get("target_distance_after_m", -1) + 0.05
            ):
                raise D7FNaturalAuditRejected("original C1 S49 MOVE/clear journal invalid")
    else:
        spawn = picked = None
        if moves or SPAWN.search(log) or PICKUP.search(log):
            raise D7FNaturalAuditRejected("true zero loot cannot have any MOVE or pickup")

    if count != 1:
        if (
            report.get("self_eat") is not False
            or report.get("d4_natural_food_pickup_eat_proven") is not False
            or report.get("d7f_original_eat_issued") is True
            or len(nonmotion.actions) != len(attack)
        ):
            raise D7FNaturalAuditRejected("0/2 natural meat cannot claim first DEV EAT")
        return {
            "status": "NOT_EXERCISED",
            "classification": "D7_F_NATURAL_EAT_NOT_EXERCISED_TRUE_RNG",
            "true_world_count": count, "paper_world_uuid": initial["world"],
            "original_attack_ids": [x["action_id"] for x in attack],
            "natural_source": True, "physical_eat_issued": False,
            "qualification": "NO_GO", "science": "NOT_RUN",
        }

    eat = report.get("d7f_eat_outcome")
    stop = report.get("d7f_live_natural_stop")
    action = report.get("d7f_eat_action_id")
    if (
        report.get("classification")
        != "D7F_NATURAL_S49_ATTACK_MOVE_PICKUP_LIVE_STOP_S51_EAT_PASS"
        or report.get("self_eat") is not True
        or report.get("d4_natural_food_pickup_eat_proven") is not True
        or report.get("d7f_original_eat_issued") is not True
        or report.get("d7f_eat_terminal") != "outcome"
        or report.get("d7f_stop_original_owner_admitted_dev") is not True
        or report.get("d7f_stage") != "S49_NATURAL_ATTACK_MOVE_STOP_S51_EAT_ONE_CYCLE_DEV"
        or report.get("d7f_server_effective_s15_clear_tick_attested") is not False
        or report.get("d7f_operator_staged_item") is not False
        or report.get("d7f_nonmotion_unresolved") is not False
        or report.get("d7f_nonmotion_sha256") != nonmotion.sha256
        or report.get("d7f_original_attack_count") != len(attack)
        or report.get("d7f_original_total_actions") != len(attack) + len(moves) + 1
        or report.get("d4_final_action_count") != len(attack) + len(moves) + 1
        or not isinstance(eat, dict) or not isinstance(stop, dict)
        or not isinstance(action, str) or not action
        or len(moves) != 1
        or stop.get("classification") != "D7_F_DEV_LIVE_NATURAL_BODY_STEADY_SOURCE"
        or stop.get("session_id") != sid
        or stop.get("action_id") != moves[0]["action_id"]
        or stop.get("original_clear_seq") != moves[0]["s15_clear_seq"]
        or stop.get("paper_world_uuid") != initial["world"]
        or stop.get("paper_player_uuid") != death["killer"]
        or stop.get("paper_item_uuid") != picked["item"]
        or stop.get("paper_pickup_tick") != int(picked["tick"])
        or stop.get("server_effective_original_clear_tick") != "NOT_CAUSALLY_ATTESTED"
        or type(stop.get("paper_quiet_tail_ticks")) is not int
        or stop["paper_quiet_tail_ticks"] < 8
        or type(stop.get("client_postclear_physics_ticks")) is not int
        or stop["client_postclear_physics_ticks"] < 8
        or eat.get("session_id") != sid or eat.get("action_id") != action
        or eat.get("consumed_item") != "rotten_flesh"
        or eat.get("count_before") != 1 or eat.get("count_after") != 0
        or report.get("d7f_native_after_eat", {}).get("rotten_flesh") != 0
    ):
        raise D7FNaturalAuditRejected("original natural STOP / S51 EAT not source-qualified")
    before = native_integral_food(eat.get("food_before"))
    after = native_integral_food(eat.get("food_after"))
    if not before < after:
        raise D7FNaturalAuditRejected("S51 Food did not actually rise")
    last = nonmotion.actions[-1]
    if (
        last.get("kind") != "EAT" or last.get("status") != "S16_OUTCOME"
        or last.get("session_id") != sid or last.get("action_id") != action
        or last.get("subject") != "rotten_flesh"
        or last.get("terminal") != "outcome"
        or last.get("result") != {
            "food_before": before, "food_after": after,
            "item_count_before": 1, "item_count_after": 0,
        }
    ):
        raise D7FNaturalAuditRejected("original fsynced S49/S51 EAT ledger mismatch")

    # Independently test live owner's *reported* STOP tick against the
    # finished Paper source. Paper was stopped only AFTER the meal.
    source_rows = [_fields(line, TICK_MARK) for line in log.splitlines()
                   if TICK_MARK in line]
    if not source_rows:
        raise D7FNaturalAuditRejected("Paper main-thread source absent")
    first = _integer(source_rows[0], "tick")
    old = None
    quiet = 0
    observed_stop = False
    old_xz = None
    for idx, row in enumerate(source_rows, 1):
        tick = _integer(row, "tick")
        if (
            row.get("source") != SOURCE
            or row.get("world") != initial["world"]
            or row.get("player") != death["killer"]
            or _integer(row, "ordinal") != idx
            or (old is not None and tick != old + 1)
        ):
            raise D7FNaturalAuditRejected("Paper server tick identity/continuity mismatch")
        old = tick
        off = _inputs_off(row)
        pos = (_number(row, "x"), _number(row, "z"))
        speed = math.hypot(_number(row, "vx"), _number(row, "vz"))
        _number(row, "y")
        _number(row, "vy")
        is_quiet = (
            tick > int(picked["tick"]) and off and row.get("ground") == "true"
            and old_xz is not None and math.dist(pos, old_xz) <= 0.01
            and speed <= 0.01
        )
        quiet = quiet + 1 if is_quiet else 0
        old_xz = pos
        if tick == stop.get("paper_last_tick"):
            observed_stop = True
            if quiet != stop["paper_quiet_tail_ticks"] or quiet < 8:
                raise D7FNaturalAuditRejected("original owner's Paper stop window false")
    if not observed_stop or first > int(picked["tick"]) or old is None:
        raise D7FNaturalAuditRejected("original Paper source missing live STOP tick")

    records = []
    for line in client.splitlines():
        try:
            v = json.loads(line)
        except (TypeError, ValueError) as exc:
            raise D7FNaturalAuditRejected("native direct S50 source malformed") from exc
        records.append(v)
    clear = None
    original_off_ticks = 0
    for i, row in enumerate(records, 1):
        if (
            not isinstance(row, dict)
            or row.get("source") != "S50_DEV_NATIVE_READBACK_V1"
            or row.get("session_id") != sid or row.get("ordinal") != i
            or not isinstance(row.get("controls"), dict)
            and row.get("kind") != "SESSION_START"
        ):
            raise D7FNaturalAuditRejected("original S50 session/evidence corrupt")
        if row.get("kind") == "EFFECT_ACK" and (
            row.get("native_action_id") == moves[0]["action_id"] + "-s15-clear"
            and row.get("native_seq") == moves[0]["s15_clear_seq"]
        ):
            if clear is not None:
                raise D7FNaturalAuditRejected("duplicate original MOVE S15 clear")
            clear = i
        if clear is not None and row.get("kind") == "PHYSICS_TICK":
            controls = row["controls"]
            if set(controls) != set(CONTROL_KEYS) or any(
                type(x) is not bool or x for x in controls.values()
            ):
                raise D7FNaturalAuditRejected("client native motor controls reactivated")
            original_off_ticks += 1
    if clear is None or original_off_ticks < stop["client_postclear_physics_ticks"]:
        raise D7FNaturalAuditRejected("original S50 native postclear not attested")
    return {
        "status": "PASS_DEV",
        "classification": "D7_F_ONE_REAL_NATURAL_ZOMBIE_ATTACK_MOVE_STOP_S51_EAT",
        "true_vanilla_natural_loot_count": 1,
        "paper_world_uuid": initial["world"],
        "paper_zombie_uuid": initial["zombie"],
        "paper_item_uuid": picked["item"],
        "original_s49_attack_ids": [x["action_id"] for x in attack],
        "original_s49_move_id": moves[0]["action_id"],
        "original_s49_eat_id": action,
        "original_food_before": before, "original_food_after": after,
        "original_inventory_before": 1, "original_inventory_after": 0,
        "original_nonmotion_sha256": nonmotion.sha256,
        "original_motion_sha256": motion.sha256,
        "server_effective_clear_packet_tick_attested": False,
        "two_full_cycles_proven": False, "long_run_proven": False,
        "qualification": "NO_GO", "science": "NOT_RUN",
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--report", type=Path, required=True)
    p.add_argument("--server-log", type=Path, required=True)
    p.add_argument("--s50-sidecar", type=Path, required=True)
    p.add_argument("--nonmotion-fence", type=Path, required=True)
    p.add_argument("--motion-fence", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    result = audit(
        a.server_log.read_text(encoding="utf8"),
        json.loads(a.report.read_text(encoding="utf8")),
        a.s50_sidecar.read_text(encoding="utf8"),
        nonmotion_path=a.nonmotion_fence,
        motion_path=a.motion_fence,
    )
    a.out.write_text(json.dumps(result, sort_keys=True, indent=2)+"\n",
                     encoding="utf8")
    print(result["classification"])


if __name__ == "__main__":
    main()
