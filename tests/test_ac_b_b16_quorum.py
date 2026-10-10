"""B16: matched noisy repeated World evidence vs cheapest counted quorum."""
from __future__ import annotations

from dataclasses import replace

import pytest

from experiments.ac_b_b11_governed_habit import (
    CurrentWorld,
    cue_for,
    empty_repertoire,
)
from experiments.ac_b_b16_quorum import (
    BatchLedger,
    ExperimentQuorumAuthority,
    PairedTrial,
    QuorumNotQualified,
    commit_test_quorum_habit,
    expected_feedback,
    initial_state,
    issue_observed_trial,
    issue_test_authority,
    native_s10_commit,
    propose_quorum_habit,
    run_b16_comparison,
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


def simple_world(*, noisy: bool = False):
    world = CurrentWorld()
    trials = tuple(
        issue_observed_trial(world, 0, 0, i, noisy=noisy) for i in range(5)
    )
    return world, BatchLedger(world, 0, 0, trials)


def native_grant(batch, *, granted=True):
    return LearningUpdateAuthority(
        authority_id="b16-existing-s10-grant",
        target_id=initial_state(batch).target_id,
        provenance=Provenance("b16-explicit-test-owner", batch.digest),
        granted=granted,
    )


def full_commit(batch, owner=None):
    owner = owner if owner is not None else empty_repertoire()
    c = native_s10_commit(batch, native_grant(batch))
    draft = propose_quorum_habit(batch, owner, c)
    return owner, c, draft


def test_preregistered_two_episodes_three_arms_same_world_budget():
    all_results = run_b16_comparison()
    assert all_results["classification"] == "B16_EXPERIMENT_ONLY_MATCHED_NOISY_QUORUM_TEST"
    assert all_results["shared_actual_world_actions_total"] == 80
    assert all_results["no_physical_source_attestation"] is True
    assert all_results["no_production_s11_acquisition_owner"] is True
    assert all_results["no_autonomous_l2_to_l1_distillation"] is True
    clean, noisy = all_results["episodes"]
    assert clean["episode"] == "clean"
    assert noisy["episode"] == "adversarial"
    for report in (clean, noisy):
        assert report["total_actual_world_actions"] == 40
        assert report["one_shot_available_after_actions"] == 8
        assert report["quorum_available_after_actions"] == 40
        assert report["quorum_agrees_cheap_counts"] is True
        assert report["truth_visible_to_learner"] is False
        assert report["actual_native_s10_commits"] == report["new_s11_rules"]
        assert report["separate_b16_test_s11_grants"] == report["new_s11_rules"]
        assert report["original_owner_revision"] == 0
        assert report["new_owner_revision"] == report["new_s11_rules"]
    assert clean["first"] == (4, 4)
    assert clean["s10_s11_quorum"] == clean["cheap_counts"] == (4, 4)
    assert clean["heldout"]["first"] == (12, 12)
    assert clean["heldout"]["s10_s11_quorum"] == (12, 12)
    assert clean["heldout"]["cheap_counts"] == (12, 12)
    assert clean["new_s11_rules"] == 4
    assert noisy["first"] == (3, 0)
    assert noisy["s10_s11_quorum"] == noisy["cheap_counts"] == (3, 2)
    assert noisy["heldout"]["first"] == (9, 0)
    assert noisy["heldout"]["s10_s11_quorum"] == (9, 6)
    assert noisy["heldout"]["cheap_counts"] == (9, 6)
    assert noisy["new_s11_rules"] == 3


def test_exact_frozen_noisy_vote_schedule_and_clean_controls():
    clean = run_b16_comparison()["episodes"][0]["vote_sequences"]
    assert clean == {
        "00": (0, 0, 0, 0, 0),
        "01": (1, 1, 1, 1, 1),
        "10": (1, 1, 1, 1, 1),
        "11": (0, 0, 0, 0, 0),
    }
    noisy = run_b16_comparison()["episodes"][1]["vote_sequences"]
    assert noisy == {
        "00": (1, 0, 0, 0, 0),
        "01": (None, 1, 1, 1, 1),
        "10": (0, 0, 0, 1, 1),
        "11": (1, 1, 1, 1, 1),
    }


def test_prefix_evidence_not_quorum_without_all_five_pairs():
    world = CurrentWorld()
    trials: list[PairedTrial] = []
    for n in range(5):
        trials.append(issue_observed_trial(world, 0, 0, n, noisy=True))
        ledger = BatchLedger(world, 0, 0, tuple(trials))
        assert ledger.first_shot() == 1  # first synthetic report was poisoned
        assert ledger.counted_quorum() == (0 if n == 4 else None)
        if n < 4:
            with pytest.raises(QuorumNotQualified, match="five source trials"):
                expected_feedback(ledger)
    assert world.actions_executed == 10
    assert len(ledger.evidence_ids) == 10
    assert ledger.counted_quorum() == 0


def test_missing_alternative_cannot_supply_fake_vote():
    world = CurrentWorld()
    pair = issue_observed_trial(world, 0, 0, 0, noisy=False)
    copied = PairedTrial(0, pair.action0, pair.action0)
    with pytest.raises(QuorumNotQualified, match="exact Action"):
        BatchLedger(world, 0, 0, (copied,))
    assert world.actions_executed == 2


def test_cloned_non_source_and_duplicated_event_and_swapped_world_denied():
    world, batch = simple_world()
    raw = batch.trials
    with pytest.raises(QuorumNotQualified, match="source-owned"):
        BatchLedger(
            world, 0, 0,
            (replace(raw[0], action0=replace(raw[0].action0)),) + raw[1:],
        )
    with pytest.raises(QuorumNotQualified, match="duplicated"):
        BatchLedger(
            world, 0, 0, (raw[0], replace(raw[1], action0=raw[0].action0))
            + raw[2:],
        )
    foreign = CurrentWorld()
    with pytest.raises(QuorumNotQualified, match="source-owned"):
        BatchLedger(foreign, 0, 0, raw)
    wrong = CurrentWorld()
    wrong.change_rule(announce=True)
    with pytest.raises(QuorumNotQualified, match="source-owned"):
        BatchLedger(wrong, 0, 0, raw)
    assert world.actions_executed == 10


def test_experiment_owner_requires_a_real_native_s10_commit():
    _, batch = simple_world(noisy=True)
    original = empty_repertoire()
    assert batch.counted_quorum() == 0
    for c in (None, {"feedback": "yes"}, native_grant(batch)):
        with pytest.raises(QuorumNotQualified, match="native S10"):
            propose_quorum_habit(batch, original, c)
    with pytest.raises(MissingLearningAuthority):
        native_s10_commit(batch, None)
    with pytest.raises(InvalidLearningAuthority):
        native_s10_commit(batch, native_grant(batch, granted=False))
    assert original.rules == ()


def test_signed_pair_only_b12_permission_not_valid_as_full_quorum_grant():
    _, batch = simple_world()
    owner, c, draft = full_commit(batch)
    for grant in (
        None, native_grant(batch), {"granted": True},
        replace(issue_test_authority(draft), granted=False),
        replace(issue_test_authority(draft), owner_id="different"),
        replace(issue_test_authority(draft), owner_revision=999),
        replace(issue_test_authority(draft), evidence_digest="0" * 64),
        replace(issue_test_authority(draft), winner=1),
        replace(issue_test_authority(draft), source_revision=1),
        replace(issue_test_authority(draft), world_local_id=0),
        replace(issue_test_authority(draft), granted="true"),
    ):
        with pytest.raises(QuorumNotQualified, match="separate test-only"):
            commit_test_quorum_habit(batch, owner, c, draft, grant)
    assert owner.revision == 0 and owner.rules == ()


def test_owner_is_immutable_and_replay_of_old_proposal_fails():
    _, batch = simple_world()
    old, c, draft = full_commit(batch)
    grant = issue_test_authority(draft)
    updated = commit_test_quorum_habit(batch, old, c, draft, grant)
    assert old.rules == () and old.revision == 0
    assert updated.revision == 1 and len(updated.rules) == 1
    cue = cue_for(0, 0, trial="new-nuisance")
    choice = select_habit(updated, cue)
    assert choice.status is HabitSelectionStatus.SELECTED
    assert choice.selected_candidate_ref == "action:0"
    with pytest.raises(QuorumNotQualified, match="draft/owner mismatch"):
        commit_test_quorum_habit(batch, updated, c, draft, grant)


def test_wrong_committed_native_s10_direction_even_with_owner_grant_denied():
    _, batch = simple_world()
    old = empty_repertoire()
    s10 = initial_state(batch)
    correct = expected_feedback(batch)
    assert correct.direction is FeedbackDirection.DECREASE
    for wrong_direction in (FeedbackDirection.HOLD, FeedbackDirection.INCREASE):
        feedback = replace(correct, direction=wrong_direction)
        p = propose_learning_update(s10, feedback, RULE)
        c = commit_learning_update(
            s10, p, native_grant(batch),
            provenance=Provenance("b16-test", "wrong-orientation"),
        )
        with pytest.raises(QuorumNotQualified, match="mismatch"):
            propose_quorum_habit(batch, old, c)
    assert old.rules == ()


def test_3_of_5_poison_means_abstain_and_5_of_5_poison_wrong():
    world = CurrentWorld()
    for a, b in ((1, 0), (1, 1)):
        pairs = tuple(
            issue_observed_trial(world, a, b, i, noisy=True) for i in range(5)
        )
        ledger = BatchLedger(world, a, b, pairs)
        if (a, b) == (1, 0):
            assert [p.vote() for p in pairs] == [0, 0, 0, 1, 1]
            assert ledger.counted_quorum() is None
            with pytest.raises(QuorumNotQualified, match="four-vote"):
                expected_feedback(ledger)
        else:
            assert ledger.counted_quorum() == 1
            assert not world.heldout_score(a, b, 1)
    assert world.actions_executed == 20


def test_stale_world_revision_invalidates_completed_batch():
    world, batch = simple_world()
    assert batch.counted_quorum() == 0
    world.change_rule(announce=True)
    with pytest.raises(QuorumNotQualified, match="stale"):
        batch.counted_quorum()
    with pytest.raises(QuorumNotQualified, match="stale"):
        native_s10_commit(batch, native_grant(batch))


def test_same_process_forged_experiment_quorum_grant_is_accepted_witness():
    # Plain test grants MUST NOT be advertised as secure product authority.
    _, batch = simple_world()
    owner, committed, draft = full_commit(batch)
    fabricated = ExperimentQuorumAuthority(
        owner_id=draft.owner_id,
        owner_revision=draft.owner_revision,
        session=draft.session,
        source_revision=draft.source_revision,
        world_local_id=draft.world_local_id,
        evidence_digest=draft.evidence_digest,
        winner=draft.winner,
        granted=True,
    )
    updated = commit_test_quorum_habit(batch, owner, committed, draft, fabricated)
    assert updated.revision == 1 and owner.revision == 0
