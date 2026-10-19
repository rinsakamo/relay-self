"""W4/NH1 OFFLINE prospective geometry and explicit missing-trust inventory.

No supplied strings/booleans are accepted as external attestations. This module
has no World launcher, Action owner, signer or S10 permission conversion.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from adapters.mineflayer.python_protocol import MineflayerObservation, MineflayerPosition

PREREG_ID = "SELFWORLD-W4-NH1-DEV-PROSPECTIVE-20261019-v0"
SCENARIO = "w4-nh1-forward-horizontal-2m-v0"


class W4PreworldBlocked(ValueError):
    """Missing source orientation or externally qualified acquisition contract."""


@dataclass(frozen=True, slots=True)
class W4SyntheticOrientation:
    """TEST-only geometry input, never an authenticated native observation."""

    session_id: str
    seq: int
    position: MineflayerPosition
    yaw_rad: float
    pitch_rad: float


@dataclass(frozen=True, slots=True)
class W4OfflinePlacement:
    prereg_id: str
    scenario: str
    session_id: str
    source_seq: int
    slot: int
    horizontal_distance_m: float
    spawn: MineflayerPosition
    command: str
    physical_run_permitted: bool = False
    source_orientation_qualified: bool = False


def plan_synthetic_nh1_placement(
    orientation: W4SyntheticOrientation, *, expected_session: str,
    before_seq: int, slot: int,
) -> W4OfflinePlacement:
    """Mineflayer radians: forward=(-sin(yaw), 0, -cos(yaw)).

    Pitch does not shorten the preregistered *horizontal* 2m. No motor
    commands are produced. First slot retains the original +X 10m baseline.
    This pure TEST planner cannot attest provenance or launch a World.
    """
    if (type(orientation) is not W4SyntheticOrientation
            or not expected_session or orientation.session_id != expected_session
            or type(orientation.seq) is not int or orientation.seq < 0
            or type(before_seq) is not int or orientation.seq >= before_seq
            or type(slot) is not int or slot not in (0, 1, 2)
            or not isinstance(orientation.position, MineflayerPosition)
            or any(type(v) not in (int, float) or not math.isfinite(v)
                   for v in (orientation.yaw_rad, orientation.pitch_rad))
            or abs(orientation.pitch_rad) > math.pi / 2):
        raise W4PreworldBlocked("orientation/session/pre-action source rejected")
    distance = 10.0 if slot == 0 else 2.0
    dx, dz = ((10.0, 0.0) if slot == 0 else
              (-2 * math.sin(orientation.yaw_rad), -2 * math.cos(orientation.yaw_rad)))
    p = orientation.position
    spawn = MineflayerPosition(p.x + dx, p.y, p.z + dz)
    command = (
        f"summon minecraft:zombie {spawn.x!r} {spawn.y!r} {spawn.z!r} "
        "{NoAI:1b,Silent:1b,PersistenceRequired:1b,Invulnerable:1b}"
    )
    return W4OfflinePlacement(
        PREREG_ID, SCENARIO, orientation.session_id, orientation.seq,
        slot, distance, spawn, command,
    )


def require_native_nh1_orientation(reading: MineflayerObservation) -> None:
    """Explicit STOP: frozen native schema has no yaw/pitch/source binding.

    Never infer yaw from displacement, LOOK ACK, W3 outcomes or a caller's
    synthetic orientation. A future opt-in authenticated acquisition path
    requires implementation and qualification before any physical runner.
    """
    raise W4PreworldBlocked(
        "PREWORLD_BLOCKED: native snapshot has no source-bound yaw/pitch; "
        "NH1 live scenario not qualified; W4 external custody contract required"
    )


def external_trust_readout() -> dict[str, str]:
    """Current implementation capability, not a runtime attestation parser."""
    return {
        "classification": "W4_EXTERNAL_TRUST_NO_GO",
        "independent_archivist_identity": "BLOCKED",
        "external_immutable_storage": "BLOCKED",
        "advance_out_of_band_archive_pin": "BLOCKED",
        "independent_signer_principal_key_custody": "BLOCKED",
        "signer_process_authentication_and_policy": "BLOCKED",
        "advance_issuer_authority_pin": "BLOCKED",
        "node_emitter_completeness": "NOT_TESTED",
        "global_ledger_single_use": "BLOCKED",
        "live_s10_permission": "BLOCKED",
        "physical_nh1": "PREWORLD_BLOCKED",
    }


def prepare_unsigned_custody_handoff(capture_root, *, received_at_utc: str) -> dict:
    """Read-only W3 bytes inventory for an external archivist to receive.

    This candidate is neither signed nor immutable independent custody. An
    archivist must independently authenticate, store, sign and publish its pin
    through its own pre-established channel. Never self-promote this document.
    """
    import hashlib
    import json
    from datetime import datetime

    from adapters.mineflayer.self_world_stage_w3_capture import audit_w3_sealed_stdout

    timestamp = datetime.fromisoformat(received_at_utc.replace("Z", "+00:00"))
    if timestamp.tzinfo is None:
        raise W4PreworldBlocked("timezone-aware transfer observation required")
    audit_w3_sealed_stdout(capture_root)
    raw_path = capture_root / "w3-node-stdout.raw.jsonl"
    receipt_path = capture_root / "w3-node-stdout-receipt.json"
    raw = raw_path.read_bytes()
    receipt_bytes = receipt_path.read_bytes()
    receipt = json.loads(receipt_bytes)
    return {
        "schema": "w4-unsigned-custody-handoff-candidate-v0",
        "scope": "NODE_BRIDGE_STDOUT_JSONL_BYTES_NOT_MINECRAFT_TCP",
        "raw_sha256": hashlib.sha256(raw).hexdigest(),
        "receipt_sha256": hashlib.sha256(receipt_bytes).hexdigest(),
        "byte_count": len(raw),
        "session_id": receipt["session_id"],
        "first_seq": receipt["first_seq"],
        "last_seq": receipt["last_seq"],
        "frame_count": receipt["frame_count"],
        "capture_start_utc": None,
        "capture_end_utc": None,
        "capture_time_status": "NOT_ATTESTED_BY_W3_RECEIPT",
        "transfer_history": [{"observed_at_utc": received_at_utc,
                              "kind": "LOCAL_READBACK_NOT_INDEPENDENT_CUSTODY"}],
        "archivist_identity": None,
        "archivist_public_key_pin": None,
        "signature": None,
        "independent_custody_qualified": False,
        "s10_permission": False,
    }
