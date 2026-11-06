"""Independent D2 real zombie DeathEvent -> natural Item -> native inventory audit.

A positive D2 is still operator killing/positioning. Only original Paper
and original Mineflayer native evidence support a material claim.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

UUID = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
SRC = {
    "RESPAWN_DEATH": re.compile(
        rf"RSELF_RESPAWN_DEATH world=(?P<world>{UUID}) entity=(?P<zombie>{UUID}) "
        rf"generation=(?P<gen>\d+) tick=(?P<tick>\d+) due_tick=(?P<due>\d+)"),
    "DROP_DEATH": re.compile(
        rf"RSELF_NATURAL_DROP_DEATH world=(?P<world>{UUID}) zombie=(?P<zombie>{UUID}) "
        rf"tick=(?P<tick>\d+) rotten_count=(?P<count>\d+) "
        r"killer=(?P<killer>UNKNOWN|[0-9a-f-]+) "
        r"source=ACTUAL_PAPER_ENTITY_DEATH_DROPS"),
    "DROP_SPAWN": re.compile(
        rf"RSELF_NATURAL_DROP_SPAWN world=(?P<world>{UUID}) zombie=(?P<zombie>{UUID}) "
        rf"item=(?P<item>{UUID}) tick=(?P<tick>\d+) rotten_count=(?P<count>\d+) "
        r"source=ACTUAL_PAPER_ITEM_SPAWN_NEAR_DEATH"),
    "DROP_PICKUP": re.compile(
        rf"RSELF_NATURAL_DROP_PICKUP world=(?P<world>{UUID}) zombie=(?P<zombie>{UUID}) "
        rf"item=(?P<item>{UUID}) player=(?P<player>{UUID}) "
        r"tick=(?P<tick>\d+) rotten_count=(?P<count>\d+) "
        r"source=ACTUAL_PAPER_ITEM_PICKUP"),
    "RESPAWN_NEW": re.compile(
        rf"RSELF_RESPAWN_SPAWN world=(?P<world>{UUID}) entity=(?P<zombie>{UUID}) "
        rf"generation=(?P<gen>\d+) tick=(?P<tick>\d+)"),
}


class NaturalDropD2Rejected(ValueError):
    pass


def _audit_real_zero_loot(log: str, report: dict) -> dict:
    """Real valid zero drop, independently observed, never counted as pickup."""
    if (
        "RSELF_NATURAL_DROP_SPAWN" in log
        or "RSELF_NATURAL_DROP_PICKUP" in log
        or "RSELF_NATURAL_DROP_FAULT" in log
        or "RSELF_RESPAWN_FAULT" in log
        or "RSELF_NATURAL_DROP_DISABLED_DEFAULT" in log
    ):
        raise NaturalDropD2Rejected("zero-drop branch contradicts original Paper")
    extracted: dict[str, re.Match[str]] = {}
    for key in ("RESPAWN_DEATH", "DROP_DEATH", "RESPAWN_NEW"):
        matches = list(SRC[key].finditer(log))
        if len(matches) != 1:
            raise NaturalDropD2Rejected("missing/duplicated zero-loot source " + key)
        extracted[key] = matches[0]
    death = extracted["RESPAWN_DEATH"].groupdict()
    loot = extracted["DROP_DEATH"].groupdict()
    next_generation = extracted["RESPAWN_NEW"].groupdict()
    if (
        death["world"] != loot["world"]
        or death["world"] != next_generation["world"]
        or death["zombie"] != loot["zombie"]
        or next_generation["zombie"] == death["zombie"]
        or int(death["tick"]) != int(loot["tick"])
        or int(loot["count"]) != 0
        or int(death["due"]) != int(death["tick"]) + 600
        or int(next_generation["tick"]) < int(death["due"])
        or int(death["gen"]) != 1
        or int(next_generation["gen"]) != 2
    ):
        raise NaturalDropD2Rejected("real zero loot death/respawn identity mismatch")
    before, after = report.get("native_before"), report.get("native_after")
    initial, reborn = report.get("native_initial"), report.get("native_respawn")
    if (
        report.get("status") != "PASS_DEV"
        or report.get("classification") != "D2_OPERATOR_KILLED_REAL_ZOMBIE_ZERO_LOOT"
        or report.get("zombie_kill_principal") != "OPERATOR_CONSOLE_ONLY"
        or report.get("item_origin") != "ACTUAL_PAPER_ZOMBIE_DEATH_EVENT"
        or report.get("real_vanilla_loot_count") != 0
        or report.get("original_s49_actions") != 0
        or report.get("self_move_issued") is not False
        or report.get("self_eat_issued") is not False
        or report.get("self_attack_issued") is not False
        or report.get("node_exit") != 0 or report.get("java_exit") != 0
        or not isinstance(before, dict) or not isinstance(after, dict)
        or not isinstance(initial, dict) or not isinstance(reborn, dict)
        or not report.get("session_id")
        or len({
            report["session_id"], before.get("session_id"), after.get("session_id"),
            initial.get("session_id"), reborn.get("session_id"),
        }) != 1
        or type(before.get("seq")) is not int
        or type(after.get("seq")) is not int
        or before["seq"] >= after["seq"]
        or type(initial.get("seq")) is not int
        or type(reborn.get("seq")) is not int
        or initial["seq"] >= reborn["seq"]
        or initial.get("zombie_entity_id") == reborn.get("zombie_entity_id")
        or before.get("rotten_flesh") != 0 or after.get("rotten_flesh") != 0
        or before.get("health", 0) <= 0 or after.get("health", 0) <= 0
        or report.get("paper_item_spawn") is not None
        or report.get("paper_item_pickup") is not None
    ):
        raise NaturalDropD2Rejected("zero-drop Paper/native scope is incomplete")
    return {
        "classification": "D2_REAL_ZERO_VANILLA_ROTTEN_FLESH_WITH_600TICK_RESPAWN_PASS",
        "world_uuid": death["world"],
        "old_zombie_uuid": death["zombie"],
        "new_zombie_uuid": next_generation["zombie"],
        "death_tick": int(death["tick"]),
        "due_tick": int(death["due"]),
        "respawn_tick": int(next_generation["tick"]),
        "respawn_server_tick_delta":
            int(next_generation["tick"]) - int(death["tick"]),
        "real_vanilla_rotten_flesh_count": 0,
        "native_inventory_rotten_flesh_delta": 0,
        "operator_killed": True,
        "pickup_proven": False,
        "self_attack_proven": False,
        "self_eat_proven": False,
        "endless_survival_proven": False,
        "qualification": "NO_GO",
        "science": "NOT_RUN",
    }


def audit(log: str, report: dict) -> dict:
    if report.get("classification") == "D2_OPERATOR_KILLED_REAL_ZOMBIE_ZERO_LOOT":
        return _audit_real_zero_loot(log, report)
    if (
        "RSELF_NATURAL_DROP_FAULT" in log
        or "RSELF_RESPAWN_FAULT" in log
        or "RSELF_NATURAL_DROP_DISABLED_DEFAULT" in log
    ):
        raise NaturalDropD2Rejected("World plugin fault or disabled source")
    found = {}
    for key, regex in SRC.items():
        hits = list(regex.finditer(log))
        if len(hits) != 1:
            raise NaturalDropD2Rejected(f"original {key} is not unique and full")
        found[key] = hits[0]
    r, d, s, p, n = (found[x] for x in (
        "RESPAWN_DEATH", "DROP_DEATH", "DROP_SPAWN",
        "DROP_PICKUP", "RESPAWN_NEW",
    ))
    if not r.start() < d.start() < s.start() < p.start() < n.start():
        # Paper event handlers may log drop death before respawn handler.
        # Both death events may occur in either handler order; only require
        # both death receipts before item creation.
        if not (max(r.start(), d.start()) < s.start() < p.start() < n.start()):
            raise NaturalDropD2Rejected("original causal log order invalid")
    a, b, c, e, f = (x.groupdict() for x in (r, d, s, p, n))
    count = int(b["count"])
    if (
        count < 1 or count > 2
        or len({a["world"], b["world"], c["world"], e["world"], f["world"]}) != 1
        or len({a["zombie"], b["zombie"], c["zombie"], e["zombie"]}) != 1
        or c["item"] != e["item"]
        or int(b["tick"]) != int(a["tick"])
        or int(c["tick"]) < int(b["tick"])
        or int(c["tick"]) > int(b["tick"]) + 3
        or int(e["tick"]) < int(c["tick"])
        or int(e["tick"]) >= int(f["tick"])
        or int(a["due"]) != int(a["tick"]) + 600
        or int(f["tick"]) < int(a["due"])
        or f["zombie"] == a["zombie"]
        or int(a["gen"]) != 1 or int(f["gen"]) != 2
        or count != int(c["count"]) or count != int(e["count"])
    ):
        raise NaturalDropD2Rejected("World-side drop count/identity/tick mismatch")
    first, later = report.get("native_before"), report.get("native_after")
    original, reborn = report.get("native_initial"), report.get("native_respawn")
    if (
        report.get("status") != "PASS_DEV"
        or report.get("classification") != "D2_OPERATOR_KILLED_REAL_ZOMBIE_NATURAL_DROP"
        or report.get("zombie_kill_principal") != "OPERATOR_CONSOLE_ONLY"
        or report.get("item_origin") != "ACTUAL_PAPER_ZOMBIE_DEATH_EVENT"
        or report.get("original_s49_actions") != 0
        or report.get("self_move_issued") is not False
        or report.get("self_eat_issued") is not False
        or report.get("java_exit") != 0 or report.get("node_exit") != 0
        or not isinstance(first, dict) or not isinstance(later, dict)
        or not isinstance(original, dict) or not isinstance(reborn, dict)
        or not report.get("session_id")
        or len({
            report["session_id"],
            first.get("session_id"), later.get("session_id"),
            original.get("session_id"), reborn.get("session_id"),
        }) != 1
        or type(first.get("seq")) is not int or type(later.get("seq")) is not int
        or first["seq"] >= later["seq"]
        or type(original.get("seq")) is not int or type(reborn.get("seq")) is not int
        or original["seq"] >= reborn["seq"]
        or original.get("zombie_entity_id") == reborn.get("zombie_entity_id")
        or first.get("rotten_flesh") != 0
        or later.get("rotten_flesh") != count
        or first.get("health", 0) <= 0 or later.get("health", 0) <= 0
    ):
        raise NaturalDropD2Rejected("native truth or DEV classification missing")
    return {
        "classification": "D2_OPERATOR_CAUSED_REAL_ZOMBIE_NATURAL_LOOT_PICKUP_AND_RESPAWN_PASS",
        "world_uuid": a["world"],
        "old_zombie_uuid": a["zombie"],
        "new_zombie_uuid": f["zombie"],
        "natural_loot_item_uuid": c["item"],
        "death_tick": int(a["tick"]),
        "natural_item_spawn_tick": int(c["tick"]),
        "natural_item_pickup_tick": int(e["tick"]),
        "respawn_tick": int(f["tick"]),
        "respawn_server_tick_delta": int(f["tick"]) - int(a["tick"]),
        "native_inventory_rotten_flesh_delta": count,
        "operator_killed": True,
        "self_attack_issued": False,
        "self_move_for_pickup_issued": False,
        "self_eat_issued": False,
        "autonomous_survival_proven": False,
        "qualification": "NO_GO",
        "science": "NOT_RUN",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--server-log", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = audit(
        args.server_log.read_text(encoding="utf-8"),
        json.loads(args.report.read_text(encoding="utf-8")),
    )
    args.out.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n",
                        encoding="utf-8")
    print(result["classification"])


if __name__ == "__main__":
    main()
