"""S-owned extended P1 WAIT source *coverage* audit (no P1 recovery).

Paper exposes loaded chunks and native Bukkit event callbacks, but the log
is a per-tick sampler, not an exhaustive native packet/action lifecycle.
S cannot issue an authoritative P1 WAIT interval from this evidence.
"""
from __future__ import annotations

import re

from adapters.mineflayer.m02_paper_dev.s50_boundary import (
    BoundaryRejected, integer, rows,
)

COUNTERS = (
    "movement_events", "teleport_events", "velocity_events",
    "damage_events", "interact_events", "combat_events", "swing_events",
)
BOUNDS = {"loaded_worlds": 16, "loaded_chunks": 4096,
          "loaded_entities": 32768, "other_loaded_entities": 32768,
          "other_online_players": 2048}


def review_scope(original: str, *, marker: str, world: str,
                 wait_first_tick: int, wait_last_tick: int,
                 original_outcome: str) -> dict:
    if original_outcome != "outcome" or not marker or not world:
        raise BoundaryRejected("S50 WAIT scope needs true terminal OUTCOME")
    if wait_last_tick - wait_first_tick != 7 or wait_first_tick < 1:
        raise BoundaryRejected("not an eight-tick source candidate")
    samples = rows(original, "S50_DEV_WAIT_SCOPE ")
    ticks = rows(original, "S50_DEV_WAIT_TICK ")
    if len(samples) != 8 or len(ticks) != 8:
        raise BoundaryRejected("missing/duplicate scope or WAIT snapshots")
    previous = None
    ambiguous = []
    other_online = []
    other_entities = []
    for idx, (r, t) in enumerate(zip(samples, ticks), 1):
        stamp = wait_first_tick + idx - 1
        if (r.get("marker_id") != marker or r.get("world") != world
                or r.get("coverage") != "LOADED_CHUNK_SAMPLER_ONLY"
                or r.get("client_held_controls") != "NOT_OBSERVED"
                or r.get("entity_lifecycle") != "NOT_ATTESTED"
                or integer(r, "index") != idx or integer(r, "tick") != stamp
                or t.get("marker_id") != marker or t.get("world") != world
                or integer(t, "index") != idx or integer(t, "tick") != stamp):
            raise BoundaryRejected("unbound native loaded-chunk sample")
        digest = r.get("census_sha256", "")
        if re.fullmatch("[0-9a-f]{64}", digest) is None:
            raise BoundaryRejected("missing native census SHA256")
        nums = {key: integer(r, key) for key in BOUNDS}
        if (any(nums[key] > maximum for key, maximum in BOUNDS.items())
                or nums["loaded_worlds"] < 1 or nums["loaded_chunks"] < 1
                or nums["other_loaded_entities"] > nums["loaded_entities"]
                or nums["other_online_players"] > nums["loaded_entities"]
                or nums["teleport_events"] > integer(r, "movement_events")):
            raise BoundaryRejected("impossible loaded-chunk census")
        counts = tuple(integer(r, name) for name in COUNTERS)
        if (integer(r, "combat_events") != integer(t, "combat_events")
                or integer(r, "swing_events") != integer(t, "swing_events")):
            raise BoundaryRejected("activity callbacks do not match tick row")
        if previous is not None and any(a < b for a, b in zip(counts, previous)):
            raise BoundaryRejected("counter regressed in native scope")
        if previous is not None and counts != previous:
            ambiguous.append(stamp)
        if nums["other_online_players"] > 0:
            other_online.append(stamp)
        if nums["other_loaded_entities"] > 0:
            other_entities.append(stamp)
        previous = counts
    return {
        "classification": "S_P1_LOADED_CHUNK_CENSUS_AND_EVENTS_SAMPLE_ONLY",
        "first_world_tick": wait_first_tick,
        "last_world_tick": wait_last_tick,
        "source_scope_rows": len(samples),
        "activity_counter_changed_after_first_sampler": ambiguous,
        "other_online_players_seen_ticks": other_online,
        "other_loaded_entities_seen_ticks": other_entities,
        "scope": "ALL_CURRENTLY_LOADED_CHUNKS_PER_SAMPLER",
        "unloaded_entity_lifecycle": "NOT_ATTESTED",
        "held_motor_control_absence": "NOT_ATTESTED",
        "whole_tick_all_activity_absence": "NOT_ATTESTED",
        "independent_R_qualification": False,
        "wait_ticks_admitted": 0,
        "p1_fatigue_recovered": 0.0,
        "science_go": False,
    }
