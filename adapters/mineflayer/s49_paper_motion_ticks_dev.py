"""DEV read-only server PlayerMoveEvent tick observation.

Unlike the unobserved Paper PlayerInputEvent ON/OFF in the preceding
fail-closed trial, these are server position-change events. They do NOT
attest when BACK input was applied, whole effective tick counts, or
cross-process time synchronization.
"""
from __future__ import annotations

import asyncio
import math
import re
import time
from pathlib import Path

from adapters.mineflayer.m02_paper_dev.s50_boundary import BoundaryRejected

ID = r"([A-Za-z0-9_.:-]+)"
START = re.compile(rf"S49_MOTION_SERVER_ARM action_id={ID} session_id={ID} player_uuid={ID} world={ID} tick=(\d+) authority=NONE input_edge_attested=false")
STOP = re.compile(rf"S49_MOTION_SERVER_COMPLETE action_id={ID} session_id={ID} player_uuid={ID} world={ID} movement_events=(\d+) distinct_position_change_ticks=(\d+) authority=NONE input_edge_attested=false")
SAMPLE = re.compile(rf"S49_MOTION_SERVER_POSITION action_id={ID} session_id={ID} world={ID} tick=(\d+) index=(\d+) from_x=([^ ]+) from_z=([^ ]+) to_x=([^ ]+) to_z=([^ ]+) input_edge_attested=false")


async def await_paper_motion_marker_dev(
    paper_log: Path, offset: int, *, marker: str, action_id: str,
    session_id: str, timeout_s: float = 10,
) -> None:
    if marker not in ("ARM", "COMPLETE") or type(offset) is not int or offset < 0:
        raise BoundaryRejected("Paper motion marker invalid")
    until = time.monotonic() + timeout_s
    while time.monotonic() < until:
        if paper_log.is_file():
            with paper_log.open("rb") as source:
                source.seek(offset)
                data = source.read(65537)
            if len(data) > 65536:
                raise BoundaryRejected("Paper motion marker window exceeded")
            sample = data.decode("utf-8")
            if "S49_MOTION_SERVER_DENIED" in sample or "S49_MOTION_SERVER_ABORT" in sample:
                raise BoundaryRejected("Paper passive motion session denied/aborted")
            pattern = START if marker == "ARM" else STOP
            if any(match[0] == action_id and match[1] == session_id
                   for match in pattern.findall(sample)):
                return
        await asyncio.sleep(0.05)
    raise BoundaryRejected("Paper passive movement marker timeout")


def review_paper_motion_ticks_dev(paper_log: Path, original: dict, node_clock: dict):
    if (not paper_log.is_file() or not isinstance(original, dict)
            or not isinstance(node_clock, dict)
            or node_clock.get("status") != "DEV_S49_THREE_CLOCKS_OBSERVED"
            or node_clock.get("original_session_id") != original.get("session_id")
            or original.get("status") != "PASS"):
        raise BoundaryRejected("Paper event log needs existing S49 and Node clocks")
    data = paper_log.read_text("utf-8")
    if (len(data) > 2000000 or "S49_MOTION_SERVER_DENIED" in data
            or "S49_MOTION_SERVER_ABORT" in data):
        raise BoundaryRejected("Paper motion trace invalid")
    arms, stops, frames = START.findall(data), STOP.findall(data), SAMPLE.findall(data)
    if len(arms) != 1 or len(stops) != 1 or not 1 <= len(frames) <= 64:
        raise BoundaryRejected("one fully closed passive motion observation required")
    aid = original["actual_native_actions"][1]["action"]
    sid = original["session_id"]
    arm, stop = arms[0], stops[0]
    if (arm[:4] != stop[:4]
            or arm[0] != aid or arm[1] != sid
            or int(stop[4]) != len(frames)):
        raise BoundaryRejected("Paper arm/stop original Action mismatch")
    rows = []
    for i, frame in enumerate(frames, 1):
        if (frame[:3] != (aid, sid, arm[3])
                or int(frame[4]) != i
                or int(frame[3]) < int(arm[4])):
            raise BoundaryRejected("Paper MOVE sample source/sequence mismatch")
        try:
            coords = [float(x) for x in frame[5:9]]
        except ValueError as exc:
            raise BoundaryRejected("Paper coordinates invalid") from exc
        if not all(math.isfinite(x) for x in coords):
            raise BoundaryRejected("Paper coordinates non-finite")
        rows.append((int(frame[3]), coords))
    ticks = [row[0] for row in rows]
    if (any(b < a for a, b in zip(ticks, ticks[1:]))
            or len(set(ticks)) != int(stop[5])
            or ticks[-1] - ticks[0] > 20):
        raise BoundaryRejected("Paper movement ticks unavailable or rewound")
    assert node_clock["node_actions"][1]["action_id"] == aid
    from_xy = rows[0][1][:2]
    to_xy = rows[-1][1][2:]
    displacement = math.hypot(to_xy[0] - from_xy[0], to_xy[1] - from_xy[1])
    if displacement < 0 or displacement > 10:
        raise BoundaryRejected("Paper event displacement outside bounded world")
    return {
        "status": "DEV_PAPER_SERVER_POSITION_EVENT_TICKS_OBSERVED",
        "action_id": aid,
        "native_session_id": sid,
        "paper_world_id": arm[3],
        "paper_arm_world_tick": int(arm[4]),
        "paper_first_position_change_tick": ticks[0],
        "paper_last_position_change_tick": ticks[-1],
        "paper_distinct_position_change_ticks": len(set(ticks)),
        "paper_position_change_event_count": len(rows),
        "paper_edge_to_edge_displacement_m": displacement,
        "node_back_on_to_off_ms":
            node_clock["node_actions"][1]["node_control_active_monotonic_ms"],
        "node_physics_tick_callbacks":
            node_clock["node_actions"][1]["node_physics_tick_callbacks_while_back_active"],
        "original_s16_displacement_m": original["actual_native_actions"][1]["movement_m"],
        "paper_player_input_back_on_observed": False,
        "paper_player_input_back_off_observed": False,
        "server_input_effective_tick_count_attested": False,
        "cross_process_clock_alignment_attested": False,
        "no_new_action_issuer": True,
        "qualification_go": False,
        "science_go": False,
    }
