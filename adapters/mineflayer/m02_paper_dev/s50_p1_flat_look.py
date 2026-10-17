"""FLAT P1: source-bound Paper yaw before the existing S50 FORWARD (DEV only).

The native LOOK ACK is client-local. Only a subsequent actual Paper server
snapshot can witness the requested orientation. No extra LOOK/MOVE authority.
A match at one instant cannot certify orientation for an entire later tick.
"""
from __future__ import annotations

import asyncio
import math
import re
from pathlib import Path

from adapters.mineflayer.m02_paper_dev.s50_boundary import BoundaryRejected
from adapters.mineflayer.s31a_real_server_ci import _command

PREFIX = "S_V8_DEV_SNAPSHOT "
MARKER = re.compile(r"[A-Za-z0-9_-]{1,108}")
MAX_SNAPSHOTS = 12
MAX_WAIT_POLLS = 60
MAX_YAW_DIFF_DEGREES = 5.0
MAX_PITCH_DIFF_DEGREES = 5.0


def _number(row: dict, field: str) -> float:
    try:
        result = float(row[field])
    except (ValueError, KeyError, TypeError) as exc:
        raise BoundaryRejected("missing or invalid real Paper look source") from exc
    if not math.isfinite(result):
        raise BoundaryRejected("nonfinite real Paper look source")
    return result


def _gap(a: float, b: float) -> float:
    return abs((a - b + 180.0) % 360.0 - 180.0)


def check_snapshot(line: str, *, marker_id: str,
                   expected_yaw_rad: float, world: str | None,
                   previous_tick: int | None) -> dict:
    """Only one exact, source-issued Paper snapshot; never a Mineflayer ACK."""
    if (not MARKER.fullmatch(marker_id)
            or not isinstance(expected_yaw_rad, (float, int))
            or not math.isfinite(expected_yaw_rad)
            or not line.count(PREFIX) == 1):
        raise BoundaryRejected("foreign or malformed Paper LOOK witness request")
    fields = line.split(PREFIX, 1)[1].split()
    kv = [pair.split("=", 1) for pair in fields]
    if any(len(pair) != 2 for pair in kv) or len({p[0] for p in kv}) != len(kv):
        raise BoundaryRejected("duplicate/unparseable Paper snapshot field")
    row = dict(kv)
    if (row.get("marker_id") != marker_id
            or row.get("seed") != "63101"
            or not row.get("world")
            or (world is not None and row["world"] != world)):
        raise BoundaryRejected("wrong FLAT source, marker, or World")
    tick = _number(row, "full_time")
    if (not tick.is_integer() or tick < 0
            or previous_tick is not None and tick < previous_tick):
        raise BoundaryRejected("Paper LOOK World clock regressed or is invalid")
    x, y, z = (_number(row, axis) for axis in ("x", "y", "z"))
    if any(abs(v - want) > 0.03
           for v, want in zip((x, y, z), (0.5, -60.0, 0.5), strict=True)):
        raise BoundaryRejected("Self moved before FORWARD or left FLAT fixed pose")
    observed_yaw = _number(row, "yaw")
    observed_pitch = _number(row, "pitch")
    expected_yaw = math.degrees(expected_yaw_rad)
    # Only Paper degrees are comparable to Minecraft direction; native LOOK
    # uses radians. A client ACK has no authority to substitute for this row.
    return {
        "classification": "S_P1_FLAT_PAPER_LOOK_PRE_FORWARD_SNAPSHOT_DEV_ONLY",
        "marker_id": marker_id,
        "seed": 63101,
        "world": row["world"],
        "paper_full_time": int(tick),
        "paper_yaw_degrees": observed_yaw,
        "paper_pitch_degrees": observed_pitch,
        "look_requested_yaw_degrees": expected_yaw,
        "yaw_gap_degrees": _gap(observed_yaw, expected_yaw),
        "pitch_gap_degrees": abs(observed_pitch),
        "orientation_matches": (
            _gap(observed_yaw, expected_yaw) <= MAX_YAW_DIFF_DEGREES
            and abs(observed_pitch) <= MAX_PITCH_DIFF_DEGREES
        ),
        "real_move_authorized_by_this_snapshot": False,
        "later_forward_server_effective_tick": "NOT_ATTESTED",
        "whole_tick_orientation_attested": False,
        "P1_wait_ticks_admitted": 0,
        "P1_fatigue_recovered": 0.0,
    }


async def await_paper_look_before_forward(
    server, paper_log: Path, *, marker: str, expected_yaw_rad: float,
) -> dict:
    """Bounded Paper-source look barrier after existing LOOK ACK.

    No FORWARD is ever issued by this reader. Caller invokes the original
    governed FORWARD only if this source check returns a positive match.
    """
    if (not MARKER.fullmatch(marker)
            or server.returncode is not None or server.stdin is None
            or not paper_log.is_file() or paper_log.is_symlink()):
        raise BoundaryRejected("unavailable original Paper look source")
    world = None
    previous = None
    for n in range(1, MAX_SNAPSHOTS + 1):
        marker_id = f"{marker}-P1LOOK-{n:02d}"
        if len(marker_id) > 128:
            raise BoundaryRejected("Paper source marker length exceeded")
        _command(server, "relaydevsnapshot " + marker_id)
        await server.stdin.drain()
        row = None
        for _ in range(MAX_WAIT_POLLS):
            if server.returncode is not None or not paper_log.is_file():
                raise BoundaryRejected("Paper stopped during look-readback barrier")
            matches = [line for line in paper_log.read_text(encoding="utf-8").splitlines()
                       if f"{PREFIX}marker_id={marker_id} " in line]
            if len(matches) > 1:
                raise BoundaryRejected("duplicate Paper LOOK snapshot")
            if matches:
                row = matches[0]
                break
            await asyncio.sleep(0.05)
        if row is None:
            raise BoundaryRejected("Paper native LOOK snapshot never acknowledged")
        witness = check_snapshot(row, marker_id=marker_id,
                                 expected_yaw_rad=expected_yaw_rad,
                                 world=world, previous_tick=previous)
        world = witness["world"]
        previous = witness["paper_full_time"]
        if witness["orientation_matches"]:
            witness["source_snapshots_checked"] = n
            return witness
        await asyncio.sleep(0.05)
    raise BoundaryRejected("LOOK_ACK_WITHOUT_PAPER_EFFECTIVE_YAW: do not issue FORWARD")
