"""AC-B B7 offline cross-object signed World receipt + separate grant handoff.

Imports ONLY actual committed mainline Memory and Provenance. Source and grant
keys, current epoch and revocation state are external trust inputs, never
retained owner fields. This is NOT production-grade public-key attestation,
LearningFeedback commitment, Habit acquisition, or physical Action authority.
"""
from __future__ import annotations

import hmac
import json
import secrets
import tempfile
from dataclasses import asdict, dataclass
from enum import Enum
from hashlib import sha256
from pathlib import Path
from types import MappingProxyType

from relay_self.persistent_cognition import (
    IdentitySpecification,
    Memory,
    PersistentCognition,
    load_persistent_cognition,
    save_persistent_cognition,
)
from relay_self.provenance import Provenance

SOURCE = "b7.offline-world.signed-outcome"
CONTEXTS = ((0, 0), (0, 1), (1, 0), (1, 1))
RECEIPT_FIELDS = frozenset({
    "event_id", "session", "revision", "sequence", "a", "b",
    "action", "success", "kind", "digest", "mac",
})


class InvalidEvidence(ValueError):
    """Unverified or malformed evidence/authority is not actionable."""


class Status(str, Enum):
    FOUND = "FOUND"
    UNKNOWN = "UNKNOWN"
    CONFLICT = "CONFLICT"
    STALE = "STALE"
    NO_SOURCE_WITNESS = "NO_SOURCE_WITNESS"
    DENIED = "DENIED"
    ADMITTED = "ADMITTED"
    QUARANTINED = "QUARANTINED"


def _binary(name: str, val: object) -> None:
    if type(val) is not int or val not in (0, 1):
        raise InvalidEvidence(f"{name} must be 0/1 exact int")


def _nat(name: str, val: object) -> None:
    if type(val) is not int or val < 0:
        raise InvalidEvidence(f"{name} must be nonnegative exact int")


def _token(name: str, val: object) -> None:
    if not isinstance(val, str) or not val or val.strip() != val:
        raise InvalidEvidence(f"{name} must be a nonempty canonical token")
    if any(ch.isspace() for ch in val):
        raise InvalidEvidence(f"{name} contains whitespace")


def _key(secret: bytes) -> bytes:
    if not isinstance(secret, bytes) or len(secret) < 32:
        raise InvalidEvidence("separate 32-byte-or-longer secret required")
    return secret


def _canon(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False).encode("utf-8")


def _proof(secret: bytes, value: object) -> str:
    return hmac.new(_key(secret), _canon(value), sha256).hexdigest()


def _no_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for name, value in pairs:
        if name in result:
            raise InvalidEvidence("repeated JSON field")
        result[name] = value
    return result


@dataclass(frozen=True, slots=True)
class SignedReceipt:
    event_id: str
    session: str
    revision: int
    sequence: int
    a: int
    b: int
    action: int
    success: bool
    kind: str
    digest: str
    mac: str

    def payload(self) -> dict[str, object]:
        d = asdict(self)
        d.pop("digest")
        d.pop("mac")
        return d


@dataclass(slots=True)
class CurrentEpoch:
    """Trusted externally supplied latest epoch; not inferred from receipt JSON."""

    session: str
    revision: int = 0

    def __post_init__(self) -> None:
        _token("epoch session", self.session)
        _nat("epoch revision", self.revision)

    def advance(self) -> None:
        self.revision += 1


class WorldSource:
    """Independently executes reset Actions, then MAC-signs real outcomes."""

    def __init__(self, secret: bytes, session: str = "b7-world") -> None:
        self.__secret = _key(secret)
        _token("world session", session)
        self.session = session
        self.revision = 0
        self.__flip = 0
        self.__sequence = 0

    def act(self, a: int, b: int, action: int) -> SignedReceipt:
        _binary("a", a)
        _binary("b", b)
        _binary("action", action)
        self.__sequence += 1
        event_id = f"{self.session}:event:{self.__sequence}"
        body = {
            "event_id": event_id,
            "session": self.session,
            "revision": self.revision,
            "sequence": self.__sequence,
            "a": a, "b": b, "action": action,
            "success": action == (a ^ b ^ self.__flip),
            "kind": "OBSERVED_ACTION",
        }
        digest = sha256(_canon(body)).hexdigest()
        mac = _proof(self.__secret, {**body, "digest": digest})
        return SignedReceipt(**body, digest=digest, mac=mac)

    def change_rule(self, *, announce: bool) -> None:
        self.__flip ^= 1
        if announce:
            self.revision += 1

    @property
    def action_count(self) -> int:
        return self.__sequence


class EvidenceVerifier:
    """Verify new Python objects reconstructed from a signed source bundle.

    HMAC is CONDITIONAL on an independently trustworthy secret/epoch oracle;
    merely possessing serialized Memory + receipt JSON never grants a verifier.
    """

    def __init__(self, source_key: bytes, epoch: CurrentEpoch) -> None:
        self.__key = _key(source_key)
        if not isinstance(epoch, CurrentEpoch):
            raise InvalidEvidence("independent epoch authority required")
        self.epoch = epoch

    def verify(self, receipt: SignedReceipt) -> None:
        if not isinstance(receipt, SignedReceipt):
            raise InvalidEvidence("missing signed source receipt")
        for field in ("event_id", "session"):
            _token(field, getattr(receipt, field))
        for field in ("revision", "sequence"):
            _nat(field, getattr(receipt, field))
        if receipt.sequence < 1 or receipt.event_id != (
            f"{receipt.session}:event:{receipt.sequence}"
        ):
            raise InvalidEvidence("invalid event identity / sequence")
        for field in ("a", "b", "action"):
            _binary(field, getattr(receipt, field))
        if type(receipt.success) is not bool or receipt.kind != "OBSERVED_ACTION":
            raise InvalidEvidence("not an observed binary Action outcome")
        if (
            not isinstance(receipt.digest, str) or len(receipt.digest) != 64
            or not isinstance(receipt.mac, str) or len(receipt.mac) != 64
        ):
            raise InvalidEvidence("malformed digest/MAC")
        if receipt.session != self.epoch.session or receipt.revision != self.epoch.revision:
            raise InvalidEvidence("source receipt wrong session or stale epoch")
        body = receipt.payload()
        expected_digest = sha256(_canon(body)).hexdigest()
        if not hmac.compare_digest(receipt.digest, expected_digest):
            raise InvalidEvidence("source digest mismatch")
        if not hmac.compare_digest(receipt.mac, _proof(
            self.__key, {**body, "digest": receipt.digest},
        )):
            raise InvalidEvidence("World source HMAC not verified")


def encode_receipts(items: tuple[SignedReceipt, ...]) -> str:
    if not isinstance(items, tuple) or not all(
        isinstance(x, SignedReceipt) for x in items
    ):
        raise InvalidEvidence("receipt tuple expected")
    return json.dumps([asdict(x) for x in items], sort_keys=True, indent=2)


def decode_receipts(raw: str) -> tuple[SignedReceipt, ...]:
    if not isinstance(raw, str):
        raise InvalidEvidence("source receipt JSON must be text")
    try:
        items = json.loads(raw, object_pairs_hook=_no_duplicate_keys)
    except (ValueError, TypeError) as exc:
        raise InvalidEvidence("malformed source receipt JSON") from exc
    if not isinstance(items, list):
        raise InvalidEvidence("source JSON must be an array")
    receipts = []
    for entry in items:
        if not isinstance(entry, dict) or set(entry) != RECEIPT_FIELDS:
            raise InvalidEvidence("source receipt fields not exact")
        receipts.append(SignedReceipt(**entry))
    return tuple(receipts)


def observe_all(world: WorldSource) -> tuple[SignedReceipt, ...]:
    return tuple(
        world.act(a, b, action) for a, b in CONTEXTS for action in (0, 1)
    )


def retain_fixture(receipts: tuple[SignedReceipt, ...]) -> PersistentCognition:
    """Explicit TEST-FIXTURE admission. The read-only bridge NEVER retains."""
    identity = IdentitySpecification(
        self_id="b7-fixture-self",
        directives=("Do not treat Memory prose as World attestation.",),
        provenance=Provenance("b7.fixture.identity", "identity"),
    )
    owner = PersistentCognition(identity)
    for receipt in receipts:
        owner = owner.retain_memory(Memory(
            memory_id=f"memory:{receipt.event_id}",
            content="Prediction: Action 1 always succeeds (untrusted).",
            source_provenance=Provenance(SOURCE, receipt.event_id),
            integration_provenance=Provenance(
                "b7.fixture.integration", f"integration:{receipt.event_id}",
            ),
        ))
    return owner


@dataclass(frozen=True, slots=True)
class ProposalDraft:
    a: int
    b: int
    action: int
    candidate_ref: str
    target_id: str
    session: str
    revision: int
    observed_ids: tuple[str, ...]
    memory_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class DraftResult:
    status: Status
    draft: ProposalDraft | None


class ReadOnlyBridge:
    """Derive *schema-only* candidate; no S10/S11/S17 import or owner update."""

    def __init__(
        self,
        snapshot: PersistentCognition,
        receipts: tuple[SignedReceipt, ...],
        verifier: EvidenceVerifier | None,
        *, quarantined: bool = False,
    ) -> None:
        if not isinstance(snapshot, PersistentCognition) or not isinstance(
            receipts, tuple
        ):
            raise InvalidEvidence("mainline Memory snapshot and receipt tuple required")
        if verifier is not None and not isinstance(verifier, EvidenceVerifier):
            raise InvalidEvidence("trusted verifier required")
        self.snapshot = snapshot
        self.verifier = verifier
        self.quarantined = quarantined
        self.snapshot_epoch = (
            verifier.epoch.revision if verifier is not None else None
        )
        self.snapshot_session = (
            verifier.epoch.session if verifier is not None else None
        )
        if verifier is None:
            self.rows = MappingProxyType({})
            return
        source_map: dict[str, SignedReceipt] = {}
        for receipt in receipts:
            verifier.verify(receipt)
            if receipt.event_id in source_map:
                raise InvalidEvidence("duplicate signed source event")
            source_map[receipt.event_id] = receipt
        memories: dict[str, Memory] = {}
        witnessed: set[str] = set()
        for memory in snapshot.memories:
            if memory.source_provenance.source != SOURCE:
                continue
            event_id = memory.source_provenance.reference
            if event_id in witnessed:
                raise InvalidEvidence("two retained Memories alias one source event")
            witnessed.add(event_id)
            if event_id not in source_map:
                raise InvalidEvidence("retained source pointer lacks signed witness")
            memories[event_id] = memory
        if set(source_map) != witnessed:
            # Admissible World evidence must have a unique retained pointer;
            # no extra receipt is silently admitted as a Memory observation.
            raise InvalidEvidence("unretained or missing source evidence in bundle")
        pair_rows: dict[tuple[int, int], list[tuple[SignedReceipt, Memory]]] = {}
        keys: set[tuple[int, int, int]] = set()
        for event_id, mem in memories.items():
            receipt = source_map[event_id]
            key = (receipt.a, receipt.b, receipt.action)
            if key in keys:
                raise InvalidEvidence("same cue/action has duplicate/conflicting outcomes")
            keys.add(key)
            pair_rows.setdefault((receipt.a, receipt.b), []).append((receipt, mem))
        self.rows = MappingProxyType({
            key: tuple(value) for key, value in pair_rows.items()
        })

    def draft(
        self, a: int, b: int, *, target_id: str,
        session: str, revision: int,
    ) -> DraftResult:
        _binary("a", a)
        _binary("b", b)
        _token("target_id", target_id)
        if self.quarantined:
            return DraftResult(Status.QUARANTINED, None)
        if self.verifier is None:
            return DraftResult(Status.NO_SOURCE_WITNESS, None)
        epoch = self.verifier.epoch
        if (
            session != self.snapshot_session or revision != self.snapshot_epoch
            or epoch.session != self.snapshot_session
            or epoch.revision != self.snapshot_epoch
        ):
            return DraftResult(Status.STALE, None)
        rows = self.rows.get((a, b), ())
        if len(rows) != 2:
            return DraftResult(Status.UNKNOWN, None)
        actions = {r.action for r, _ in rows}
        if actions != {0, 1} or sum(int(r.success) for r, _ in rows) != 1:
            return DraftResult(Status.CONFLICT, None)
        selected = next(r.action for r, _ in rows if r.success)
        return DraftResult(Status.FOUND, ProposalDraft(
            a, b, selected, f"action:{selected}", target_id,
            session, revision,
            tuple(sorted(r.event_id for r, _ in rows)),
            tuple(sorted(m.memory_id for _, m in rows)),
        ))

    def reconsider(self, receipt: SignedReceipt) -> ReadOnlyBridge:
        if self.verifier is None:
            raise InvalidEvidence("no source witness for reconsideration")
        self.verifier.verify(receipt)
        prior = self.rows.get((receipt.a, receipt.b), ())
        old = [r for r, _ in prior if r.action == receipt.action]
        if (
            len(old) != 1 or old[0].success != receipt.success
            or self.quarantined
        ):
            changed = object.__new__(ReadOnlyBridge)
            changed.snapshot = self.snapshot
            changed.verifier = self.verifier
            changed.quarantined = True
            changed.snapshot_epoch = self.snapshot_epoch
            changed.snapshot_session = self.snapshot_session
            changed.rows = self.rows
            return changed
        return self


@dataclass(frozen=True, slots=True)
class SignedGrant:
    nonce: str
    target_id: str
    session: str
    revision: int
    observed_ids: tuple[str, ...]
    candidate_ref: str
    granted: bool
    mac: str

    def body(self) -> dict[str, object]:
        value = asdict(self)
        value.pop("mac")
        return value


@dataclass(frozen=True, slots=True)
class ReadOnlyHandoff:
    target_id: str
    session: str
    revision: int
    cue_features: tuple[tuple[str, int], ...]
    action_candidate_ref: str
    proposed_feedback_direction: str
    source_outcome_refs: tuple[str, ...]
    retained_memory_ids: tuple[str, ...]
    grant_nonce: str
    non_authoritative: bool = True


@dataclass(frozen=True, slots=True)
class Admission:
    status: Status
    handoff: ReadOnlyHandoff | None


class HandoffGate:
    """Explicit separate offline issuer and verifier for schema-only handoff.

    The HMAC key and mutable revoked/spent nonce sets are NOT held in Memory.
    This is not a real user permission, S10 authority, or distributed ledger.
    """

    def __init__(self, grant_key: bytes, epoch: CurrentEpoch) -> None:
        self.__key = _key(grant_key)
        if not isinstance(epoch, CurrentEpoch):
            raise InvalidEvidence("trusted independent current epoch required")
        self.epoch = epoch
        self._revoked: set[str] = set()
        self._spent: set[str] = set()

    def issue(self, draft: ProposalDraft, *, granted: bool = True) -> SignedGrant:
        if not isinstance(draft, ProposalDraft) or type(granted) is not bool:
            raise InvalidEvidence("explicit typed grant issuance required")
        if draft.session != self.epoch.session or draft.revision != self.epoch.revision:
            raise InvalidEvidence("cannot issue from stale proposal")
        body = {
            "nonce": secrets.token_hex(16),
            "target_id": draft.target_id,
            "session": draft.session,
            "revision": draft.revision,
            "observed_ids": draft.observed_ids,
            "candidate_ref": draft.candidate_ref,
            "granted": granted,
        }
        return SignedGrant(**body, mac=_proof(self.__key, body))

    def revoke(self, nonce: str) -> None:
        _token("nonce", nonce)
        self._revoked.add(nonce)

    def admit(
        self, bridge: ReadOnlyBridge, proposal: DraftResult,
        grant: SignedGrant | None,
    ) -> Admission:
        if not isinstance(bridge, ReadOnlyBridge) or not isinstance(
            proposal, DraftResult
        ):
            raise InvalidEvidence("qualified read-only bridge and draft required")
        if proposal.status is not Status.FOUND or proposal.draft is None:
            return Admission(Status.DENIED, None)
        draft = proposal.draft
        # Require current external-source attestation, not a forged draft.
        current = bridge.draft(
            draft.a, draft.b, target_id=draft.target_id,
            session=draft.session, revision=draft.revision,
        )
        if current != proposal or current.status is not Status.FOUND:
            return Admission(Status.DENIED, None)
        if not isinstance(grant, SignedGrant):
            return Admission(Status.DENIED, None)
        if (
            not isinstance(grant.mac, str) or len(grant.mac) != 64
            or type(grant.granted) is not bool
            or not hmac.compare_digest(grant.mac, _proof(self.__key, grant.body()))
        ):
            return Admission(Status.DENIED, None)
        if (
            not grant.granted or grant.nonce in self._revoked
            or grant.nonce in self._spent
            or draft.session != self.epoch.session
            or draft.revision != self.epoch.revision
            or grant.session != draft.session
            or grant.revision != draft.revision
            or grant.target_id != draft.target_id
            or grant.observed_ids != draft.observed_ids
            or grant.candidate_ref != draft.candidate_ref
        ):
            return Admission(Status.DENIED, None)
        self._spent.add(grant.nonce)
        return Admission(Status.ADMITTED, ReadOnlyHandoff(
            target_id=draft.target_id,
            session=draft.session,
            revision=draft.revision,
            cue_features=(("a", draft.a), ("b", draft.b)),
            action_candidate_ref=draft.candidate_ref,
            proposed_feedback_direction="increase",
            source_outcome_refs=draft.observed_ids,
            retained_memory_ids=draft.memory_ids,
            grant_nonce=grant.nonce,
        ))


def run_fixture() -> dict[str, object]:
    """One deterministic scenario; signed keys intentionally ephemeral."""
    source_key = secrets.token_bytes(32)
    grant_key = secrets.token_bytes(32)
    world = WorldSource(source_key)
    epoch = CurrentEpoch(world.session, world.revision)
    original = observe_all(world)
    owner = retain_fixture(original)
    serial = encode_receipts(original)
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "b7-owner.json"
        save_persistent_cognition(path, owner)
        restored = load_persistent_cognition(path)
        recovered_receipts = decode_receipts(serial)
        verifier = EvidenceVerifier(source_key, CurrentEpoch(world.session, 0))
        bridge = ReadOnlyBridge(restored, recovered_receipts, verifier)
        gate = HandoffGate(grant_key, epoch)
        drafts = [
            bridge.draft(a, b, target_id="b7-learning-target",
                         session=world.session, revision=0)
            for a, b in CONTEXTS
        ]
        denied = sum(gate.admit(bridge, draft, None).status is Status.DENIED
                     for draft in drafts)
        handed = [gate.admit(bridge, draft, gate.issue(draft.draft)) for draft in drafts]
        admitted = sum(approved.status is Status.ADMITTED for approved in handed)
        spare_old_grants = [gate.issue(draft.draft) for draft in drafts]
        candidate_actions = [draft.draft.action for draft in drafts]
        fresh_objects = all(a is not b for a, b in zip(original, recovered_receipts))
        independent_json = restored is not owner and restored == owner
        # Fresh-process-like verifier/key root: different Python objects
        # from source/original ledger, no event identity/object pointer checks.
        fresh_verifier = EvidenceVerifier(source_key, epoch)
        fresh_bridge = ReadOnlyBridge(restored, decode_receipts(serial),
                                      fresh_verifier)
        equivalent = sum(
            fresh_bridge.draft(a, b, target_id="b7-learning-target",
                               session=world.session, revision=0) == d
            for (a, b), d in zip(CONTEXTS, drafts)
        )
        world.change_rule(announce=True)
        epoch.advance()
        # Old verifier's separate copy epoch did not advance. The bridge
        # cannot infer fresh World revision without a live trusted oracle!
        # Explicitly check live-root-connected bridge, NOT the stale mock.
        stale = sum(fresh_bridge.draft(
            a, b, target_id="b7-learning-target", session=world.session,
            revision=0).status is Status.STALE for a, b in CONTEXTS)
        old_grants_blocked = sum(
            gate.admit(fresh_bridge, draft, old).status is Status.DENIED
            for draft, old in zip(drafts, spare_old_grants)
        )
        shifted = observe_all(world)
        shifted_owner = retain_fixture(shifted)
        shifted_bridge = ReadOnlyBridge(
            shifted_owner, decode_receipts(encode_receipts(shifted)),
            EvidenceVerifier(source_key, epoch),
        )
        new_drafts = [
            shifted_bridge.draft(a, b, target_id="b7-learning-target",
                                 session=world.session, revision=1)
            for a, b in CONTEXTS
        ]
        recovered = sum(
            gate.admit(shifted_bridge, d, gate.issue(d.draft)).status is Status.ADMITTED
            for d in new_drafts
        )
        world.change_rule(announce=False)
        first = new_drafts[0].draft
        silent = world.act(first.a, first.b, first.action)
        stopped = shifted_bridge.reconsider(silent)
        quarantine = stopped.draft(
            first.a, first.b, target_id=first.target_id,
            session=world.session, revision=1,
        ).status is Status.QUARANTINED
    success = (
        len(original) == 8 and all(d.status is Status.FOUND for d in drafts)
        and candidate_actions == [0, 1, 1, 0]
        and denied == admitted == equivalent == stale == recovered == 4
        and old_grants_blocked == 4 and independent_json
        and fresh_objects and quarantine
    )
    return {
        "classification": (
            "SERIALIZED_SOURCE_AND_EXPLICIT_HANDOFF_GATE_QUALIFIED"
            if success else "UNDETERMINED"
        ),
        "source_observed_actions": len(original),
        "retained_mainline_memories": len(owner.memories),
        "signed_new_python_objects": fresh_objects,
        "retained_json_roundtrip": independent_json,
        "qualified_drafts": sum(d.status is Status.FOUND for d in drafts),
        "denied_without_grant": denied,
        "admitted_with_grant": admitted,
        "rehydrated_equivalent_drafts": equivalent,
        "announced_shift_stale_with_live_epoch": stale,
        "rev0_grants_denied_after_shift": old_grants_blocked,
        "requalification_actions": len(shifted),
        "readmitted_after_requalification": recovered,
        "silent_observed_mismatch_quarantined": quarantine,
        "source_actions_during_draft_queries": 0,
    }


if __name__ == "__main__":
    print(json.dumps(run_fixture(), indent=2, sort_keys=True))
