"""S-owned FLAT Paper tick-lineage screen for prospective P1 Body integration.

A Paper PlayerMoveEvent witness means MOVEMENT OBSERVED, not source admission
of a complete World tick. All gaps are UNKNOWN, never a free WAIT/recovery.
P1 owner physics stays on its independent branch. This module never imports
P1, issues SourceBoundTick or advances an authoritative body state.
"""
from __future__ import annotations

import math

from adapters.mineflayer.m02_paper_dev.s50_boundary import BoundaryRejected

MAX_TICK_SPAN = 2400
MAX_MOVE_EVENTS = 300
P1_DRAFT_MOVE_RATE = 0.04


def _bounded_number(value: object, *, maximum: float) -> float:
    if (type(value) not in (int, float) or not math.isfinite(value)
            or value < 0 or value > maximum):
        raise BoundaryRejected("invalid bounded original-native quantity")
    return float(value)


def movement_tick_ledger(screen: dict) -> dict:
    """Preserve original World tick sequence and unknown intervals faithfully.

    Input is the output of screen_motion after SHA/readback, *not* arbitrary
    unverified caller data. Validate anyway so a mutated readback fails shut.
    """
    if (not isinstance(screen, dict)
            or screen.get("classification")
            != "S_FLAT_P1_MOTION_SOURCE_CANDIDATE_DEV_ONLY"
            or screen.get("flat_world_seed") != 63101
            or screen.get("P1_state_advanced") is not False
            or screen.get("move_SourceBoundTick_issued") is not False
            or screen.get("wait_SourceBoundTick_issued") is not False
            or screen.get("p1_wait_ticks_admitted") != 0
            or screen.get("p1_fatigue_recovered") != 0.0
            or screen.get("R_independent_review") != "PENDING"):
        raise BoundaryRejected("foreign/admitted P1 or non-FLAT source")
    world = screen.get("world")
    arm = screen.get("arm")
    if (not isinstance(world, str) or not world
            or arm not in ("BASE_ON", "SHAM_ON", "BASAL_ZERO",
                           "WALK_ZERO", "BOTH_ZERO")):
        raise BoundaryRejected("missing original World or arm")
    start = screen.get("start_full_time")
    end = screen.get("terminal_full_time")
    if (type(start) is not int or type(end) is not int
            or end <= start or end - start > MAX_TICK_SPAN):
        raise BoundaryRejected("impossible World tick duration")
    groups = screen.get("tick_event_groups")
    if (not isinstance(groups, list)
            or not groups or len(groups) > MAX_MOVE_EVENTS):
        raise BoundaryRejected("missing/oversized Paper motion groups")
    if screen.get("native_moving_tick_count") != len(groups):
        raise BoundaryRejected("native moving tick count drift")
    native_count = screen.get("native_motion_events")
    if type(native_count) is not int or not 1 <= native_count <= MAX_MOVE_EVENTS:
        raise BoundaryRejected("invalid original motion event count")
    by_tick = {}
    blocks_total = 0.0
    event_count = 0
    prior = start
    for group in groups:
        if not isinstance(group, dict):
            raise BoundaryRejected("malformed Paper event group")
        tick = group.get("world_full_time")
        count = group.get("event_count")
        if (type(tick) is not int or tick < start or tick > end
                or tick <= prior or type(count) is not int or count < 1):
            raise BoundaryRejected("duplicate/regressed/out-of-World motion group")
        blocks = _bounded_number(group.get("event_blocks"), maximum=float(count))
        if blocks <= 0:
            raise BoundaryRejected("nonpositive native MOVE evidence")
        by_tick[tick] = (count, blocks)
        event_count += count
        blocks_total += blocks
        prior = tick
    if event_count != native_count or not math.isclose(
        blocks_total,
        _bounded_number(screen.get("native_observed_horizontal_blocks"),
                        maximum=float(MAX_MOVE_EVENTS)),
        rel_tol=1e-8, abs_tol=1e-8,
    ):
        raise BoundaryRejected("source motion event aggregates changed")
    # No idle classification is possible from absence of motion events.
    unknown = 0
    moving = 0
    timeline = []
    for tick in range(start + 1, end + 1):
        if tick in by_tick:
            count, blocks = by_tick[tick]
            moving += 1
            timeline.append({
                "world_full_time": tick,
                "activity": "MOVE_EVENT_OBSERVED_NOT_FULL_TICK_ADMITTED",
                "event_count": count,
                "native_horizontal_blocks": blocks,
                "P1_hypothetical_gain_not_admitted": blocks * P1_DRAFT_MOVE_RATE,
                "P1_frame_issued": False,
            })
        else:
            unknown += 1
            timeline.append({
                "world_full_time": tick,
                "activity": "UNKNOWN_NOT_WAIT",
                "event_count": 0,
                "native_horizontal_blocks": None,
                "P1_hypothetical_gain_not_admitted": None,
                "P1_frame_issued": False,
            })
    # Motion on the INITIAL snapshot tick cannot be assigned to a following
    # tick. Such source is rejected rather than disappearing from the ledger.
    if start in by_tick:
        raise BoundaryRejected("native movement belongs to initial boundary tick")
    return {
        "classification": "S_FLAT_P1_WORLD_TICK_LINEAGE_CANDIDATE_DEV_ONLY",
        "world": world,
        "arm": arm,
        "start_full_time": start,
        "terminal_full_time": end,
        "move_observed_ticks": moving,
        "unclassified_ticks": unknown,
        "native_motion_events": native_count,
        "native_observed_horizontal_blocks": blocks_total,
        "P1_hypothetical_total_move_gain_unadmitted": (
            blocks_total * P1_DRAFT_MOVE_RATE
        ),
        "ticks": timeline,
        "full_tick_motor_coverage": "NOT_ATTESTED",
        "all_S15_S16_issuers_absent_for_unknown": "NOT_ATTESTED",
        "R_independent_source_admission": "NOT_ATTESTED",
        "P1_state_advanced": False,
        "SourceBoundTick_MOVE_issued": 0,
        "SourceBoundTick_WAIT_issued": 0,
        "P1_wait_recovery": 0.0,
        "science_trials": 0,
        "production_go": False,
    }


def contiguous_motion_windows(ledger: dict) -> list[dict]:
    """Independent MOVE-only runs; UNKNOWN explicitly breaks P1 continuity."""
    if (not isinstance(ledger, dict)
            or ledger.get("classification")
            != "S_FLAT_P1_WORLD_TICK_LINEAGE_CANDIDATE_DEV_ONLY"
            or ledger.get("P1_state_advanced") is not False
            or ledger.get("SourceBoundTick_WAIT_issued") != 0
            or ledger.get("P1_wait_recovery") != 0.0
            or ledger.get("R_independent_source_admission") != "NOT_ATTESTED"):
        raise BoundaryRejected("forged P1 lineage")
    ticks = ledger.get("ticks")
    if (not isinstance(ticks, list) or not ticks
            or len(ticks) != ledger["terminal_full_time"] - ledger["start_full_time"]):
        raise BoundaryRejected("truncated source timeline")
    windows = []
    current = []
    for i, row in enumerate(ticks, 1):
        if (not isinstance(row, dict)
                or row.get("world_full_time") != ledger["start_full_time"] + i
                or row.get("P1_frame_issued") is not False):
            raise BoundaryRejected("foreign or reordered World tick")
        activity = row.get("activity")
        if activity == "UNKNOWN_NOT_WAIT":
            if (row.get("event_count") != 0
                    or row.get("native_horizontal_blocks") is not None
                    or row.get("P1_hypothetical_gain_not_admitted") is not None):
                raise BoundaryRejected("free WAIT/zero displacement smuggled")
            if current:
                windows.append(current)
                current = []
        elif activity == "MOVE_EVENT_OBSERVED_NOT_FULL_TICK_ADMITTED":
            if (type(row.get("event_count")) is not int
                    or row["event_count"] < 1
                    or _bounded_number(row.get("native_horizontal_blocks"),
                                       maximum=float(row["event_count"])) <= 0):
                raise BoundaryRejected("invalid positive MOVE witness")
            expected = row["native_horizontal_blocks"] * P1_DRAFT_MOVE_RATE
            if not math.isclose(row["P1_hypothetical_gain_not_admitted"], expected,
                                rel_tol=1e-8, abs_tol=1e-8):
                raise BoundaryRejected("candidate P1 motion cost mutated")
            current.append(row)
        else:
            raise BoundaryRejected("unexpected implicit WAIT/FIGHT label")
    if current:
        windows.append(current)
    if sum(len(w) for w in windows) != ledger["move_observed_ticks"]:
        raise BoundaryRejected("lost positive motion witness")
    return [{
        "first_world_tick": window[0]["world_full_time"],
        "last_world_tick": window[-1]["world_full_time"],
        "consecutive_positive_motion_ticks": len(window),
        "native_horizontal_blocks": sum(x["native_horizontal_blocks"]
                                        for x in window),
        "P1_hypothetical_gain_unadmitted": sum(
            x["P1_hypothetical_gain_not_admitted"] for x in window
        ),
        "cross_unknown_gap_state_continuation_allowed": False,
    } for window in windows]
