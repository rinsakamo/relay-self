"""Independent D1 Paper item UUID + native count original-log audit."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

UUID = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
P = re.compile(
    rf"RSELF_LOOT_(?P<event>STAGED|PICKED) "
    rf"world=(?P<world>{UUID}) owner=(?P<owner>{UUID}) "
    rf"entity=(?P<item>{UUID}) item=rotten_flesh count=1 "
    rf"tick=(?P<tick>\d+) source=(?P<source>[A-Z_]+)"
)


class PickupD1AuditRejected(ValueError):
    pass


def audit(log: str, report: dict) -> dict:
    if "[ERROR]" in log or "RSELF_LOOT_DISABLED_DEFAULT" in log:
        raise PickupD1AuditRejected("original Paper failed or fixture disabled")
    markers = list(P.finditer(log))
    if [m.group("event") for m in markers] != ["STAGED", "PICKED"]:
        raise PickupD1AuditRejected("one ordered staged/picked item pair required")
    first, last = (m.groupdict() for m in markers)
    if (
        (first["world"], first["owner"], first["item"])
        != (last["world"], last["owner"], last["item"])
        or first["source"] != "OPERATOR_FIXTURE_NOT_ZOMBIE_DROP"
        or last["source"] != "ACTUAL_PAPER_PICKUP_EVENT"
        or int(last["tick"]) < int(first["tick"])
    ):
        raise PickupD1AuditRejected("server pickup identity/provenance invalid")
    before, after = report.get("native_before", {}), report.get("native_after", {})
    gain = report.get("native_pickup_gain", {})
    if (
        report.get("status") != "PASS_DEV"
        or report.get("item_origin") != "OPERATOR_FIXTURE_NOT_ZOMBIE_DROP"
        or report.get("original_s49_actions") != 0
        or report.get("self_action_issued") is not False
        or report.get("zombie_kill_attested") is not False
        or report.get("node_exit") != 0 or report.get("java_exit") != 0
        or not isinstance(before, dict) or not isinstance(after, dict)
        or not isinstance(gain, dict)
        or not report.get("session_id")
        or before.get("session_id") != report["session_id"]
        or after.get("session_id") != report["session_id"]
        or before.get("rotten_flesh") != 0
        or after.get("rotten_flesh") != 1
        or type(before.get("seq")) is not int
        or type(after.get("seq")) is not int
        or before["seq"] >= after["seq"]
        or gain.get("item_name") != "rotten_flesh"
        or gain.get("outcome_scope") != "NATIVE_INVENTORY_DELTA_ONLY"
        or gain.get("before_count") != 0 or gain.get("after_count") != 1
        or not isinstance(report.get("paper_staged"), str)
        or not isinstance(report.get("paper_pickup"), str)
        or "RSELF_LOOT_STAGED" not in report["paper_staged"]
        or "RSELF_LOOT_PICKED" not in report["paper_pickup"]
    ):
        raise PickupD1AuditRejected("native inventory / scope / cleanup invalid")
    return {
        "classification": "D1_OPERATOR_STAGED_PAPER_ITEM_NATIVE_PICKUP_MATCHED",
        "world_uuid": first["world"],
        "player_uuid": first["owner"],
        "item_uuid": first["item"],
        "staged_tick": int(first["tick"]),
        "collected_tick": int(last["tick"]),
        "native_before_seq": before["seq"],
        "native_after_seq": after["seq"],
        "native_rotten_flesh_delta": 1,
        "operator_item_fixture": True,
        "vanilla_zombie_drop_proven": False,
        "self_move_for_pickup_proven": False,
        "self_attack_proven": False,
        "self_eat_proven": False,
        "qualification": "NO_GO",
        "science": "NOT_RUN",
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--server-log", type=Path, required=True)
    p.add_argument("--report", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    result = audit(
        a.server_log.read_text(encoding="utf-8"),
        json.loads(a.report.read_text(encoding="utf-8")),
    )
    a.out.write_text(
        json.dumps(result, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(result["classification"])


if __name__ == "__main__":
    main()
