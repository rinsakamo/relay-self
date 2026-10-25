"""Read-only DEV comparison of three non-equivalent clocks.

Node hrtime records control changes and Mineflayer physicsTick callbacks.
Paper existing one-shot observer records eight later server WAIT tick numbers.
Neither is a certified server-effective control duration. No clock is mapped
to another by invented offsets or cross-runtime wall-time equality.
"""
from __future__ import annotations

import json
import math
import re
from pathlib import Path

from adapters.mineflayer.m02_paper_dev.s50_boundary import BoundaryRejected

SCHEMA = "DEV_MOTOR_CLOCK_V0"
KINDS = {"back_on", "physics_tick", "back_off"}
PAPER_WAIT_RE = re.compile(
    r"S49_DEV_BACK_WAIT_TICK .*?action_id=([A-Za-z0-9_.:-]+)"
    r" .*?session_id=([A-Za-z0-9_.:-]+).*?tick=([0-9]+) index=([0-9]+)"
)


def review_native_motor_clock_dev(
    native_log: Path, paper_log: Path, source: dict,
    feedback: dict,
) -> dict[str, object]:
    if (not isinstance(source, dict) or source.get("status") != "PASS"
            or source.get("node_exit") != 0 or source.get("server_exit") != 0
            or not isinstance(feedback, dict)
            or feedback.get("status") != "DEV_REAL_S49_SELF_BODY_MOTION_CLOSED_LOOP"
            or not native_log.is_file() or not paper_log.is_file()):
        raise BoundaryRejected("original S49 and clock files must be complete")
    original = source.get("actual_native_actions")
    if (not isinstance(original, list) or len(original) != 4
            or any(a.get("terminal") != "outcome" for a in original)):
        raise BoundaryRejected("four original native S16 Actions required")
    ids = [a["action"] for a in original]
    raw = native_log.read_text("utf-8")
    if not raw or len(raw.encode()) > 100000 or len(raw.splitlines()) > 120:
        raise BoundaryRejected("bounded Node read-only clock artifact required")
    rows = [json.loads(line) for line in raw.splitlines()]
    if not rows:
        raise BoundaryRejected("no native clock source")
    for index, row in enumerate(rows):
        if (not isinstance(row, dict)
                or set(row) != {
                    "schema", "kind", "action_id", "index", "node_monotonic_ns",
                    "mineflayer_physics_tick_counter", "mineflayer_position_xz",
                    "paper_world_tick_attested", "new_action_issuer",
                }
                or row["schema"] != SCHEMA or row["kind"] not in KINDS
                or row["action_id"] not in ids
                or row["index"] != index
                or type(row["mineflayer_physics_tick_counter"]) is not int
                or row["mineflayer_physics_tick_counter"] < 0
                or type(row["node_monotonic_ns"]) is not str
                or not re.fullmatch(r"[1-9][0-9]*", row["node_monotonic_ns"])
                or row["paper_world_tick_attested"] is not False
                or row["new_action_issuer"] is not False
                or not isinstance(row["mineflayer_position_xz"], dict)
                or set(row["mineflayer_position_xz"]) != {"x", "z"}
                or any(type(v) not in (int, float) or not math.isfinite(v)
                       for v in row["mineflayer_position_xz"].values())):
            raise BoundaryRejected("invalid Node observational frame")
    if any(
        int(a["node_monotonic_ns"]) >= int(b["node_monotonic_ns"])
        or a["mineflayer_physics_tick_counter"] > b[
            "mineflayer_physics_tick_counter"
        ]
        for a, b in zip(rows, rows[1:])
    ):
        raise BoundaryRejected("Node local chronology reversed")
    summary = []
    for action in original:
        aid = action["action"]
        frames = [r for r in rows if r["action_id"] == aid]
        on = [r for r in frames if r["kind"] == "back_on"]
        off = [r for r in frames if r["kind"] == "back_off"]
        ticks = [r for r in frames if r["kind"] == "physics_tick"]
        if (len(on) != 1 or len(off) != 1
                or frames[0] is not on[0] or frames[-1] is not off[0]
                or any(r["kind"] != "physics_tick" for r in frames[1:-1])
                or len(ticks) > 20):
            raise BoundaryRejected("only one bounded on/ticks/off per issued action")
        active_ns = int(off[0]["node_monotonic_ns"]) - int(on[0]["node_monotonic_ns"])
        if active_ns <= 0:
            raise BoundaryRejected("Node local active interval invalid")
        observed = action["movement_m"]
        if type(observed) is not float or not math.isfinite(observed) or observed < 0.05:
            raise BoundaryRejected("original S16 physical displacement invalid")
        summary.append({
            "action_id": aid,
            "node_control_active_monotonic_ms": active_ns / 1e6,
            "node_physics_tick_callbacks_while_back_active": len(ticks),
            "node_physics_tick_counter_difference":
                off[0]["mineflayer_physics_tick_counter"]
                - on[0]["mineflayer_physics_tick_counter"],
            "observed_original_s16_displacement_m": observed,
            "on_node_tick": on[0]["mineflayer_physics_tick_counter"],
            "off_node_tick": off[0]["mineflayer_physics_tick_counter"],
            "realized_server_effective_control_ticks_attested": False,
        })
    lines = paper_log.read_text("utf-8")
    if len(lines) > 2_000_000:
        raise BoundaryRejected("Paper console log unbounded")
    wait = [m.groups() for m in PAPER_WAIT_RE.finditer(lines)]
    if (len(wait) != 8 or len({i[0] for i in wait}) != 1
            or len({i[1] for i in wait}) != 1
            or wait[0][1] != source["session_id"]
            or wait[0][0] != ids[1]
            or [int(i[3]) for i in wait] != list(range(1, 9))
            or any(int(b[2]) != int(a[2]) + 1
                   for a, b in zip(wait, wait[1:]))):
        raise BoundaryRejected("existing Paper eight-tick WAIT window changed")
    return {
        "status": "DEV_S49_THREE_CLOCKS_OBSERVED",
        "original_session_id": source["session_id"],
        "source_action_count": 4,
        "node_actions": summary,
        "paper_after_second_action_wait_tick_first": int(wait[0][2]),
        "paper_after_second_action_wait_tick_last": int(wait[-1][2]),
        "paper_wait_tick_samples": 8,
        "paper_wait_source_action_id": ids[1],
        "node_monotonic_ns_clock_domain": "NODE_HRTIME_LOCAL_MONOTONIC",
        "mineflayer_tick_domain": "CLIENT_PHYSICS_CALLBACK_COUNTER",
        "paper_tick_domain": "WORLD_FULL_TIME_POST_ACTION_WAIT",
        "paper_control_on_off_tick_observed": False,
        "paper_effective_move_tick_count_attested": False,
        "cross_domain_clock_alignment_attested": False,
        "s49_transport_owner_changed": False,
        "native_fatigue_measured": False,
        "new_action_issuer": False,
        "qualification_go": False,
        "science_go": False,
    }
