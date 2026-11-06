"""Independent read-only D3: original S49 strikes + Paper killer and respawn.

Operator preinjures/freezes one arena zombie. This checks genuine attack/death
provenance, not autonomous AI target choice or natural-food completion.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

UUID = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
INITIAL = re.compile(
    rf"RSELF_RESPAWN_INITIAL world=(?P<world>{UUID}) "
    rf"entity=(?P<zombie>{UUID}) generation=1 tick=(?P<tick>\d+)"
)
DEATH = re.compile(
    rf"RSELF_RESPAWN_DEATH world=(?P<world>{UUID}) "
    rf"entity=(?P<zombie>{UUID}) generation=1 "
    rf"tick=(?P<tick>\d+) due_tick=(?P<due>\d+) "
    rf"paper_drops=(?P<drops>\d+) killer=(?P<killer>{UUID}|UNKNOWN)"
)
LOOT = re.compile(
    rf"RSELF_NATURAL_DROP_DEATH world=(?P<world>{UUID}) "
    rf"zombie=(?P<zombie>{UUID}) tick=(?P<tick>\d+) "
    rf"rotten_count=(?P<rotten>\d+) killer=(?P<killer>{UUID}|UNKNOWN) "
    r"source=ACTUAL_PAPER_ENTITY_DEATH_DROPS killer_is_relay_self=(?P<self>true|false)"
)
REBORN = re.compile(
    rf"RSELF_RESPAWN_SPAWN world=(?P<world>{UUID}) "
    rf"entity=(?P<zombie>{UUID}) generation=2 tick=(?P<tick>\d+)"
)


class D3CombatAuditRejected(ValueError):
    pass


def audit(log: str, report: dict) -> dict:
    if "RSELF_RESPAWN_FAULT" in log or "RSELF_NATURAL_DROP_FAULT" in log:
        raise D3CombatAuditRejected("Paper World fault")
    proof = {}
    positions = {}
    for key, pat in (
        ("initial", INITIAL),
        ("death", DEATH),
        ("loot", LOOT),
        ("reborn", REBORN),
    ):
        found = list(pat.finditer(log))
        if len(found) != 1:
            raise D3CombatAuditRejected(f"non-unique original Paper {key} source")
        proof[key] = found[0].groupdict()
        positions[key] = found[0].start()
    ini, dead, loot, new = (
        proof[key] for key in ("initial", "death", "loot", "reborn")
    )
    if (
        not positions["initial"] < min(positions["death"], positions["loot"])
        or not max(positions["death"], positions["loot"]) < positions["reborn"]
        or len({ini["world"], dead["world"], loot["world"], new["world"]}) != 1
        or len({ini["zombie"], dead["zombie"], loot["zombie"]}) != 1
        or ini["zombie"] == new["zombie"]
        or dead["killer"] == "UNKNOWN"
        or dead["killer"] != loot["killer"]
        or loot["self"] != "true"
        or int(ini["tick"]) >= int(dead["tick"])
        or int(dead["tick"]) != int(loot["tick"])
        or int(dead["due"]) != int(dead["tick"]) + 600
        or int(new["tick"]) < int(dead["due"])
        or not 0 <= int(loot["rotten"]) <= 2
    ):
        raise D3CombatAuditRejected("World zombie death/true killer/tick mismatch")

    actions = report.get("s49_actions")
    initial = report.get("native_initial")
    reborn = report.get("native_respawn")
    if (
        report.get("status") != "PASS_DEV"
        or report.get("classification") not in {
            "D3_S49_MULTIHIT_PAPER_KILL_RESPAWN_PASS",
            "D3_S49_ONE_HIT_PAPER_KILL_RESPAWN_PASS",
        }
        or report.get("operator_world_kill") is not False
        or report.get("operator_staged_no_ai") is not True
        or report.get("self_goal_selected_autonomously") is not False
        or report.get("self_attack_principal_attested") is not True
        or report.get("self_move_to_loot") is not False
        or report.get("self_eat") is not False
        or report.get("java_exit") != 0 or report.get("node_exit") != 0
        or not isinstance(actions, list)
        or not 1 <= len(actions) <= 8
        or report.get("attack_count") != len(actions)
        or report.get("owner_action_count") != len(actions)
        or report.get("owner_attack_count") != len(actions)
        or report.get("original_supervisor_open_count") != 0
        or (len(actions) > 1) != (
            report["classification"] == "D3_S49_MULTIHIT_PAPER_KILL_RESPAWN_PASS"
        )
        or not isinstance(initial, dict) or not isinstance(reborn, dict)
        or not report.get("session_id")
        or initial.get("session_id") != report["session_id"]
        or reborn.get("session_id") != report["session_id"]
        or initial.get("zombie_entity_id") == reborn.get("zombie_entity_id")
        or initial.get("seq", 10**12) >= reborn.get("seq", -1)
        or report.get("real_rotten_flesh_count") != int(loot["rotten"])
    ):
        raise D3CombatAuditRejected("S49 Action supervisor/native witness incomplete")
    previous_last_seq = -1
    issued_ids = set()
    native_target_ids = set()
    for action in actions:
        if (
            action.get("action_id") in issued_ids
            or action.get("session_id") != report["session_id"]
            or action.get("ack") != "applied"
            or action.get("terminal") != "outcome"
            or action.get("kill_attested_by_effect_ack") is not False
            or action.get("scope") != "ORIGINAL_S49_NATIVE_ATTACK_COMMAND_ONLY"
            or type(action.get("target_entity_id")) is not int
            or not all(type(action.get(k)) is int for k in (
                "previous_seq", "admitted_seq", "effect_seq", "after_seq"
            ))
            or not previous_last_seq < action["previous_seq"]
            < action["admitted_seq"] < action["effect_seq"] < action["after_seq"]
        ):
            raise D3CombatAuditRejected("stale/replayed/unqualified original S49 Action")
        previous_last_seq = action["after_seq"]
        issued_ids.add(action["action_id"])
        native_target_ids.add(action["target_entity_id"])
    if len(native_target_ids) != 1:
        raise D3CombatAuditRejected("strikes attributed to different native target IDs")

    return {
        "classification": report["classification"],
        "world_uuid": ini["world"],
        "initial_zombie_uuid": ini["zombie"],
        "killed_zombie_uuid": dead["zombie"],
        "new_zombie_uuid": new["zombie"],
        "paper_killer_uuid": dead["killer"],
        "paper_killer_is_relay_self": True,
        "real_death_tick": int(dead["tick"]),
        "next_spawn_tick": int(new["tick"]),
        "source_delta_ticks": int(new["tick"]) - int(dead["tick"]),
        "original_s49_attack_action_count": len(actions),
        "original_s49_action_id_unique": True,
        "real_rotten_flesh_drop_count": int(loot["rotten"]),
        "real_rotten_flesh_pickup_proven": False,
        "real_eat_proven": False,
        "autonomous_target_selection_proven": False,
        "original_worldbody_fatigue_unchanged": True,
        "qualification": "NO_GO",
        "science": "NOT_RUN",
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--server-log", type=Path, required=True)
    p.add_argument("--report", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    proof = audit(
        args.server_log.read_text(encoding="utf8"),
        json.loads(args.report.read_text(encoding="utf8")),
    )
    args.out.write_text(
        json.dumps(proof, indent=2, sort_keys=True) + "\n",
        encoding="utf8",
    )
    print(proof["classification"])


if __name__ == "__main__":
    main()
