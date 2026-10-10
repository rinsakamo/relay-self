"""Lane A E7: read-only native Mineflayer JSONL geometry audit, NOT live proof.

This code only parses a *caller-supplied* bridge stream. Its provenance and hashes
are unauthenticated, even if every source-native field is consistent. It neither
launches the Minecraft bridge nor sends observe/Action commands; full Action3
ancestry, survival effects, user permission and E5 36 real trials remain absent.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from adapters.mineflayer.python_protocol import (
    MINEFLAYER_NEARBY_ENTITY_MAX_DISTANCE,
    MINEFLAYER_NEARBY_ENTITY_SOURCE_SCOPE,
    MineflayerAdapterStarted,
    MineflayerDecodedMessage,
    MineflayerObservation,
    MineflayerShutdownAck,
    MineflayerStreamDecoder,
)
from experiments import epistemic_e5_prospective_gate as e5
from experiments import epistemic_e6_feasibility_interlock as e6

VERSION = "AC-A-E7-NATIVE-GEOMETRY-TRACE-READONLY-v1.1"
MANIFEST_SHA256 = "211b84fc2b3e15cb7f8581d2663fdfe3d01a7bf394474195b010e01edb50a60d"
MANIFEST = {
    "version": VERSION,
    "base_e6": "4c4a5e2481468b94708df3296173c5ec9c1fdfe0",
    "e5_manifest": "2ede0bd82ab6c8ada2557a5477f9c6d6084e6cbae50a5e1a6b8ffc6d1626e2f3",
    "e6_manifest": "bf78c4f647a3a7b138b1b6189312be4395a82ed49711aff6b3fc1d35ec1bd2cf",
    "scope": "strict read-only decode of a saved single Mineflayer JSONL stream; no generation or physical launcher",
    "geometry_cm": [180, 20],
    "policy_s24_boundary_cm": 100,
    "source": "MineflayerStreamDecoder exact seq/session; one spawn then far probe; native far entity gone and DIFFERENT near entity spawned; second near probe; stable bot",
    "first_request_id": "e7:far:one",
    "second_request_id": "e7:near:two",
    "comparison": "typed source geometry (rounded cm) is not physical authenticity, Action3 ancestry, E5 36-run qualification or survival evidence",
    "result_ceiling": "E7_OFFLINE_TYPED_TRACE_GATE_PASS; SYNTHETIC_TYPED_TRACE_ONLY or UNATTESTED_NATIVE_TRACE",
    "real_world_authorization": "not granted; no server startup, node launch, Action command or physical run",
    "paths": [
        "experiments/epistemic_e7_native_trace_gate.py",
        "tests/test_epistemic_e7_native_trace_gate.py",
        ".github/workflows/epistemic-e7-trace.yml",
    ],
}
MAX_FRAMES = 256
MAX_BYTES = 1_000_000
BOT_POSITION_TOLERANCE_M = 0.01
MAX_SOURCE_DISTANCE_DISCREPANCY_M = 1e-6


class E7Rejected(ValueError):
    """No safe interpretation of a partial, malformed or equivocal native stream."""


@dataclass(frozen=True, slots=True)
class E7TraceAudit:
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


def digest(manifest: object = MANIFEST) -> str:
    data = json.dumps(manifest, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False)
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def _frozen() -> None:
    if (
        digest() != MANIFEST_SHA256
        or e5.digest() != MANIFEST["e5_manifest"]
        or e6.digest() != MANIFEST["e6_manifest"]
        or e5.MANIFEST["distances_cm"] != [20, 180]
        or len(e5.planned_trials()) != 36
    ):
        raise E7Rejected("frozen E5/E6/E7 source/authority drift")


def _zombie(snapshot: object, *, allow_absent: bool = False):
    if not hasattr(snapshot, "nearby_entities_coverage"):
        raise E7Rejected("typed native snapshot required")
    coverage = snapshot.nearby_entities_coverage
    if (
        coverage.source_scope != MINEFLAYER_NEARBY_ENTITY_SOURCE_SCOPE
        or coverage.max_distance != MINEFLAYER_NEARBY_ENTITY_MAX_DISTANCE
        or coverage.truncated
        or coverage.candidate_count != len(snapshot.nearby_entities)
    ):
        raise E7Rejected("incomplete source-native entity registry coverage")
    matches = [v for v in snapshot.nearby_entities if v.name == "zombie"]
    if not matches and allow_absent:
        return None
    if len(matches) != 1:
        raise E7Rejected("missing/ambiguous actual zombie; absence is not safety")
    target = matches[0]
    # The source bridge reports Euclidean bot/entity center distance.
    distance = math.dist(
        (snapshot.position.x, snapshot.position.y, snapshot.position.z),
        (target.position.x, target.position.y, target.position.z),
    )
    if (
        not math.isfinite(distance)
        or distance <= 0
        or distance > coverage.max_distance
        or not math.isclose(
            target.distance, distance, rel_tol=0,
            abs_tol=MAX_SOURCE_DISTANCE_DISCREPANCY_M,
        )
    ):
        raise E7Rejected("inconsistent entity distance vs source-native positions")
    return target, math.floor(distance * 100 + 0.5)


def _stationary(current: MineflayerObservation, origin: MineflayerObservation) -> None:
    a, b = current.snapshot.position, origin.snapshot.position
    if math.dist((a.x, a.y, a.z), (b.x, b.y, b.z)) > BOT_POSITION_TOLERANCE_M:
        raise E7Rejected("bot physically moved during intended static source calibration")


def audit_decoded(
    messages: Iterable[MineflayerDecodedMessage],
    *,
    source_kind: str = "UNATTESTED",
) -> E7TraceAudit:
    """Check structure/geometry ONLY. source_kind is a label, not attestation."""
    _frozen()
    if source_kind not in ("UNATTESTED", "SYNTHETIC") or type(source_kind) is not str:
        raise E7Rejected("unrecognized data-source label cannot confer trust")
    stream = tuple(messages)
    if not 6 <= len(stream) <= MAX_FRAMES:
        raise E7Rejected("missing or unbounded stream frames")
    if (
        not isinstance(stream[0], MineflayerAdapterStarted)
        or stream[0].seq != 0
        or not isinstance(stream[-1], MineflayerShutdownAck)
    ):
        raise E7Rejected("one started session and final shutdown ACK required")
    session_id = stream[0].session_id
    spawn: MineflayerObservation | None = None
    far: MineflayerObservation | None = None
    near: MineflayerObservation | None = None
    old_entity_id: int | None = None
    new_entity_id: int | None = None
    old_absent = False
    new_seen = False
    phase = 0  # 0 spawn, 1 far probe, 2 old gone, 3 new appeared, 4 near probe
    for index, frame in enumerate(stream):
        if frame.session_id != session_id or frame.seq != index:
            raise E7Rejected("adapter session/sequence changed or replayed")
        if index == 0 or index == len(stream) - 1:
            continue
        if not isinstance(frame, MineflayerObservation):
            raise E7Rejected("unexpected effect/Action/terminal/hurt/death message")
        if frame.kind in ("death", "respawn", "forcedMove"):
            raise E7Rejected("damage/respawn or externally forced bot movement in source trace")
        if spawn is None:
            if frame.kind != "spawn":
                raise E7Rejected("no initial typed spawn before source reads")
            spawn = frame
            _zombie(frame.snapshot, allow_absent=True)
            continue
        if frame.kind == "spawn":
            raise E7Rejected("duplicate bot spawn/reset in one session")
        _stationary(frame, spawn)
        if frame.kind not in ("probe", "entities", "health", "time", "inventory", "move"):
            raise E7Rejected("unsupported native observation in calibration")
        if frame.kind == "probe":
            if phase == 0:
                if frame.request_id != MANIFEST["first_request_id"]:
                    raise E7Rejected("first exact far correlated request_id mismatch")
                first = _zombie(frame.snapshot)
                if first[1] != 180:
                    raise E7Rejected("first far target must be exactly rounded 180cm")
                far = frame
                old_entity_id = first[0].entity_id
                phase = 1
            elif phase == 3:
                if frame.request_id != MANIFEST["second_request_id"]:
                    raise E7Rejected("second exact near correlated request_id mismatch")
                second = _zombie(frame.snapshot)
                if second[1] != 20 or second[0].entity_id != new_entity_id:
                    raise E7Rejected("second near target identity/20cm geometry mismatch")
                near = frame
                phase = 4
            else:
                raise E7Rejected("third/early/replayed/legacy probe or transition absent")
        elif frame.kind == "entities":
            found = _zombie(frame.snapshot, allow_absent=True)
            if phase == 1:
                if found is None:
                    old_absent = True
                    phase = 2
                elif found[0].entity_id != old_entity_id:
                    raise E7Rejected("far old zombie replaced without witnessed gone event")
            elif phase == 2:
                if found is not None:
                    if found[0].entity_id == old_entity_id or found[1] != 20:
                        raise E7Rejected("new distinct zombie must be at rounded 20cm")
                    new_entity_id = found[0].entity_id
                    new_seen = True
                    phase = 3
            elif phase == 3 and (
                found is None or found[0].entity_id != new_entity_id
                or found[1] != 20
            ):
                raise E7Rejected("new near zombie disappeared or geometry drifted")
            elif phase == 4:
                raise E7Rejected("World changed after final correlated near probe")
        elif frame.kind in ("move", "health") and phase == 4:
            raise E7Rejected("bot state changed after final near probe")
    if (
        phase != 4 or far is None or near is None or spawn is None
        or not old_absent or not new_seen
        or old_entity_id is None or new_entity_id is None
        or old_entity_id == new_entity_id
        or not far.seq < near.seq
    ):
        raise E7Rejected("incomplete two-request source-native far→near transition")
    return E7TraceAudit(
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
    )


def audit_jsonl(data: bytes, *, source_kind: str = "UNATTESTED") -> E7TraceAudit:
    """Pass entire raw JSONL through the unchanged production stream decoder."""
    _frozen()
    if type(data) is not bytes or not data or len(data) > MAX_BYTES:
        raise E7Rejected("missing/out-of-bound 1MB bridge stream")
    try:
        text = data.decode("utf-8")
    except UnicodeError as exc:
        raise E7Rejected("raw bridge source is not UTF-8") from exc
    if not text.endswith("\n") or "\r" in text or "\x00" in text:
        raise E7Rejected("unframed/noncanonical raw bridge JSONL")
    lines = text.splitlines()
    if not 6 <= len(lines) <= MAX_FRAMES or not all(lines):
        raise E7Rejected("unbounded/empty bridge JSONL frames")
    decoder = MineflayerStreamDecoder()
    # The decoder is the SAME production parser/strict seq/source checker.
    try:
        frames = [decoder.decode(line) for line in lines]
    except (ValueError, TypeError, KeyError) as exc:
        raise E7Rejected("Mineflayer native protocol decoder rejected frames") from exc
    return audit_decoded(frames, source_kind=source_kind)


def _report_data(report: E7TraceAudit) -> dict[str, object]:
    return {k: getattr(report, k) for k in report.__dataclass_fields__}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read-only E7 typed geometry trace audit")
    command = parser.add_mutually_exclusive_group(required=True)
    command.add_argument("--plan", action="store_true")
    command.add_argument("--audit", type=Path, metavar="BRIDGE.jsonl")
    args = parser.parse_args(argv)
    try:
        if args.plan:
            _frozen()
            result: dict[str, object] = {
                "version": VERSION, "manifest_sha256": MANIFEST_SHA256,
                "base_e6": MANIFEST["base_e6"],
                "expected_cm": MANIFEST["geometry_cm"],
                "first_request_id": MANIFEST["first_request_id"],
                "second_request_id": MANIFEST["second_request_id"],
                "classification": "E7_PHYSICAL_SOURCE_NOT_QUALIFIED",
                "world_launched_by_e7": False,
                "new_physical_approval": False,
            }
            exit_code = 0  # safe plan, not physical authorization
        else:
            assert args.audit is not None
            if not args.audit.is_file() or args.audit.stat().st_size > MAX_BYTES:
                raise E7Rejected("raw native trace missing/exceeds 1MB")
            result = _report_data(audit_jsonl(args.audit.read_bytes()))
            # Never allow a file-shaped JSONL replay to be called physical PASS.
            exit_code = 3
    except (E7Rejected, OSError, ValueError, TypeError) as exc:
        result = {
            "classification": "E7_TRACE_REJECTED",
            "reason": str(exc),
            "world_launched_by_e7": False,
            "physically_authenticated": False,
        }
        exit_code = 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
