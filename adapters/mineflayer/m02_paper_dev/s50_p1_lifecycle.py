"""S-owned prospective Paper entity/chunk callback ledger reader.

This is a strictly callback-bounded DEV evidence screen. Even a complete
8-snapshot stream does not certify an entire World tick, unloaded entities,
held Mineflayer inputs, or absence of every issued/open Action.
"""
from __future__ import annotations

import uuid

from adapters.mineflayer.m02_paper_dev.s50_boundary import (
    BoundaryRejected,
    integer,
    rows,
)

PREFIX_BEGIN = "S50_DEV_WAIT_LIFECYCLE_BEGIN "
PREFIX_EVENT = "S50_DEV_WAIT_LIFECYCLE_EVENT "
PREFIX_SAMPLE = "S50_DEV_WAIT_LIFECYCLE_SAMPLE "
MAX_EVENTS = 256
ENTITY_KINDS = frozenset({"ENTITY_ADD", "ENTITY_REMOVE"})
CHUNK_KINDS = frozenset({"CHUNK_LOAD", "CHUNK_UNLOAD"})
BEGIN_FIELDS = frozenset({
    "marker_id", "world", "tick", "subject_uuid", "event_count", "coverage",
})
EVENT_FIELDS = frozenset({
    "marker_id", "world", "tick", "seq", "kind", "entity_world",
    "entity_tick", "uuid", "type", "chunk_x", "chunk_z", "coverage",
})
SAMPLE_FIELDS = frozenset({
    "marker_id", "world", "tick", "index", "event_count", "overflow",
    "async_seen", "coverage",
})


def _canonical(value: str | None) -> str:
    try:
        canonical = str(uuid.UUID(value))
    except (ValueError, TypeError, AttributeError) as exc:
        raise BoundaryRejected("invalid lifecycle World/entity UUID") from exc
    if value != canonical:
        raise BoundaryRejected("noncanonical lifecycle UUID")
    return canonical


def _signed_chunk(value: str | None) -> int:
    try:
        n = int(value)
    except (ValueError, TypeError) as exc:
        raise BoundaryRejected("invalid lifecycle chunk coordinate") from exc
    if str(n) != value or abs(n) > 30_000_000:
        raise BoundaryRejected("noncanonical/out-of-range chunk")
    return n


def review_lifecycle(
    original: str, *, marker: str, world: str,
    self_uuid: str, self_entity_world_uuid: str,
    wait_first_tick: int, wait_last_tick: int,
) -> dict:
    """Read original interleaving, not independently sorted event/snapshot lists."""
    if not marker or not world or wait_last_tick - wait_first_tick != 7:
        raise BoundaryRejected("invalid lifecycle WAIT source bracket")
    subject = _canonical(self_uuid)
    subject_world = _canonical(self_entity_world_uuid)
    start_tick = wait_first_tick - 1
    begun = False
    done = False
    sample_index = 0
    event_count = 0
    same_world_entity_ticks: list[int] = []
    same_world_chunk_ticks: list[int] = []
    other_world_event_ticks: list[int] = []
    last_source_tick = start_tick
    observed_event_worlds: set[str] = set()

    for line in original.splitlines():
        if PREFIX_BEGIN in line:
            row = rows(line, PREFIX_BEGIN)[0]
            if (begun or row.keys() != BEGIN_FIELDS
                    or row.get("marker_id") != marker
                    or row.get("world") != world
                    or _canonical(row.get("subject_uuid")) != subject
                    or integer(row, "tick") != start_tick
                    or integer(row, "event_count") != 0
                    or row.get("coverage") != "CALLBACK_PREFIX_TO_SAMPLE_ONLY"):
                raise BoundaryRejected("bad or duplicate native lifecycle begin")
            begun = True
            continue

        if PREFIX_EVENT in line:
            row = rows(line, PREFIX_EVENT)[0]
            if (not begun or done or row.keys() != EVENT_FIELDS
                    or row.get("marker_id") != marker
                    or row.get("world") != world
                    or row.get("coverage") != "PAPER_CALLBACK_ONLY"):
                raise BoundaryRejected("foreign/partial lifecycle event")
            event_count += 1
            if event_count > MAX_EVENTS or integer(row, "seq") != event_count:
                raise BoundaryRejected("missing/duplicate/unbounded lifecycle event")
            tick = integer(row, "tick")
            if (tick < start_tick or tick > wait_last_tick
                    or tick < last_source_tick):
                raise BoundaryRejected("out-of-bracket/regressed lifecycle World tick")
            last_source_tick = tick
            event_world = _canonical(row.get("entity_world"))
            observed_event_worlds.add(event_world)
            integer(row, "entity_tick")  # Independent dimension time source.
            _signed_chunk(row.get("chunk_x"))
            _signed_chunk(row.get("chunk_z"))
            kind = row.get("kind")
            if kind in ENTITY_KINDS:
                _canonical(row.get("uuid"))
                if row.get("type") in (None, "CHUNK", "NONE"):
                    raise BoundaryRejected("bad entity lifecycle type")
            elif kind in CHUNK_KINDS:
                if row.get("uuid") != "NONE" or row.get("type") != "CHUNK":
                    raise BoundaryRejected("bad chunk lifecycle identity")
            else:
                raise BoundaryRejected("unsupported lifecycle callback")
            if event_world != subject_world:
                other_world_event_ticks.append(tick)
            elif kind in ENTITY_KINDS and row["uuid"] != subject:
                same_world_entity_ticks.append(tick)
            elif kind in CHUNK_KINDS:
                same_world_chunk_ticks.append(tick)
            continue

        if PREFIX_SAMPLE in line:
            row = rows(line, PREFIX_SAMPLE)[0]
            sample_index += 1
            if (not begun or done or row.keys() != SAMPLE_FIELDS
                    or row.get("marker_id") != marker
                    or row.get("world") != world
                    or integer(row, "index") != sample_index
                    or integer(row, "tick") != start_tick + sample_index
                    or integer(row, "event_count") != event_count
                    or row.get("overflow") != "false"
                    or row.get("async_seen") != "false"
                    or row.get("coverage") != "CALLBACK_PREFIX_TO_SAMPLE_ONLY"
                    or sample_index > 8):
                raise BoundaryRejected("missing/forged lifecycle sampler or overflow")
            last_source_tick = start_tick + sample_index
            if sample_index == 8:
                done = True

    if not begun or not done or sample_index != 8:
        raise BoundaryRejected("incomplete prospective lifecycle source")
    return {
        "classification": "S_P1_PAPER_CALLBACK_PREFIX_SCREEN_ONLY",
        "first_world_tick": wait_first_tick,
        "last_world_tick": wait_last_tick,
        "event_count": event_count,
        "event_world_uuids": sorted(observed_event_worlds),
        "same_world_entity_lifecycle_ticks": same_world_entity_ticks,
        "same_world_chunk_change_ticks": same_world_chunk_ticks,
        "other_world_event_ticks": other_world_event_ticks,
        "prefix_callbacks_consistent": True,
        "whole_tick_entity_lifecycle": "NOT_ATTESTED",
        "unloaded_entity_coverage": "NOT_ATTESTED",
        "held_motor_control_absence": "NOT_ATTESTED",
        "action_free_interval": "NOT_ATTESTED",
        "independent_R_qualification": False,
        "wait_ticks_admitted": 0,
        "p1_fatigue_recovered": 0.0,
        "science_go": False,
    }
