"""Stage W1 offline, independently replayable source extraction contract.

The archive is a canonical, content-addressed *extraction* of source-shaped
S49 data. It is NOT the immutable raw Minecraft/Node event stream.
Its expected SHA256 must be supplied from outside the request/envelope.
Reject model predictions, mismatched geometry, feedback labels and frame order.
No physical trust or S10 grant is established by this module.
"""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path

from adapters.mineflayer.self_world_stage_v_attestation import StageVGrantRequest

_DOMAIN = b"RelaySelf/SelfWorld/StageV/S10-grant/1\x00"
_SCHEMA = "stage-w1-source-extract-v0"
_ARCHIVE_KEYS = frozenset(("schema", "run_id", "source", "native", "terminal"))
_SOURCE_KEYS = frozenset((
    "session_id", "original_seq", "original_request_id", "action_id",
    "binding_id", "before_seq", "after_seq", "before_health", "after_health",
    "before_target_m", "after_target_m", "target_id", "world_provenance",
    "outcome_ref", "feedback_id", "next_probe_seq", "next_probe_request_id",
))
_NATIVE_KEYS = frozenset((
    "source_scope", "complete_registry", "original_bot_xyz",
    "original_target_xyz", "before_bot_xyz", "before_target_xyz",
    "after_bot_xyz", "after_target_xyz", "horizontal_movement_m",
))
_TERMINAL_KEYS = frozenset((
    "action_state", "disposition", "outcome_reason",
    "action_ref", "world_status", "intent_id",
))


class StageWArchiveRejected(ValueError):
    """Independent source extract unavailable, forged or non-replayable."""


def canonical(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")


def _mapping(value: object, fields: frozenset[str], name: str) -> dict:
    if not isinstance(value, dict) or value.keys() != fields:
        raise StageWArchiveRejected(f"invalid {name} field set")
    return value


def _positive_int(value: object) -> bool:
    return type(value) is int and value >= 0


def _vector(value: object) -> tuple[float, float, float]:
    if (
        not isinstance(value, list) or len(value) != 3
        or any(type(p) not in (int, float) for p in value)
        or any(not math.isfinite(float(p)) for p in value)
    ):
        raise StageWArchiveRejected("nonfinite or incomplete original XYZ")
    return (float(value[0]), float(value[1]), float(value[2]))


def _near(a: float, b: object, tolerance: float = 1e-6) -> bool:
    return (
        type(b) in (int, float) and math.isfinite(float(b))
        and math.isclose(a, float(b), rel_tol=0, abs_tol=tolerance)
    )


@dataclass(frozen=True, slots=True)
class StageWArchiveReadback:
    archive_sha256: str
    source_sha256: str
    session_id: str
    action_id: str
    direction: str
    delta_m: float
    correlated_native: bool
    physical_raw_stream_attested: bool = False
    independently_trusted_archivist: bool = False


def audit_independent_source_extract(
    *, archive_path: Path, expected_archive_sha256: str,
    expected: StageVGrantRequest,
) -> StageWArchiveReadback:
    """Read sealed extraction, recompute source SHA and native separation.

    Independent-of-request digest is an externally pinned *archive* hash.
    A caller-supplied/self-minted pin still cannot establish real World truth.
    """
    if (
        not isinstance(archive_path, Path) or not archive_path.is_file()
        or archive_path.is_symlink()
        or not isinstance(expected, StageVGrantRequest)
        or type(expected_archive_sha256) is not str
        or len(expected_archive_sha256) != 64
        or any(c not in "0123456789abcdef" for c in expected_archive_sha256)
    ):
        raise StageWArchiveRejected("external extraction archive pin required")
    try:
        if archive_path.stat().st_size > 64 * 1024:
            raise StageWArchiveRejected("extraction too large")
        raw = archive_path.read_bytes()
        archive_sha = hashlib.sha256(raw).hexdigest()
        if archive_sha != expected_archive_sha256:
            raise StageWArchiveRejected("archive does not match externally pinned SHA")
        value = json.loads(raw)
        if raw != canonical(value):
            raise StageWArchiveRejected("noncanonical or ambiguous archive bytes")
    except (OSError, UnicodeError, ValueError, TypeError, OverflowError) as exc:
        if isinstance(exc, StageWArchiveRejected):
            raise
        raise StageWArchiveRejected("unreadable/corrupt source extraction") from exc
    archive = _mapping(value, _ARCHIVE_KEYS, "archive")
    src = _mapping(archive["source"], _SOURCE_KEYS, "source")
    native = _mapping(archive["native"], _NATIVE_KEYS, "native")
    terminal = _mapping(archive["terminal"], _TERMINAL_KEYS, "terminal")
    prov = _mapping(
        src["world_provenance"], frozenset(("source", "reference")),
        "World provenance",
    )
    if (
        archive["schema"] != _SCHEMA
        or archive["run_id"] != expected.run_id
        or src["session_id"] != expected.session_id
        or src["action_id"] != expected.action_id
        or src["feedback_id"] != expected.feedback_id
        or src["target_id"] != expected.entity_id
        or src["after_seq"] != expected.after_seq
        or src["next_probe_seq"] != expected.next_probe_seq
        or terminal["action_state"] != "outcome"
        or terminal["disposition"] != "outcome"
        or terminal["outcome_reason"] != "observed_execution"
        or terminal["action_ref"] != "MOVE_BACKWARD"
        or terminal["world_status"] != "executed"
        or not isinstance(terminal["intent_id"], str)
        or not terminal["intent_id"]
        or native["source_scope"] != "mineflayer_entity_registry"
        or native["complete_registry"] is not True
        or not isinstance(prov["source"], str)
        or not isinstance(prov["reference"], str)
        or not prov["source"] or not prov["reference"]
        or not all(_positive_int(src[k]) for k in (
            "original_seq", "before_seq", "after_seq", "next_probe_seq",
        ))
    ):
        raise StageWArchiveRejected("source, run, terminal or native coverage mismatch")
    event = expected.action_id.removeprefix("s49-native-move-")
    sid = expected.session_id
    try:
        later = src["next_probe_request_id"].removeprefix(
            f"s49-actual:{sid}:event-"
        )
    except AttributeError as exc:
        raise StageWArchiveRejected("missing original later probe identity") from exc
    if (
        src["original_request_id"] != f"s49-actual:{sid}:event-{event}"
        or src["binding_id"] != f"s49-binding-{event}"
        or not event.isdecimal()
        or int(event) != src["original_seq"]
        or not src["original_seq"] < src["before_seq"] < src["after_seq"]
        or not isinstance(src["next_probe_request_id"], str)
        or not src["next_probe_request_id"].startswith(f"s49-actual:{sid}:event-")
        or not later.isdecimal()
        or not src["after_seq"] < int(later) < src["next_probe_seq"]
        or any(not _near(float(src[k]), src[k]) or float(src[k]) < 0 for k in (
            "before_health", "after_health",
        ) if type(src[k]) in (int, float))
        or any(type(src[k]) not in (int, float) for k in (
            "before_health", "after_health",
        ))
    ):
        raise StageWArchiveRejected("original Action or future native sequence mismatch")

    o_bot = _vector(native["original_bot_xyz"])
    o_target = _vector(native["original_target_xyz"])
    b_bot = _vector(native["before_bot_xyz"])
    b_target = _vector(native["before_target_xyz"])
    a_bot = _vector(native["after_bot_xyz"])
    a_target = _vector(native["after_target_xyz"])
    # Validate native entity geometry; NEVER accept a claimed distance label.
    b_distance = math.dist(b_bot, b_target)
    a_distance = math.dist(a_bot, a_target)
    o_distance = math.dist(o_bot, o_target)
    horizontal = math.hypot(a_bot[0] - b_bot[0], a_bot[2] - b_bot[2])
    if (
        not math.isfinite(o_distance)
        or not _near(b_distance, src["before_target_m"])
        or not _near(a_distance, src["after_target_m"])
        or not _near(horizontal, native["horizontal_movement_m"])
        or horizontal < 0.05
    ):
        raise StageWArchiveRejected("unreproducible original native geometry")
    delta = a_distance - b_distance
    if delta >= 0.1:
        direction, kind = "increase", "separation_increased"
    elif delta <= -0.1:
        direction, kind = "decrease", "separation_decreased"
    else:
        raise StageWArchiveRejected("HOLD or unresolved source is not grantable")
    criterion = f"stage-s-same-target-separation-v0:{sid}:{event}:{kind}"
    feedback = (
        f"feedback:{criterion}:risk_weight:{expected.action_id}:"
        f"{src['binding_id']}:{sid}:observed_execution"
    )
    outcome_ref = (
        f"action-outcome:{expected.action_id}:{src['binding_id']}:"
        f"{sid}:observed_execution"
    )
    if (
        expected.direction != direction
        or expected.proposed_value != (5 if direction == "increase" else 3)
        or src["feedback_id"] != feedback
        or src["outcome_ref"] != outcome_ref
    ):
        raise StageWArchiveRejected("S17 feedback is not independently reproducible")
    source_sha = hashlib.sha256(_DOMAIN + canonical(src)).hexdigest()
    if source_sha != expected.evidence_sha256:
        raise StageWArchiveRejected("Stage V signed source hash mismatches archive")
    return StageWArchiveReadback(
        archive_sha256=archive_sha, source_sha256=source_sha,
        session_id=sid, action_id=expected.action_id,
        direction=direction, delta_m=delta, correlated_native=True,
    )
