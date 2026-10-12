"""L4 source-shaped prospective paired holdout tests. Not physical science."""
from __future__ import annotations

from dataclasses import replace

import pytest

import test_habit_shadow as l3
from relay_self.learning_contrast import (
    ExternalTrialAdmission,
    LearningReviewStatus,
    MatchedEvidenceRejected,
    ProspectiveTrial,
    TrialArm,
    review_matched_transfer,
)

HEAD = "916814742567f8ff396b5c078d22f897d8418927"
PLAN = "f" * 64
WORLD = "e" * 64
GOAL = "d" * 64
CANDIDATES = "c" * 64


def trial(pair: int, arm: TrialArm, *, goal: bool, work: int = 3,
          cue: str | None = None, session: str | None = None,
          world: str = WORLD, head: str = HEAD,
          memory_id: str | None = None) -> ProspectiveTrial:
    suffix = 0 if arm is TrialArm.RETAINED else 1
    number = 200 + pair * 10 + suffix
    if arm is TrialArm.RETAINED and memory_id is None:
        memory_id = "l1:synthetic-session-0:synthetic-action-0:3"
    return ProspectiveTrial(
        f"pair-{pair}", arm,
        session or f"heldout-session-{pair}-{suffix}",
        head, world, GOAL, CANDIDATES,
        cue or f"new_holdout_cue_{pair}",
        PLAN,
        f"{number:064x}", f"{number+1000:064x}",
        f"{number+2000:064x}", f"{number+3000:064x}",
        goal, work, memory_id=memory_id,
    )


def fixture(*, retained_goals=(True, True), cheap_goals=(False, False),
            retained_work=(3, 3), cheap_work=(5, 5)):
    owner, labels, admission_l3 = l3.fixture()
    pairs = []
    for i, (retain_goal, cheap_goal) in enumerate(zip(retained_goals, cheap_goals)):
        pairs.extend((
            trial(i, TrialArm.RETAINED, goal=retain_goal, work=retained_work[i],
                  memory_id=labels[0].observed_memory_id),
            trial(i, TrialArm.CHEAP, goal=cheap_goal, work=cheap_work[i]),
        ))
    return (
        owner, labels[:3], tuple(pairs),
        ExternalTrialAdmission(
            admission_l3.admitted_action_sha256
            | frozenset(x.action_sha256 for x in pairs),
            admission_l3.admitted_goal_sha256
            | frozenset(x.goal_sha256 for x in pairs),
            frozenset(x.decision_sha256 for x in pairs),
            frozenset(x.cost_sha256 for x in pairs),
            frozenset({PLAN}),
        ),
    )


def assess(owner, train, pairs, admission):
    return review_matched_transfer(
        owner, training=train, trials=pairs,
        admission=admission, preregistered_plan_sha256=PLAN,
    )


def test_positive_source_shaped_counterexample_remains_v_review_only():
    owner, training, pairs, admission = fixture()
    prior = owner
    review = assess(owner, training, pairs, admission)
    assert review.status is LearningReviewStatus.REVIEW_LIFT_ONLY
    assert review.paired_trials == 2
    assert review.retained_goal_successes == 2
    assert review.cheap_goal_successes == 0
    assert review.retained_work_units == 6
    assert review.cheap_work_units == 10
    assert review.transfer_contexts == 2
    assert not review.science_qualified
    assert not review.action_authority
    assert review.habit_grants == review.learning_updates == 0
    assert owner == prior and len(owner.memories) == 5


def test_s9_two_actions_without_independent_goal_or_matched_cheap_control_are_no_go():
    owner, _, _, admission = fixture()
    result = assess(owner, (), (), admission)
    assert result.status is LearningReviewStatus.NO_MATCHED_HOLDOUT
    assert result.reason == "S9_two_actions_same_session_not_a_matched_cheap_control"
    assert result.science_qualified is False
    assert assess(owner, (), (trial(0, TrialArm.RETAINED, goal=True),), admission).status is (
        LearningReviewStatus.NO_GOAL_SOURCE
    )


@pytest.mark.parametrize(("retained", "cheap", "work_retained", "work_cheap",
                          "expected"), [
    ((True, True), (True, True), (3, 3), (3, 3),
     LearningReviewStatus.CHEAP_NULL_EQUAL),
    ((False, False), (True, True), (3, 3), (5, 5),
     LearningReviewStatus.CHEAP_DOMINATES),
    ((True, True), (False, False), (9, 9), (5, 5),
     LearningReviewStatus.CHEAP_DOMINATES),
])
def test_cheap_null_and_resource_regressions_not_promoted(
    retained, cheap, work_retained, work_cheap, expected,
):
    owner, training, pairs, admission = fixture(
        retained_goals=retained, cheap_goals=cheap,
        retained_work=work_retained, cheap_work=work_cheap,
    )
    result = assess(owner, training, pairs, admission)
    assert result.status is expected
    assert result.science_qualified is False
    assert result.habit_grants == 0


def test_unverified_plan_originals_or_goal_and_work_returns_unknown():
    owner, train, pairs, a = fixture()
    missing_plan = replace(a, plan_sha256=frozenset())
    assert assess(owner, train, pairs, missing_plan).status is (
        LearningReviewStatus.UNVERIFIED
    )
    lacking_goal = replace(a, goal_sha256=frozenset(
        x.goal_source_sha256 for x in train
    ))
    assert assess(owner, train, pairs, lacking_goal).status is (
        LearningReviewStatus.UNVERIFIED
    )
    lacking_cost = replace(a, cost_sha256=frozenset())
    assert assess(owner, train, pairs, lacking_cost).status is (
        LearningReviewStatus.UNVERIFIED
    )


def test_missing_cheap_arm_and_insufficient_independent_holdout():
    owner, train, pairs, admission = fixture()
    missing = (pairs[0], pairs[2])
    assert assess(owner, train, missing, admission).status is (
        LearningReviewStatus.NO_MATCHED_HOLDOUT
    )
    assert assess(owner, train, pairs[:2], admission).status is (
        LearningReviewStatus.NO_TRANSFER
    )


def test_wrong_world_hash_or_wrong_source_head_not_pair_matched():
    owner, train, pairs, admission = fixture()
    wrong_world = (*pairs[:1], replace(pairs[1], initial_world_sha256="b" * 64),
                   *pairs[2:])
    assert assess(owner, train, wrong_world, admission).status is (
        LearningReviewStatus.NON_MATCHED
    )
    wrong_head = (*pairs[:1], replace(pairs[1], source_head="1" * 40),
                  *pairs[2:])
    assert assess(owner, train, wrong_head, admission).status is (
        LearningReviewStatus.NON_MATCHED
    )


def test_no_unseen_transfer_context_is_not_generalization():
    owner, train, pairs, admission = fixture()
    same_cue = "/".join(l3.l1.TAGS)
    changed = tuple(replace(p, cue_key=same_cue) for p in pairs)
    assert assess(owner, train, changed, admission).status is (
        LearningReviewStatus.NO_TRANSFER
    )


def test_training_and_test_session_cannot_overlap_and_source_cannot_replay():
    owner, train, pairs, admission = fixture()
    reused = (replace(pairs[0], session_id="synthetic-session-0"), *pairs[1:])
    with pytest.raises(MatchedEvidenceRejected, match="session replay"):
        assess(owner, train, reused, admission)
    duplicate = (pairs[0], replace(pairs[1], action_sha256=pairs[0].action_sha256),
                 *pairs[2:])
    with pytest.raises(MatchedEvidenceRejected, match="replayed source"):
        assess(owner, train, duplicate, admission)


def test_memory_id_must_come_from_admitted_prior_training_not_new_session():
    owner, train, pairs, admission = fixture()
    changed = (replace(pairs[0], memory_id="l1:foreign:unseen:3"), *pairs[1:])
    with pytest.raises(MatchedEvidenceRejected, match="independent training"):
        assess(owner, train, changed, admission)
    with pytest.raises(MatchedEvidenceRejected, match="retained arm"):
        replace(pairs[0], memory_id=None)
    with pytest.raises(MatchedEvidenceRejected, match="cheap arm"):
        replace(pairs[1], memory_id=train[0].observed_memory_id)


def test_training_episodes_without_independently_admitted_goal_cannot_train():
    owner, train, pairs, admission = fixture()
    lacking_training = replace(admission, goal_sha256=frozenset(
        x.goal_sha256 for x in pairs
    ))
    with pytest.raises(MatchedEvidenceRejected, match="unverified"):
        assess(owner, train, pairs, lacking_training)
    not_goal = (replace(train[0], goal_reached=False), *train[1:])
    with pytest.raises(MatchedEvidenceRejected, match="unsuccessful"):
        assess(owner, not_goal, pairs, admission)


def test_unregistered_trial_and_duplicate_arm_fail_closed():
    owner, train, pairs, admission = fixture()
    changed = (replace(pairs[0], plan_sha256="4" * 64), *pairs[1:])
    assert assess(owner, train, changed, admission).status is (
        LearningReviewStatus.NON_MATCHED
    )
    duplicate = (pairs[0], replace(pairs[0], session_id="other-session",
                                  action_sha256="9" * 64,
                                  decision_sha256="8" * 64,
                                  goal_sha256="7" * 64,
                                  cost_sha256="6" * 64), *pairs[1:])
    with pytest.raises(MatchedEvidenceRejected):
        assess(owner, train, duplicate, admission)


def test_data_type_and_authority_are_not_inferred_from_dataclass():
    a = ExternalTrialAdmission(
        frozenset(), frozenset(), frozenset(), frozenset(), frozenset(),
    )
    assert a.action_sha256 == frozenset()
    with pytest.raises(MatchedEvidenceRejected, match="source digest"):
        replace(trial(0, TrialArm.CHEAP, goal=False), goal_sha256="none")
    with pytest.raises(MatchedEvidenceRejected, match="typed outcome"):
        replace(trial(0, TrialArm.CHEAP, goal=False), goal_reached=1)
    with pytest.raises(MatchedEvidenceRejected, match="original S/R/V"):
        replace(a, cost_sha256=frozenset({"invalid"}))
