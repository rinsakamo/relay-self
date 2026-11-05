"""Post-World original P1 physical law DEV check (operator-only source).

Uses original S49 outcomes, original #734 Paper callback plugin, and
P1WORLD private server trace from the SAME disposable World. Does NOT
authenticate SourceBoundTick, upgrade WAIT to R quality, give true fatigue
to Self, or claim an observed speed reduction when the physical cap is idle.
"""
from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path
from typing import Any

from adapters.mineflayer.s49_p1_paper_dev import (
    _float, _int, _rows as _existing_s49_rows,
)


def _rows(log: str, key: str) -> list[dict[str, str]]:
    # Reuse the existing #734 strict Paper parser for S49P1 rows.
    if key.startswith("S49P1_"):
        return _existing_s49_rows(log, key.removeprefix("S49P1_"))
    if not key.startswith("P1WORLD_"):
        raise P1PhysicalPostRejected("unexpected Paper marker kind")
    marker = key + " "
    rows = []
    for line in log.splitlines():
        if marker not in line:
            continue
        tokens = line.split(marker, 1)[1].split()
        if not tokens or any(token.count("=") != 1 for token in tokens):
            raise P1PhysicalPostRejected("malformed P1 Paper marker")
        kv = [token.split("=", 1) for token in tokens]
        entry = dict(kv)
        if len(entry) != len(kv):
            raise P1PhysicalPostRejected("duplicate P1 Paper marker fields")
        rows.append(entry)
    return rows

P1_SHA = "d23f1f595095adb1da0b3ce74a72803b85b68359dc94d2ee8b03fcd2078f68b0"
P1_HEAD = "0ab76b4e46efd914877e543a65de58b6cfc71326"


class P1PhysicalPostRejected(ValueError):
    pass


def require(ok: bool, reason: str) -> None:
    if not ok:
        raise P1PhysicalPostRejected(reason)


def inspect_original_p1_physical_dev(
    report: dict[str, Any], log: str,
) -> dict[str, Any]:
    require(isinstance(report, dict) and isinstance(log, str),
            "report and original Paper log required")
    sid = report.get("session_id")
    actions = report.get("actual_native_actions")
    nonce = report.get("worldbody_p1_source_nonce")
    choice = report.get("worldbody_postmove_l0_choice", {})
    require(
        isinstance(sid, str) and bool(re.fullmatch(r"[0-9a-f-]{36}", sid))
        and isinstance(nonce, str) and nonce == sid.replace("-", "")[:20]
        and report.get("status") == "PASS"
        and report.get("classification")
        == "DEV_ONLY_PINNED_P1_WORLD_PHYSICAL_CAP_NATIVE_S49"
        and report.get("worldbody_profile")
        == "PINNED_ORIGINAL_P1_PER_WORLD_TICK_CAP_DEV"
        and report.get("worldbody_p1_physics_dev") is True
        and report.get("worldbody_p1_same_world_source_dev") is True
        and report.get("worldbody_true_fatigue_received_by_self") is False
        and report.get("worldbody_physics_write_from_self") is False
        and report.get("worldbody_rest_action_count") == 0
        and isinstance(choice, dict) and choice.get("selected") in ("WAIT", "REST")
        and choice.get("rest_action_issued") is False
        and isinstance(actions, list) and len(actions) == 2
        and all(a.get("terminal") == "outcome"
                and a.get("source") == sid
                and a.get("movement_m", 0) > 0
                and a.get("action", "") == f"s49-native-move-{a.get('event_seq')}"
                for a in actions),
        "original S49 P1 physical World not closed or source altered",
    )
    require(
        not _rows(log, "P1WORLD_SOURCE_FAULT")
        and not _rows(log, "S49P1_SOURCE_FAULT"),
        "Paper source fault; never credit P1 recovery",
    )

    ready = _rows(log, "P1WORLD_READY")
    attach = _rows(log, "P1WORLD_ATTACH")
    stop = _rows(log, "P1WORLD_STOP")
    tickrows = _rows(log, "P1WORLD_TICK")
    owners = _rows(log, "P1WORLD_S49_ACTION")
    p1cap = _rows(log, "P1WORLD_CAP")
    s49start = _rows(log, "S49P1_START")
    s49stop = _rows(log, "S49P1_STOP")
    s49action = _rows(log, "S49P1_ACTION")
    s49choice = _rows(log, "S49P1_CHOICE")
    s49ticks = _rows(log, "S49P1_TICK")
    require(
        len(ready) == len(attach) == len(stop) == len(s49start)
        == len(s49stop) == len(s49choice) == 1
        and len(owners) == len(s49action) == 4
        and 10 <= len(tickrows) <= 2400
        and 10 <= len(s49ticks) <= 2400,
        "missing or duplicate pinned P1/old S49 Paper source brackets",
    )
    a, z = attach[0], stop[0]
    world, player = a.get("world"), a.get("player")
    require(
        bool(world and re.fullmatch(r"[0-9a-f-]{36}", world))
        and bool(player and re.fullmatch(r"[0-9a-f-]{36}", player))
        and a.get("nonce") == nonce and z.get("nonce") == nonce
        and ready[0].get("original_p1") == P1_HEAD
        and ready[0].get("profile") == P1_SHA
        and ready[0].get("legacy_worldbody_active") == "false"
        and a.get("original_p1") == P1_HEAD
        and a.get("enabled_profile_sha") == P1_SHA
        and a.get("independent_s_r_attestation") == "false"
        and z.get("independent_s_r_attestation") == "false"
        and z.get("world") == world
        and s49start[0].get("world") == world
        and s49start[0].get("player") == player
        and s49stop[0].get("world") == world
        and s49choice[0].get("world") == world
        and s49choice[0].get("selected") == choice["selected"]
        and _int(s49stop[0], "faults") == 0
        and s49start[0].get("coverage") == "SERVER_TICK_CALLBACK_NOT_FULL_TICK"
        and s49stop[0].get("coverage") == "SERVER_TICK_CALLBACK_NOT_FULL_TICK",
        "foreign player, World, P1 owner profile or source qualification",
    )

    previous = _int(a, "tick")
    fatigue = 0.0
    activity_count = {"MOVE": 0, "WAIT": 0, "FIGHT": 0}
    moved = 0.0
    recovered = 0.0
    for row in tickrows:
        t = _int(row, "tick")
        kind = row.get("activity")
        d = _float(row, "accepted_blocks")
        actual = _float(row, "truth_fatigue")
        reported_recovery = _float(row, "recovered")
        cap = _float(row, "p1_cap_blocks")
        require(
            row.get("world") == world and row.get("nonce") == nonce
            and row.get("r_qualified") == "false"
            and t == previous + 1 and kind in activity_count
            and 0 <= d <= 1.0 and 0 <= actual <= 1.0
            and row.get("blocked") in ("true", "false"),
            "gapped/foreign P1 per-tick source or invalid physical receipt",
        )
        if kind == "MOVE":
            expect = min(1.0, fatigue + d * 0.04)
            r = 0.0
            require(row["blocked"] == ("true" if d == 0 else "false"),
                    "blocked MOVE misclassified as WAIT")
            moved += d
        elif kind == "FIGHT":
            require(d == 0 and row["blocked"] == "false",
                    "FIGHT mixed with observed MOVE")
            expect = min(1.0, fatigue + 0.20)
            r = 0.0
        else:
            require(d == 0 and row["blocked"] == "false",
                    "WAIT contains physical MOVE")
            r = min(fatigue, 0.10)
            expect = max(0.0, fatigue - r)
        expect_cap = max(0.20, 1.0 - 0.70 * expect)
        require(
            math.isclose(expect, actual, abs_tol=1e-9)
            and math.isclose(r, reported_recovery, abs_tol=1e-9)
            and math.isclose(expect_cap, cap, abs_tol=1e-9),
            "P1 server physical state differs from pinned original #626",
        )
        activity_count[kind] += 1
        recovered += r
        fatigue = expect
        previous = t

    require(
        _int(z, "tick") >= previous
        and _int(z, "committed") == len(tickrows)
        and _int(z, "move") == activity_count["MOVE"]
        and _int(z, "fight") == activity_count["FIGHT"]
        and _int(z, "wait_candidate") == activity_count["WAIT"]
        and _int(z, "cap_applied") == len(p1cap),
        "P1 stopped before native Paper source was sealed",
    )
    pprev = _int(s49start[0], "tick")
    for i, row in enumerate(s49ticks, 1):
        require(
            row.get("nonce") == nonce and row.get("world") == world
            and _int(row, "tick") == pprev + 1
            and _int(row, "index") == i,
            "original #734 Paper callback stream incomplete",
        )
        pprev += 1
    require(
        _int(s49stop[0], "index") == len(s49ticks)
        and _int(s49stop[0], "tick") >= pprev,
        "original #734 source STOP missing",
    )
    for index, (p1begin, p1closed, paperbegin, paperclosed, receipt) in enumerate(
        zip(owners[::2], owners[1::2],
            s49action[::2], s49action[1::2], actions, strict=True),
        1,
    ):
        expected_id = receipt["action"]
        require(
            all(row.get("nonce") == nonce and row.get("world") == world
                for row in (p1begin, p1closed, paperbegin, paperclosed))
            and p1begin.get("phase") == paperbegin.get("phase") == "begin"
            and p1closed.get("phase") == paperclosed.get("phase") == "closed"
            and all(row.get("action") == expected_id
                    for row in (p1begin, p1closed, paperbegin, paperclosed))
            and _int(p1begin, "tick") <= _int(p1closed, "tick")
            and abs(_int(p1begin, "tick") - _int(paperbegin, "tick")) <= 2
            and abs(_int(p1closed, "tick") - _int(paperclosed, "tick")) <= 2,
            f"S49 Action {index} not linked to the same native World",
        )

    return {
        "classification": "DEV_ORIGINAL_P1_WORLD_PHYSICAL_STATE_AND_S49_SOURCE_JOIN",
        "original_p1_head": P1_HEAD,
        "original_enabled_p1_profile_sha": P1_SHA,
        "world_uuid": world,
        "session_id": sid,
        "paper_p1_tick_count": len(tickrows),
        "paper_original_callback_tick_count": len(s49ticks),
        "original_s49_action_count": 2,
        "activity_counts": activity_count,
        "physical_cap_event_count": len(p1cap),
        "p1_total_move_blocks": moved,
        "p1_total_private_recovery": recovered,
        "p1_final_private_fatigue": fatigue,
        "p1_world_physics_installed": True,
        "original_p1_math_independently_recomputed_from_server_log": True,
        "native_speed_loss_caused_by_p1_cap_proven": False,
        "full_tick_wait_independently_r_attested": False,
        "p1_b_source_bound_tick_formally_admitted": 0,
        "world_rules_mutable_by_self": False,
        "self_received_private_fatigue": False,
        "qualification_go": False,
        "science_run": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--paper-log", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = inspect_original_p1_physical_dev(
        json.loads(args.report.read_text(encoding="utf-8")),
        args.paper_log.read_text(encoding="utf-8"),
    )
    args.out.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print("DEV_ORIGINAL_P1_PAPER_WORLD_SOURCE_JOIN_ONLY_NO_R_QUALIFICATION")


if __name__ == "__main__":
    main()
