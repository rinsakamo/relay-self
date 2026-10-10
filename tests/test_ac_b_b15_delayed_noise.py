"""B15 exact matched evidence, delayed receipt, noise and silent-shift tests."""
from __future__ import annotations

import secrets
from dataclasses import replace

import pytest

from experiments.ac_b_b11_governed_habit import (
    CurrentWorld,
    QualifiedLedger,
    UnqualifiedHabitAcquisition,
    cue_for,
    empty_repertoire,
    observe_training,
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
    propose_same_source_s11,
)
from experiments.ac_b_b15_delayed_noise import (
    CONTEXT_ACTIONS,
    DELAYS,
    DelayedEpisode,
    run_b15_matched_probe,
)
from relay_self.habit import select_habit
from relay_self.learning import (
    InvalidLearningAuthority,
    LearningUpdateAuthority,
)
from relay_self.provenance import Provenance


def native_permission(pair, granted=True):
    return LearningUpdateAuthority(
        authority_id=f"b15-explicit-S10:{pair.a}:{pair.b}",
        target_id=pair.target_id,
        granted=granted,
        provenance=Provenance("b15-S10-test-owner", pair.digest),
    )


def test_full_b15_fixed_world_actions_and_matched_noisy_delayed_recovery():
    receipt = run_b15_matched_probe()
    assert receipt["classification"] == "DELAY_NOISE_SILENT_SHIFT_MATCHED_SOURCE_PROBE"
    assert receipt["world_actions_shared"] == 24
    assert receipt["world_revision_never_announced"] == 0
    assert receipt["delivery_offsets"] == DELAYS
    assert receipt["no_new_relevant_cues"] is True
    assert receipt["source_is_physical_minecraft"] is False
    assert receipt["native_s10_is_causal_habit_discovery"] is False

    initial, silent, noisy = receipt["phase_reports"]
    assert all(
        phase["command_count"] == phase["receipt_count"] == 8
        and phase["pending_after_completion"] == 0
        and phase["heldout_nuisance_count"] == 12
        and phase["source_revision"] == 0
        for phase in (initial, silent, noisy)
    )
    assert initial["first_contradiction_release_tick"] is None
    assert silent["first_contradiction_release_tick"] == 1
    assert silent["alarm_is_actual_world_shift"] is True
    assert noisy["first_contradiction_release_tick"] == 2
    assert noisy["alarm_is_actual_world_shift"] is False  # noise false alarm

    assert initial["first_tick"] == (0, 0, 0, 0)
    assert silent["first_tick"] == (4, 0, 4, 0)
    assert noisy["first_tick"] == (4, 4, 4, 4)
    for phase in (initial, silent):
        assert phase["final_covered"] == (4, 4)
        assert phase["final_correct"] == (4, 4)
        assert phase["heldout_habit_covered"] == 12
        assert phase["heldout_tag_covered"] == 12
        assert phase["heldout_habit_correct"] == 12
        assert phase["heldout_tag_correct"] == 12
        assert phase["native_s10_commits_in_current_policy"] == 4
        assert phase["separate_s11_test_grants_in_current_policy"] == 4
        assert phase["tag_inserts_in_current_policy"] == 4
        assert len(phase["admitted_cues"]) == 4

    assert noisy["ambiguous_cues"] == ((0, 0),)
    assert noisy["final_covered"] == (3, 3)
    assert noisy["final_correct"] == (2, 2)
    assert noisy["heldout_habit_covered"] == 9
    assert noisy["heldout_tag_covered"] == 9
    assert noisy["heldout_habit_correct"] == 6
    assert noisy["heldout_tag_correct"] == 6
    assert noisy["native_s10_commits_in_current_policy"] == 3
    assert noisy["separate_s11_test_grants_in_current_policy"] == 3
    assert noisy["tag_inserts_in_current_policy"] == 3
    assert len(noisy["admitted_cues"]) == 3


def test_published_receipts_not_issued_commands_are_learning_input():
    world = CurrentWorld()
    episode = DelayedEpisode(world, 0, None, None)
    episode.issue_at(0)
    assert world.actions_executed == 1
    assert len(episode.pending) == 1
    assert episode.pending[0].due_tick == 2
    assert episode.release_at(0) == ()
    assert episode.published == []
    assert episode.policies.owner.rules == ()
    assert episode.policies.tag == {}
    assert episode.policies.score(0, 0, "pending-only").habit_covered == 0
    episode.issue_at(1)
    released = episode.release_at(1)
    assert len(released) == 1
    assert len(episode.published) == 1  # still only 1/2 competing results
    assert episode.policies.owner.rules == ()
    assert episode.policies.tag == {}
    episode.issue_at(2)
    delivered = episode.release_at(2)
    assert len(delivered) == 1
    assert len(episode.published) == 2
    assert episode.policies.owner.revision == 1
    assert episode.policies.tag == {(0, 0): 0}
    assert world.actions_executed == 3  # third issued but still PENDING
    assert episode.policies.score(2, 2, "first-pair-ready").habit_correct == 1


def test_delayed_source_delivery_order_differs_from_command_order():
    world = CurrentWorld()
    engine = DelayedEpisode(world, 0, None, None)
    for tick in range(10):
        if tick < 8:
            engine.issue_at(tick)
        engine.release_at(tick)
    assert engine.command_count == 8
    assert engine.delivered_count == 8
    assert [x.event_id for x in engine.published] != [
        f"{world.session}:event:{i + 1}" for i in range(8)
    ]
    assert sorted(x.event_id for x in engine.published) == sorted(
        f"{world.session}:event:{i + 1}" for i in range(8)
    )
    assert engine.policies.owner.revision == 4
    assert engine.policies.tag[(1, 1)] == 0
    assert len(CONTEXT_ACTIONS) == len(DELAYS) == 8
    assert world.actions_executed == 8


def test_silent_shift_undetectable_until_first_real_contradiction_released():
    world = CurrentWorld()
    old = DelayedEpisode(world, 0, None, None)
    old.run()
    old_owner = old.policies.owner
    prior = old.delivered_index()
    cue = cue_for(0, 0, trial="stale-raw-S11")
    assert select_habit(old_owner, cue).selected_candidate_ref == "action:0"

    world.change_rule(announce=False)
    assert world.revision == 0
    changing = DelayedEpisode(world, 1, old.policies, prior)
    changing.issue_at(0)
    changing.release_at(0)
    # Both policies are stale and wrong, but no evidence arrived.
    score = changing.policies.score(0, 0, "before-first-release")
    assert (score.habit_covered, score.habit_correct) == (4, 0)
    assert (score.tag_covered, score.tag_correct) == (4, 0)
    assert changing.alarm_tick is None
    changing.issue_at(1)
    emitted = changing.release_at(1)
    assert len(emitted) == 1
    assert changing.alarm_tick == 1
    assert changing.policies.owner is not old_owner
    assert changing.policies.owner.rules == ()
    assert changing.policies.tag == {}
    assert select_habit(old_owner, cue).selected_candidate_ref == "action:0"


def test_noise_can_create_false_alarm_and_an_indistinguishable_wrong_pair():
    world = CurrentWorld()
    clean = DelayedEpisode(world, 0, None, None)
    clean.run()
    world.change_rule(announce=False)
    shifted = DelayedEpisode(world, 1, clean.policies, clean.delivered_index())
    shifted.run()
    # No hidden rule change in phase 2. Only three source-reported bit flips.
    noisy = DelayedEpisode(world, 2, shifted.policies, shifted.delivered_index())
    report = noisy.run()
    assert report["first_contradiction_release_tick"] == 2
    assert report["alarm_is_actual_world_shift"] is False
    assert report["ambiguous_cues"] == ((0, 0),)
    assert (1, 1) in noisy.completed
    assert (0, 0) not in noisy.completed
    assert noisy.policies.tag[1, 1] == 0  # coherent but FALSE reported winner
    assert world.heldout_score(1, 1, 0) is False
    cue = cue_for(1, 1, trial="coherent-source-misleads")
    assert select_habit(noisy.policies.owner, cue).selected_candidate_ref == (
        "action:0"
    )
    assert world.revision == 0
    assert world.actions_executed == 24


def test_both_same_result_reports_abstain_not_discarded_or_promoted_to_success():
    world = CurrentWorld()
    # One execution outcome is overwritten as a corrupted but World-registered
    # report (not independently authenticated sensor truth).
    a = world.act(0, 0, 0)
    b = world.act(0, 0, 1)
    new_b = replace(b, success=True)
    assert a.success == new_b.success is True
    world._issued[new_b.event_id] = new_b
    ledger = QualifiedLedger(world, (a, new_b))
    with pytest.raises(UnqualifiedHabitAcquisition, match="uniquely"):
        ledger.chosen(0, 0)
    with pytest.raises(NoSharedWorldEvidence, match="missing"):
        exact_source_pair(ledger, 0, 0)
    assert world.actions_executed == 2


def test_cloned_world_source_and_duplicate_receipts_fail_closed():
    world = CurrentWorld()
    originals = observe_training(world)
    with pytest.raises(UnqualifiedHabitAcquisition, match="did not issue"):
        QualifiedLedger(world, (replace(originals[0]), originals[1]))
    with pytest.raises(UnqualifiedHabitAcquisition, match="duplicate"):
        QualifiedLedger(world, originals + (originals[0],))
    assert world.actions_executed == 8


def test_no_native_s10_or_wrong_b12_grant_never_authorizes_retained_s11():
    world = CurrentWorld()
    ledger = QualifiedLedger(world, observe_training(world))
    pair = exact_source_pair(ledger, 0, 0)
    owner = empty_repertoire()
    with pytest.raises(InvalidLearningAuthority):
        commit_existing_s10(
            ledger, pair, initial_s10_state(pair),
            native_permission(pair, granted=False),
        )
    assert ledger.chosen(0, 0)[0] == 0  # simple tags still have winner
    valid = commit_existing_s10(
        ledger, pair, initial_s10_state(pair), native_permission(pair),
    )
    draft = propose_same_source_s11(owner, ledger, pair, valid)
    bad_signed = OfflineIndependentS11Issuer(secrets.token_bytes(32)).grant(draft)
    with pytest.raises(InvalidIndependentHabitGrant, match="MAC"):
        IndependentS11Admission(secrets.token_bytes(32)).commit(
            owner, draft, ledger, bad_signed,
        )
    assert owner.rules == ()
