"""D7-D source-only Paper/S50 post-staged-pickup audit.

Uses original D6-C independently qualified operator fixture and one S49 MOVE.
NEVER turns a sampled quiet streak into a STOP certificate or EAT authority.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from tools.bug0_d7_postmove_native_controls_post import audit_passive_controls
from tools.bug0_d7_paper_server_tick_post import (
    EVENT_MARK, SOURCE, TICK_MARK,
    _fields, _inputs_off, _integer, _number,
)

MAX_PAPER_TICKS = 8192


class D7StagedStopRejected(ValueError):
    """Missing original staged item / S49 / client / Paper source."""


def audit_staged_stop(
    log: str, report: dict, staged_audit: dict, native_sidecar: str,
) -> dict:
    """One original S49 session: MOVE clear → client readback + Paper pickup.

    Reuse the existing strict D7-A S50 audit through a *source-qualified*
    projection of independently verified D6-C staged data. It is not a
    fabricated D6 natural-drop audit and cannot claim natural origin.
    """
    if (
        not isinstance(log, str)
        or not isinstance(native_sidecar, str)
        or not isinstance(report, dict)
        or not isinstance(staged_audit, dict)
        or staged_audit.get("status") != "PASS_DEV"
        or staged_audit.get("classification")
        != "D6_STAGED_ITEM_ORIGINAL_S49_FENCED_MOVE_PICKUP_PASS"
        or staged_audit.get("natural_zombie_drop_proven") is not False
        or staged_audit.get("post_move_eat_authorized") is not False
        or staged_audit.get("second_hunt_or_eat_proven") is not False
        or staged_audit.get("physical_exactly_once_attested") is not False
        or report.get("status") != "PASS_DEV"
        or report.get("classification") != "D6_OPERATOR_STAGED_S49_MOVE_PICKUP_PASS"
        or report.get("item_origin") != "OPERATOR_FIXTURE_NOT_ZOMBIE_DROP"
        or report.get("d6_item_origin") != "OPERATOR_FIXTURE_NOT_ZOMBIE_DROP"
        or report.get("d7_staged_paper_tick_source") is not True
        or report.get("d7_staged_s50_direct_source") is not True
        or report.get("d7_staged_original_eat_issued") is not False
        or report.get("d6_post_move_eat_fenced") is not True
        or report.get("d6_eat_after_move") is not False
        or report.get("session_id") in (None, "")
        or report.get("d6_same_supervisor") is not True
        or report.get("node_exit") != 0 or report.get("java_exit") != 0
        or report.get("cleanup_done") is not True
        or report.get("real_model_calls") != 0
        or report.get("learning_updated") is not False
    ):
        raise D7StagedStopRejected("staged D6/S49 original source unqualified")
    sid = report["session_id"]
    world = staged_audit.get("world_uuid")
    player = staged_audit.get("player_uuid")
    item = staged_audit.get("paper_item_uuid")
    pickup = staged_audit.get("paper_pickup_tick")
    moves = report.get("d6_original_s49_move_actions")
    if (
        not all(isinstance(x, str) and x for x in (sid, world, player, item))
        or not isinstance(moves, list) or not moves
        or staged_audit.get("original_s49_move_count") != len(moves)
        or staged_audit.get("original_move_action_ids") != [
            m.get("action_id") for m in moves
        ]
        or type(pickup) is not int or pickup < 0
    ):
        raise D7StagedStopRejected("staged item/original MOVE source identities mismatched")
    # Read-only structural adapter for the *actual staged source*; all fields
    # are derived from independent D6-C post-audit, not imaginary World facts.
    native_report = {
        "status": report["status"],
        "node_exit": report["node_exit"], "java_exit": report["java_exit"],
        "cleanup_done": report["cleanup_done"],
        "d7_same_s49_passive_s50_readback": True,
        "d7_paper_effective_stop_proven": False,
        "d7_eat_grant_issued": False, "self_eat": False,
        "d6_post_move_eat_fenced": report["d6_post_move_eat_fenced"],
        "d6_multigen_no_eat": not report["d6_eat_after_move"],
        "session_id": sid, "d6_original_s49_move_actions": moves,
    }
    native_original = {
        "status": staged_audit["status"],
        "no_eat_after_move": not report["d6_eat_after_move"],
        "same_supervisor_retained": report["d6_same_supervisor"],
        "unresolved_motion": False,  # stage_audit first required fence.require_clear()
        "unresolved_nonmotion": False,  # stage world issues only MOVE
        "session_id": sid, "original_move_count": len(moves),
    }
    client = audit_passive_controls(native_sidecar, native_report, native_original)
    if (
        client.get("source_scope") != "S50_NATIVE_CLIENT_HELD_CONTROLS_ONLY"
        or client.get("original_s49_move_action_ids")
        != staged_audit.get("original_move_action_ids")
        or client.get("body_physically_stopped_proven") is not False
        or client.get("original_EAT_issued") is not False
    ):
        raise D7StagedStopRejected("direct same-original-S49 S50 source rejected")

    lines = log.splitlines()
    ready = [s for s in lines if "RSELF_D7_PAPER_READY " in s]
    stop = [s for s in lines if "RSELF_D7_PAPER_STOP " in s]
    truncated = [s for s in lines if "RSELF_D7_PAPER_TRUNCATED " in s]
    pickup_lines = [s for s in lines if "RSELF_LOOT_PICKED " in s]
    if len(ready) != 1 or len(stop) != 1 or truncated or len(pickup_lines) != 1:
        raise D7StagedStopRejected("original Paper source lifetime or pickup missing")
    if (
        f"world={world} owner={player} entity={item}" not in pickup_lines[0]
        or f"tick={pickup} source=ACTUAL_PAPER_PICKUP_EVENT" not in pickup_lines[0]
    ):
        raise D7StagedStopRejected("Paper staged item has wrong source or UUID")
    rows = [_fields(s, TICK_MARK) for s in lines if TICK_MARK in s]
    evs = [_fields(s, EVENT_MARK) for s in lines if EVENT_MARK in s]
    if not 8 <= len(rows) <= MAX_PAPER_TICKS or len(evs) > 512:
        raise D7StagedStopRejected("Paper tick source incomplete")
    previous_tick = None
    previous_pos = None
    current_quiet = longest_quiet = 0
    after_pickup_rows = 0
    paper_input_off = 0
    post_pickup_first = None
    for index, row in enumerate(rows, 1):
        tick = _integer(row, "tick")
        if (
            row.get("source") != SOURCE
            or row.get("player") != player or row.get("world") != world
            or _integer(row, "ordinal") != index
            or (previous_tick is not None and tick != previous_tick + 1)
            or row.get("ground") not in ("true", "false")
        ):
            raise D7StagedStopRejected("Paper original tick/world/player chronology mismatch")
        previous_tick = tick
        off = _inputs_off(row)
        if off:
            paper_input_off += 1
        xyz = tuple(_number(row, x) for x in ("x", "y", "z"))
        v = tuple(_number(row, x) for x in ("vx", "vy", "vz"))
        if tick > pickup:
            after_pickup_rows += 1
            if post_pickup_first is None:
                post_pickup_first = tick
            dist_sq = (
                (xyz[0] - previous_pos[0])**2 + (xyz[2] - previous_pos[2])**2
                if previous_pos is not None else math.inf
            )
            # Small values here mean *observed* near-idle, not authoritative
            # server-effective S49 CLEAR or an EAT admission threshold.
            quiet = (
                off and row["ground"] == "true"
                and dist_sq <= 0.0001 and v[0]**2 + v[2]**2 <= 0.0001
            )
            current_quiet = current_quiet + 1 if quiet else 0
            longest_quiet = max(longest_quiet, current_quiet)
        previous_pos = xyz
    if not rows or not _integer(rows[0], "tick") <= pickup <= previous_tick:
        raise D7StagedStopRejected("original staged pickup outside Paper coverage")
    for index, event in enumerate(evs, 1):
        if (
            event.get("source") != SOURCE
            or event.get("player") != player
            or event.get("world") != world
            or _integer(event, "ordinal") != index
            or not _integer(rows[0], "tick") - 1
                <= _integer(event, "tick") <= previous_tick
        ):
            raise D7StagedStopRejected("foreign Paper input event")
        _inputs_off(event)
    stop_data = _fields(stop[0], "RSELF_D7_PAPER_STOP ")
    if (
        _integer(stop_data, "total_ticks") != len(rows)
        or _integer(stop_data, "input_events") != len(evs)
        or stop_data.get("truncated") != "false"
        or stop_data.get("eat_authority") != "none"
    ):
        raise D7StagedStopRejected("Paper tick accounting mismatch")
    if after_pickup_rows < 8:
        raise D7StagedStopRejected("fewer than eight Paper post-pickup ticks")
    return {
        "status": "PASS_DEV",
        "classification": "D7_D_STAGED_PAPER_PICKUP_POSTMOVE_SOURCE_ONLY",
        "item_origin": "OPERATOR_FIXTURE_NOT_ZOMBIE_DROP",
        "natural_zombie_drop_proven": False,
        "world_uuid": world, "player_uuid": player,
        "staged_item_uuid": item, "paper_pickup_tick": pickup,
        "session_id": sid, "original_s49_move_count": len(moves),
        "original_s49_move_ids": [m["action_id"] for m in moves],
        "original_s50_clear_seq": client["original_s49_last_clear_native_seq"],
        "native_7_controls_off_after_clear": (
            client["direct_all_seven_controls_off_after_last_clear"]
        ),
        "client_postclear_physics_ticks": client["post_clear_client_physics_tick_rows"],
        "paper_total_contiguous_ticks": len(rows),
        "paper_last_reported_inputs_off_ticks": paper_input_off,
        "paper_input_event_rows": len(evs),
        "paper_postpickup_tick_rows": after_pickup_rows,
        "paper_first_postpickup_tick": post_pickup_first,
        "paper_last_tick": previous_tick,
        "paper_postpickup_longest_quiet_streak": longest_quiet,
        "paper_postpickup_latest_quiet_streak": current_quiet,
        "paper_latest_eight_quiet_observed": current_quiet >= 8,
        "paper_last_reported_input_not_proven_effective_clear": True,
        "server_effective_S49_clear_tick": "NOT_CAUSALLY_ATTESTED",
        "body_physically_stopped_proven": False,
        "authenticated_S_owner_EAT_resume_grant": False,
        "original_EAT_issued": False,
        "qualification": "NO_GO", "science": "NOT_RUN",
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--server-log", type=Path, required=True)
    p.add_argument("--report", type=Path, required=True)
    p.add_argument("--staged-audit", type=Path, required=True)
    p.add_argument("--native-sidecar", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    result = audit_staged_stop(
        a.server_log.read_text(encoding="utf8"),
        json.loads(a.report.read_text(encoding="utf8")),
        json.loads(a.staged_audit.read_text(encoding="utf8")),
        a.native_sidecar.read_text(encoding="utf8"),
    )
    a.out.write_text(json.dumps(result, indent=2, sort_keys=True)+"\n", encoding="utf8")
    print(result["classification"])


if __name__ == "__main__":
    main()
