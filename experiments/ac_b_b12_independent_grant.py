"""AC-B B12: independently scoped EXPERIMENTAL S11 grant; S10 is NOT S11.

Use exact existing S10 LearningCommitResult and S11 HabitRepertoire types.
A real S17 ActionFeedbackCriterion can authorize S10 feedback orientation,
but that scalar change does NOT identify B11 cue/action source witnesses.
No production Habit owner authority or physical World attestation is claimed.
"""
from __future__ import annotations

import hmac
import json
from dataclasses import asdict, dataclass
from hashlib import sha256

from experiments.ac_b_b11_governed_habit import (
    ExperimentHabitAuthority,
    HabitAcquisitionDraft,
    QualifiedLedger,
    UnqualifiedHabitAcquisition,
    commit_experiment_habit,
    grant_test_authority,
    propose_habit,
)
from relay_self.habit import HabitRepertoire
from relay_self.learning import LearningCommitResult

GRANT_KIND = "B12_INDEPENDENT_S11_EXPERIMENT_GRANT_V1"
NO_SHARED_SOURCE = "NO_SHARED_WORLD_CUE_WITNESSES"


class InvalidIndependentHabitGrant(ValueError):
    """Fail closed: S10, B11 plain approval, or text cannot be a B12 grant."""


def _key(value: object) -> bytes:
    if type(value) is not bytes or len(value) < 32:
        raise InvalidIndependentHabitGrant("external S11 key must be 32+ bytes")
    return value


def _canonical(obj: object) -> bytes:
    try:
        return json.dumps(
            obj, sort_keys=True, separators=(",", ":"), allow_nan=False,
            ensure_ascii=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise InvalidIndependentHabitGrant("noncanonical grant value") from exc


def _proposal_digest(draft: HabitAcquisitionDraft) -> str:
    if not isinstance(draft, HabitAcquisitionDraft):
        raise InvalidIndependentHabitGrant("actual B11 typed proposal required")
    return sha256(_canonical(asdict(draft))).hexdigest()


def _sign(key: bytes, body: object) -> str:
    return hmac.new(_key(key), _canonical(body), sha256).hexdigest()


@dataclass(frozen=True, slots=True)
class SignedHabitGrant:
    kind: str
    grant_id: str
    owner_id: str
    expected_revision: int
    proposal_id: str
    source_session: str
    source_revision: int
    observed_ids: tuple[str, str]
    a: int
    b: int
    candidate_ref: str
    proposal_digest: str
    granted: bool
    mac: str

    def body(self) -> dict[str, object]:
        result = asdict(self)
        result.pop("mac")
        return result


def _expected_body(
    draft: HabitAcquisitionDraft, *, granted: bool,
) -> dict[str, object]:
    if type(granted) is not bool:
        raise InvalidIndependentHabitGrant("typed approval flag required")
    return {
        "kind": GRANT_KIND,
        "grant_id": f"b12-s11:{draft.proposal_id}",
        "owner_id": draft.owner_id,
        "expected_revision": draft.expected_revision,
        "proposal_id": draft.proposal_id,
        "source_session": draft.source_session,
        "source_revision": draft.source_revision,
        "observed_ids": draft.observed_ids,
        "a": draft.a,
        "b": draft.b,
        "candidate_ref": draft.rule.candidate_ref,
        "proposal_digest": _proposal_digest(draft),
        "granted": granted,
    }


class OfflineIndependentS11Issuer:
    """Offline mock of an independent grant holder, NOT secure key custody."""

    def __init__(self, secret: bytes) -> None:
        self.__secret = _key(secret)

    def grant(
        self, draft: HabitAcquisitionDraft, *, granted: bool = True,
    ) -> SignedHabitGrant:
        body = _expected_body(draft, granted=granted)
        return SignedHabitGrant(**body, mac=_sign(self.__secret, body))


def serialize_grant(grant: SignedHabitGrant) -> str:
    if not isinstance(grant, SignedHabitGrant):
        raise InvalidIndependentHabitGrant("signed grant required")
    return json.dumps(asdict(grant), sort_keys=True)


def _unique_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for name, value in pairs:
        if name in result:
            raise InvalidIndependentHabitGrant("duplicate grant JSON key")
        result[name] = value
    return result


def parse_grant(raw: str) -> SignedHabitGrant:
    if type(raw) is not str:
        raise InvalidIndependentHabitGrant("serialized grant text required")
    try:
        obj = json.loads(raw, object_pairs_hook=_unique_pairs)
    except (TypeError, ValueError) as exc:
        raise InvalidIndependentHabitGrant("invalid JSON grant") from exc
    if type(obj) is not dict or set(obj) != set(SignedHabitGrant.__dataclass_fields__):
        raise InvalidIndependentHabitGrant("wrong signed grant fields")
    ids = obj["observed_ids"]
    if type(ids) is not list or len(ids) != 2 or not all(
        type(v) is str for v in ids
    ):
        raise InvalidIndependentHabitGrant("invalid two source IDs")
    obj["observed_ids"] = tuple(ids)
    return SignedHabitGrant(**obj)


@dataclass(frozen=True, slots=True)
class S10NonTransferDecision:
    source_feedback_id: str
    source_learning_revision: int
    status: str = NO_SHARED_SOURCE
    authorizes_s11: bool = False


def inspect_real_s10_nontransfer(
    committed: LearningCommitResult,
    draft: HabitAcquisitionDraft | None = None,
) -> S10NonTransferDecision:
    """A real S10 state transition cannot identify B11's TWO World Actions."""
    if not isinstance(committed, LearningCommitResult):
        raise InvalidIndependentHabitGrant("actual S10 commit result required")
    if draft is not None and not isinstance(draft, HabitAcquisitionDraft):
        raise InvalidIndependentHabitGrant("typed independent cue draft required")
    if (
        committed.new_state.revision != committed.previous_state.revision + 1
        or committed.record.feedback_id != committed.proposal.feedback.feedback_id
        or committed.record.committed_revision != committed.new_state.revision
        or committed.record.previous_revision != committed.previous_state.revision
    ):
        raise InvalidIndependentHabitGrant("inconsistent S10 retained commit")
    return S10NonTransferDecision(
        source_feedback_id=committed.record.feedback_id,
        source_learning_revision=committed.new_state.revision,
    )


class IndependentS11Admission:
    """Bounded test-only verification gate with exact S11 owner read-back.

    It verifies an independently MAC-authorized B11 source-qualified Habit
    proposal before delegating to B11's experiment-only snapshot construction.
    Anyone calling B11 commit_experiment_habit directly, or holding MAC key,
    can bypass this test gate: NOT a hardened production owner boundary.
    """

    def __init__(self, trusted_key: bytes) -> None:
        self.__trusted_key = _key(trusted_key)
        self.__spent: set[str] = set()

    def commit(
        self,
        owner: HabitRepertoire,
        draft: HabitAcquisitionDraft,
        ledger: QualifiedLedger,
        grant: SignedHabitGrant,
    ) -> HabitRepertoire:
        if not isinstance(owner, HabitRepertoire):
            raise InvalidIndependentHabitGrant("actual S11 owner required")
        if not isinstance(ledger, QualifiedLedger):
            raise InvalidIndependentHabitGrant("actual B11 World ledger required")
        if not isinstance(draft, HabitAcquisitionDraft):
            raise InvalidIndependentHabitGrant("typed source proposal required")
        if not isinstance(grant, SignedHabitGrant):
            raise InvalidIndependentHabitGrant("signed S11 grant required")
        # Re-derive both winner and owner revision against current WORLD.
        try:
            verified_draft = propose_habit(owner, ledger, draft.a, draft.b)
        except UnqualifiedHabitAcquisition as exc:
            raise InvalidIndependentHabitGrant("unqualified or stale World") from exc
        if verified_draft != draft:
            raise InvalidIndependentHabitGrant("source/proposal/owner mismatch")
        if (
            type(grant.granted) is not bool or grant.granted is not True
            or type(grant.expected_revision) is not int
            or type(grant.source_revision) is not int
            or type(grant.a) is not int or type(grant.b) is not int
        ):
            raise InvalidIndependentHabitGrant("unsigned or denied owner grant")
        expected = _expected_body(verified_draft, granted=True)
        if grant.body() != expected:
            raise InvalidIndependentHabitGrant("signed grant scope mismatch")
        if type(grant.mac) is not str or len(grant.mac) != 64:
            raise InvalidIndependentHabitGrant("invalid S11 signature")
        if not hmac.compare_digest(grant.mac, _sign(self.__trusted_key, expected)):
            raise InvalidIndependentHabitGrant("wrong independent grant MAC")
        if grant.grant_id in self.__spent:
            raise InvalidIndependentHabitGrant("grant already spent")
        # After explicit independent signed check, the existing experiment
        # retention helper still revalidates the source and owner snapshot.
        trusted_test_authority: ExperimentHabitAuthority = grant_test_authority(draft)
        try:
            updated = commit_experiment_habit(
                owner, draft, trusted_test_authority, ledger,
            )
        except UnqualifiedHabitAcquisition as exc:
            raise InvalidIndependentHabitGrant("existing S11 rule conflict") from exc
        self.__spent.add(grant.grant_id)
        return updated
