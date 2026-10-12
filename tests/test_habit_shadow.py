"""L3 shadow S11 gate: source and goal labels are synthetic typed fixtures ONLY."""
from __future__ import annotations

import json
from dataclasses import replace

import pytest

import test_experience_bridge as l1
from relay_self.experience_bridge import retain_observation
from relay_self.habit_shadow import (
    ExternalGoalLabel,
    GoalSourceAdmission,
    ShadowHabitRejected,
    ShadowStatus,
    review_shadow_habit,
)
from relay_self.persistent_cognition import Memory, save_persistent_cognition
from relay_self.provenance import Provenance


def fixture(
    *,
    outcomes: tuple[bool, ...] = (True, True, True, True, True),
    action_refs: tuple[str, ...] | None = None,
    unknown_at: int | None = None,
):
    """Five independently shaped synthetic sessions. NO physical goal labels."""
    owner = l1.identity()
    labels = []
    action_hashes = []
    goal_hashes = []
    for i, success in enumerate(outcomes):
        session = f"synthetic-session-{i}"
        action = f"synthetic-action-{i}"
        action_digest = f"{i+1:064x}"
        goal_digest = f"{i+101:064x}"
        q = l1.qualified(
            action_id=action, session=session, revision=3,
            digest=action_digest, unknown=unknown_at == i,
        )
        if action_refs:
            action_obj, outcome = l1.terminal(
                action_id=action, session=session, action_ref=action_refs[i],
                unknown=unknown_at == i,
            )
            from relay_self.experience_bridge import qualify_episode
            q = qualify_episode(
                action_obj, outcome, world_revision=3,
                evidence_sha256=action_digest, cue_tags=l1.TAGS,
            )
        owner = retain_observation(
            owner, q, integration_provenance=Provenance("synthetic", f"retain-{i}"),
        )
        labels.append(ExternalGoalLabel(
            q.episode.memory_id, goal_digest, success,
            Provenance("synthetic-unverified-goal", f"goal-{i}"),
        ))
        action_hashes.append(action_digest)
        goal_hashes.append(goal_digest)
    return (
        owner, tuple(labels),
        GoalSourceAdmission(frozenset(action_hashes), frozenset(goal_hashes)),
    )


def review(owner, labels, admission, *, holdout=None):
    return review_shadow_habit(
        owner, train=labels[:3], holdout=labels[3:] if holdout is None else holdout,
        admission=admission, cue_tags=l1.TAGS,
    )


def test_qualified_synthetic_shadow_is_equal_to_cheap_null_and_never_promotes(tmp_path):
    owner, labels, admission = fixture()
    snapshot_before = owner
    result = review(owner, labels, admission)
    assert result.status is ShadowStatus.CHEAP_NULL_EQUAL
    assert result.candidate_ref == result.cheap_candidate_ref == "MOVE_BACKWARD"
    assert result.train_sessions == 3
    assert result.holdout_sessions == 2
    assert result.selection_matches
    assert result.action_authority is False
    assert result.habit_grants == result.learning_updates == 0
    assert owner == snapshot_before
    assert owner.appraisal_dispositions == ()
    assert len(owner.memories) == 5  # Not 6: no new retained Habit.
    assert not hasattr(result, "issue") and not hasattr(result, "grant")
    path = tmp_path / "existing-owner.json"
    save_persistent_cognition(path, owner)
    assert path.is_file()


def test_no_external_goal_evidence_is_not_an_implicit_success():
    owner, _, admission = fixture()
    assert review_shadow_habit(
        owner, train=(), holdout=(), admission=admission, cue_tags=l1.TAGS,
    ).status is ShadowStatus.NO_GOAL_EVIDENCE


def test_movement_with_unadmitted_goal_label_never_creates_eligible_habit():
    owner, labels, admission = fixture()
    lacking = GoalSourceAdmission(admission.admitted_action_sha256, frozenset())
    result = review(owner, labels, lacking)
    assert result.status is ShadowStatus.UNVERIFIED
    assert result.candidate_ref is None
    lacking_action = GoalSourceAdmission(frozenset(), admission.admitted_goal_sha256)
    assert review(owner, labels, lacking_action).status is ShadowStatus.UNVERIFIED


@pytest.mark.parametrize(("outcomes", "expected"), [
    ((True, True, False, True, True), ShadowStatus.CONFLICTING),
    ((True, True, True, True, False), ShadowStatus.SHIFT_DETECTED),
    ((True, True, True, False, False), ShadowStatus.SHIFT_DETECTED),
])
def test_training_conflict_and_holdout_distribution_shift_block(outcomes, expected):
    owner, labels, admission = fixture(outcomes=outcomes)
    result = review(owner, labels, admission)
    assert result.status is expected
    assert result.candidate_ref is None
    assert result.habit_grants == 0


def test_absent_executed_action_holdout_cannot_be_counterfactual_scored():
    refs = ("MOVE_BACKWARD", "MOVE_BACKWARD", "MOVE_BACKWARD", "WAIT", "WAIT")
    owner, labels, admission = fixture(action_refs=refs)
    result = review(owner, labels, admission)
    assert result.status is ShadowStatus.INSUFFICIENT
    assert result.candidate_ref is None
    assert result.reason == "no_independent_holdout_for_executed_action"


def test_unseen_cue_and_unmatched_context_abstain():
    owner, labels, admission = fixture()
    result = review_shadow_habit(
        owner, train=labels[:3], holdout=labels[3:],
        admission=admission, cue_tags=("unseen",),
    )
    assert result.status is ShadowStatus.INSUFFICIENT
    assert result.habit_grants == 0


def test_unknown_original_action_cannot_be_goal_labeled_by_l3():
    owner, labels, admission = fixture(unknown_at=1)
    with pytest.raises(ShadowHabitRejected, match="observed S16"):
        review(owner, labels, admission)


def test_holdout_reuse_or_replayed_session_fails_closed():
    owner, labels, admission = fixture()
    with pytest.raises(ShadowHabitRejected, match="independent original"):
        review_shadow_habit(
            owner, train=labels[:3], holdout=(labels[0], labels[4]),
            admission=admission, cue_tags=l1.TAGS,
        )
    with pytest.raises(ShadowHabitRejected, match="duplicate"):
        review_shadow_habit(
            owner, train=(labels[0], labels[0], labels[1]),
            holdout=labels[3:], admission=admission, cue_tags=l1.TAGS,
        )


def test_forged_goal_and_missing_original_l1_are_not_accepted():
    owner, labels, admission = fixture()
    with pytest.raises(ShadowHabitRejected, match="goal evidence"):
        replace(labels[0], goal_reached="true")
    bad = replace(labels[0], observed_memory_id="l1:phantom")
    with pytest.raises(ShadowHabitRejected, match="absent"):
        review_shadow_habit(
            owner, train=(bad, *labels[1:3]), holdout=labels[3:],
            admission=admission, cue_tags=l1.TAGS,
        )


def test_l2_comparison_is_not_a_goal_attestation():
    owner, labels, admission = fixture()
    owner = owner.retain_memory(Memory(
        "l2:comparison:fake",
        json.dumps({
            "schema": "L2_OBSERVED_COMPARISON_V1",
            "status": "match",
            "goal_success_attested": False,
            "learning_authorized": False,
        }),
        Provenance("synthetic", "not-physical-goal"),
        Provenance("synthetic", "derived"),
    ))
    assert review(
        owner, labels,
        GoalSourceAdmission(admission.admitted_action_sha256, frozenset()),
    ).status is ShadowStatus.UNVERIFIED


def test_malformed_original_observed_memory_cannot_be_upgraded():
    owner, labels, admission = fixture()
    stored = owner.memories[0]
    invalid = Memory(
        stored.memory_id, '{"schema":"L1_SOURCE_EPISODE_V1"}',
        stored.source_provenance, stored.integration_provenance,
    )
    from relay_self.persistent_cognition import PersistentCognition
    owner = PersistentCognition(
        owner.identity, (invalid, *owner.memories[1:]),
        owner.appraisal_dispositions,
    )
    with pytest.raises(ShadowHabitRejected, match="malformed original"):
        review(owner, labels, admission)


def test_invalid_evidence_admission_shape_rejected():
    with pytest.raises(ShadowHabitRejected, match="digest admission"):
        GoalSourceAdmission(frozenset({"invalid"}), frozenset())
    with pytest.raises(ShadowHabitRejected, match="source cue"):
        owner, labels, admission = fixture()
        review_shadow_habit(
            owner, train=labels[:3], holdout=labels[3:],
            admission=admission, cue_tags=("bad cue",),
        )
