"""D7-B independent read-only Paper tick census. NEVER grants S49 EAT.

Paper's getCurrentInput() reports LAST RECEIVED input, not the uniquely
correlated network delivery of original S15 clear. Server tick positions
and velocity are valuable evidence but cannot themselves unlock EAT.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

CONTROLS = ("forward", "back", "left", "right", "jump", "sprint", "sneak")
SOURCE = "PAPER_SERVER_MAIN_THREAD_V1"
TICK_MARK = "RSELF_D7_PAPER_TICK "
EVENT_MARK = "RSELF_D7_PAPER_INPUT_EVENT "
MAX_TICKS = 8192


class D7PaperSourceRejected(ValueError):
    """Malformed or mismatched Paper-owned per-tick observation."""


def _fields(line: str, marker: str) -> dict[str, str]:
    if marker not in line:
        raise D7PaperSourceRejected("Paper source event missing")
    result: dict[str, str] = {}
    for token in line.split(marker, 1)[1].split():
        if "=" not in token:
            raise D7PaperSourceRejected("bad source token")
        key, value = token.split("=", 1)
        if not key or not value or key in result:
            raise D7PaperSourceRejected("duplicate/empty source field")
        result[key] = value
    return result


def _number(row: dict[str, str], key: str) -> float:
    try:
        value = float(row[key])
    except (TypeError, ValueError, KeyError) as exc:
        raise D7PaperSourceRejected("missing Paper number " + key) from exc
    if not math.isfinite(value):
        raise D7PaperSourceRejected("nonfinite Paper number " + key)
    return value


def _integer(row: dict[str, str], key: str) -> int:
    try:
        value = int(row[key])
    except (ValueError, KeyError, TypeError) as exc:
        raise D7PaperSourceRejected("missing Paper integer " + key) from exc
    if value < 0 or str(value) != row[key]:
        raise D7PaperSourceRejected("noncanonical Paper integer " + key)
    return value


def _inputs_off(row: dict[str, str]) -> bool:
    for key in CONTROLS:
        if row.get(key) not in ("true", "false"):
            raise D7PaperSourceRejected("missing/nonboolean Paper input " + key)
    return not any(row[key] == "true" for key in CONTROLS)


def audit_paper_ticks(
    log: str, report: dict, original_audit: dict, client_audit: dict,
) -> dict:
    """Join genuine Paper tick census with already qualified D6/S50 originals."""
    if (
        not isinstance(log, str)
        or not isinstance(report, dict)
        or not isinstance(original_audit, dict)
        or not isinstance(client_audit, dict)
        or original_audit.get("status") != "PASS_DEV"
        or original_audit.get("session_id") != report.get("session_id")
        or client_audit.get("source_session") != report.get("session_id")
        or client_audit.get("body_physically_stopped_proven") is not False
        or client_audit.get("original_EAT_issued") is not False
        or original_audit.get("no_eat_after_move") is not True
        or report.get("self_eat") is not False
        or report.get("d7_eat_grant_issued") is not False
        or not isinstance(original_audit.get("paper_world_uuid"), str)
    ):
        raise D7PaperSourceRejected("unqualified original World/S50 join")
    lines = log.splitlines()
    ready = [x for x in lines if "RSELF_D7_PAPER_READY " in x]
    stop = [x for x in lines if "RSELF_D7_PAPER_STOP " in x]
    truncated = [x for x in lines if "RSELF_D7_PAPER_TRUNCATED " in x]
    if len(ready) != 1 or len(stop) != 1 or truncated:
        raise D7PaperSourceRejected("Paper source lifetime/truncation missing")
    ticks = [_fields(x, TICK_MARK) for x in lines if TICK_MARK in x]
    events = [_fields(x, EVENT_MARK) for x in lines if EVENT_MARK in x]
    max_ticks = 12000 if report.get("d14_tick_horizon_optin") is True else MAX_TICKS
    if not 8 <= len(ticks) <= max_ticks or len(events) > 512:
        raise D7PaperSourceRejected("Paper source insufficient or above cap")
    world = original_audit["paper_world_uuid"]
    player = ticks[0].get("player")
    if (
        not player
        or ticks[0].get("world") != world
        or any(r.get("source") != SOURCE for r in ticks + events)
    ):
        raise D7PaperSourceRejected("server tick source/World missing")
    first_tick = _integer(ticks[0], "tick")
    last_tick = first_tick - 1
    off_ticks = 0
    stable_streak = 0
    longest_streak = 0
    prev_position: tuple[float, float, float] | None = None
    input_active_ticks = 0
    for index, row in enumerate(ticks, 1):
        tick = _integer(row, "tick")
        if (
            row.get("player") != player
            or row.get("world") != world
            or _integer(row, "ordinal") != index
            or tick != last_tick + 1
            or row.get("ground") not in ("true", "false")
        ):
            raise D7PaperSourceRejected("Paper source tick gap/identity drift")
        last_tick = tick
        off = _inputs_off(row)
        if not off:
            input_active_ticks += 1
        else:
            off_ticks += 1
        position = tuple(_number(row, k) for k in ("x", "y", "z"))
        velocity = tuple(_number(row, k) for k in ("vx", "vy", "vz"))
        horizontal_delta_sq = (
            (position[0] - prev_position[0]) ** 2
            + (position[2] - prev_position[2]) ** 2
            if prev_position is not None else float("inf")
        )
        # Diagnostics, NOT an EAT permission threshold or proof that
        # the specific original S49 control-clear reached Paper.
        quiet = (
            off and prev_position is not None
            and row["ground"] == "true"
            and horizontal_delta_sq <= 0.0001
            and velocity[0] ** 2 + velocity[2] ** 2 <= 0.0001
        )
        stable_streak = stable_streak + 1 if quiet else 0
        longest_streak = max(longest_streak, stable_streak)
        prev_position = position
    for ev in events:
        if (
            ev.get("player") != player
            or ev.get("world") != world
            or _integer(ev, "tick") < first_tick - 1
            or _integer(ev, "tick") > last_tick
            or _integer(ev, "ordinal") < 1
        ):
            raise D7PaperSourceRejected("foreign Paper PlayerInputEvent")
        _inputs_off(ev)
    # D6 originals independently attest a NATURAL item with a stable Paper
    # UUID. Restrict a diagnostic 'quiet after pickup' window to this exact
    # item and player rather than counting quiet ticks before any physical
    # MOVE, when the client could already be stationary by construction.
    original_item = original_audit.get("natural_item_uuid")
    original_moves = original_audit.get("original_move_count")
    if type(original_moves) is not int or original_moves < 0:
        raise D7PaperSourceRejected("original S49 MOVE count not attested")
    pickup_tick = None
    if original_moves:
        pickups = [
            _fields(x, "RSELF_NATURAL_DROP_PICKUP ")
            for x in lines if "RSELF_NATURAL_DROP_PICKUP " in x
        ]
        if (
            not isinstance(original_item, str) or not original_item
            or len(pickups) != 1
            or pickups[0].get("item") != original_item
            or pickups[0].get("world") != world
            or pickups[0].get("player") != player
        ):
            raise D7PaperSourceRejected("genuine original Paper item pickup mismatch")
        pickup_tick = _integer(pickups[0], "tick")
        if not first_tick <= pickup_tick <= last_tick:
            raise D7PaperSourceRejected("Paper item pickup outside server tick census")
    elif original_item is not None:
        raise D7PaperSourceRejected("Paper pickup attributed without original MOVE")
    post_pickup_rows = []
    after_pickup_streak = 0
    longest_post_pickup_streak = 0
    prior_pos = None
    for row in ticks:
        tick = _integer(row, "tick")
        position = tuple(_number(row, k) for k in ("x", "y", "z"))
        velocity = tuple(_number(row, k) for k in ("vx", "vy", "vz"))
        if pickup_tick is not None and tick > pickup_tick:
            post_pickup_rows.append(tick)
            dxz_sq = (
                (position[0] - prior_pos[0]) ** 2
                + (position[2] - prior_pos[2]) ** 2
                if prior_pos is not None else float("inf")
            )
            same_world_quiet = (
                _inputs_off(row) and row["ground"] == "true"
                and dxz_sq <= 0.0001
                and velocity[0] ** 2 + velocity[2] ** 2 <= 0.0001
            )
            after_pickup_streak = (
                after_pickup_streak + 1 if same_world_quiet else 0
            )
            longest_post_pickup_streak = max(
                longest_post_pickup_streak, after_pickup_streak
            )
        prior_pos = position
    # Event ordinal sequence is exact even if the event has the same tick
    # as an independent scheduler tick row.
    if [_integer(e, "ordinal") for e in events] != list(range(1, len(events) + 1)):
        raise D7PaperSourceRejected("Paper input event duplicate/reordered")
    stop_fields = _fields(stop[0], "RSELF_D7_PAPER_STOP ")
    if (
        _integer(stop_fields, "total_ticks") != len(ticks)
        or _integer(stop_fields, "input_events") != len(events)
        or stop_fields.get("truncated") != "false"
        or stop_fields.get("eat_authority") != "none"
    ):
        raise D7PaperSourceRejected("Paper source count/truncation mismatch")
    if report.get("d6_original_s49_move_actions") and (
        client_audit.get("source_scope")
        != "S50_NATIVE_CLIENT_HELD_CONTROLS_ONLY"
    ):
        raise D7PaperSourceRejected("post-MOVE client source missing")
    return {
        "classification": "D7_B_REAL_PAPER_CONTIGUOUS_TICK_SOURCE_READ_ONLY",
        "world": world,
        "original_session": report["session_id"],
        "paper_player": player,
        "first_Paper_tick": first_tick,
        "last_Paper_tick": last_tick,
        "gapfree_Paper_tick_rows": len(ticks),
        "server_last_reported_inputs_off_ticks": off_ticks,
        "server_input_active_ticks": input_active_ticks,
        "Paper_input_event_rows": len(events),
        "longest_sampled_quiet_Paper_tick_streak": longest_streak,
        "original_natural_Paper_item_uuid": original_item,
        "original_Paper_pickup_tick": (
            pickup_tick if pickup_tick is not None else "NOT_EXERCISED"
        ),
        "post_pickup_Paper_tick_rows": len(post_pickup_rows),
        "longest_post_pickup_sampled_quiet_Paper_tick_streak": (
            longest_post_pickup_streak
        ),
        "post_pickup_8_quiet_server_ticks_observed": (
            longest_post_pickup_streak >= 8
        ),
        "latest_Paper_tick": last_tick,
        "latest_8_post_pickup_Paper_ticks_quiet": (
            after_pickup_streak >= 8
        ),
        "post_pickup_quiet_is_stop_authority": False,
        "server_effective_original_S49_clear_tick": "NOT_CAUSALLY_ATTESTED",
        "body_physically_stopped_proven": False,
        "authenticated_S_owner_EAT_resume_grant": False,
        "original_EAT_issued": False,
        "original_World_Action_replayed": False,
        "qualification": "NO_GO",
        "science": "NOT_RUN",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--server-log", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--original-audit", type=Path, required=True)
    parser.add_argument("--client-audit", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = audit_paper_ticks(
        args.server_log.read_text(encoding="utf8"),
        json.loads(args.report.read_text(encoding="utf8")),
        json.loads(args.original_audit.read_text(encoding="utf8")),
        json.loads(args.client_audit.read_text(encoding="utf8")),
    )
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n",
                        encoding="utf8")
    print(result["classification"])


if __name__ == "__main__":
    main()
