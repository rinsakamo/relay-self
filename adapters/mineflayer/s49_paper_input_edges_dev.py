"""Pre-arm the existing Paper DEV observer; review server BACK input events.

Paper's PlayerInputEvent/Bukkit World.getFullTime describe a separate server
clock domain. Server event edges are not a SourceBoundTick grant, duration
attestation or a claim of whole-tick effective movement.
"""
from __future__ import annotations

import asyncio
import math
import re
import time
from pathlib import Path

from adapters.mineflayer.m02_paper_dev.s50_boundary import BoundaryRejected

ID = r"([A-Za-z0-9_.:-]+)"
BASE = rf"action_id={ID} session_id={ID} world={ID} run_id={ID}"
EDGE = re.compile(
    rf"S49_OBSERVER_BACK_(TRUE|FALSE) marker_id={ID} "
    + BASE + r" tick=(\d+) back=(true|false)"
    + r" x=(-?\d+(?:\.\d+)?(?:[Ee][+-]?\d+)?)"
    + r" z=(-?\d+(?:\.\d+)?(?:[Ee][+-]?\d+)?)"
)
ARM = re.compile(rf"S49_OBSERVER_PRE_ARM marker_id={ID} " + BASE + r" tick=(\d+) input_idle=true")
WAIT = re.compile(rf"S49_DEV_BACK_WAIT_TICK marker_id={ID} " + BASE + r" tick=(\d+) index=(\d+) input_idle=true")


async def await_paper_input_arm_dev(
    server_log: Path, *, offset: int, action_id: str,
    session_id: str, timeout_s: float = 12.0,
) -> None:
    """No additional Paper or Node process reader: poll original console file."""
    if (type(offset) is not int or offset < 0 or not action_id
            or not session_id):
        raise BoundaryRejected("prearm requires original Action source")
    end = time.monotonic() + timeout_s
    while time.monotonic() < end:
        if server_log.is_file():
            with server_log.open("rb") as stream:
                stream.seek(offset)
                window = stream.read(65537)
            if len(window) > 65536:
                raise BoundaryRejected("prearm Paper log window exceeded")
            text = window.decode("utf-8")
            if "S49_OBSERVER_DENIED" in text or "S49_DEV_BACK_WAIT_ABORT" in text:
                raise BoundaryRejected("Paper prearm denied or aborted")
            for match in ARM.finditer(text):
                _, aid, sid, _, _, _ = match.groups()
                if aid == action_id and sid == session_id:
                    return
        await asyncio.sleep(0.05)
    raise BoundaryRejected("Paper never confirmed server PRE_ARM before native MOVE")


def review_paper_input_edges_dev(
    paper_log: Path, original: dict, node_review: dict,
) -> dict[str, object]:
    if (not paper_log.is_file() or not isinstance(original, dict)
            or not isinstance(node_review, dict)
            or node_review.get("status") != "DEV_S49_THREE_CLOCKS_OBSERVED"
            or node_review.get("original_session_id") != original.get("session_id")
            or not isinstance(original.get("actual_native_actions"), list)
            or len(original["actual_native_actions"]) != 4):
        raise BoundaryRejected("original S49 and Node clock review must precede Paper")
    data = paper_log.read_text("utf-8")
    if len(data) > 2_000_000 or "S49_DEV_BACK_WAIT_ABORT" in data or "S49_OBSERVER_DENIED" in data:
        raise BoundaryRejected("Paper prearm log failed or exceeded bounds")
    aid = original["actual_native_actions"][1]["action"]
    session_id = original["session_id"]
    arms = ARM.findall(data)
    edges = EDGE.findall(data)
    waits = WAIT.findall(data)
    if len(arms) != 1 or len(edges) != 2 or len(waits) != 8:
        raise BoundaryRejected("exactly one prearm, two server input edges, eight WAIT ticks")
    def owner(marker, act, session, world, run):
        if (act != aid or session != session_id or marker != aid + "-" + session_id
                or not world or not run):
            raise BoundaryRejected("foreign Paper action, session, world or run")
        return world, run
    arm = arms[0]
    aworld, arun = owner(*arm[:5])
    on, off = edges
    if on[0] != "TRUE" or off[0] != "FALSE" or on[7] != "true" or off[7] != "false":
        raise BoundaryRejected("Paper input release order/source incorrect")
    if (owner(*on[1:6]) != (aworld, arun)
            or owner(*off[1:6]) != (aworld, arun)):
        raise BoundaryRejected("different Paper world/run for BACK edges")
    arm_tick, on_tick, off_tick = int(arm[5]), int(on[6]), int(off[6])
    if not arm_tick <= on_tick < off_tick or off_tick - on_tick > 20:
        raise BoundaryRejected("Paper input edges not monotonically separated")
    for index, item in enumerate(waits, 1):
        if (owner(*item[:5]) != (aworld, arun)
                or int(item[5]) != off_tick + index
                or int(item[6]) != index):
            raise BoundaryRejected("post-release Paper WAIT window inconsistent")
    pos = [float(on[i]) for i in (8, 9)] + [float(off[i]) for i in (8, 9)]
    if not all(math.isfinite(v) for v in pos):
        raise BoundaryRejected("Paper player position not finite")
    movement = math.hypot(pos[2] - pos[0], pos[3] - pos[1])
    if movement > 10.0:
        raise BoundaryRejected("Paper input edge displacement is not bounded")
    node_rows = [row for row in node_review["node_actions"] if row["action_id"] == aid]
    if len(node_rows) != 1 or original["actual_native_actions"][1]["terminal"] != "outcome":
        raise BoundaryRejected("Paper edge lacks original closed S16 Action")
    return {
        "status": "DEV_PAPER_SERVER_INPUT_EDGE_TICKS_OBSERVED",
        "source_action_id": aid,
        "native_session_id": session_id,
        "paper_world_id": aworld,
        "paper_observer_run_id": arun,
        "paper_arm_tick": arm_tick,
        "paper_server_back_on_event_tick": on_tick,
        "paper_server_back_off_event_tick": off_tick,
        "paper_observed_input_edge_tick_span": off_tick - on_tick,
        "paper_server_edge_position_xz": {
            "back_on": {"x": pos[0], "z": pos[1]},
            "back_off": {"x": pos[2], "z": pos[3]},
        },
        "paper_server_position_displacement_between_edge_events_m": movement,
        "node_back_active_ms_same_action":
            node_rows[0]["node_control_active_monotonic_ms"],
        "node_physics_tick_callbacks_same_action":
            node_rows[0]["node_physics_tick_callbacks_while_back_active"],
        "original_s16_displacement_m":
            original["actual_native_actions"][1]["movement_m"],
        "post_release_consecutive_world_wait_ticks": 8,
        "paper_full_effective_movement_ticks_attested": False,
        "cross_process_clock_alignment_attested": False,
        "original_action_issuer_unchanged": True,
        "new_paper_command_effect": False,
        "native_fatigue_measured": False,
        "qualification_go": False,
        "science_go": False,
    }
