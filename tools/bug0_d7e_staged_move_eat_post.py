"""Independent DEV-only original S49 MOVE + fenced S51 post-MOVE EAT audit."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from relay_self.s49_nonmotion_physical_fence import OriginalS49NonMotionFence


class D7EPostRejected(ValueError):
    pass


def audit_staged_eat(
    report: dict, stage: dict, *,
    nonmotion_path: Path,
) -> dict:
    eat = report.get("d7e_original_eat_outcome")
    stop = report.get("d7e_live_stop")
    action = report.get("d7e_eat_action_id")
    after = report.get("d7e_native_after_eat")
    sid = report.get("session_id")
    if (
        report.get("status") != "PASS_DEV"
        or report.get("classification") != "D6_OPERATOR_STAGED_S49_MOVE_PICKUP_PASS"
        or report.get("item_origin") != "OPERATOR_FIXTURE_NOT_ZOMBIE_DROP"
        or report.get("zombie_kill_attested") is not False
        or report.get("d7e_stage") != "ONE_REAL_STAGED_MOVE_PICKUP_STOP_EAT_DEV_PASS"
        or report.get("d7e_original_EAT_issued") is not True
        or report.get("d7e_eat_terminal") != "outcome"
        or report.get("d7e_stop_original_owner_admitted_dev") is not True
        or report.get("d7e_physical_server_effective_clear_tick_proven") is not False
        or report.get("d7e_total_original_s49_action_count") != 2
        or report.get("d7e_operator_item_origin") != "OPERATOR_FIXTURE_NOT_ZOMBIE_DROP"
        or not isinstance(eat, dict)
        or not isinstance(stop, dict)
        or not isinstance(after, dict)
        or not isinstance(sid, str) or not sid
        or not isinstance(action, str) or not action
        or not isinstance(stage, dict) or stage.get("status") != "PASS_DEV"
        or stage.get("natural_zombie_drop_proven") is not False
        or stage.get("post_move_eat_authorized") is not False
        or stop.get("classification") != "D7_E_DEV_LIVE_STAGED_BODY_STEADY_SOURCE"
        or stop.get("session_id") != sid
        or stop.get("action_id") not in stage.get("original_move_action_ids", [])
        or stop.get("paper_world_uuid") != stage.get("world_uuid")
        or stop.get("paper_player_uuid") != stage.get("player_uuid")
        or stop.get("paper_item_uuid") != stage.get("paper_item_uuid")
        or stop.get("paper_pickup_tick") != stage.get("paper_pickup_tick")
        or stop.get("server_effective_original_clear_tick") != "NOT_CAUSALLY_ATTESTED"
        or type(stop.get("client_postclear_physics_ticks")) is not int
        or stop["client_postclear_physics_ticks"] < 8
        or type(stop.get("paper_quiet_tail_ticks")) is not int
        or stop["paper_quiet_tail_ticks"] < 8
        or eat.get("session_id") != sid
        or eat.get("action_id") != action
        or eat.get("consumed_item") != "rotten_flesh"
        or eat.get("count_before") != 1 or eat.get("count_after") != 0
        or type(eat.get("food_before")) is not int
        or type(eat.get("food_after")) is not int
        or not 0 <= eat["food_before"] < eat["food_after"] <= 20
        or after.get("session_id") != sid
        or after.get("rotten_flesh") != 0
        or report.get("d7e_original_nonmotion_unresolved") is not False
        or report.get("node_exit") != 0 or report.get("java_exit") != 0
        or report.get("cleanup_done") is not True
    ):
        raise D7EPostRejected("original STOP owner and S51 EAT provenance/effects not qualified")
    fence = OriginalS49NonMotionFence.restore(
        nonmotion_path, self_id="s49-original-self",
    )
    fence.require_clear()
    rows = fence.actions
    if (
        fence.sha256 != report.get("d7e_original_nonmotion_fence_sha256")
        or len(rows) != 1
        or rows[0].get("session_id") != sid
        or rows[0].get("action_id") != action
        or rows[0].get("kind") != "EAT"
        or rows[0].get("status") != "S16_OUTCOME"
        or rows[0].get("terminal") != "outcome"
        or rows[0].get("subject") != "rotten_flesh"
        or rows[0].get("result") != {
            "food_before": eat["food_before"],
            "food_after": eat["food_after"],
            "item_count_before": 1, "item_count_after": 0,
        }
    ):
        raise D7EPostRejected("original durable EAT fsynced physical ledger mismatch")
    return {
        "status": "PASS_DEV",
        "classification": "D7_E_STAGED_S49_MOVE_PAPER_PICKUP_LIVE_STOP_S51_EAT_ONE_CYCLE",
        "session_id": sid,
        "world_uuid": stage["world_uuid"],
        "player_uuid": stage["player_uuid"],
        "operator_fixture_item_uuid": stage["paper_item_uuid"],
        "s49_original_move": stage["original_move_action_ids"],
        "s49_original_eat_action_id": action,
        "s49_s51_native_food_before": eat["food_before"],
        "s49_s51_native_food_after": eat["food_after"],
        "s49_s51_native_inventory_before": 1,
        "s49_s51_native_inventory_after": 0,
        "original_eat_fence_sha256": fence.sha256,
        "source_stop_staged_dev_only": True,
        "server_effective_clear_tick_attested": False,
        "natural_zombie_loot_eaten": False,
        "full_two_cycle_proven": False,
        "qualification": "NO_GO",
        "science": "NOT_RUN",
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--report", type=Path, required=True)
    p.add_argument("--staged-audit", type=Path, required=True)
    p.add_argument("--eat-fence", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    v = audit_staged_eat(
        json.loads(args.report.read_text(encoding="utf8")),
        json.loads(args.staged_audit.read_text(encoding="utf8")),
        nonmotion_path=args.eat_fence,
    )
    args.out.write_text(json.dumps(v, indent=2, sort_keys=True)+"\n", encoding="utf8")
    print(v["classification"])


if __name__ == "__main__":
    main()
