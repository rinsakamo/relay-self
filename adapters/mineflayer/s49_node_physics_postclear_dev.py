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



def audit_node_paper_motion_fingerprint_dev(
    node: dict, paper: dict, *, action_id: str, session_id: str,
) -> dict:
    """Match two consecutive *nonzero translations*, not absolute tick IDs.

    Both are source-local producer readbacks from ONE original native S49
    session. Without synchronized clocks, their relative sample index is
    unknown. A matching physical displacement footprint demonstrates
    changing, mutually consistent motion state; it neither proves exact
    frame correspondence nor attests packet/origin trust.
    """
    if (
        type(node) is not dict or type(paper) is not dict
        or not isinstance(action_id, str) or not action_id
        or not isinstance(session_id, str) or not session_id
        or node.get("classification")
           != "NODE_LOCAL_PHYSICS_AFTER_CONTROL_CLEAR_DEV_ONLY"
        or paper.get("classification")
           != "PAPER_PASSIVE_POST_RELEASE_TRANSLATION_DEV_ONLY"
        or node.get("action_id") != action_id
        or paper.get("action_id") != action_id
        or node.get("session_id") != session_id
        or paper.get("session_id") != session_id
        or node.get("node_paper_tick_join_attested") is not False
        or node.get("node_postclear_forward_sprint_all_false") is not True
        or node.get("node_postclear_physics_ticks") != 5
        or paper.get("paper_callbacks") != 5
        or paper.get("speed_modifier_present") is not False
        or node.get("WAIT_sourcebound_admitted") is not False
        or paper.get("WAIT_sourcebound_admitted") is not False
        or node.get("M0_posted") is not False
        or paper.get("M0_posted") is not False
        or node.get("P1_posted") is not False
        or paper.get("P1_posted") is not False
    ):
        raise NativePhysicsTraceRejected("Node/Paper motion comparison not source joined")
    n, p = (
        node.get("node_postclear_horizontal_deltas_m"),
        paper.get("post_release_deltas_m"),
    )
    if (
        type(n) is not list or len(n) != 5
        or type(p) is not list or len(p) != 4
        or any(type(x) not in (int, float) or not math.isfinite(x)
               or not 0 <= x <= 1.5 for x in n + p)
    ):
        raise NativePhysicsTraceRejected("invalid finite Node/Paper translation windows")

    # Coherent pairs must be both physically nontrivial and adjacent IN EACH
    # producer's own ordinal sequence. A single coincidence, 0==0,
    # shifting or cherry-picking disjoint rows cannot pass.
    candidates = []
    for ni in range(5):
        for pi in range(4):
            length = 0
            while (
                ni + length < 5 and pi + length < 4
                and n[ni + length] > 0.01
                and p[pi + length] > 0.01
                and math.isclose(
                    n[ni + length], p[pi + length],
                    rel_tol=0.0, abs_tol=1e-6,
                )
            ):
                length += 1
            if length >= 2:
                candidates.append((length, ni, pi))
    if not candidates:
        raise NativePhysicsTraceRejected(
            "no two adjacent nontrivial Node/Paper motion displacements match"
        )
    length, ni, pi = max(candidates, key=lambda t: (t[0], -t[1], -t[2]))
    return {
        "classification": "S49_NODE_PAPER_CONSECUTIVE_TRANSLATION_FOOTPRINT_DEV_ONLY",
        "action_id": action_id,
        "session_id": session_id,
        "matched_consecutive_nonzero_deltas": length,
        "node_relative_start_index": ni + 1,
        "paper_relative_start_index_excluding_mixed": pi + 1,
        "node_matched_deltas_m": n[ni:ni + length],
        "paper_matched_deltas_m": p[pi:pi + length],
        "matched_tolerance_m": 1e-6,
        "node_controls_held_off_throughout": True,
        "paper_dash_modifier_removed": True,
        "two_producer_local_motion_views_consistent": True,
        "native_Paper_tick_correspondence_attested": False,
        "independent_source_trust_attested": False,
        "physical_WAIT_qualified": False,
        "P1_posted": False,
        "M0_posted": False,
        "qualification_go": False,
        "science_go": False,
    }
