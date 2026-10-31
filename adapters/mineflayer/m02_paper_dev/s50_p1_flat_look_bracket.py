"""DEV-only original-source screening of the Paper yaw / S50 FORWARD boundary.

No S Action authorization, P1 state transition or R qualification lives here.
The Paper yaw event belongs before PRE_FORWARD and is not a substitute for a
server-effective input-release tick or continuous whole-tick inactivity.
"""
from __future__ import annotations

import math
import re

from adapters.mineflayer.m02_paper_dev.s50_boundary import BoundaryRejected, phases
from adapters.mineflayer.m02_paper_dev.s50_p1_flat_look import (
    MAX_SNAPSHOTS,
    check_snapshot,
)

LOOK_LINE = "S_V8_DEV_SNAPSHOT "
SOURCE_SUFFIX = re.compile(r"-P1LOOK-(\d{2})")


def screen_paper_look_forward_bracket(
    original_console: str,
    *,
    marker: str,
    requested_yaw_rad: float,
    producer_look_witness: dict | None = None,
) -> dict:
    """Read the original snapshots and independently check the S50 phase gate.

    An admitted source in this method means merely that the source shape is
    internally consistent with a prospective look gate, not a P1 Body grant.
    """
    if (
        not isinstance(original_console, str)
        or not 1 <= len(marker) <= 108
        or re.fullmatch(r"[A-Za-z0-9_-]+", marker) is None
        or type(requested_yaw_rad) not in (float, int)
        or not math.isfinite(requested_yaw_rad)
    ):
        raise BoundaryRejected("invalid source marker/yaw request")
    lines = original_console.splitlines()
    look_lines: list[tuple[int, str]] = []
    for index, line in enumerate(lines):
        if LOOK_LINE not in line:
            continue
        fields = line.split(LOOK_LINE, 1)[1].split()
        first = fields[0] if fields else ""
        if not first.startswith("marker_id=" + marker + "-P1LOOK-"):
            continue
        suffix = first[len("marker_id=" + marker):]
        match = SOURCE_SUFFIX.fullmatch(suffix)
        if match is None:
            raise BoundaryRejected("bad Paper LOOK marker suffix")
        look_lines.append((index, line))
    if not 1 <= len(look_lines) <= MAX_SNAPSHOTS:
        raise BoundaryRejected("no bounded Paper yaw original snapshots")
    frame_rows = phases(original_console, marker)
    source_world = frame_rows[0]["world"]
    pre_forward_tick = int(frame_rows[0]["world_full_time"])
    phase_line_index = [
        i for i, line in enumerate(lines)
        if "M02_DEV_S50_PHASE " in line
        and "marker_id=" + marker + " " in line
        and "phase=PRE_FORWARD " in line
    ]
    if len(phase_line_index) != 1:
        raise BoundaryRejected("duplicate/missing original PRE_FORWARD source")
    phase_index = phase_line_index[0]
    previous_tick = None
    screens = []
    for n, (index, line) in enumerate(look_lines, 1):
        if index >= phase_index:
            raise BoundaryRejected("yaw snapshot emitted after PRE_FORWARD")
        parsed = check_snapshot(
            line, marker_id=f"{marker}-P1LOOK-{n:02d}",
            expected_yaw_rad=requested_yaw_rad, world=source_world,
            previous_tick=previous_tick,
        )
        if parsed["paper_full_time"] > pre_forward_tick:
            raise BoundaryRejected("PRE_FORWARD preceded Paper yaw snapshot time")
        if screens and screens[-1]["orientation_matches"]:
            raise BoundaryRejected("continued yaw polling after successful match")
        screens.append(parsed)
        previous_tick = parsed["paper_full_time"]
    last = screens[-1]
    if last["orientation_matches"] is not True:
        raise BoundaryRejected("original LOOK ACK never became Paper yaw match")
    if producer_look_witness is not None:
        if not isinstance(producer_look_witness, dict):
            raise BoundaryRejected("invalid producer Paper look witness")
        compare = (
            "classification", "marker_id", "world", "paper_full_time",
            "paper_yaw_degrees", "paper_pitch_degrees",
            "look_requested_yaw_degrees", "yaw_gap_degrees",
            "pitch_gap_degrees", "orientation_matches",
            "source_snapshots_checked",
        )
        retained = dict(last, source_snapshots_checked=len(screens))
        if any(producer_look_witness.get(k) != retained.get(k) for k in compare):
            raise BoundaryRejected("producer yaw witness differs from Paper original")
    return {
        "classification": "S_P1_FLAT_LOOK_PAPER_PHASE_SOURCE_SCREEN_DEV_ONLY",
        "marker": marker,
        "world": source_world,
        "paper_snapshots_before_forward": len(screens),
        "last_yaw_paper_world_tick": last["paper_full_time"],
        "pre_forward_paper_world_tick": pre_forward_tick,
        "last_real_paper_yaw_degrees": last["paper_yaw_degrees"],
        "look_request_yaw_degrees": last["look_requested_yaw_degrees"],
        "final_yaw_matches": True,
        "all_look_snapshots_precede_pre_forward": True,
        "look_ack_server_effective_tick": "NOT_ATTESTED",
        "forward_motor_action_receipt": "SEPARATE_S15_S16_SOURCE_REQUIRED",
        "P1_source_bound_move_ticks": 0,
        "P1_wait_ticks_admitted": 0,
        "P1_fatigue_recovered": 0.0,
        "P1_qualified": False,
        "science_go": False,
    }
