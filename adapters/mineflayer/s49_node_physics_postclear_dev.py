"""Original Mineflayer Node-local physicsTick and control readback, DEV only.

Written solely by existing bridge.mjs process. No duplicate stdin/stdout
reader, no new Action authority. Never equate Node physics ticks with Paper
World ticks or qualify WAIT, M0, P1, or a native effect tick.
"""
from __future__ import annotations

import json
import math
from pathlib import Path


class NativePhysicsTraceRejected(ValueError):
    pass


def audit_node_physics_postclear_dev(
    path: Path, *, session_id: str, action_id: str, paper_post_release: dict,
) -> dict:
    if (not isinstance(path, Path) or path.is_symlink() or not path.is_file()
            or path.stat().st_size > 50000
            or not isinstance(session_id, str) or not session_id
            or not isinstance(action_id, str) or not action_id
            or type(paper_post_release) is not dict
            or paper_post_release.get("action_id") != action_id
            or paper_post_release.get("session_id") != session_id
            or paper_post_release.get("paper_callbacks") != 5
            or paper_post_release.get("WAIT_sourcebound_admitted") is not False
            or paper_post_release.get("M0_posted") is not False
            or paper_post_release.get("P1_posted") is not False):
        raise NativePhysicsTraceRejected("Node or Paper original session boundary invalid")
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise NativePhysicsTraceRejected("Node physics JSON unavailable") from exc
    if (type(raw) is not dict
            or raw.get("version") != "S49_NODE_PHYSICS_POST_CLEAR_DEV_V1"
            or raw.get("session_id") != session_id
            or raw.get("action_id") != action_id
            or raw.get("complete") is not True
            or raw.get("source_attested") is not False
            or raw.get("clear_seen") is not True
            or type(raw.get("post_clear_ticks")) is not int
            or raw["post_clear_ticks"] != 5
            or type(raw.get("rows")) is not list):
        raise NativePhysicsTraceRejected("Node trace header unsupported")
    rows = raw["rows"]
    if not 10 <= len(rows) <= 90:
        raise NativePhysicsTraceRejected("Node trace count insufficient/oversized")
    phases = [row.get("phase") if type(row) is dict else None for row in rows]
    if phases[0] != "SET" or phases.count("CLEAR") != 1:
        raise NativePhysicsTraceRejected("missing original local control state edges")
    idx = phases.index("CLEAR")
    if (not 3 <= idx <= 84
            or phases[1:idx] != ["ACTIVE"] * (idx - 1)
            or phases[idx + 1:] != ["POST_CLEAR"] * 5):
        raise NativePhysicsTraceRejected("Node physics event order or replay")
    initial_t = None
    prev_clock = -1
    prior_index = 0
    deltas = []
    for i, row in enumerate(rows):
        if type(row) is not dict:
            raise NativePhysicsTraceRejected("invalid Node physics sample")
        seq = row.get("index")
        clk = row.get("monotonic_ms")
        if (type(seq) is not int or seq < 0
                or type(clk) is not int or clk < 0
                or clk < prev_clock):
            raise NativePhysicsTraceRejected("invalid Node monotonic physics sequence")
        if i == 0:
            if seq != 0:
                raise NativePhysicsTraceRejected("Node SET index must be zero")
            initial_t = clk
        elif i == idx:
            if seq != prior_index:
                raise NativePhysicsTraceRejected("local CLEAR must share previous physics index")
        elif seq != prior_index + 1:
            raise NativePhysicsTraceRejected("Node physics index skipped or duplicated")
        prev_clock, prior_index = clk, seq
        on = i < idx
        if (row.get("forward") is not on or row.get("sprint") is not on
                or any(row.get(key) is not False for key in ("back", "left", "right"))):
            raise NativePhysicsTraceRejected("Node local forward/sprint did not clear")
        for name in ("x", "z", "vx", "vz"):
            v = row.get(name)
            if type(v) not in (int, float) or not math.isfinite(v):
                raise NativePhysicsTraceRejected("nonfinite Node position/velocity")
        if i > idx:
            preceding = rows[i - 1]
            delta = math.hypot(row["x"] - preceding["x"],
                               row["z"] - preceding["z"])
            if not math.isfinite(delta) or delta > 1.5:
                raise NativePhysicsTraceRejected("impossible Node postclear displacement")
            deltas.append(delta)
    # Node-local physics ticks vs Paper fullTime are separate clocks. Sample
    # and compare aggregates but NEVER derive the exact corresponding Paper tick.
    return {
        "classification": "NODE_LOCAL_PHYSICS_AFTER_CONTROL_CLEAR_DEV_ONLY",
        "action_id": action_id, "session_id": session_id,
        "node_active_physics_ticks": idx - 1,
        "node_postclear_physics_ticks": 5,
        "node_forward_sprint_at_set": True,
        "node_forward_sprint_at_clear": False,
        "node_postclear_forward_sprint_all_false": True,
        "node_postclear_horizontal_deltas_m": deltas,
        "node_postclear_translation_ticks": sum(x > 0.002 for x in deltas),
        "node_time_elapsed_ms_first_to_final": prev_clock - initial_t,
        "paper_postrelease_callbacks": paper_post_release["paper_callbacks"],
        "paper_postrelease_positive_translation_ticks": paper_post_release[
            "post_release_positive_translation_ticks"
        ],
        "node_paper_tick_join_attested": False,
        "client_packet_world_tick_attested": False,
        "P1_posted": False, "M0_posted": False,
        "WAIT_sourcebound_admitted": False,
        "science_go": False, "qualification_go": False,
    }
