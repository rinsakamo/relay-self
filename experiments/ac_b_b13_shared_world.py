"""B13: same OFFLINE simulator observations can orient real S10 + S11 draft.

This is not an S17 ActionFeedbackCriterion mapping. B11's binary source
records are not S16 WorldConsequence or physical Minecraft. S10's scalar
commit is only an explicit bridge ADMISSION condition: the World data
already suffice to infer the Habit candidate and a cheap dictionary.
No S11 retention occurs here, and no trusted source/production grant exists.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from experiments.ac_b_b11_governed_habit import (
    HabitAcquisitionDraft,
    QualifiedLedger,
    UnqualifiedHabitAcquisition,
    propose_habit,
)
from relay_self.habit import HabitRepertoire
from relay_self.learning import (
    FeedbackDirection,
    LearningCommitResult,
    LearningFeedback,
    LearningPreferenceState,
    LearningUpdateAuthority,
    LearningUpdateProposal,
    LearningUpdateRule,
    commit_learning_update,
    propose_learning_update,
)
from relay_self.provenance import Provenance

ORIENTATION_ID = "b13-action1-positive-action0-negative-v1"
STEP_RULE = LearningUpdateRule(
    rule_id="b13-binary-context-preference", version=1, step=1,
)


class NoSharedWorldEvidence(ValueError):
    """Reject source/owner/feedback mismatches before any S11 proposal."""


@dataclass(frozen=True, slots=True)
class CommonSourcePair:
    a: int
    b: int
    winner: int
    evidence_ids: tuple[str, str]
    session: str
    revision: int
    digest: str
    criterion_id: str = ORIENTATION_ID

    @property
    def target_id(self) -> str:
        return f"b13-preference-{self.a}-{self.b}"

    @property
    def consequence_ref(self) -> str:
        return f"b13-pair-{self.digest}"


def exact_source_pair(
    ledger: QualifiedLedger, a: int, b: int,
) -> CommonSourcePair:
    if not isinstance(ledger, QualifiedLedger):
        raise NoSharedWorldEvidence("actual B11 World ledger required")
    if type(a) is not int or a not in (0, 1):
        raise NoSharedWorldEvidence("a must be binary")
    if type(b) is not int or b not in (0, 1):
        raise NoSharedWorldEvidence("b must be binary")
    try:
        winner, evidence_ids = ledger.chosen(a, b)
    except UnqualifiedHabitAcquisition as exc:
        raise NoSharedWorldEvidence("missing or stale competing World evidence") from exc
    data = {
        "criterion_id": ORIENTATION_ID, "session": ledger.session,
        "revision": ledger.revision, "a": a, "b": b,
        "winner": winner, "evidence_ids": evidence_ids,
    }
    digest = hashlib.sha256(
        json.dumps(data, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return CommonSourcePair(
        a=a, b=b, winner=winner,
        evidence_ids=evidence_ids,
        session=ledger.session,
        revision=ledger.revision, digest=digest,
    )


def initial_s10_state(pair: CommonSourcePair) -> LearningPreferenceState:
    if not isinstance(pair, CommonSourcePair):
        raise NoSharedWorldEvidence("typed source pair required")
    return LearningPreferenceState(
        target_id=pair.target_id, value=1, minimum=0, maximum=2, revision=0,
        origin_provenance=Provenance(
            "b13.offline-scalar-owner", f"{pair.session}:{pair.a}:{pair.b}",
        ),
    )


def orient_pair_as_s10_feedback(pair: CommonSourcePair) -> LearningFeedback:
    """Caller-declared orientation. This is NOT frozen S17 interpretation."""
    if not isinstance(pair, CommonSourcePair):
        raise NoSharedWorldEvidence("typed pair and explicit orientation required")
    return LearningFeedback(
        feedback_id=f"b13-feedback-{pair.digest}",
        target_id=pair.target_id,
        direction=(
            FeedbackDirection.INCREASE
            if pair.winner == 1 else FeedbackDirection.DECREASE
        ),
        provenance=Provenance(
            "b13.offline-criterion", f"{ORIENTATION_ID}:{pair.digest}",
        ),
        consequence_ref=pair.consequence_ref,
    )


def propose_existing_s10(
    pair: CommonSourcePair, state: LearningPreferenceState,
) -> LearningUpdateProposal:
    if not isinstance(state, LearningPreferenceState):
        raise NoSharedWorldEvidence("actual S10 owner required")
    if state != initial_s10_state(pair):
        raise NoSharedWorldEvidence("unexpected S10 initial owner snapshot")
    return propose_learning_update(
        state, orient_pair_as_s10_feedback(pair), STEP_RULE,
    )


def commit_existing_s10(
    pair: CommonSourcePair,
    state: LearningPreferenceState,
    authority: LearningUpdateAuthority | None,
) -> LearningCommitResult:
    """Real S10 API; caller must provide a separate native S10 authority."""
    proposal = propose_existing_s10(pair, state)
    return commit_learning_update(
        state, proposal, authority,
        provenance=Provenance("b13.offline-s10-commit", pair.digest),
    )


def propose_same_source_s11(
    owner: HabitRepertoire,
    ledger: QualifiedLedger,
    pair: CommonSourcePair,
    s10_commit: LearningCommitResult | None,
) -> HabitAcquisitionDraft:
    """Control-gated B11 draft, not an actual autonomous S10->S11 learner.

    The winner and rule are independently rederived from B11 World evidence;
    S10 only gates this *explicit* proposal interface after real owner commit.
    """
    if not isinstance(owner, HabitRepertoire):
        raise NoSharedWorldEvidence("actual retained S11 owner required")
    if not isinstance(pair, CommonSourcePair):
        raise NoSharedWorldEvidence("typed original World source required")
    actual = exact_source_pair(ledger, pair.a, pair.b)
    if actual != pair:
        raise NoSharedWorldEvidence("source cue, witness or epoch mismatch")
    if not isinstance(s10_commit, LearningCommitResult):
        raise NoSharedWorldEvidence("separately authorized real S10 commit required")
    initial = initial_s10_state(actual)
    feedback = orient_pair_as_s10_feedback(actual)
    expected_proposal = propose_learning_update(initial, feedback, STEP_RULE)
    expected_value = 2 if actual.winner == 1 else 0
    c = s10_commit
    if (
        c.previous_state != initial
        or c.proposal != expected_proposal
        or c.new_state.target_id != actual.target_id
        or c.new_state.value != expected_value
        or c.new_state.revision != 1
        or c.new_state.minimum != 0
        or c.new_state.maximum != 2
        or c.new_state.last_update != c.record
        or c.record.target_id != actual.target_id
        or c.record.previous_value != initial.value
        or c.record.resulting_value != expected_value
        or c.record.previous_revision != 0
        or c.record.committed_revision != 1
        or c.record.feedback_id != feedback.feedback_id
        or c.record.feedback_provenance != feedback.provenance
        or c.record.rule_id != STEP_RULE.rule_id
        or c.record.rule_version != STEP_RULE.version
        or not c.record.authority_id
    ):
        raise NoSharedWorldEvidence("S10 commit and shared World winner mismatch")
    try:
        return propose_habit(owner, ledger, pair.a, pair.b)
    except UnqualifiedHabitAcquisition as exc:
        raise NoSharedWorldEvidence("World source cannot propose this Habit") from exc
