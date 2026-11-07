"""D7-A read-only audit: actual S50 seven Mineflayer controls after original S49 MOVE.

The existing S50 wrapper captures the SAME Mineflayer bot's real physicsTick
and getControlState() values, passively. Native client physicsTick is NOT
Paper server tick, a network-effective control release certificate, or a
full-tick occupancy certificate. Even a perfect quiet trace MUST NOT unlock
the original S49 post-MOVE EAT fence.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

CONTROLS = ("forward", "back", "left", "right", "jump", "sprint", "sneak")
SOURCE = "S50_DEV_NATIVE_READBACK_V1"
MAX_ROWS = 8192
MAX_BYTES = 4_000_000


class D7PassiveReadbackRejected(ValueError):
    """Original S50 same-process client control source is missing or inconsistent."""


def _unique_keys(pairs):
    out = {}
    for name, value in pairs:
        if name in out:
            raise D7PassiveReadbackRejected("duplicate original direct control field")
        out[name] = value
    return out


def _all_controls_off(row: dict) -> bool:
    controls = row.get("controls")
    if (
        not isinstance(controls, dict)
        or set(controls) != set(CONTROLS)
        or any(type(controls[k]) is not bool for k in CONTROLS)
    ):
        raise D7PassiveReadbackRejected("missing/nonboolean 7 direct held controls")
    return not any(controls.values())


def audit_passive_controls(
    source: str, report: dict, prior_audit: dict,
) -> dict:
    """Sidecar chronology + original Action/World joins, without EAT authority."""
    if (
        not isinstance(source, str)
        or not 0 < len(source.encode("utf8")) <= MAX_BYTES
        or not isinstance(report, dict)
        or not isinstance(prior_audit, dict)
        or report.get("status") != "PASS_DEV"
        or report.get("node_exit") != 0 or report.get("java_exit") != 0
        or report.get("cleanup_done") is not True
        or report.get("d7_same_s49_passive_s50_readback") is not True
        or report.get("d7_paper_effective_stop_proven") is not False
        or report.get("d7_eat_grant_issued") is not False
        or report.get("self_eat") is not False
        or (
            bool(report.get("d6_original_s49_move_actions"))
            and report.get("d6_post_move_eat_fenced") is not True
        )
        or report.get("d6_multigen_no_eat") is not True
        or prior_audit.get("status") != "PASS_DEV"
        or prior_audit.get("no_eat_after_move") is not True
        or prior_audit.get("same_supervisor_retained") is not True
        or prior_audit.get("unresolved_motion") is not False
        or prior_audit.get("unresolved_nonmotion") is not False
        or prior_audit.get("session_id") != report.get("session_id")
    ):
        raise D7PassiveReadbackRejected("original S49 EAT fence and audited World absent")
    moves = report.get("d6_original_s49_move_actions", [])
    if not isinstance(moves, list) or prior_audit.get("original_move_count") != len(moves):
        raise D7PassiveReadbackRejected("original auditor MOVE count disagrees")
    if not moves:
        # This is a valid genuine all-zero natural World, not a positive
        # post-MOVE STOP or EAT qualification. Preserve it as NOT_EXERCISED.
        if (
            not source.startswith('{"source":"S50_DEV_NATIVE_READBACK_V1"')
            and '"source": "S50_DEV_NATIVE_READBACK_V1"' not in source.splitlines()[0]
        ):
            raise D7PassiveReadbackRejected("original S50 source absent in zero case")
        return {
            "classification": "D7_A_NO_MOVE_STOP_SOURCE_NOT_EXERCISED",
            "source_session": report["session_id"],
            "original_s49_move_action_ids": [],
            "source_scope": "NO_PHYSICAL_S49_MOVE_OBSERVED",
            "body_physically_stopped_proven": False,
            "authenticated_S_owner_EAT_resume_grant": False,
            "original_EAT_issued": False,
            "server_effective_release_tick": "NOT_ATTESTED",
            "full_Paper_world_tick_motor_coverage": "NOT_ATTESTED",
            "qual": "NO_GO",
            "science": "NOT_RUN",
        }
    if (
        len({m.get("action_id") for m in moves}) != len(moves)
        or any(
            m.get("session_id") != report["session_id"]
            or m.get("terminal") != "outcome"
            or m.get("action_ref") != "MOVE_BACKWARD"
            for m in moves
        )
    ):
        raise D7PassiveReadbackRejected("no original completed real S49 MOVE for settling")
    try:
        rows = [
            json.loads(line, object_pairs_hook=_unique_keys)
            for line in source.splitlines()
        ]
    except (UnicodeError, ValueError, TypeError) as exc:
        raise D7PassiveReadbackRejected("invalid original S50 JSONL") from exc
    if not 12 <= len(rows) <= MAX_ROWS:
        raise D7PassiveReadbackRejected("direct control stream incomplete or truncated")
    sid = report["session_id"]
    if (
        rows[0].get("source") != SOURCE
        or rows[0].get("kind") != "SESSION_START"
        or rows[0].get("native_seq") != 0
        or rows[0].get("session_id") != sid
        or rows[0].get("client_physics_tick") != 0
        or rows[-1].get("kind") != "SHUTDOWN_ACK"
        or rows[-1].get("session_id") != sid
    ):
        raise D7PassiveReadbackRejected("original S50 session/source bounds absent")
    kinds = {"PHYSICS_TICK", "EFFECT_ACK", "PROBE", "SHUTDOWN_ACK"}
    total_client_ticks = 0
    ticks = []
    native_effect_ack = {}
    shutdown_count = 0
    for i, row in enumerate(rows, 1):
        kind = row.get("kind")
        if (
            not isinstance(row, dict)
            or row.get("source") != SOURCE
            or row.get("session_id") != sid
            or type(row.get("ordinal")) is not int
            or row["ordinal"] != i
            or type(row.get("client_physics_tick")) is not int
            or row["client_physics_tick"] != total_client_ticks
                + int(kind == "PHYSICS_TICK")
            or (i == 1 and kind != "SESSION_START")
            or (i > 1 and kind not in kinds)
        ):
            raise D7PassiveReadbackRejected(
                "original source not one continuous client physicsTick stream"
            )
        if i > 1:
            off = _all_controls_off(row)
            if kind == "PHYSICS_TICK":
                total_client_ticks += 1
                ticks.append((i, row["client_physics_tick"], off))
            elif kind == "EFFECT_ACK":
                key = (row.get("native_action_id"), row.get("native_seq"))
                if (
                    not isinstance(key[0], str) or not key[0]
                    or type(key[1]) is not int
                    or key in native_effect_ack
                ):
                    raise D7PassiveReadbackRejected("duplicate/bad original S15 ACK")
                native_effect_ack[key] = (i, row, off)
            elif kind == "SHUTDOWN_ACK":
                shutdown_count += 1
                if i != len(rows) or type(row.get("native_seq")) is not int:
                    raise D7PassiveReadbackRejected("shutdown not terminal")
        if i > 1 and i != len(rows) and shutdown_count:
            raise D7PassiveReadbackRejected("source events after shutdown")
    if total_client_ticks < 8 or shutdown_count != 1:
        raise D7PassiveReadbackRejected("direct tick/shutdown source incomplete")

    # The original S15 MOVE has exactly one clear receipt tied to its own
    # native action_id + '-clear'. Same-client-local ordering only.
    for m in moves:
        clear_key = (m["action_id"] + "-clear", m.get("s15_clear_seq"))
        if clear_key not in native_effect_ack:
            raise D7PassiveReadbackRejected("original MOVE clear has no direct control ACK")
        index, row, all_off = native_effect_ack[clear_key]
        if not all_off:
            raise D7PassiveReadbackRejected("direct native controls still held at clear ACK")
    last = moves[-1]
    final_clear_index, final_clear, _ = native_effect_ack[
        (last["action_id"] + "-clear", last["s15_clear_seq"])
    ]
    future = [(i, tick, off) for i, tick, off in ticks if i > final_clear_index]
    if len(future) < 8:
        raise D7PassiveReadbackRejected("not eight genuine post-MOVE client physics ticks")
    first_eight = future[:8]
    if (
        any(not x[2] for x in future)
        or [x[1] for x in first_eight]
            != list(range(first_eight[0][1], first_eight[0][1]+8))
        or not all(_all_controls_off(row) for row in rows[final_clear_index:])
        or any(
            row.get("kind") == "EFFECT_ACK"
            for row in rows[final_clear_index:]
        )
    ):
        raise D7PassiveReadbackRejected(
            "post-MOVE native controls reactivated or client physicsTick coverage broken"
        )
    return {
        "classification": "D7_A_S50_DIRECT_CLIENT_CONTROLS_POSTMOVE_QUIET_OBSERVED",
        "source_session": sid,
        "original_s49_move_action_ids": [m["action_id"] for m in moves],
        "original_s49_last_clear_native_seq": last["s15_clear_seq"],
        "original_s49_last_after_native_seq": last["s15_after_seq"],
        "last_clear_direct_control_row_ordinal": final_clear["ordinal"],
        "first_post_clear_client_physics_tick": first_eight[0][1],
        "eighth_post_clear_client_physics_tick": first_eight[7][1],
        "post_clear_client_physics_tick_rows": len(future),
        "direct_all_seven_controls_off_after_last_clear": True,
        "native_source_rows": len(rows),
        "native_session_end_seen": True,
        "same_original_supervisor": True,
        "source_scope": "S50_NATIVE_CLIENT_HELD_CONTROLS_ONLY",
        "server_effective_release_tick": "NOT_ATTESTED",
        "full_Paper_world_tick_motor_coverage": "NOT_ATTESTED",
        "Paper_velocity_and_position_census": "NOT_ATTESTED",
        "body_physically_stopped_proven": False,
        "authenticated_S_owner_EAT_resume_grant": False,
        "original_EAT_issued": False,
        "self_policy_changed": False,
        "qual": "NO_GO",
        "science": "NOT_RUN",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sidecar", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--original-audit", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = audit_passive_controls(
        args.sidecar.read_text(encoding="utf8"),
        json.loads(args.report.read_text(encoding="utf8")),
        json.loads(args.original_audit.read_text(encoding="utf8")),
    )
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True)+"\n",
                        encoding="utf8")
    print(result["classification"])


if __name__ == "__main__":
    main()
