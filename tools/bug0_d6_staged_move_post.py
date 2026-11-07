"""Read-only independent D6-C one-World source and original S49 MOVE fence audit.

Operator-created meat is NOT a natural zombie drop. The original S49 move
toward one actual native item is independently matched with the C1 durable
physical S15/S16 ledger and Paper pickup UUID.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from relay_self.c1_physical_action_fence import OriginalS49PhysicalFence
from tools.bug0_pickup_d1_post import P


class D6StagedSourceAuditRejected(ValueError):
    pass


def audit(log: str, report: dict, fence_path: Path) -> dict:
    markers = list(P.finditer(log))
    if [m.group("event") for m in markers] != ["STAGED", "PICKED"]:
        raise D6StagedSourceAuditRejected("one Paper staged/pickup UUID pair required")
    first, last = (m.groupdict() for m in markers)
    if (
        (first["world"], first["owner"], first["item"])
        != (last["world"], last["owner"], last["item"])
        or first["source"] != "OPERATOR_FIXTURE_NOT_ZOMBIE_DROP"
        or last["source"] != "ACTUAL_PAPER_PICKUP_EVENT"
        or int(last["tick"]) <= int(first["tick"])
        or "mode=BACK_2_2M" not in report.get("paper_staged", "")
    ):
        raise D6StagedSourceAuditRejected("World item source/fixture staging mismatch")
    moves = report.get("d6_original_s49_move_actions")
    sid = report.get("session_id")
    before = report.get("native_before")
    after = report.get("native_after")
    gain = report.get("native_pickup_gain")
    if (
        report.get("status") != "PASS_DEV"
        or report.get("classification") != "D6_OPERATOR_STAGED_S49_MOVE_PICKUP_PASS"
        or report.get("item_origin") != "OPERATOR_FIXTURE_NOT_ZOMBIE_DROP"
        or report.get("d6_item_origin") != "OPERATOR_FIXTURE_NOT_ZOMBIE_DROP"
        or not isinstance(sid, str) or not sid
        or type(report.get("original_s49_actions")) is not int
        or not 1 <= report["original_s49_actions"] <= 4
        or report["original_s49_actions"] != report.get("d6_original_move_count")
        or report.get("self_action_issued") is not True
        or report.get("d6_same_supervisor") is not True
        or report.get("d6_native_orientation_optin") is not True
        or report.get("d6_original_s49_supervisor_kept") is not True
        or report.get("d6_post_move_eat_fenced") is not True
        or report.get("d6_eat_after_move") is not False
        or report.get("d6_s14_generic_loot_route_admitted") is not False
        or report.get("zombie_kill_attested") is not False
        or report.get("self_granted_inventory") is not False
        or report.get("real_model_calls") != 0
        or report.get("learning_updated") is not False
        or report.get("node_exit") != 0 or report.get("java_exit") != 0
        or report.get("cleanup_done") is not True
        or not isinstance(moves, list) or len(moves) != report["original_s49_actions"]
        or not isinstance(before, dict) or not isinstance(after, dict)
        or before.get("rotten_flesh") != 0 or after.get("rotten_flesh") != 1
        or before.get("session_id") != sid or after.get("session_id") != sid
        or not isinstance(gain, dict)
        or gain.get("item_name") != "rotten_flesh"
        or gain.get("before_count") != 0 or gain.get("after_count") != 1
        or gain.get("outcome_scope") != "NATIVE_INVENTORY_DELTA_ONLY"
        or not isinstance(report.get("d6_original_fence_sha256"), str)
    ):
        raise D6StagedSourceAuditRejected("original S49 + native count not qualified")
    fence = OriginalS49PhysicalFence.restore(
        fence_path, self_id="s49-original-self",
    )
    fence.require_clear()
    rows = fence.actions
    if (
        fence.sha256 != report["d6_original_fence_sha256"]
        or len(rows) != len(moves)
        or len({m.get("action_id") for m in moves}) != len(moves)
        or not isinstance(report.get("d6_item_native_id"), int)
        or any(m.get("item_entity_id") != report["d6_item_native_id"] for m in moves)
    ):
        raise D6StagedSourceAuditRejected("durable original movement count/identity mismatch")
    last_after_seq = -1
    for move, row in zip(moves, rows):
        if (
            move.get("intent_id") != "collect-operator-staged-loot"
            or move.get("session_id") != sid
            or move.get("action_ref") != "MOVE_BACKWARD"
            or move.get("terminal") != "outcome"
            or move.get("native_source") != f"{sid}:{move.get('decision_seq')}"
            or move.get("food_identity_verified_by_entity") is not False
            or move.get("pickup_verified_by_move_alone") is not False
            or row["action_id"] != move["action_id"]
            or row["session_id"] != sid
            or row["intent_id"] != move["intent_id"]
            or row["status"] != "S16_OUTCOME"
            or row["terminal_state"] != "outcome"
            or row["decision_seq"] != move.get("decision_seq")
            or row["decision_request_id"] != move.get("decision_request_id")
            or row["source_reference"] != move.get("native_source")
            or row["before_seq"] != move.get("s15_before_seq")
            or row["dispatch_seq"] != move.get("s15_dispatch_seq")
            or row["cleanup_seq"] != move.get("s15_clear_seq")
            or row["after_seq"] != move.get("s15_after_seq")
            or row["movement_m"] != move.get("movement_m")
            or row["decision_seq"] <= last_after_seq
            or not (move.get("target_distance_before_m", 0) >
                    move.get("target_distance_after_m", -1) + 0.05)
        ):
            raise D6StagedSourceAuditRejected("original S15/S16 approach source mismatch")
        last_after_seq = row["after_seq"]
    return {
        "status": "PASS_DEV",
        "classification": "D6_STAGED_ITEM_ORIGINAL_S49_FENCED_MOVE_PICKUP_PASS",
        "world_uuid": first["world"], "player_uuid": first["owner"],
        "paper_item_uuid": first["item"],
        "native_item_entity_id": report["d6_item_native_id"],
        "paper_staged_tick": int(first["tick"]),
        "paper_pickup_tick": int(last["tick"]),
        "original_move_action_ids": [m["action_id"] for m in moves],
        "original_s49_move_count": len(moves),
        "original_physical_fence_sha256": fence.sha256,
        "native_rotten_flesh_delta": 1,
        "natural_zombie_drop_proven": False,
        "autonomous_goal_selection_proven": False,
        "second_hunt_or_eat_proven": False,
        "post_move_eat_authorized": False,
        "physical_exactly_once_attested": False,
        "qualification": "NO_GO", "science": "NOT_RUN",
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--server-log", type=Path, required=True)
    p.add_argument("--report", type=Path, required=True)
    p.add_argument("--move-fence", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    result = audit(
        a.server_log.read_text(encoding="utf8"),
        json.loads(a.report.read_text(encoding="utf8")),
        a.move_fence,
    )
    a.out.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf8")
    print(result["classification"])


if __name__ == "__main__":
    main()
