"""S-owned extended P1 WAIT source *coverage* audit (no P1 recovery).

Paper exposes loaded chunks and native Bukkit event callbacks, but the log
is a per-tick sampler, not an exhaustive native packet/action lifecycle.
S cannot issue an authoritative P1 WAIT interval from this evidence.
"""
from __future__ import annotations

import hashlib
import re
import uuid

from adapters.mineflayer.m02_paper_dev.s50_boundary import (
    BoundaryRejected,
    integer,
    rows,
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
    entities = rows(original, "S50_DEV_WAIT_ENTITY ")
    if len(samples) != 8 or len(ticks) != 8:
        raise BoundaryRejected("missing/duplicate scope or WAIT snapshots")
    previous = None
    ambiguous = []
    other_online = []
    other_entities = []
    types = {}
    roster_digests = []
    cursor = 0
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
                or integer(r, "teleport_events") > integer(r, "movement_events")):
            raise BoundaryRejected("impossible loaded-chunk census")
        subject = r.get("subject_uuid")
        try:
            subject = str(uuid.UUID(subject))
        except (TypeError, ValueError) as exc:
            raise BoundaryRejected("no canonical native Self UUID") from exc
        observed = []
        seen = set()
        for entry_index in range(1, nums["loaded_entities"] + 1):
            if cursor >= len(entities):
                raise BoundaryRejected("truncated original roster")
            e = entities[cursor]
            cursor += 1
            if (e.get("marker_id") != marker or e.get("world") != world
                    or integer(e, "tick") != stamp
                    or integer(e, "index") != idx
                    or integer(e, "roster_index") != entry_index):
                raise BoundaryRejected("foreign or reordered native roster")
            try:
                identity = str(uuid.UUID(e.get("uuid", "")))
                entity_world = str(uuid.UUID(e.get("entity_world", "")))
                chunk_x = int(e["chunk_x"])
                chunk_z = int(e["chunk_z"])
            except (ValueError, KeyError, TypeError) as exc:
                raise BoundaryRejected("invalid native entity locator") from exc
            if (identity != e.get("uuid") or entity_world != e.get("entity_world")
                    or identity in seen
                    or re.fullmatch("[A-Z0-9_]{2,80}", e.get("type", "")) is None):
                raise BoundaryRejected("duplicate/noncanonical entity ID or type")
            seen.add(identity)
            value = f"{entity_world}:{chunk_x}:{chunk_z}:{identity}:{e['type']}"
            observed.append(value)
            if idx == 1:
                types[e["type"]] = types.get(e["type"], 0) + 1
        if (len(seen) != nums["loaded_entities"]
                or (subject in seen) is False
                or len(seen - {subject}) != nums["other_loaded_entities"]
                or observed != sorted(observed)):
            raise BoundaryRejected("native subject/other census or ordering mismatch")
        computed = hashlib.sha256(
            ("".join(value + "\\n" for value in observed)).encode("utf-8")
        ).hexdigest()
        if computed != digest:
            raise BoundaryRejected("native roster SHA disagrees with entity rows")
        roster_digests.append(computed)
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
    if cursor != len(entities):
        raise BoundaryRejected("extra or duplicated native roster originals")
    return {
        "classification": "S_P1_LOADED_CHUNK_CENSUS_AND_EVENTS_SAMPLE_ONLY",
        "first_world_tick": wait_first_tick,
        "last_world_tick": wait_last_tick,
        "source_scope_rows": len(samples),
        "source_entity_rows": len(entities),
        "first_sample_entity_types": types,
        "native_roster_digests": roster_digests,
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
