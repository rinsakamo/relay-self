"""B12 independent test grant; no production S11 owner or causal S10 bridge.

The trusted caller separately supplies the key, issuer, live World and admitted
owner snapshot. A key holder can sign arbitrary data. B11 can still be called
directly: this wrapper is not a hardened production boundary. Replay and owner
state are local memory only; source evidence remains B11 object identity.
"""
from __future__ import annotations

import hmac
import json
from dataclasses import asdict, dataclass
from hashlib import sha256

from experiments.ac_b_b11_governed_habit import (
    CONTEXTS,
    CurrentWorld,
    HabitAcquisitionDraft,
    QualifiedHabitView,
    QualifiedLedger,
    UnqualifiedHabitAcquisition,
    cheap_flat_tags,
    commit_experiment_habit,
    cue_for,
    empty_repertoire,
    grant_test_authority,
    observe_training,
    propose_habit,
)
from relay_self.action_feedback import ActionFeedbackCriterion
from relay_self.habit import HabitRepertoire
from relay_self.learning import LearningCommitResult

DOMAIN = "B12_INDEPENDENT_EXPERIMENT_S11_GRANT_V1"
NO_SHARED_SOURCE = "NO_SHARED_WORLD_CUE_WITNESSES"


class InvalidHabitGrant(ValueError):
    """Fail closed without retained owner change."""


def canonical(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False)


def digest(value: object) -> str:
    return sha256(canonical(value).encode("ascii")).hexdigest()


def key_bytes(key: bytes) -> bytes:
    if type(key) is not bytes or len(key) < 32:
        raise InvalidHabitGrant("independent caller key must contain at least 32 bytes")
    return key


def source_rows(ledger: QualifiedLedger) -> tuple:
    return tuple(ledger.rows[cue][action]
                 for cue in sorted(ledger.rows) for action in sorted(ledger.rows[cue]))


def grant_body(owner: HabitRepertoire, draft: HabitAcquisitionDraft,
               ledger: QualifiedLedger, *, issuer: str, grant_id: str,
               granted: bool = True) -> dict:
    """Issuer's data binding; not source qualification or owner admission."""
    if type(granted) is not bool or not issuer or not grant_id:
        raise InvalidHabitGrant("explicit issuer, grant ID and boolean decision required")
    pair = ledger.rows[draft.a, draft.b]
    return {
        "domain": DOMAIN, "issuer": issuer, "grant_id": grant_id, "granted": granted,
        "repertoire_id": owner.repertoire_id, "expected_revision": owner.revision,
        "owner_snapshot_digest": digest(asdict(owner)),
        "source_session": draft.source_session, "source_revision": draft.source_revision,
        "observed_action_ids": draft.observed_ids, "cue": [draft.a, draft.b],
        "candidate_action": draft.rule.candidate_ref, "proposal_id": draft.proposal_id,
        "proposal": asdict(draft),
        "evidence_digest": digest([asdict(pair[a]) for a in sorted(pair)]),
    }


@dataclass(frozen=True, slots=True)
class SignedHabitGrant:
    body: str
    mac: str


class OfflineS11Issuer:
    """Trusted offline test caller, not an isolated production trust root."""

    def __init__(self, key: bytes, issuer: str):
        self.__key = key_bytes(key)
        self.issuer = issuer

    def sign_body(self, body: dict) -> SignedHabitGrant:
        """Intentionally can sign arbitrary data; verifier must recompute it."""
        encoded = canonical(body)
        return SignedHabitGrant(encoded, hmac.new(
            self.__key, encoded.encode("ascii"), sha256).hexdigest())

    def grant(self, owner, draft, ledger, *, grant_id: str, granted: bool = True):
        return self.sign_body(grant_body(owner, draft, ledger, issuer=self.issuer,
                                        grant_id=grant_id, granted=granted))


class IndependentS11Admission:
    """Owner snapshot admitted separately at construction by trusted caller.

    Commit cannot replace that owner or live World with receipt-supplied objects.
    Successful commits advance the admitted immutable owner; rejected commits
    neither consume a grant nor update the owner. No concurrency/durable ledger.
    """

    def __init__(self, *, trusted_key: bytes, trusted_issuer: str,
                 live_world: CurrentWorld, admitted_owner: HabitRepertoire):
        self.__key = key_bytes(trusted_key)
        if (not isinstance(live_world, CurrentWorld)
                or not isinstance(admitted_owner, HabitRepertoire)
                or type(trusted_issuer) is not str or not trusted_issuer):
            raise InvalidHabitGrant("independent live World, issuer and owner admission required")
        self.__world = live_world
        self.__owner = admitted_owner
        self.__issuer = trusted_issuer
        self.__spent_grants: set[str] = set()
        self.__spent_proposals: set[str] = set()

    @property
    def owner(self) -> HabitRepertoire:
        return self.__owner

    def commit(self, owner: HabitRepertoire, draft: HabitAcquisitionDraft,
               ledger: QualifiedLedger, grant: SignedHabitGrant) -> HabitRepertoire:
        if owner is not self.__owner:
            raise InvalidHabitGrant("owner is not independently admitted current snapshot")
        if not isinstance(grant, SignedHabitGrant):
            raise InvalidHabitGrant("independent signed S11 grant required")
        if not isinstance(draft, HabitAcquisitionDraft) or not isinstance(ledger, QualifiedLedger):
            raise InvalidHabitGrant("typed B11 proposal and ledger required")
        if ledger.world is not self.__world:
            raise InvalidHabitGrant("independently supplied live World required")
        try:
            # Re-admit original source objects, not just stored IDs or declared scope.
            current = QualifiedLedger(self.__world, source_rows(ledger))
            recomputed = propose_habit(owner, current, draft.a, draft.b)
            if recomputed != draft:
                raise InvalidHabitGrant("source/proposal mismatch")
        except (UnqualifiedHabitAcquisition, KeyError, TypeError) as exc:
            raise InvalidHabitGrant("unqualified or stale source") from exc
        if type(grant.body) is not str or type(grant.mac) is not str:
            raise InvalidHabitGrant("invalid signed envelope")
        try:
            supplied = json.loads(grant.body)
            grant_id = supplied["grant_id"]
            if type(grant_id) is not str or not grant_id:
                raise InvalidHabitGrant("invalid grant ID")
            expected = canonical(grant_body(owner, recomputed, current,
                                           issuer=self.__issuer, grant_id=grant_id))
        except (ValueError, TypeError, KeyError) as exc:
            raise InvalidHabitGrant("invalid grant body") from exc
        # Exact canonical bytes also reject duplicates, extras, missing fields,
        # noncanonical JSON and boolean/int substitutions before MAC comparison.
        if grant.body != expected:
            raise InvalidHabitGrant("grant scope or canonical body mismatch")
        mac = hmac.new(self.__key, expected.encode("ascii"), sha256).hexdigest()
        if len(grant.mac) != 64 or not grant.mac.isascii() or not hmac.compare_digest(grant.mac, mac):
            raise InvalidHabitGrant("wrong independent HMAC")
        proposal_key = digest(asdict(recomputed))
        if grant_id in self.__spent_grants or proposal_key in self.__spent_proposals:
            raise InvalidHabitGrant("replayed grant or proposal")
        try:
            updated = commit_experiment_habit(owner, recomputed,
                                             grant_test_authority(recomputed), current)
        except UnqualifiedHabitAcquisition as exc:
            raise InvalidHabitGrant("retained rule conflict") from exc
        self.__spent_grants.add(grant_id)
        self.__spent_proposals.add(proposal_key)
        self.__owner = updated
        return updated


@dataclass(frozen=True, slots=True)
class S10NonTransferDecision:
    status: str = NO_SHARED_SOURCE
    authorizes_s11: bool = False


def inspect_s10_nontransfer(commit: LearningCommitResult,
                            criterion: ActionFeedbackCriterion) -> S10NonTransferDecision:
    """Actual scalar commit plus criterion lacks B11 competing cue witnesses.

    This is a read-only negative decision, never a grant issuer or authenticity
    attestation for an arbitrary constructed LearningCommitResult.
    """
    if not isinstance(commit, LearningCommitResult) or not isinstance(criterion, ActionFeedbackCriterion):
        raise InvalidHabitGrant("real S10 commit and S17 criterion types required")
    return S10NonTransferDecision()


def qualify_fixture(key: bytes) -> dict:
    world = CurrentWorld()
    ledger = QualifiedLedger(world, observe_training(world))
    first = empty_repertoire("b12-owner")
    gate = IndependentS11Admission(trusted_key=key, trusted_issuer="b12.offline-s11",
                                  live_world=world, admitted_owner=first)
    issuer = OfflineS11Issuer(key, "b12.offline-s11")
    for i, (a, b) in enumerate(CONTEXTS):
        draft = propose_habit(gate.owner, ledger, a, b)
        signed = issuer.grant(gate.owner, draft, ledger, grant_id=f"grant:{i}")
        gate.commit(gate.owner, draft, ledger, signed)
    view = QualifiedHabitView(gate.owner, world.session, world.revision)
    flat = cheap_flat_tags(ledger)
    habit = cheap = 0
    for round_id in range(3):
        for a, b in CONTEXTS:
            status, candidate = view.select(cue_for(a, b, trial=f"heldout-{round_id}"), world)
            if status == "selected":
                habit += int(world.heldout_score(a, b, int(candidate.split(":")[1])))
            cheap += int(world.heldout_score(a, b, flat[a, b]))
    return {
        "classification": "INDEPENDENT_EXPERIMENTAL_S11_GRANT_CHECK_QUALIFIED",
        "causal_bridge": "NO_CAUSAL_S10_TO_S11_BRIDGE",
        "production_authority": "NO_PRODUCTION_HABIT_OWNER_AUTHORITY",
        "comparison": "CHEAP_TAG_RULE_MATCHES_HABIT_ON_HELDOUT" if habit == cheap else "UNDETERMINED",
        "grand_null_retained": habit <= cheap,
        "training_offline_actions": world.actions_executed,
        "owner_revision": gate.owner.revision, "new_rules": len(gate.owner.rules),
        "original_owner_revision": first.revision, "original_rules": len(first.rules),
        "holdout": 12, "habit_correct": habit, "cheap_tag_correct": cheap,
        "novel_relevant_cues": False, "cheap_lookups": 12,
        "habit_feature_check_upper_bound": 96,
    }
