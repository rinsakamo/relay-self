"""S50 FLAT/P1 opt-in native-client LOOK-pose source gate (DEV only).

A successful Mineflayer LOOK ACK may precede Paper's effective pose. This
checker observes only the real bot.entity radians recorded synchronously
with that native ACK. Paper yaw needs its own independently timed readback.
Neither source is a World-tick activity certificate, Action, or P1 grant.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

from adapters.mineflayer.m02_paper_dev.s50_boundary import BoundaryRejected
from adapters.mineflayer.m02_paper_dev.s50_p1_native_controls import SOURCE

MAX_SOURCE_BYTES = 2_000_000
MAX_SOURCE_ROWS = 8192
YAW_TOLERANCE_RADIANS = math.radians(5)
PITCH_TOLERANCE_RADIANS = math.radians(5)
ALLOWED_KINDS = {
    "SESSION_START", "PHYSICS_TICK", "EFFECT_ACK", "PROBE", "SHUTDOWN_ACK",
}


def _unique_keys(pairs):
    out = {}
    for name, value in pairs:
        if name in out:
            raise BoundaryRejected("duplicate native pose source key")
        out[name] = value
    return out


def _rad(row: dict, name: str) -> float:
    value = row.get(name)
    if type(value) not in (int, float) or not math.isfinite(value):
        raise BoundaryRejected("missing/nonfinite direct native yaw or pitch")
    return float(value)


def _angular_gap(actual: float, expected: float) -> float:
    return abs((actual - expected + math.pi) % (2 * math.pi) - math.pi)


def read_client_look_pose(sidecar: Path, *, session_id: str,
                          action_id: str, requested_yaw_rad: float,
                          requested_pitch_rad: float = 0.0) -> dict:
    """Only the genuine LOOK-effect sidecar row; no extrapolation to Paper.

    This is invoked BEFORE issuing the governed FORWARD. The sidecar's
    synchronous write precedes the already-acknowledged native frame, so
    the recorded LOOK pose is available without a host timing assumption.
    """
    if (not isinstance(sidecar, Path) or not sidecar.is_absolute()
            or sidecar.is_symlink() or not sidecar.is_file()
            or sidecar.parent.is_symlink()
            or not isinstance(session_id, str) or not session_id
            or not isinstance(action_id, str) or not action_id
            or type(requested_yaw_rad) not in (int, float)
            or type(requested_pitch_rad) not in (int, float)
            or not math.isfinite(requested_yaw_rad)
            or not math.isfinite(requested_pitch_rad)):
        raise BoundaryRejected("foreign native client LOOK source")
    size = sidecar.stat().st_size
    if not 0 < size <= MAX_SOURCE_BYTES:
        raise BoundaryRejected("empty/unbounded native client LOOK source")
    try:
        content = sidecar.read_text(encoding="utf-8")
        rows = [json.loads(line, object_pairs_hook=_unique_keys)
                for line in content.splitlines()]
    except (UnicodeError, ValueError, TypeError) as exc:
        raise BoundaryRejected("invalid native client LOOK source JSONL") from exc
    if not 2 <= len(rows) <= MAX_SOURCE_ROWS:
        raise BoundaryRejected("missing native client LOOK source rows")
    if (rows[0].get("kind") != "SESSION_START"
            or rows[0].get("native_seq") != 0
            or rows[0].get("client_physics_tick") != 0):
        raise BoundaryRejected("native session start not bound")
    last_tick = 0
    look = []
    effects = []
    for i, row in enumerate(rows, 1):
        if (not isinstance(row, dict)
                or row.get("source") != SOURCE
                or row.get("session_id") != session_id
                or row.get("kind") not in ALLOWED_KINDS
                or type(row.get("ordinal")) is not int
                or row["ordinal"] != i
                or type(row.get("client_physics_tick")) is not int
                or row["client_physics_tick"] < last_tick):
            raise BoundaryRejected("native client pose source identity/order invalid")
        last_tick = row["client_physics_tick"]
        if row["kind"] == "EFFECT_ACK":
            effects.append(row)
            if row.get("native_action_id") == action_id + "-look":
                look.append(row)
    if not effects or effects[0].get("native_action_id") != action_id + "-look":
        raise BoundaryRejected("first native effect was not governed LOOK")
    if len(look) != 1:
        raise BoundaryRejected("duplicate/missing native LOOK pose ACK")
    witness = look[0]
    if type(witness.get("native_seq")) is not int or witness["native_seq"] < 1:
        raise BoundaryRejected("native LOOK ACK missing source seq")
    actual_yaw = _rad(witness, "client_yaw_radians")
    actual_pitch = _rad(witness, "client_pitch_radians")
    yaw_gap = _angular_gap(actual_yaw, requested_yaw_rad)
    pitch_gap = _angular_gap(actual_pitch, requested_pitch_rad)
    if yaw_gap > YAW_TOLERANCE_RADIANS or pitch_gap > PITCH_TOLERANCE_RADIANS:
        raise BoundaryRejected("LOOK_ACK_WITHOUT_NATIVE_CLIENT_POSE: do not issue FORWARD")
    return {
        "classification": "S50_FLAT_CLIENT_LOOK_ACK_POSE_DEV_ONLY",
        "source_session": session_id,
        "action_id": action_id,
        "look_ack_native_seq": witness["native_seq"],
        "look_ack_client_physics_tick": witness["client_physics_tick"],
        "native_client_yaw_radians": actual_yaw,
        "native_client_pitch_radians": actual_pitch,
        "requested_yaw_radians": float(requested_yaw_rad),
        "requested_pitch_radians": float(requested_pitch_rad),
        "yaw_gap_radians": yaw_gap,
        "pitch_gap_radians": pitch_gap,
        "source_rows_at_review": len(rows),
        "paper_effective_yaw": "SEPARATE_PAPER_SOURCE_REQUIRED",
        "server_effective_input_tick": "NOT_ATTESTED",
        "all_issuer_absence": "NOT_ATTESTED",
        "P1_SourceBoundTick_MOVE_issued": 0,
        "P1_SourceBoundTick_WAIT_issued": 0,
        "P1_fatigue_recovered": 0.0,
        "science_go": False,
    }
