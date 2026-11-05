"""Strict read-only R1 original Paper + Mineflayer probe audit."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

UUID = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
PATTERNS = {
    name: re.compile(
        rf"RSELF_RESPAWN_{name} world=(?P<world>{UUID}) "
        rf"entity=(?P<entity>{UUID}) generation=(?P<generation>\d+) "
        rf"tick=(?P<tick>\d+)"
        + (r" due_tick=(?P<due>\d+)" if name == "DEATH" else "")
    )
    for name in ("INITIAL", "DEATH", "SPAWN")
}


class RespawnAuditError(ValueError):
    pass


def audit(log: str, report: dict) -> dict:
    if "RSELF_RESPAWN_FAULT" in log:
        raise RespawnAuditError("server World-owned gate fault")
    parsed = {}
    for name, pat in PATTERNS.items():
        matches = list(pat.finditer(log))
        if len(matches) != 1:
            raise RespawnAuditError(f"{name} original exact marker count invalid")
        parsed[name] = matches[0]
    a, d, b = (parsed[x] for x in ("INITIAL", "DEATH", "SPAWN"))
    aa, dd, bb = (x.groupdict() for x in (a, d, b))
    if not (a.start() < d.start() < b.start()):
        raise RespawnAuditError("original server causal order invalid")
    if not (aa["world"] == dd["world"] == bb["world"]
            and aa["entity"] == dd["entity"] and bb["entity"] != dd["entity"]
            and int(aa["generation"]) == int(dd["generation"]) == 1
            and int(bb["generation"]) == 2
            and int(dd["due"]) == int(dd["tick"]) + 600
            and int(bb["tick"]) >= int(dd["due"])
            and int(aa["tick"]) < int(dd["tick"])):
        raise RespawnAuditError("600 source tick / identity / generation mismatch")
    if (
        report.get("status") != "PASS_DEV" or report.get("operator_kill") is not True
        or report.get("original_s49_actions") != 0
        or report.get("node_exit") != 0 or report.get("java_exit") != 0
        or report.get("session_id") != report.get("native_initial", {}).get("session_id")
        or report.get("session_id") != report.get("native_respawn", {}).get("session_id")
        or report.get("native_initial", {}).get("zombie_entity_id")
            == report.get("native_respawn", {}).get("zombie_entity_id")
        or report.get("native_initial", {}).get("seq", 100000)
            >= report.get("native_respawn", {}).get("seq", -1)
        or report.get("paper_initial") != a.group(0) and "RSELF_RESPAWN_INITIAL" not in report.get("paper_initial", "")
        or "RSELF_RESPAWN_DEATH" not in report.get("paper_death", "")
        or "RSELF_RESPAWN_SPAWN" not in report.get("paper_respawn", "")
    ):
        raise RespawnAuditError("native original source or cleanup qualification missing")
    return {
        "classification": "R1_OPERATOR_DEATH_REAL_PAPER_600TICK_RESPAWN_NATIVE_DIFFERENCE_PASS",
        "world_uuid": aa["world"],
        "old_zombie_uuid": aa["entity"],
        "new_zombie_uuid": bb["entity"],
        "death_tick": int(dd["tick"]),
        "scheduled_tick": int(dd["due"]),
        "respawn_tick": int(bb["tick"]),
        "delay_ticks_observed": int(bb["tick"]) - int(dd["tick"]),
        "native_zombie_entity_id_changed": True,
        "operator_kill": True,
        "autonomous_self_kill": False,
        "pickup_proven": False,
        "eat_proven": False,
        "qualification": "NO_GO",
        "science": "NOT_RUN",
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--server-log", type=Path, required=True)
    p.add_argument("--report", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    result = audit(
        args.server_log.read_text(encoding="utf-8"),
        json.loads(args.report.read_text(encoding="utf-8")),
    )
    args.out.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(result["classification"])


if __name__ == "__main__":
    main()
