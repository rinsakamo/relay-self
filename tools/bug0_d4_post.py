"""Independent D4 Paper natural Item UUID -> native pickup -> S49/S51 EAT audit.

This never treats operator melee placement or hunger stimulus as learned
self-care, MOVE, autonomous looting or proof of indefinite survival.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from tools.bug0_natural_drop_d2_post import SRC
from tools.bug0_s49_combat_d3_post import D3CombatAuditRejected, audit as audit_combat


class D4NaturalEatRejected(ValueError):
    pass


def _native(read: object, *, session_id: str, desc: str) -> dict:
    if (
        not isinstance(read, dict)
        or read.get("session_id") != session_id
        or type(read.get("seq")) is not int
        or type(read.get("rotten_flesh")) is not int
        or not read.get("request_id")
        or not read.get("provenance")
        or type(read.get("health")) not in (int, float)
        or read["health"] <= 0
    ):
        raise D4NaturalEatRejected("missing authentic native source: " + desc)
    return read


def audit(log: str, report: dict) -> dict:
    """Reverify real D3 death/600tick proof AND same-session native D4 food."""
    if not isinstance(report, dict):
        raise D4NaturalEatRejected("original JSON report absent")
    count = report.get("real_rotten_flesh_count")
    ate = report.get("d4_natural_food_pickup_eat_proven")
    if (
        report.get("status") != "PASS_DEV"
        or type(count) is not int or not 0 <= count <= 2
        or type(ate) is not bool
        or ate != (count > 0)
        or report.get("classification") != (
            "D4_REAL_NATURAL_LOOT_PICKUP_S49_EAT_AND_RESPAWN_PASS"
            if ate else "D4_GENUINE_ZERO_LOOT_NO_EAT_RESPAWN_PASS"
        )
        or report.get("self_move_to_loot") is not False
        or report.get("d4_self_move_for_item") is not False
        or report.get("d4_item_manual_stage") is not False
        or report.get("operator_world_kill") is not False
        or report.get("d4_operator_hunger_induced_for_dev") is not True
        or report.get("self_goal_selected_autonomously") is not False
        or report.get("self_eat") is not ate
        or report.get("java_exit") != 0 or report.get("node_exit") != 0
        or report.get("cleanup_done") is not True
        or report.get("d4_final_supervisor_open_count") != 0
        or report.get("d4_final_action_count") != (
            report.get("attack_count", -100) + int(ate)
        )
        or report.get("d4_combat_closed_action_count") != report.get("attack_count")
        or report.get("d4_natural_count") != count
        or report.get("d4_pickup_passive") is not ate
        or report.get("d4_eat_terminal") != ("outcome" if ate else "NOT_ISSUED")
        or report.get("d4_self_eat_issued") is not ate
    ):
        raise D4NaturalEatRejected("D4 real actions/World source scope unqualified")

    # Reuse the independent D3 original Paper attacker/world proof. The
    # normalized label only selects the prior audit's expected schema; the
    # full D4 report remains original and its EAT action is audited below.
    combat_only = dict(
        report,
        classification=(
            "D3_S49_MULTIHIT_PAPER_KILL_RESPAWN_PASS"
            if len(report.get("s49_actions", [])) >= 2
            else "D3_S49_ONE_HIT_PAPER_KILL_RESPAWN_PASS"
        ),
        self_eat=False,
    )
    try:
        combat = audit_combat(log, combat_only)
    except (D3CombatAuditRejected, ValueError, TypeError) as exc:
        raise D4NaturalEatRejected("original Paper/S49 death source invalid") from exc
    sid = report["session_id"]
    before = _native(report.get("d4_baseline_inventory"), session_id=sid, desc="baseline")
    if before["rotten_flesh"] != 0:
        raise D4NaturalEatRejected("natural food came from preexisting inventory")
    if not ate:
        after = _native(report.get("d4_native_after_zero"), session_id=sid, desc="zero")
        if (
            after["seq"] <= before["seq"] or after["rotten_flesh"] != 0
            or report.get("d4_paper_item_spawn") is not None
            or report.get("d4_paper_item_pickup") is not None
            or report.get("d4_eat_outcome") is not None
            or "RSELF_NATURAL_DROP_SPAWN" in log
            or "RSELF_NATURAL_DROP_PICKUP" in log
        ):
            raise D4NaturalEatRejected("real zero-meat World had fake loot/eating")
        return {
            **combat,
            "classification": "D4_GENUINE_ZERO_LOOT_NO_EAT_RESPAWN_PASS",
            "real_rotten_flesh_pickup_proven": False,
            "real_eat_proven": False,
            "world_zero_loot_valid": True,
            "self_move_to_loot_proven": False,
            "unlimited_survival_proven": False,
        }

    spawned = list(SRC["DROP_SPAWN"].finditer(log))
    picked = list(SRC["DROP_PICKUP"].finditer(log))
    if len(spawned) != 1 or len(picked) != 1:
        raise D4NaturalEatRejected("exactly one real Paper item UUID and pickup required")
    sp, pk = spawned[0].groupdict(), picked[0].groupdict()
    if (
        sp["world"] != combat["world_uuid"]
        or pk["world"] != combat["world_uuid"]
        or sp["zombie"] != combat["killed_zombie_uuid"]
        or pk["zombie"] != combat["killed_zombie_uuid"]
        or sp["item"] != pk["item"]
        or int(sp["count"]) != count
        or int(pk["count"]) != count
        or int(sp["tick"]) < combat["real_death_tick"]
        or int(pk["tick"]) < int(sp["tick"])
        or int(pk["tick"]) >= combat["next_spawn_tick"]
        or report.get("d4_paper_item_spawn") is None
        or sp["item"] not in report["d4_paper_item_spawn"]
        or report.get("d4_paper_item_pickup") is None
        or sp["item"] not in report["d4_paper_item_pickup"]
    ):
        raise D4NaturalEatRejected("actual natural item UUID/count/world mismatch")
    gathered = _native(
        report.get("d4_native_after_pickup"), session_id=sid, desc="pickup",
    )
    eaten = _native(report.get("d4_post_eat"), session_id=sid, desc="after-EAT")
    outcome = report.get("d4_eat_outcome")
    next_choice = report.get("d4_next_food_decision")
    if (
        gathered["seq"] <= before["seq"]
        or gathered["rotten_flesh"] != count
        or eaten["rotten_flesh"] != count - 1
        or not gathered["seq"] < eaten["seq"]
        or not isinstance(outcome, dict)
        or outcome.get("session_id") != sid
        or outcome.get("action_id") != report.get("d4_eat_action_id")
        or outcome.get("consumed_item") != "rotten_flesh"
        or outcome.get("count_before") != count
        or outcome.get("count_after") != count - 1
        or not (
            type(outcome.get("food_before")) in (int, float)
            and type(outcome.get("food_after")) in (int, float)
            and 0 <= outcome["food_before"] < outcome["food_after"] <= 20
        )
        or type(outcome.get("after_probe_seq")) is not int
        or not gathered["seq"] < outcome["after_probe_seq"] < eaten["seq"]
        or not isinstance(next_choice, dict)
        or next_choice.get("selected") != "WAIT"
        or next_choice.get("reason") not in (
            "NOT_HUNGRY", "ONE_EAT_BUDGET_USED",
        )
        or next_choice.get("seq") != eaten["seq"]
        or report.get("d4_native_pickup_attempt", 999) not in range(1, 13)
    ):
        raise D4NaturalEatRejected("original S49/S51 native EAT proof incomplete")

    return {
        **combat,
        "classification": "D4_REAL_NATURAL_LOOT_PICKUP_S49_EAT_AND_RESPAWN_PASS",
        "natural_item_uuid": sp["item"],
        "paper_pickup_tick": int(pk["tick"]),
        "native_rotten_flesh_before": before["rotten_flesh"],
        "native_rotten_flesh_after_pickup": gathered["rotten_flesh"],
        "native_rotten_flesh_after_eat": eaten["rotten_flesh"],
        "original_s49_eat_action_id": outcome["action_id"],
        "original_s49_total_actions": report["d4_final_action_count"],
        "food_before_eating": outcome["food_before"],
        "food_after_eating": outcome["food_after"],
        "real_rotten_flesh_pickup_proven": True,
        "real_eat_proven": True,
        "self_move_to_loot_proven": False,
        "operator_induced_hunger": True,
        "autonomous_self_care_proven": False,
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
