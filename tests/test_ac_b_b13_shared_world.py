"""B13: common B11 simulator observations feed ACTUAL S10 + S11 draft."""
from __future__ import annotations

import secrets
from dataclasses import replace

import pytest

from experiments.ac_b_b11_governed_habit import (
    CONTEXTS,
    CurrentWorld,
    QualifiedHabitView,
    QualifiedLedger,
    UnqualifiedHabitAcquisition,
    cheap_flat_tags,
    cue_for,
    empty_repertoire,
    observe_training,
    propose_habit,
)
from experiments.ac_b_b12_independent_grant import (
    IndependentS11Admission,
    InvalidIndependentHabitGrant,
    OfflineIndependentS11Issuer,
)
from experiments.ac_b_b13_shared_world import (
    ORIENTATION_ID,
    NoSharedWorldEvidence,
    commit_existing_s10,
    exact_source_pair,
    initial_s10_state,
    orient_pair_as_s10_feedback,
    propose_existing_s10,
    propose_same_source_s11,
)
from relay_self.habit import HabitSelectionStatus, select_habit
from relay_self.learning import (
    FeedbackDirection,
    InvalidLearningAuthority,
    LearningUpdateAuthority,
    MissingLearningAuthority,
    commit_learning_update,
    propose_learning_update,
)
from relay_self.provenance import Provenance


def fixed_world():
    world = CurrentWorld()
    outcomes = observe_training(world)
    ledger = QualifiedLedger(world, outcomes)
    return world, ledger, outcomes


def permission(pair, *, granted=True):
    return LearningUpdateAuthority(
        authority_id=f"b13-explicit-s10-{pair.a}-{pair.b}",
        target_id=pair.target_id,
        granted=granted,
        provenance=Provenance("b13.test-S10-owner", pair.digest),
    )


def commit_pair(ledger, pair):
    return commit_existing_s10(
        ledger, pair, initial_s10_state(pair), permission(pair),
    )


def test_one_original_world_pair_feeds_real_s10_and_read_only_s11_draft():
    world, ledger, outcomes = fixed_world()
    assert world.actions_executed == 8
    assert len(outcomes) == 8
    owner = empty_repertoire()
    for a, b in CONTEXTS:
        pair = exact_source_pair(ledger, a, b)
        assert pair.criterion_id == ORIENTATION_ID
        assert pair.source_world_identity == id(world)
        assert pair.winner == a ^ b
        assert len(pair.evidence_ids) == 2
        feedback = orient_pair_as_s10_feedback(pair)
        assert feedback.target_id == pair.target_id
        assert feedback.consequence_ref == pair.consequence_ref
        assert feedback.direction is (
            FeedbackDirection.INCREASE if pair.winner == 1
            else FeedbackDirection.DECREASE
        )
        state = initial_s10_state(pair)
        proposal = propose_existing_s10(ledger, pair, state)
        assert state.value == 1 and state.revision == 0
        assert proposal.proposed_value == (2 if pair.winner else 0)
        c = commit_existing_s10(ledger, pair, state, permission(pair))
        assert c.previous_state is state
        assert c.new_state.value == (2 if pair.winner else 0)
        assert c.new_state.revision == 1
        assert c.record.feedback_id == feedback.feedback_id
        assert c.proposal.feedback == feedback
        draft = propose_same_source_s11(owner, ledger, pair, c)
        assert draft.observed_ids == pair.evidence_ids
        assert draft.rule.candidate_ref == f"action:{pair.winner}"
        assert tuple(draft.rule.provenance.reference.split(",")) == pair.evidence_ids
        assert owner.rules == ()
    assert world.actions_executed == 8


def test_four_real_s10_updates_and_four_independent_s11_test_grants():
    world, ledger, _ = fixed_world()
    initial = empty_repertoire()
    owner = initial
    key = secrets.token_bytes(32)
    issuer = OfflineIndependentS11Issuer(key)
    gate = IndependentS11Admission(key)
    for i, (a, b) in enumerate(CONTEXTS):
        pair = exact_source_pair(ledger, a, b)
        c = commit_pair(ledger, pair)
        draft = propose_same_source_s11(owner, ledger, pair, c)
        assert owner.revision == i
        owner = gate.commit(owner, draft, ledger, issuer.grant(draft))
        assert owner.revision == i + 1
        assert len(owner.rules) == i + 1
    assert len(owner.rules) == 4 and owner.revision == 4
    assert initial.rules == () and initial.revision == 0
    assert world.actions_executed == 8
    view = QualifiedHabitView(owner, world.session, world.revision)
    flat = cheap_flat_tags(ledger)
    actual_count = 0
    flat_count = 0
    for trial in range(3):
        for a, b in CONTEXTS:
            cue = cue_for(a, b, trial=f"b13-nuisance-heldout-{trial}")
            selection = select_habit(owner, cue)
            assert selection.status is HabitSelectionStatus.SELECTED
            status, candidate = view.select(cue, world)
            assert status == "selected"
            assert candidate == selection.selected_candidate_ref
            s11_action = int(candidate.split(":")[1])
            actual_count += int(world.heldout_score(a, b, s11_action))
            flat_count += int(world.heldout_score(a, b, flat[a, b]))
    assert (actual_count, flat_count) == (12, 12)
    assert world.actions_executed == 8


def test_without_s10_commit_b11_and_cheap_tags_still_learn_source_winner():
    world, ledger, _ = fixed_world()
    pair = exact_source_pair(ledger, 0, 1)
    owner = empty_repertoire()
    # No S10 commit -> B13 admission rejects even though evidence exists.
    with pytest.raises(NoSharedWorldEvidence, match="S10 commit"):
        propose_same_source_s11(owner, ledger, pair, None)
    # Independent B11 rule and cheap flat tags BOTH infer winner anyway:
    assert propose_habit(owner, ledger, 0, 1).rule.candidate_ref == "action:1"
    assert cheap_flat_tags(ledger)[0, 1] == 1
    assert world.actions_executed == 8


def test_native_s10_learning_authority_required_not_a_habit_permission():
    world, ledger, _ = fixed_world()
    pair = exact_source_pair(ledger, 0, 0)
    state = initial_s10_state(pair)
    with pytest.raises(MissingLearningAuthority):
        commit_existing_s10(ledger, pair, state, None)
    with pytest.raises(InvalidLearningAuthority):
        commit_existing_s10(ledger, pair, state, permission(pair, granted=False))
    s10 = commit_existing_s10(ledger, pair, state, permission(pair))
    owner = empty_repertoire()
    draft = propose_same_source_s11(owner, ledger, pair, s10)
    with pytest.raises(InvalidIndependentHabitGrant, match="signed S11"):
        IndependentS11Admission(secrets.token_bytes(32)).commit(
            owner, draft, ledger, permission(pair),
        )
    assert owner.rules == ()
    assert world.actions_executed == 8


@pytest.mark.parametrize("direction", [
    FeedbackDirection.HOLD, FeedbackDirection.INCREASE,
])
def test_wrong_s10_orientation_even_if_native_committed_does_not_admit_s11(
    direction,
):
    # (0,0) winner=0 -> proper orientation is DECREASE.
    _, ledger, _ = fixed_world()
    pair = exact_source_pair(ledger, 0, 0)
    state = initial_s10_state(pair)
    reversed_feedback = replace(
        orient_pair_as_s10_feedback(pair), direction=direction,
    )
    proposal = propose_learning_update(
        state, reversed_feedback, propose_existing_s10(
            ledger, pair, state,
        ).rule,
    )
    wrong = commit_learning_update(
        state, proposal, permission(pair),
        provenance=Provenance("b13.wrong-criterion", "real-S10-commit"),
    )
    assert wrong.new_state.revision == 1
    with pytest.raises(NoSharedWorldEvidence, match="S10 commit"):
        propose_same_source_s11(empty_repertoire(), ledger, pair, wrong)


def test_other_cue_real_s10_commit_does_not_authorize_habit():
    _, ledger, _ = fixed_world()
    p00 = exact_source_pair(ledger, 0, 0)
    p11 = exact_source_pair(ledger, 1, 1)
    alien = commit_pair(ledger, p11)
    with pytest.raises(NoSharedWorldEvidence, match="S10 commit"):
        propose_same_source_s11(empty_repertoire(), ledger, p00, alien)


def test_cross_world_same_session_and_same_event_strings_not_same_source():
    world, ledger, _ = fixed_world()
    other, other_ledger, _ = fixed_world()
    assert world is not other
    assert world.session == other.session
    p = exact_source_pair(ledger, 0, 1)
    other_p = exact_source_pair(other_ledger, 0, 1)
    assert p.evidence_ids == other_p.evidence_ids
    assert p.session == other_p.session and p.revision == other_p.revision
    assert p.source_world_identity != other_p.source_world_identity
    with pytest.raises(NoSharedWorldEvidence, match="source"):
        propose_same_source_s11(
            empty_repertoire(), other_ledger, p, commit_pair(ledger, p),
        )
    with pytest.raises(NoSharedWorldEvidence, match="source"):
        commit_existing_s10(
            other_ledger, p, initial_s10_state(p), permission(p),
        )


def test_fake_source_pair_or_cloned_world_record_rejected_before_s10():
    world, ledger, outcomes = fixed_world()
    with pytest.raises(UnqualifiedHabitAcquisition, match="World did not issue"):
        QualifiedLedger(world, (replace(outcomes[0]),))
    p = exact_source_pair(ledger, 0, 0)
    for changed in (
        replace(p, digest="0" * 64),
        replace(p, winner=1),
        replace(p, evidence_ids=("fake-A", "fake-B")),
        replace(p, source_world_identity=0),
        replace(p, revision=10),
    ):
        with pytest.raises(NoSharedWorldEvidence, match="source"):
            commit_existing_s10(
                ledger, changed, initial_s10_state(changed),
                permission(changed),
            )
    assert world.actions_executed == 8


def test_world_epoch_shift_stales_s10_proposal_and_existing_s11_view():
    world, ledger, _ = fixed_world()
    p = exact_source_pair(ledger, 0, 0)
    c = commit_pair(ledger, p)
    old_owner = empty_repertoire()
    draft = propose_same_source_s11(old_owner, ledger, p, c)
    key = secrets.token_bytes(32)
    old_owner = IndependentS11Admission(key).commit(
        old_owner, draft, ledger, OfflineIndependentS11Issuer(key).grant(draft),
    )
    guarded = QualifiedHabitView(old_owner, world.session, world.revision)
    cue = cue_for(0, 0, trial="before-revision")
    assert guarded.select(cue, world) == ("selected", "action:0")
    world.change_rule(announce=True)
    assert guarded.select(cue, world) == ("STALE", None)
    # Raw frozen S11 may still choose stale action.
    assert select_habit(old_owner, cue).selected_candidate_ref == "action:0"
    with pytest.raises(NoSharedWorldEvidence, match="source"):
        propose_same_source_s11(old_owner, ledger, p, c)
    with pytest.raises(NoSharedWorldEvidence, match="source"):
        commit_existing_s10(ledger, p, initial_s10_state(p), permission(p))


def test_missing_alternative_world_action_gives_no_learning_or_habit_pair():
    world = CurrentWorld()
    observations = observe_training(world)
    incomplete = QualifiedLedger(world, observations[:-1])
    with pytest.raises(NoSharedWorldEvidence, match="missing"):
        exact_source_pair(incomplete, 1, 1)
    assert world.actions_executed == 8


def test_source_produced_s10_record_is_not_an_unforgeable_proof():
    # Even a genuine S10 typed dataclass can be cloned in-process.
    # B13 relies on caller honesty, a source identity ledger and review; no
    # cryptographic proof of independent S10 owner authority is provided.
    _, ledger, _ = fixed_world()
    p = exact_source_pair(ledger, 0, 0)
    real = commit_pair(ledger, p)
    copied = replace(real)
    assert copied == real and copied is not real
    assert propose_same_source_s11(
        empty_repertoire(), ledger, p, copied,
    ).rule.candidate_ref == "action:0"


def test_b12_independent_test_grant_wrong_key_denied_after_valid_s10():
    _, ledger, _ = fixed_world()
    p = exact_source_pair(ledger, 0, 1)
    owner = empty_repertoire()
    draft = propose_same_source_s11(owner, ledger, p, commit_pair(ledger, p))
    signed = OfflineIndependentS11Issuer(secrets.token_bytes(32)).grant(draft)
    with pytest.raises(InvalidIndependentHabitGrant, match="MAC"):
        IndependentS11Admission(secrets.token_bytes(32)).commit(
            owner, draft, ledger, signed,
        )
    assert owner.rules == ()
