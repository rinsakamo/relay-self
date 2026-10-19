"""W4-WIN: read-only, content-correlated World placement-window candidate.

This module NEVER sends server commands or reads from Mineflayer. It defines
an opt-in experimenter handshake which MUST later be implemented under the
existing server-stdout collector and sole original native-reader owner.

A matching Minecraft console text line or caller-supplied clock is NOT a
cryptographic witness, independent custody or proof of Node emitter
completeness. No resulting receipt is physical execution permission.
"""
from __future__ import annotations

import hashlib
import math
import re
from dataclasses import asdict, dataclass

from adapters.mineflayer.python_protocol import (
    MineflayerObservation,
    MineflayerOrientedSnapshot,
)
from adapters.mineflayer.self_world_stage_w4_preflight import (
    W4OfflinePlacement,
    W4PreworldBlocked,
    plan_native_nh1_placement,
)

_TOKEN = re.compile(r"[a-z0-9]{24,48}\Z")


@dataclass(frozen=True, slots=True)
class W4PlacementCommands:
    """World-experimenter-only commands; no avatar controls or Action grants."""

    session_id: str
    slot: int
    source_reference: str
    marker_tag: str
    confirmation_marker: str
    summon_command: str
    confirm_command: str
    expected_log_suffix: str
    summon_sha256: str
    confirm_sha256: str
    physical_run_permitted: bool = False


@dataclass(frozen=True, slots=True)
class W4WindowEvent:
    """Caller-reported single-coordinator order; synthetic/untrusted until qualified."""

    name: str
    order: int
    monotonic_ns: int
    source: str
    content: str
    server_pid: int | None = None


_EVENTS = (
    "native_before_probe",
    "server_summon_write",
    "server_summon_drain",
    "server_confirm_write",
    "server_confirm_drain",
    "server_stdout_marker",
    "native_after_probe",
)


def build_w4_window_commands(
    placement: W4OfflinePlacement, *, one_time_token: str,
) -> W4PlacementCommands:
    """Prepare conditional *tagged* summon and server-console readiness marker.

    Token is a caller-registered unique per-run/slot value, not an authority.
    The marker is emitted by the server only if the tagged zombie exists.
    The native after-probe must independently see exactly the planned zombie
    position. A marker alone never attests the native entity identity.
    """
    if (
        type(placement) is not W4OfflinePlacement
        or placement.slot not in (1, 2)
        or placement.physical_run_permitted
        or placement.source_orientation_qualified is not True
        or not placement.source_probe_request_id
        or not placement.source_reference
        or type(one_time_token) is not str
        or not _TOKEN.fullmatch(one_time_token)
    ):
        raise W4PreworldBlocked("W4-WIN requires typed near-slot plan and safe token")
    base = placement.command
    if not base.startswith("summon minecraft:zombie ") or not base.endswith(
        "{NoAI:1b,Silent:1b,PersistenceRequired:1b,Invulnerable:1b}"
    ):
        raise W4PreworldBlocked("unrecognized preregistered World summon template")
    tag = f"w4nh1_{one_time_token}_s{placement.slot}"
    marker = f"W4NH1_READY_{one_time_token.upper()}_S{placement.slot}"
    # The NBT is amended ONLY for a distinct prospective DEV experimenter
    # command. The entity type, coordinates and original properties are fixed.
    summon = base[:-1] + f',Tags:["{tag}"]' + "}"
    confirm = (
        "execute if entity "
        f"@e[type=minecraft:zombie,tag={tag},limit=1] "
        f"run say {marker}"
    )
    return W4PlacementCommands(
        session_id=placement.session_id, slot=placement.slot,
        source_reference=placement.source_reference,
        marker_tag=tag, confirmation_marker=marker,
        summon_command=summon, confirm_command=confirm,
        expected_log_suffix=f"[Server] {marker}",
        summon_sha256=hashlib.sha256((summon + "\n").encode()).hexdigest(),
        confirm_sha256=hashlib.sha256((confirm + "\n").encode()).hexdigest(),
    )


def reconcile_w4_window_offline(
    before: MineflayerObservation,
    after: MineflayerObservation,
    *,
    expected_session: str,
    before_request_id: str,
    after_request_id: str,
    minimum_seq: int,
    slot: int,
    one_time_token: str,
    events: tuple[W4WindowEvent, ...],
) -> dict:
    """Correlate producer-content only; preserve independent physical NO_GO.

    Events must be recorded by a future *single* experimenter sequencer.
    Clock/order fields and stdout content can all be forged by that producer.
    Thus this checks internal causal ordering, NOT original World authority.
    """
    if (
        type(after) is not MineflayerObservation
        or after.session_id != expected_session
        or after.kind != "probe"
        or not after_request_id
        or after_request_id == before_request_id
        or after.request_id != after_request_id
        or not isinstance(after.snapshot, MineflayerOrientedSnapshot)
        or after.snapshot.nearby_entities_coverage.truncated
        or after.snapshot.nearby_entities_coverage.source_scope != "mineflayer_entity_registry"
        or len(events) != len(_EVENTS)
        or not isinstance(events, tuple)
    ):
        raise W4PreworldBlocked("after probe or event cardinality invalid")
    plan = plan_native_nh1_placement(
        before, expected_session=expected_session,
        expected_request_id=before_request_id, before_seq=after.seq, slot=slot,
    )
    if before.seq < minimum_seq or type(minimum_seq) is not int or minimum_seq < 0:
        raise W4PreworldBlocked("preplacement source older than owner cursor")
    if after.seq <= before.seq:
        raise W4PreworldBlocked("postplacement probe is not newer")
    commands = build_w4_window_commands(plan, one_time_token=one_time_token)
    if any(type(e) is not W4WindowEvent for e in events):
        raise W4PreworldBlocked("invalid step receipt type")
    if tuple(e.name for e in events) != _EVENTS:
        raise W4PreworldBlocked("staging sequence not complete/in order")
    if any(
        type(e.order) is not int or type(e.monotonic_ns) is not int
        or e.order < 0 or e.monotonic_ns < 0
        for e in events
    ) or any(
        a.order >= b.order or a.monotonic_ns >= b.monotonic_ns
        for a, b in zip(events, events[1:])
    ):
        raise W4PreworldBlocked("staging timestamp/order reversed or repeated")
    if (
        events[0].source != "sole_native_reader"
        or events[0].content != before.provenance.reference
        or events[-1].source != "sole_native_reader"
        or events[-1].content != after.provenance.reference
    ):
        raise W4PreworldBlocked("native read did not use the original reader")
    server_steps = events[1:-1]
    if (
        any(e.source != "existing_server_console_collector" for e in server_steps)
        or any(type(e.server_pid) is not int or e.server_pid <= 0
               for e in server_steps)
        or len({e.server_pid for e in server_steps}) != 1
        or server_steps[0].content != commands.summon_sha256
        or server_steps[1].content != commands.summon_sha256
        or server_steps[2].content != commands.confirm_sha256
        or server_steps[3].content != commands.confirm_sha256
    ):
        raise W4PreworldBlocked("server identity/command bytes do not bind")
    # A server log response must be a console output record, not the command
    # echoed as input. The marker is conditional on a tagged entity existing.
    marker_line = server_steps[4].content
    if (
        not isinstance(marker_line, str)
        or "\n" in marker_line or "\r" in marker_line
        or not marker_line.endswith(commands.expected_log_suffix)
        or "]: " not in marker_line
    ):
        raise W4PreworldBlocked("server marker absent/ambiguous/not console output")
    before_ids = {
        e.entity_id for e in before.snapshot.nearby_entities
        if e.name == "zombie"
    }
    targets = [
        e for e in after.snapshot.nearby_entities if e.name == "zombie"
    ]
    if (
        before.snapshot.nearby_entities_coverage.truncated
        or len(targets) != 1
        or targets[0].entity_id in before_ids
        or not all(math.isclose(
            getattr(targets[0].position, axis), getattr(plan.spawn, axis),
            rel_tol=0, abs_tol=1e-6,
        ) for axis in ("x", "y", "z"))
    ):
        raise W4PreworldBlocked("fresh unique native zombie at planned XYZ not established")
    return {
        "schema": "W4_WIN_DEV_SOURCE_CONTENT_V0",
        "prereg_id": plan.prereg_id,
        "slot": slot,
        "session_id": expected_session,
        "before_source": before.provenance.reference,
        "after_source": after.provenance.reference,
        "before_request_id": before_request_id,
        "after_request_id": after_request_id,
        "world_commands": asdict(commands),
        "observed_zombie_id": targets[0].entity_id,
        "observed_xyz": asdict(targets[0].position),
        "events": [asdict(e) for e in events],
        "placement_window": "DEV_PRODUCER_CONTENT_CORRELATED_ONLY",
        "command_dispatch_attested": False,
        "server_log_independently_attested": False,
        "sole_reader_independently_attested": False,
        "external_archivist_qualified": False,
        "physical_run_permitted": False,
        "s10_permission": False,
        "science_qualified": False,
    }
