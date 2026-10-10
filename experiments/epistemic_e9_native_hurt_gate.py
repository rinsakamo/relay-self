"""E9: independent full-source typed audit tolerating one old-zombie hurt.

Reads the complete original stream with unmodified session/seq, including hurt;
neither hides frames nor projects them into the frozen E7 grammar. Does not
launch Minecraft, issue Actions or attest origin. E7/E8 stay immutable.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from adapters.mineflayer.python_protocol import (
    MineflayerAdapterStarted,
    MineflayerDecodedMessage,
    MineflayerEntityHurt,
    MineflayerObservation,
    MineflayerShutdownAck,
    MineflayerStreamDecoder,
)
from experiments import epistemic_e7_native_trace_gate as e7
from experiments import epistemic_e8_operator_calibration as e8

VERSION = "AC-A-E9-NATIVE-ZOMBIE-HURT-SUCCESSOR-v1"
MAX_FRAMES = e7.MAX_FRAMES
MAX_BYTES = e7.MAX_BYTES
MANIFEST = e7.MANIFEST
_zombie = e7._zombie
_stationary = e7._stationary


class E9Rejected(e7.E7Rejected):
    """A complete source-native E9 trace was not established."""


def _frozen() -> None:
    e8._frozen()


@dataclass(frozen=True, slots=True)
class E9TraceAudit:
    classification: str
    physically_authenticated: bool
    world_launched_by_e7: bool
    can_start_e5_physical_study: bool
    e5_action3_parent_qualified: bool
    e5_survival_or_damage_effect: str
    session_id: str
    total_frames: int
    first_probe_seq: int
    second_probe_seq: int
    far_entity_id: int
    near_entity_id: int
    far_distance_cm: int
    near_distance_cm: int
    seen_old_entity_absent: bool
    seen_new_entity_spawn: bool
    new_physical_approval: bool
    hurt_event_count: int


def audit_decoded(
    messages: Iterable[MineflayerDecodedMessage],
    *,
    source_kind: str = "UNATTESTED",
) -> E9TraceAudit:
    """Check structure/geometry ONLY. source_kind is a label, not attestation."""
    _frozen()
    if source_kind not in ("UNATTESTED", "SYNTHETIC") or type(source_kind) is not str:
        raise E9Rejected("unrecognized data-source label cannot confer trust")
    stream = tuple(messages)
    if not 6 <= len(stream) <= MAX_FRAMES:
        raise E9Rejected("missing or unbounded stream frames")
    if (
        not isinstance(stream[0], MineflayerAdapterStarted)
        or stream[0].seq != 0
        or not isinstance(stream[-1], MineflayerShutdownAck)
    ):
        raise E9Rejected("one started session and final shutdown ACK required")
    session_id = stream[0].session_id
    spawn: MineflayerObservation | None = None
    far: MineflayerObservation | None = None
    near: MineflayerObservation | None = None
    old_entity_id: int | None = None
    new_entity_id: int | None = None
    old_absent = False
    far_seen = False
    new_seen = False
    phase = 0  # 0 spawn, 1 far probe, 2 old gone, 3 new appeared, 4 near probe
    hurt_event_count = 0
    for index, frame in enumerate(stream):
        if frame.session_id != session_id or frame.seq != index:
            raise E9Rejected("adapter session/sequence changed or replayed")
        if index == 0 or index == len(stream) - 1:
            continue
        if isinstance(frame, MineflayerEntityHurt):
            # Only the already-probed far zombie can report one native hurt
            # during removal. A hurt is NEVER an entityGone/absence witness.
            if not (
                phase == 1 and old_entity_id is not None
                and frame.entity_id == old_entity_id
                and frame.source_entity_id is None
                and frame.actor_entity_id != old_entity_id
                and hurt_event_count == 0
            ):
                raise E9Rejected("unexpected target/phase/duplicate native entity_hurt")
            hurt_event_count += 1
            continue
        if not isinstance(frame, MineflayerObservation):
            raise E9Rejected("unexpected effect/Action/terminal/death message")
        if frame.kind in ("death", "respawn", "forcedMove"):
            raise E9Rejected("damage/respawn or externally forced bot movement in source trace")
        if spawn is None:
            if frame.kind != "spawn":
                raise E9Rejected("no initial typed spawn before source reads")
            spawn = frame
            _zombie(frame.snapshot, allow_absent=True)
            continue
        if frame.kind == "spawn":
            raise E9Rejected("duplicate bot spawn/reset in one session")
        _stationary(frame, spawn)
        if frame.kind not in ("probe", "entities", "health", "time", "inventory", "move"):
            raise E9Rejected("unsupported native observation in calibration")
        if frame.kind == "probe":
            if phase == 0:
                if not far_seen:
                    raise E9Rejected("far zombie not witnessed by native entitySpawn event")
                if frame.request_id != MANIFEST["first_request_id"]:
                    raise E9Rejected("first exact far correlated request_id mismatch")
                first = _zombie(frame.snapshot)
                if first[1] != 180 or first[0].entity_id != old_entity_id:
                    raise E9Rejected("first far target must match earlier native 180cm entitySpawn")
                far = frame
                old_entity_id = first[0].entity_id
                phase = 1
            elif phase == 3:
                if frame.request_id != MANIFEST["second_request_id"]:
                    raise E9Rejected("second exact near correlated request_id mismatch")
                second = _zombie(frame.snapshot)
                if second[1] != 20 or second[0].entity_id != new_entity_id:
                    raise E9Rejected("second near target identity/20cm geometry mismatch")
                near = frame
                phase = 4
            else:
                raise E9Rejected("third/early/replayed/legacy probe or transition absent")
        elif frame.kind == "entities":
            found = _zombie(frame.snapshot, allow_absent=True)
            if phase == 0:
                if found is None or found[1] != 180:
                    raise E9Rejected("far native entitySpawn must establish exactly 180cm")
                if far_seen and found[0].entity_id != old_entity_id:
                    raise E9Rejected("far source identity changed before probe")
                old_entity_id = found[0].entity_id
                far_seen = True
            elif phase == 1:
                if found is None:
                    old_absent = True
                    phase = 2
                elif found[0].entity_id != old_entity_id:
                    raise E9Rejected("far old zombie replaced without witnessed gone event")
            elif phase == 2:
                if found is not None:
                    if found[0].entity_id == old_entity_id or found[1] != 20:
                        raise E9Rejected("new distinct zombie must be at rounded 20cm")
                    new_entity_id = found[0].entity_id
                    new_seen = True
                    phase = 3
            elif phase == 3 and (
                found is None or found[0].entity_id != new_entity_id
                or found[1] != 20
            ):
                raise E9Rejected("new near zombie disappeared or geometry drifted")
            elif phase == 4:
                raise E9Rejected("World changed after final correlated near probe")
        elif frame.kind in ("move", "health") and phase == 4:
            raise E9Rejected("bot state changed after final near probe")
    if (
        phase != 4 or far is None or near is None or spawn is None
        or not far_seen or not old_absent or not new_seen
        or old_entity_id is None or new_entity_id is None
        or old_entity_id == new_entity_id
        or not far.seq < near.seq
    ):
        raise E9Rejected("incomplete two-request source-native far→near transition")
    return E9TraceAudit(
        classification=(
            "SYNTHETIC_TYPED_TRACE_ONLY" if source_kind == "SYNTHETIC"
            else "UNATTESTED_NATIVE_TRACE"
        ),
        physically_authenticated=False,
        world_launched_by_e7=False,
        can_start_e5_physical_study=False,
        e5_action3_parent_qualified=False,
        e5_survival_or_damage_effect="UNDETERMINED",
        session_id=session_id, total_frames=len(stream),
        first_probe_seq=far.seq, second_probe_seq=near.seq,
        far_entity_id=old_entity_id, near_entity_id=new_entity_id,
        far_distance_cm=180, near_distance_cm=20,
        seen_old_entity_absent=old_absent,
        seen_new_entity_spawn=new_seen,
        new_physical_approval=False,
        hurt_event_count=hurt_event_count,
    )


def audit_jsonl(data: bytes, *, source_kind: str = "UNATTESTED") -> E9TraceAudit:
    """Pass entire raw JSONL through the unchanged production stream decoder."""
    _frozen()
    if type(data) is not bytes or not data or len(data) > MAX_BYTES:
        raise E9Rejected("missing/out-of-bound 1MB bridge stream")
    try:
        text = data.decode("utf-8")
    except UnicodeError as exc:
        raise E9Rejected("raw bridge source is not UTF-8") from exc
    if not text.endswith("\n") or "\r" in text or "\x00" in text:
        raise E9Rejected("unframed/noncanonical raw bridge JSONL")
    lines = text.splitlines()
    if not 6 <= len(lines) <= MAX_FRAMES or not all(lines):
        raise E9Rejected("unbounded/empty bridge JSONL frames")
    decoder = MineflayerStreamDecoder()
    # The decoder is the SAME production parser/strict seq/source checker.
    try:
        frames = [decoder.decode(line) for line in lines]
    except (ValueError, TypeError, KeyError) as exc:
        raise E9Rejected("Mineflayer native protocol decoder rejected frames") from exc
    return audit_decoded(frames, source_kind=source_kind)


