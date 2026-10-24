"""SelfWorld Stage V: run-scoped signed S10 grant envelope, OFFLINE DEV.

Signer is a separate process holding its private key; verifier receives only
a separately pinned public-key trust anchor. Signature checks DATA ORIGIN
against that key, not physical World truth, real issuer trust, or S10 rights.
The original S49 Action owner, S10 state, and physical route are untouched.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import re
import subprocess
import sys
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path

from adapters.mineflayer.normal_action import NormalActionClosedReadback
from adapters.mineflayer.python_protocol import MineflayerObservation
from adapters.mineflayer.self_world_stage_s_feedback import (
    StageSPredeclaredSeparationRule,
    StageSSeparationClass,
    assess_stage_s_original_separation,
)
from relay_self.learning import FeedbackDirection

_DOMAIN = b"RelaySelf/SelfWorld/StageV/S10-grant/1\x00"
_REQUEST_KEYS = frozenset((
    "version", "run_id", "session_id", "action_id", "feedback_id",
    "direction", "entity_id", "after_seq", "next_probe_seq",
    "expected_revision", "expected_value", "proposed_value",
    "evidence_sha256",
))
_ENVELOPE_KEYS = frozenset(("request", "signature_b64", "key_fingerprint_sha256"))
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{7,127}\Z")
_HEX = re.compile(r"[0-9a-f]{64}\Z")


class StageVAttestationRejected(ValueError):
    """Malformed, untrusted, tampered or replayed grant candidate."""


@dataclass(frozen=True, slots=True)
class StageVGrantRequest:
    version: int
    run_id: str
    session_id: str
    action_id: str
    feedback_id: str
    direction: str
    entity_id: int
    after_seq: int
    next_probe_seq: int
    expected_revision: int
    expected_value: int
    proposed_value: int
    evidence_sha256: str

    def __post_init__(self) -> None:
        if (
            type(self.version) is not int or self.version != 1
            or not isinstance(self.run_id, str) or not _ID.fullmatch(self.run_id)
            or not isinstance(self.session_id, str) or not self.session_id.strip()
            or not isinstance(self.action_id, str)
            or not self.action_id.startswith("s49-native-move-")
            or not self.action_id.removeprefix("s49-native-move-").isdecimal()
            or not isinstance(self.feedback_id, str) or not self.feedback_id.strip()
            or self.direction not in ("increase", "decrease")
            or type(self.entity_id) is not int or self.entity_id < 0
            or type(self.after_seq) is not int or self.after_seq < 1
            or type(self.next_probe_seq) is not int
            or self.next_probe_seq <= self.after_seq
            or type(self.expected_revision) is not int or self.expected_revision != 1
            or type(self.expected_value) is not int or self.expected_value != 4
            or type(self.proposed_value) is not int
            or self.proposed_value != (5 if self.direction == "increase" else 3)
            or not isinstance(self.evidence_sha256, str)
            or not _HEX.fullmatch(self.evidence_sha256)
        ):
            raise StageVAttestationRejected("Stage V fixed original S49 S10 scope required")

    @classmethod
    def from_dict(cls, value: object) -> StageVGrantRequest:
        if not isinstance(value, dict) or value.keys() != _REQUEST_KEYS:
            raise StageVAttestationRejected("noncanonical run-scoped request fields")
        try:
            return cls(**value)
        except TypeError as exc:
            raise StageVAttestationRejected("invalid request fields") from exc


def _canonical(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")


def request_from_existing_world(
    *, run_id: str, closed: NormalActionClosedReadback,
    following_probe: MineflayerObservation,
) -> StageVGrantRequest:
    """Create request only from original source-shaped, Stage S typed evidence.

    This routine cannot independently authenticate a Python object passed
    to it. Signing approval must NEVER be equated with physical evidence.
    """
    if (
        not isinstance(closed, NormalActionClosedReadback)
        or not isinstance(following_probe, MineflayerObservation)
        or closed.consequence.after_observation is None
    ):
        raise StageVAttestationRejected("original terminal and later probe required")
    result = assess_stage_s_original_separation(
        closed, StageSPredeclaredSeparationRule(),
    )
    if (
        result.status not in (
            StageSSeparationClass.SEPARATION_INCREASED,
            StageSSeparationClass.SEPARATION_DECREASED,
        )
        or result.typed_s17 is None or result.typed_s17.feedback is None
        or result.entity_id is None
        or result.distance_before_m is None
        or result.distance_after_m is None
    ):
        raise StageVAttestationRejected("genuine-directional-shaped S17 only")
    typed = result.typed_s17
    world = closed.consequence
    before, after = world.before_observation, world.after_observation
    assert before is not None and after is not None
    if (
        following_probe.session_id != closed.original_probe.session_id
        or following_probe.kind != "probe"
        or following_probe.seq <= after.seq
        or following_probe.request_id is None
        or following_probe.provenance.source != "mineflayer"
        or following_probe.snapshot.nearby_entities_coverage.truncated
    ):
        raise StageVAttestationRejected("correlated later native probe required")
    next_prefix = f"s49-actual:{closed.original_probe.session_id}:event-"
    if not following_probe.request_id.startswith(next_prefix):
        raise StageVAttestationRejected("later probe not from original S49 event")
    later_event = following_probe.request_id.removeprefix(next_prefix)
    if (
        not later_event.isdecimal()
        or not after.seq < int(later_event) < following_probe.seq
    ):
        raise StageVAttestationRejected("later original event/native order mismatch")
    source = {
        "session_id": closed.original_probe.session_id,
        "original_seq": closed.original_probe.seq,
        "original_request_id": closed.original_probe.request_id,
        "action_id": closed.terminal.action_id,
        "binding_id": world.binding_id,
        "before_seq": before.seq, "after_seq": after.seq,
        "before_health": before.snapshot.health,
        "after_health": after.snapshot.health,
        "before_target_m": result.distance_before_m,
        "after_target_m": result.distance_after_m,
        "target_id": result.entity_id,
        "world_provenance": asdict(world.provenance),
        "outcome_ref": typed.outcome_ref,
        "feedback_id": typed.feedback.feedback_id,
        "next_probe_seq": following_probe.seq,
        "next_probe_request_id": following_probe.request_id,
    }
    digest = hashlib.sha256(_DOMAIN + _canonical(source)).hexdigest()
    return StageVGrantRequest(
        version=1, run_id=run_id,
        session_id=result.session_id, action_id=result.action_id,
        feedback_id=typed.feedback.feedback_id,
        direction=typed.feedback.direction.value,
        entity_id=result.entity_id, after_seq=after.seq,
        next_probe_seq=following_probe.seq,
        expected_revision=1, expected_value=4,
        proposed_value=5 if typed.feedback.direction is FeedbackDirection.INCREASE else 3,
        evidence_sha256=digest,
    )


def _openssl(*args: str, payload: bytes = b"") -> bytes:
    try:
        result = subprocess.run(
            ["openssl", *args], input=payload, capture_output=True,
            check=False, timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise StageVAttestationRejected("OpenSSL verifier/signer unavailable") from exc
    if result.returncode:
        raise StageVAttestationRejected(
            "OpenSSL signature operation rejected"
        )
    return result.stdout


def fingerprint_for_public_pem(public_key: bytes) -> str:
    if not isinstance(public_key, bytes) or b"BEGIN PUBLIC KEY" not in public_key:
        raise StageVAttestationRejected("externally provisioned public PEM required")
    return hashlib.sha256(public_key).hexdigest()


def _payload(request: StageVGrantRequest) -> bytes:
    return _DOMAIN + _canonical(asdict(request))


def sign_for_external_issuer_process(
    request: StageVGrantRequest, *, private_key_path: Path, public_key_path: Path,
) -> dict[str, object]:
    """Run in issuer-only process. Never share private_key_path with S10 owner."""
    if not isinstance(request, StageVGrantRequest):
        raise StageVAttestationRejected("typed request required")
    if not isinstance(private_key_path, Path) or not isinstance(public_key_path, Path):
        raise StageVAttestationRejected("issuer private/public PEM files required")
    public_key = public_key_path.read_bytes()
    signed = _openssl(
        "dgst", "-sha256", "-sign", str(private_key_path),
        payload=_payload(request),
    )
    return {
        "request": asdict(request),
        "signature_b64": base64.b64encode(signed).decode("ascii"),
        "key_fingerprint_sha256": fingerprint_for_public_pem(public_key),
    }


class StageVPinnedGrantVerifier:
    """One-run replay guard with trust anchor supplied independently of grant.

    The caller MUST independently trust and pin the PEM/public fingerprint.
    A key generated by the requester has no issuer authority on its own.
    """

    def __init__(
        self, *, pinned_public_pem: bytes, pinned_fingerprint: str,
        expected_run_id: str,
    ) -> None:
        if (
            not isinstance(pinned_fingerprint, str)
            or not _HEX.fullmatch(pinned_fingerprint)
            or fingerprint_for_public_pem(pinned_public_pem) != pinned_fingerprint
            or not isinstance(expected_run_id, str)
            or not _ID.fullmatch(expected_run_id)
        ):
            raise StageVAttestationRejected("independent pinned key and run required")
        self._public = pinned_public_pem
        self._fingerprint = pinned_fingerprint
        self._run = expected_run_id
        self._used: set[tuple[str, str, str]] = set()

    def verify_once(
        self, envelope: object, *, expected: StageVGrantRequest,
    ) -> StageVGrantRequest:
        if (
            not isinstance(envelope, dict) or envelope.keys() != _ENVELOPE_KEYS
            or not isinstance(expected, StageVGrantRequest)
            or not isinstance(envelope.get("key_fingerprint_sha256"), str)
            or envelope["key_fingerprint_sha256"] != self._fingerprint
        ):
            raise StageVAttestationRejected("wrong signed grant envelope / trust anchor")
        request = StageVGrantRequest.from_dict(envelope["request"])
        if request != expected or request.run_id != self._run:
            raise StageVAttestationRejected("run or exact source binding mismatch")
        key = (request.run_id, request.action_id, request.feedback_id)
        if key in self._used:
            raise StageVAttestationRejected("run-scoped grant replay")
        signature = envelope.get("signature_b64")
        if not isinstance(signature, str):
            raise StageVAttestationRejected("missing detached signature")
        try:
            sig = base64.b64decode(signature, validate=True)
        except (ValueError, base64.binascii.Error) as exc:
            raise StageVAttestationRejected("malformed signature encoding") from exc
        with tempfile.TemporaryDirectory(prefix="stage-v-public-verify-") as root:
            public_path = Path(root) / "pinned-public.pem"
            signature_path = Path(root) / "signed.bin"
            public_path.write_bytes(self._public)
            signature_path.write_bytes(sig)
            _openssl(
                "dgst", "-sha256", "-verify", str(public_path),
                "-signature", str(signature_path), payload=_payload(request),
            )
        self._used.add(key)
        return request


def main(argv: list[str] | None = None) -> int:
    """Issuer CLI: subprocess-only DEV proof. Does not authorize live S10."""
    parser = argparse.ArgumentParser(description="Stage V DEV issuer process")
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--private-key", type=Path, required=True)
    parser.add_argument("--public-key", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    request = StageVGrantRequest.from_dict(json.loads(args.request.read_text()))
    envelope = sign_for_external_issuer_process(
        request, private_key_path=args.private_key, public_key_path=args.public_key,
    )
    args.output.write_bytes(_canonical(envelope) + b"\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
