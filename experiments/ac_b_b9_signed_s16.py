"""AC-B B9: a strict signed-evidence cross-check BEFORE unchanged S16 interpretation.

This standalone offline fixture uses exact frozen unmerged S17/S16 types. It
does not turn B7 generic binary success receipts into S16 WorldConsequence
and it never issues Action, closes its lifecycle, learns, or commits Habits.
HMAC source attestation remains conditional on external source key and epoch.
"""
from __future__ import annotations

import hmac
import json
import secrets
from dataclasses import asdict, dataclass
from hashlib import sha256

from adapters.mineflayer.action_outcome import interpret_world_consequence
from adapters.mineflayer.execution import (
    WorldConsequence,
    build_mineflayer_command,
)
from relay_self.action import ActionLifecycle
from relay_self.action_outcome import ActionOutcomeInterpretation
from relay_self.execution_binding import ExecutionBindingResult
from relay_self.provenance import Provenance


class UnqualifiedWorldEvidence(ValueError):
    """Fail closed without altering the S16 Action authority owner."""


@dataclass(slots=True)
class TrustedWorldEpoch:
    """External live epoch oracle; receipt alone cannot establish freshness."""

    session_id: str
    revision: int

    def __post_init__(self) -> None:
        _token("session_id", self.session_id)
        _nonnegative("revision", self.revision)

    def advance(self) -> None:
        self.revision += 1


@dataclass(frozen=True, slots=True)
class SignedS16Evidence:
    event_id: str
    session_id: str
    revision: int
    sequence: int
    action_id: str
    binding_id: str
    action_ref: str
    source_status: str
    world_source: str
    world_reference: str
    consequence_digest: str
    mac: str

    def signed_body(self) -> dict[str, object]:
        result = asdict(self)
        result.pop("mac")
        return result


EXACT_KEYS = frozenset(SignedS16Evidence.__dataclass_fields__)


def _token(name: str, value: object) -> None:
    if (
        type(value) is not str or not value
        or value != value.strip() or any(x.isspace() for x in value)
    ):
        raise UnqualifiedWorldEvidence(f"invalid {name}")


def _nonnegative(name: str, value: object) -> None:
    if type(value) is not int or value < 0:
        raise UnqualifiedWorldEvidence(f"invalid {name}")


def _secret(secret: object) -> bytes:
    if type(secret) is not bytes or len(secret) < 32:
        raise UnqualifiedWorldEvidence("trusted 32-byte source secret required")
    return secret


def _canonical(value: object) -> bytes:
    try:
        return json.dumps(
            value, sort_keys=True, separators=(",", ":"),
            ensure_ascii=False, allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise UnqualifiedWorldEvidence("non-canonical source data") from exc


def _digest(consequence: WorldConsequence) -> str:
    if not isinstance(consequence, WorldConsequence):
        raise UnqualifiedWorldEvidence(
            "B7 generic receipt is NOT an S16 WorldConsequence"
        )
    return sha256(_canonical(asdict(consequence))).hexdigest()


def _mac(key: bytes, value: object) -> str:
    return hmac.new(_secret(key), _canonical(value), sha256).hexdigest()


def _unique_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for name, value in pairs:
        if name in result:
            raise UnqualifiedWorldEvidence("duplicate JSON key")
        result[name] = value
    return result


def serialize_signed_evidence(item: SignedS16Evidence) -> str:
    if not isinstance(item, SignedS16Evidence):
        raise UnqualifiedWorldEvidence("signed S16 evidence required")
    return json.dumps(asdict(item), indent=2, sort_keys=True)


def parse_signed_evidence(value: str) -> SignedS16Evidence:
    if not isinstance(value, str):
        raise UnqualifiedWorldEvidence("serialized envelope text required")
    try:
        raw = json.loads(value, object_pairs_hook=_unique_pairs)
    except (ValueError, TypeError) as exc:
        raise UnqualifiedWorldEvidence("bad signed source JSON") from exc
    if type(raw) is not dict or set(raw) != EXACT_KEYS:
        raise UnqualifiedWorldEvidence("wrong signed envelope fields")
    return SignedS16Evidence(**raw)


class OfflineS16SourceIssuer:
    """Test-only MAC issuer over an ALREADY EXISTING typed S16 consequence.

    The issuer does not execute the physical World. A trusted independent
    source would be needed to issue these receipts in production.
    """

    def __init__(self, key: bytes, session: str) -> None:
        self.__key = _secret(key)
        _token("issuer session", session)
        self.session = session
        self.revision = 0
        self.__sequence = 0

    def sign(self, consequence: WorldConsequence) -> SignedS16Evidence:
        digest = _digest(consequence)
        if consequence.session_id != self.session:
            raise UnqualifiedWorldEvidence("issuer cannot sign another session")
        self.__sequence += 1
        fields = {
            "event_id": f"{self.session}:s16:{self.__sequence}",
            "session_id": self.session,
            "revision": self.revision,
            "sequence": self.__sequence,
            "action_id": consequence.action_id,
            "binding_id": consequence.binding_id,
            "action_ref": consequence.action_ref,
            "source_status": consequence.status.value,
            "world_source": consequence.provenance.source,
            "world_reference": consequence.provenance.reference,
            "consequence_digest": digest,
        }
        return SignedS16Evidence(**fields, mac=_mac(self.__key, fields))

    def advance(self) -> None:
        self.revision += 1


class ExternalS16EvidenceGate:
    """Verify source MAC/currentness, then call the unchanged actual S16 API.

    A single gate instance spends each event_id once. This is only LOCAL
    replay protection; there is no durable or distributed nonce journal.
    """

    def __init__(self, key: bytes, live_epoch: TrustedWorldEpoch) -> None:
        self.__key = _secret(key)
        if not isinstance(live_epoch, TrustedWorldEpoch):
            raise UnqualifiedWorldEvidence("external trusted epoch required")
        self.live_epoch = live_epoch
        self._spent: set[str] = set()

    def qualify(
        self,
        issued: ActionLifecycle,
        binding: ExecutionBindingResult,
        consequence: WorldConsequence,
        receipt: SignedS16Evidence,
    ) -> ActionOutcomeInterpretation:
        digest = _digest(consequence)
        if not isinstance(receipt, SignedS16Evidence):
            raise UnqualifiedWorldEvidence("B7 generic success cannot attest S16")
        for field in (
            "event_id", "session_id", "action_id", "binding_id", "action_ref",
            "source_status", "world_source", "world_reference",
        ):
            _token(field, getattr(receipt, field))
        for field in ("revision", "sequence"):
            _nonnegative(field, getattr(receipt, field))
        if receipt.sequence == 0 or receipt.event_id != (
            f"{receipt.session_id}:s16:{receipt.sequence}"
        ):
            raise UnqualifiedWorldEvidence("bad source event lineage")
        if not isinstance(receipt.mac, str) or len(receipt.mac) != 64:
            raise UnqualifiedWorldEvidence("bad source proof")
        if not isinstance(receipt.consequence_digest, str) or (
            len(receipt.consequence_digest) != 64
        ):
            raise UnqualifiedWorldEvidence("bad consequence digest")
        if receipt.event_id in self._spent:
            raise UnqualifiedWorldEvidence("source receipt already consumed")
        if (
            receipt.session_id != self.live_epoch.session_id
            or receipt.revision != self.live_epoch.revision
        ):
            raise UnqualifiedWorldEvidence("stale or wrong source epoch")
        if not hmac.compare_digest(
            receipt.mac, _mac(self.__key, receipt.signed_body())
        ):
            raise UnqualifiedWorldEvidence("unqualified source MAC")
        if not hmac.compare_digest(receipt.consequence_digest, digest):
            raise UnqualifiedWorldEvidence("WorldConsequence digest mismatch")
        if (
            receipt.session_id != consequence.session_id
            or receipt.action_id != consequence.action_id
            or receipt.binding_id != consequence.binding_id
            or receipt.action_ref != consequence.action_ref
            or receipt.source_status != consequence.status.value
            or receipt.world_source != consequence.provenance.source
            or receipt.world_reference != consequence.provenance.reference
        ):
            raise UnqualifiedWorldEvidence("signed World/Action lineage mismatch")
        if not isinstance(issued, ActionLifecycle) or not isinstance(
            binding, ExecutionBindingResult
        ):
            raise UnqualifiedWorldEvidence("actual issued Action and binding required")
        # Prevalidate the unchanged S15 issued Action/binding authority.
        command = build_mineflayer_command(issued, binding)
        if (
            command.action_id != receipt.action_id
            or command.binding_id != receipt.binding_id
            or command.action_ref != receipt.action_ref
        ):
            raise UnqualifiedWorldEvidence("issued Action mismatches signed source")
        # The frozen S16 interpreter checks full before/dispatch/cleanup/after
        # evidence session and command lineage, not a generic success bit.
        interpretation = interpret_world_consequence(
            issued, binding, consequence,
            provenance=Provenance("ac-b9-offline-signed-s16", receipt.event_id),
        )
        self._spent.add(receipt.event_id)
        return interpretation


def new_fixture_keys() -> bytes:
    return secrets.token_bytes(32)
