"""S50-owned DEV physical observation -> SelfBody *candidate* source handoff.

This module does NOT create relay_self.self_body.BodyObservation. That type
requires a separately admitted native Present/provenance. S50's Paper tick
samples, Mineflayer local-control receipts and outbound packet write-returns
are different clocks and different evidence classes. None grants Action,
Goal, P1 WAIT, learning, or certified physical rest.
"""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from typing import Mapping

from adapters.mineflayer.m02_paper_dev.s50_client_packet_source import (
    inspect_s50_client_packets,
)
from adapters.mineflayer.m02_paper_dev.s50_input_witness_source import (
    review_s50_input_samples,
)

WAIT_PREFIX = "S50_DEV_WAIT_TICK "
BODY_SOURCE_SCHEMA = "S50_SELFBODY_MOTION_DIAGNOSTIC_V0"
_MAX_PAPER_BYTES = 2_000_000
_MAX_NODE_BYTES = 4_000_000


class S50BodyMotionSourceRejected(ValueError):
    """Cross-run, incomplete, or overpromoted physical diagnostic source."""


@dataclass(frozen=True, slots=True)
class S50PaperMotionSample:
    world_tick: int
    displacement_m: float
    last_reported_input_active: bool
    source_scope: str = "PAPER_CALLBACK_SAMPLE_ONLY"


@dataclass(frozen=True, slots=True)
class S50ControlEffectSample:
    effect: str
    node_record_index: int
    local_controls_active: bool
    source_scope: str = "CLIENT_LOCAL_CONTROL_SNAPSHOT_ONLY"


@dataclass(frozen=True, slots=True)
class S50SelfBodyMotionSource:
    session_id: str
    action_id: str
    marker_id: str
    paper_world_uuid: str
    subject_uuid: str
    paper_original_sha256: str
    client_original_sha256: str
    paper_samples: tuple[S50PaperMotionSample, ...]
    client_effects: tuple[S50ControlEffectSample, ...]
    observed_motion_while_reported_input_off_ticks: tuple[int, ...]
    client_player_input_write_returns: int
    client_position_write_returns: int
    paper_player_input_callbacks: int
    client_packet_diagnostic: str
    schema: str = BODY_SOURCE_SCHEMA
    provenance_ceiling: str = "DIAGNOSTIC_ONLY_NOT_NATIVE_PRESENT"
    cross_clock_alignment: str = "NOT_ATTESTED"
    effective_s15_clear_world_tick: str = "NOT_ATTESTED"
    full_tick_input_coverage: bool = False
    physically_stopped_attested: bool = False
    goal_admitted: bool = False
    p1_wait_ticks_admitted: int = 0
    l10_pairs_admitted: int = 0
    s10_updates_admitted: int = 0
    s11_grants_admitted: int = 0


def _fields(line: str, prefix: str) -> dict[str, str]:
    if line.count(prefix) != 1:
        raise S50BodyMotionSourceRejected("ambiguous Paper source label")
    parts: dict[str, str] = {}
    for token in line.split(prefix, 1)[1].split():
        if token.count("=") != 1:
            raise S50BodyMotionSourceRejected("malformed Paper source field")
        name, value = token.split("=", 1)
        if not name or not value or name in parts:
            raise S50BodyMotionSourceRejected("duplicate/empty Paper field")
        parts[name] = value
    return parts


def _num(row: Mapping[str, str], key: str) -> float:
    raw = row.get(key, "")
    if not 0 < len(raw) <= 40:
        raise S50BodyMotionSourceRejected("missing or unbounded Paper coordinate")
    try:
        v = float(raw)
    except ValueError as exc:
        raise S50BodyMotionSourceRejected("invalid Paper coordinate") from exc
    if not math.isfinite(v):
        raise S50BodyMotionSourceRejected("nonfinite Paper coordinate")
    return v


def _natural(row: Mapping[str, str], key: str) -> int:
    raw = row.get(key, "")
    if not 0 < len(raw) <= 18 or not raw.isascii() or not raw.isdecimal():
        raise S50BodyMotionSourceRejected("invalid Paper tick/index")
    return int(raw)


def _client_controls(original: bytes, session: str) -> tuple[S50ControlEffectSample, ...]:
    records = [json.loads(line) for line in original.decode("utf-8").splitlines()]
    effects = []
    allowed = {"set_control", "clear_controls", "shutdown_clear_controls"}
    for row in records[:-1]:
        if row.get("kind") != "NATIVE_CONTROL_EFFECT_RETURNED":
            continue
        flags = row.get("controls_after_sample")
        if (
            row.get("session_id") != session
            or row.get("effect") not in allowed
            or not isinstance(flags, dict)
            or set(flags) != {"forward", "back", "left", "right",
                             "jump", "sneak", "sprint"}
            or any(type(v) is not bool for v in flags.values())
            or type(row.get("index")) is not int
        ):
            raise S50BodyMotionSourceRejected("unqualified client local control")
        if row["effect"] in {"clear_controls", "shutdown_clear_controls"} and any(
            flags.values()
        ):
            raise S50BodyMotionSourceRejected("clear did not sample all controls off")
        effects.append(S50ControlEffectSample(
            effect=row["effect"],
            node_record_index=row["index"],
            local_controls_active=any(flags.values()),
        ))
    if not effects or not any(e.effect == "clear_controls" for e in effects):
        raise S50BodyMotionSourceRejected("missing client clear-control sample")
    if len(effects) > 8 or any(
        a.node_record_index >= b.node_record_index
        for a, b in zip(effects, effects[1:])
    ):
        raise S50BodyMotionSourceRejected("client control effects not ordered")
    return tuple(effects)


def project_s50_body_motion_source(
    *, paper_original: bytes, client_original: bytes,
    l23_source_readback: Mapping[str, object], session_id: str,
    action_id: str, world: str, subject_uuid: str, first_tick: int,
) -> S50SelfBodyMotionSource:
    """Read-only, source-bound 8-tick diagnostic; NEVER SelfBody Present.

    Caller must already possess the original L23 readback. The copied
    readback is a claim that is checked against raw Paper SHA/tick identity,
    *not* independent authentication of a World TCP session.
    """
    if (
        not isinstance(paper_original, bytes)
        or not 0 < len(paper_original) <= _MAX_PAPER_BYTES
        or not isinstance(client_original, bytes)
        or not 0 < len(client_original) <= _MAX_NODE_BYTES
        or not isinstance(l23_source_readback, Mapping)
        or not all(isinstance(x, str) and 0 < len(x) <= 128
                   for x in (session_id, action_id, world, subject_uuid))
        or type(first_tick) is not int or first_tick < 0
    ):
        raise S50BodyMotionSourceRejected("missing/invalid owner originals")
    marker_id = f"{action_id}-{session_id}"
    if len(marker_id) > 128:
        raise S50BodyMotionSourceRejected("unbounded native marker")
    paper_sha = hashlib.sha256(paper_original).hexdigest()
    expected = {
        "session_id": session_id,
        "action_id": action_id,
        "marker_id": marker_id,
        "paper_world": world,
        "paper_original_sha256": paper_sha,
        "paper_first_tick": first_tick,
        "paper_last_tick": first_tick + 7,
        "paper_sample_count": 8,
        "accepted_goal_status": "UNDETERMINED",
        "physical_stability_verified": False,
        "p1_wait_ticks_admitted": 0,
        "qualified_real_learning_pairs": 0,
    }
    if any(l23_source_readback.get(key) != value for key, value in expected.items()):
        raise S50BodyMotionSourceRejected("L23 source/claim ceiling does not match")
    try:
        lines = paper_original.decode("utf-8").splitlines()
    except UnicodeError as exc:
        raise S50BodyMotionSourceRejected("invalid original Paper UTF-8") from exc
    rows = [_fields(line, WAIT_PREFIX) for line in lines if WAIT_PREFIX in line]
    if len(rows) != 8:
        raise S50BodyMotionSourceRejected("Paper eight WAIT samples required")
    paper_input = review_s50_input_samples(
        paper_original, marker_id=marker_id, world=world,
        subject_uuid=subject_uuid, start_tick=first_tick - 1,
    )
    packet = inspect_s50_client_packets(
        client_original, paper_original, session_id=session_id,
        marker_id=marker_id, world=world,
    )["readback"]
    last = None
    physical = []
    for n, row in enumerate(rows):
        tick = _natural(row, "tick")
        if (
            row.get("marker_id") != marker_id or row.get("world") != world
            or tick != first_tick + n or _natural(row, "index") != n + 1
        ):
            raise S50BodyMotionSourceRejected("Paper WAIT tick source mismatch")
        start = tuple(_num(row, "from_" + k) for k in ("x", "y", "z"))
        end = tuple(_num(row, k) for k in ("x", "y", "z"))
        if last is not None and start != last:
            raise S50BodyMotionSourceRejected("Paper WAIT pose chain discontinuity")
        last = end
        drift = math.dist(start, end)
        if not math.isfinite(drift):
            raise S50BodyMotionSourceRejected("invalid Paper displacement")
        physical.append(S50PaperMotionSample(
            world_tick=tick, displacement_m=drift,
            last_reported_input_active=tick in paper_input.sampled_input_active_ticks,
        ))
    activity = tuple(
        p.world_tick for p in physical
        if p.displacement_m > 0 and not p.last_reported_input_active
    )
    if (
        l23_source_readback.get("paper_activity_ticks") != [
            p.world_tick for p in physical if p.displacement_m > 0
        ]
    ):
        raise S50BodyMotionSourceRejected("Paper motion contradicts L23 readback")
    return S50SelfBodyMotionSource(
        session_id=session_id, action_id=action_id, marker_id=marker_id,
        paper_world_uuid=world, subject_uuid=subject_uuid,
        paper_original_sha256=paper_sha,
        client_original_sha256=hashlib.sha256(client_original).hexdigest(),
        paper_samples=tuple(physical),
        client_effects=_client_controls(client_original, session_id),
        observed_motion_while_reported_input_off_ticks=activity,
        client_player_input_write_returns=packet["client_player_input_write_returns"],
        client_position_write_returns=packet["client_motion_write_returns"],
        paper_player_input_callbacks=packet["paper_player_input_callbacks"],
        client_packet_diagnostic=packet["diagnostic"],
    )
