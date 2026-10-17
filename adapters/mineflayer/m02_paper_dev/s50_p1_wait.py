"""S-owned native Paper WAIT candidate source reader.

No source-authenticated full-tick WAIT or P1 fatigue recovery is conferred.
R must independently validate original action-free full-tick motor/combat
scope before a SourceBoundTick(WAIT) may be handed to the P1 Body evaluator.
"""
from __future__ import annotations

import math

from adapters.mineflayer.m02_paper_dev.s50_boundary import (
    BoundaryRejected,
    integer,
    number,
    pose,
    rows,
)


def candidate_wait_ticks(content: str, *, marker_id: str, expected_world: str,
                         source_action_terminal: str) -> dict:
    """Evaluate exactly eight consecutive native Paper snapshots after S50 OUTCOME.

    Tick snapshots are sampled at a plugin callback, not a whole-tick event
    census. Even all unchanged snapshots only establish a *candidate* idle
    interval. No caller may convert this result into P1 recovery directly.
    """
    if (not marker_id or not expected_world
            or source_action_terminal != "outcome"):
        raise BoundaryRejected("S50 WAIT candidate requires prior genuine OUTCOME")
    starts = rows(content, "S50_DEV_WAIT_BEGIN ")
    ticks = rows(content, "S50_DEV_WAIT_TICK ")
    if len(starts) != 1 or len(ticks) != 8:
        raise BoundaryRejected("missing/duplicate/partial native WAIT bracket")
    start = starts[0]
    if (start.get("marker_id") != marker_id or start.get("world") != expected_world):
        raise BoundaryRejected("foreign WAIT marker/World")
    begin_tick = integer(start, "tick")
    previous_pose = pose(start)
    previous_packet = integer(start, "packets")
    previous_blocks = number(start, "blocks")
    previous_tick_meter = number(start, "tick_meter_blocks")
    previous_combat = integer(start, "combat_events")
    previous_swings = integer(start, "swing_events")
    previous_basal = integer(start, "basal_ticks")
    candidates = []
    violations = []
    for i, row in enumerate(ticks, 1):
        tick = integer(row, "tick")
        if (row.get("marker_id") != marker_id
                or row.get("world") != expected_world
                or integer(row, "index") != i
                or tick != begin_tick + i
                or pose(row, "from_") != previous_pose):
            raise BoundaryRejected("foreign/gapped/changed native WAIT World tick")
        current = pose(row)
        counts = (
            integer(row, "motion_packets"),
            number(row, "motion_blocks"),
            number(row, "tick_meter_blocks"),
            integer(row, "combat_events"),
            integer(row, "swing_events"),
            integer(row, "basal_ticks"),
        )
        if (any(not math.isfinite(v) for v in current)
                or counts[0] < previous_packet
                or counts[1] < previous_blocks
                or counts[2] < previous_tick_meter
                or counts[3] < previous_combat
                or counts[4] < previous_swings
                or counts[5] != previous_basal + 1):
            raise BoundaryRejected("WAIT activity/BASAL counters incoherent")
        idle_in_snapshot = (
            current == previous_pose
            and counts[:5] == (
                previous_packet, previous_blocks, previous_tick_meter,
                previous_combat, previous_swings,
            )
            and row.get("sprint") == "false"
            and row.get("sneak") == "false"
            and row.get("swimming") == "false"
        )
        if not idle_in_snapshot:
            violations.append(tick)
        candidates.append({
            "world_tick": tick,
            "source": "PAPER_ONE_SAMPLER_PER_WORLD_TICK_DEV_ONLY",
            "observed_stationary": idle_in_snapshot,
            "basal_tick_counter": counts[5],
            "full_tick_activity_proven": False,
            "action_free_interval_independently_proven": False,
            "p1_wait_recovery_admitted": False,
        })
        previous_pose = current
        (previous_packet, previous_blocks, previous_tick_meter,
         previous_combat, previous_swings, previous_basal) = counts
    # Any activity in one tick invalidates the ALL-idle candidate; never
    # reclassify blocked MOVE or a fight event as a WAIT tick.
    return {
        "classification": "S_P1_WAIT_SOURCE_CANDIDATE_NOT_R_ATTESTED",
        "marker_id": marker_id,
        "world": expected_world,
        "first_world_tick": candidates[0]["world_tick"],
        "last_world_tick": candidates[-1]["world_tick"],
        "samples": candidates,
        "source_stationary_8_of_8": not violations,
        "source_activity_ticks": violations,
        "wait_ticks_admitted": 0,
        "p1_fatigue_recovered": 0.0,
        "r_full_tick_activity_witness": "NOT_ATTESTED",
        "r_action_free_interval_witness": "NOT_ATTESTED",
        "source_original_authenticated_by_r": False,
        "m02_basal_continues": True,
        "science_go": False,
    }
