"""B14: matched observations, exact-prefix curves, readaptation and cost null."""
from __future__ import annotations

import secrets
from dataclasses import replace

import pytest

from experiments.ac_b_b11_governed_habit import (
    CONTEXTS,
    CurrentWorld,
    QualifiedLedger,
    UnqualifiedHabitAcquisition,
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
    NoSharedWorldEvidence,
    commit_existing_s10,
    exact_source_pair,
    initial_s10_state,
    orient_pair_as_s10_feedback,
    propose_same_source_s11,
)
from experiments.ac_b_b14_matched_readaptation import (
    CHECKPOINTS,
    EpochComparison,
    run_matched_comparison,
)
from relay_self.habit import select_habit
from relay_self.learning import (
    FeedbackDirection,
    InvalidLearningAuthority,
    LearningUpdateAuthority,
    MissingLearningAuthority,
    commit_learning_update,
    propose_learning_update,
)
from relay_self.provenance import Provenance


def approval(pair, *, granted=True):
    return LearningUpdateAuthority(
        authority_id=f"b14-test-s10-{pair.a}-{pair.b}",
        target_id=pair.target_id,
        granted=granted,
        provenance=Provenance("b14-approval", pair.digest),
    )


def test_three_announced_regimes_and_all_matched_prefix_checkpoints():
    report = run_matched_comparison()
    assert report["classification"] == "MATCHED_WORLD_SAMPLE_AND_ANNOUNCED_READAPTATION"
    assert report["world_actions_total"] == 24
    assert report["source_revisions"] == [0, 1, 2]
    assert report["regimes"] == [0, 1, 0]
    assert report["new_relevant_cues_tested"] is False
    assert report["physical_world"] is False
    assert report["latency_or_energy_measured"] is False
    assert report["native_s10_commits_total"] == 12
    assert report["separate_s11_test_grants_total"] == 12
    assert report["cheap_tag_inserts_total"] == 12
    for epoch in report["epochs"]:
        assert epoch["world_actions_this_epoch"] == 8
        assert epoch["world_actions_to_full_coverage_habit"] == 8
        assert epoch["world_actions_to_full_coverage_tag"] == 8
        assert epoch["repertoire_revision"] == 4
        assert epoch["native_s10_commits"] == 4
        assert epoch["independent_s11_signed_test_grants"] == 4
        assert epoch["experiment_s11_retained_updates"] == 4
        assert epoch["cheap_tag_inserts"] == 4
        assert epoch["heldout_nuisance_count"] == 12
        assert epoch["habit_heldout_correct"] == 12
        assert epoch["tag_heldout_correct"] == 12
        assert [p["actions"] for p in epoch["checkpoints"]] == list(CHECKPOINTS)
        assert [p["habit_covered"] for p in epoch["checkpoints"]] == [0, 1, 2, 3, 4]
        assert [p["tag_covered"] for p in epoch["checkpoints"]] == [0, 1, 2, 3, 4]
        assert [p["habit_correct"] for p in epoch["checkpoints"]] == [0, 1, 2, 3, 4]
        assert [p["tag_correct"] for p in epoch["checkpoints"]] == [0, 1, 2, 3, 4]
        assert epoch["checkpoint_and_heldout_tag_lookups"] == 4 * (5 + 3)
        # Counts are symbolic; do not call them time/energy benchmarks.
        assert epoch["s11_rule_feature_checks_upper_bound"] >= 96


def test_no_habit_or_tag_until_two_ACTUALLY_observed_actions_per_cue():
    world = CurrentWorld()
    current = EpochComparison.create(world)
    zero = current.score("prefix-0")
    assert (zero.habit_covered, zero.tag_covered) == (0, 0)
    one = world.act(0, 0, 0)
    ledger = QualifiedLedger(world, (one,))
    with pytest.raises(NoSharedWorldEvidence, match="missing"):
        exact_source_pair(ledger, 0, 0)
    with pytest.raises(UnqualifiedHabitAcquisition, match="both real"):
        ledger.chosen(0, 0)
    assert current.score("prefix-1-no-qualified-pair").habit_covered == 0
    assert current.score("prefix-1-no-qualified-pair").tag_covered == 0
    assert world.actions_executed == 1


def test_stepwise_matching_policy_and_zero_hallucinated_source_actions():
    world = CurrentWorld()
    current = EpochComparison.create(world)
    original_owner = current.owner
    initial = current.score("initial")
    assert initial.habit_correct == initial.tag_correct == 0
    for step, (a, b) in enumerate(CONTEXTS, start=1):
        old = current.owner
        current.learn_pair(a, b)
        assert world.actions_executed == 2 * step
        p = current.score(f"after-{step}")
        assert p.habit_correct == p.tag_correct == step
        assert p.habit_covered == p.tag_covered == step
        assert current.owner.revision == step
        assert old.revision == step - 1
        assert len(old.rules) == step - 1
        assert current.s10_native_commit_count == step
        assert current.s11_signed_grant_count == step
        assert current.s11_retained_updates == step
        assert current.tag_inserts == step
        assert len(current.learned_tags) == step
    assert original_owner.revision == 0
    assert original_owner.rules == ()
    with pytest.raises(ValueError, match="duplicate"):
        current.learn_pair(0, 0)


def test_old_epoch_both_scoped_arms_abstain_even_though_raw_s11_is_stale():
    world = CurrentWorld()
    current = EpochComparison.create(world)
    for a, b in CONTEXTS:
        current.learn_pair(a, b)
    cue = cue_for(0, 0, trial="before-world-change")
    assert current.view.select(cue, world) == ("selected", "action:0")
    assert current.lookup_tag(0, 0) == 0
    old_owner = current.owner
    world.change_rule(announce=True)
    assert current.view.select(cue, world) == ("STALE", None)
    with pytest.raises(ValueError, match="stale"):
        current.lookup_tag(0, 0)
    with pytest.raises(ValueError, match="stale"):
        current.score("post-announced-flip")
    assert select_habit(old_owner, cue).selected_candidate_ref == "action:0"
    new = EpochComparison.create(world)
    assert new.score("fresh-epoch-without-observations").habit_covered == 0
    assert new.score("fresh-epoch-without-observations").tag_covered == 0
    assert new.owner.repertoire_id != old_owner.repertoire_id
    assert new.owner.rules == () and new.owner.revision == 0


def test_source_replayed_or_cloned_receipt_cannot_make_training_pair():
    world = CurrentWorld()
    data = observe_training(world)
    with pytest.raises(UnqualifiedHabitAcquisition, match="did not issue"):
        QualifiedLedger(world, (replace(data[0]), data[1]))
    with pytest.raises(UnqualifiedHabitAcquisition, match="duplicate"):
        QualifiedLedger(world, data + (data[0],))
    with pytest.raises(UnqualifiedHabitAcquisition, match="conflicting"):
        QualifiedLedger(world, data + (world.act(0, 0, 0),))


def test_missing_native_s10_authority_does_not_prevent_cheap_tag_from_learning():
    world = CurrentWorld()
    ledger = QualifiedLedger(world, observe_training(world))
    pair = exact_source_pair(ledger, 0, 1)
    assert ledger.chosen(0, 1)[0] == 1
    assert propose_habit(empty_repertoire(), ledger, 0, 1).rule.candidate_ref == (
        "action:1"
    )
    with pytest.raises(MissingLearningAuthority):
        commit_existing_s10(ledger, pair, initial_s10_state(pair), None)
    with pytest.raises(InvalidLearningAuthority):
        commit_existing_s10(
            ledger, pair, initial_s10_state(pair), approval(pair, granted=False),
        )
    with pytest.raises(NoSharedWorldEvidence, match="S10 commit"):
        propose_same_source_s11(empty_repertoire(), ledger, pair, None)
    assert world.actions_executed == 8


def test_wrong_s10_orientation_native_commit_does_not_qualify_s11():
    world = CurrentWorld()
    ledger = QualifiedLedger(world, observe_training(world))
    pair = exact_source_pair(ledger, 0, 0)
    state = initial_s10_state(pair)
    correct = orient_pair_as_s10_feedback(pair)
    assert correct.direction is FeedbackDirection.DECREASE
    for wrong_direction in (FeedbackDirection.INCREASE, FeedbackDirection.HOLD):
        changed_feedback = replace(correct, direction=wrong_direction)
        rule = propose_learning_update(
            state, correct,
            # Reuse actual exact B13 rule but intentionally override
            # the criterion's feedback direction.
            propose_existing_rule(ledger, pair, state),
        ).rule
        proposal = propose_learning_update(state, changed_feedback, rule)
        native = commit_learning_update(
            state, proposal, approval(pair),
            provenance=Provenance("b14-wrong-orientation", pair.digest),
        )
        with pytest.raises(NoSharedWorldEvidence, match="S10 commit"):
            propose_same_source_s11(
                empty_repertoire(), ledger, pair, native,
            )
    assert ledger.chosen(0, 0)[0] == 0


def propose_existing_rule(ledger, pair, state):
    from experiments.ac_b_b13_shared_world import propose_existing_s10

    return propose_existing_s10(ledger, pair, state).rule


def test_b12_grant_wrong_key_does_not_retire_or_retian_owner():
    world = CurrentWorld()
    ledger = QualifiedLedger(world, observe_training(world))
    pair = exact_source_pair(ledger, 0, 0)
    native = commit_existing_s10(
        ledger, pair, initial_s10_state(pair), approval(pair),
    )
    original = empty_repertoire()
    draft = propose_same_source_s11(original, ledger, pair, native)
    signed = OfflineIndependentS11Issuer(secrets.token_bytes(32)).grant(draft)
    with pytest.raises(InvalidIndependentHabitGrant, match="MAC"):
        IndependentS11Admission(secrets.token_bytes(32)).commit(
            original, draft, ledger, signed,
        )
    assert original.revision == 0 and original.rules == ()
    assert world.actions_executed == 8


def test_cross_world_identical_textual_events_do_not_train_s10():
    left = CurrentWorld()
    right = CurrentWorld()
    l_ledger = QualifiedLedger(left, observe_training(left))
    r_ledger = QualifiedLedger(right, observe_training(right))
    pair = exact_source_pair(l_ledger, 0, 0)
    assert pair.evidence_ids == exact_source_pair(r_ledger, 0, 0).evidence_ids
    with pytest.raises(NoSharedWorldEvidence, match="source"):
        commit_existing_s10(
            r_ledger, pair, initial_s10_state(pair), approval(pair),
        )
    assert left.actions_executed == right.actions_executed == 8
