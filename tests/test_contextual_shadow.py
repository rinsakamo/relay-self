"""L5 deterministic contextual shadow, with synthetic source-shaped episodes only."""
from __future__ import annotations

from dataclasses import replace

import pytest

import test_experience_bridge as l1
from relay_self.contextual_shadow import (
    ContextualShadowRejected,
    ContextualStatus,
    ShadowContext,
    ShadowSpecification,
    review_contextual_shadow,
)
from relay_self.experience_bridge import qualify_episode, retain_observation
from relay_self.habit_shadow import ExternalGoalLabel, GoalSourceAdmission
from relay_self.provenance import Provenance

FEATURES = ("alpha", "beta")
ACTIONS = ("OPTION_A", "OPTION_B")


def setup_experience(*, constant_winner: str | None = None,
                     remove_bin: tuple[bool, bool] | None = None,
                     contradicted: tuple[bool, bool] | None = None):
    owner = l1.identity()
    labels = []
    action_digests = []
    goal_digests = []
    count = 0
    for a in (False, True):
        for b in (False, True):
            if (a, b) == remove_bin:
                continue
            winning_action = (
                constant_winner or ("OPTION_B" if a == b else "OPTION_A")
            )
            for action_ref in ACTIONS:
                for repetition in range(2):
                    i = count
                    count += 1
                    tags = tuple(sorted([
                        *([FEATURES[0]] if a else []),
                        *([FEATURES[1]] if b else []),
                        f"training_context_{a:d}{b:d}_rep_{repetition}",
                    ]))
                    action, outcome = l1.terminal(
                        action_id=f"action-{i}", session=f"session-{i}",
                        action_ref=action_ref,
                    )
                    original_sha = f"{1000+i:064x}"
                    goal_sha = f"{2000+i:064x}"
                    observed = qualify_episode(
                        action, outcome, world_revision=4,
                        evidence_sha256=original_sha,
                        cue_tags=tags,
                    )
                    owner = retain_observation(
                        owner, observed,
                        integration_provenance=Provenance("synthetic", f"memory-{i}"),
                    )
                    is_win = action_ref == winning_action
                    if contradicted == (a, b) and repetition == 1:
                        is_win = not is_win
                    labels.append(ExternalGoalLabel(
                        observed.episode.memory_id, goal_sha, is_win,
                        Provenance("synthetic-external-goal-only", f"goal-{i}"),
                    ))
                    action_digests.append(original_sha)
                    goal_digests.append(goal_sha)
    admission = GoalSourceAdmission(
        frozenset(action_digests), frozenset(goal_digests),
    )
    return owner, tuple(labels), admission


def current(*, session="current-session", tags=("alpha", "beta", "novel_cue"),
            sha="a" * 64):
    return ShadowContext(
        session, 8, sha, tags, Provenance("synthetic-native-probe", "after"),
    )


def review(owner, labels, admission, *, observation=None, spec=None,
           cheap_action="OPTION_A", admitted=frozenset({"a" * 64})):
    return review_contextual_shadow(
        owner, training=labels, source_admission=admission,
        current=observation or current(),
        admitted_current_probe_sha256=admitted,
        specification=spec or ShadowSpecification(FEATURES, ACTIONS),
        no_memory_action_ref=cheap_action,
    )


def test_learned_contextual_candidate_differs_from_no_memory_and_cheap_controls():
    owner, labels, admission = setup_experience()
    before = owner
    result = review(owner, labels, admission)
    assert result.status is ContextualStatus.SHADOW_DIFFERENCE
    assert result.proposed_action_ref == "OPTION_B"
    assert result.original_no_memory_ref == "OPTION_A"
    assert result.exact_cue_cheap_ref is None
    assert result.singleton_cheap_ref is None
    assert result.global_cheap_ref is None
    assert result.training_sessions == 16
    assert result.comparisons == 6
    assert not result.memory_causal_benefit_established
    assert not result.goal_improvement_attested
    assert not result.action_authority
    assert result.habit_grants == result.learning_updates == 0
    assert owner == before
    assert len(owner.memories) == 16
    assert owner.appraisal_dispositions == ()


def test_same_exact_current_probe_with_memory_withheld_abstains():
    owner, labels, admission = setup_experience()
    with_memory = review(owner, labels, admission)
    withheld = review(owner, (), admission)
    assert with_memory.status is ContextualStatus.SHADOW_DIFFERENCE
    assert withheld.status is ContextualStatus.NO_GOAL_DATA
    assert withheld.proposed_action_ref is None
    assert with_memory.action_authority == withheld.action_authority is False


def test_synthetic_shadow_does_not_beat_strongest_same_information_cheap_policy():
    owner, labels, admission = setup_experience(constant_winner="OPTION_B")
    result = review(owner, labels, admission)
    assert result.status is ContextualStatus.CHEAP_EQUIVALENT
    assert result.proposed_action_ref == result.global_cheap_ref == "OPTION_B"
    assert result.goal_improvement_attested is False


def test_s_original_no_memory_policy_can_agree_without_any_new_effect():
    owner, labels, admission = setup_experience()
    result = review(owner, labels, admission, cheap_action="OPTION_B")
    assert result.status is ContextualStatus.NO_MEMORY_EQUAL
    assert result.proposed_action_ref == "OPTION_B"
    assert result.action_authority is False


@pytest.mark.parametrize(("case", "expected"), [
    ("no_current_admission", ContextualStatus.UNVERIFIED),
    ("no_goal_admission", ContextualStatus.UNVERIFIED),
    ("no_action_admission", ContextualStatus.UNVERIFIED),
    ("missing_quadrant", ContextualStatus.INSUFFICIENT),
    ("ambiguous_cell", ContextualStatus.INSUFFICIENT),
])
def test_missing_provenance_or_balanced_independent_training_abstains(case, expected):
    owner, labels, admission = setup_experience(
        remove_bin=(False, False) if case == "missing_quadrant" else None,
        contradicted=(True, True) if case == "ambiguous_cell" else None,
    )
    admitted = frozenset() if case == "no_current_admission" else frozenset({"a" * 64})
    if case == "no_goal_admission":
        admission = replace(admission, admitted_goal_sha256=frozenset())
    if case == "no_action_admission":
        admission = replace(admission, admitted_action_sha256=frozenset())
    result = review(owner, labels, admission, admitted=admitted)
    assert result.status is expected
    assert result.proposed_action_ref is None
    assert result.action_authority is False


def test_replayed_source_current_session_or_original_sha_are_not_training():
    owner, labels, admission = setup_experience()
    with pytest.raises(ContextualShadowRejected, match="replay"):
        review(owner, labels, admission, observation=current(session="session-0"))
    with pytest.raises(ContextualShadowRejected, match="replay"):
        review(
            owner, labels, admission,
            observation=current(sha=f"{1000:064x}"),
            admitted=frozenset({f"{1000:064x}"}),
        )
    replayed = (labels[0], labels[0], *labels[2:])
    with pytest.raises(ContextualShadowRejected, match="training denied"):
        review(owner, replayed, admission)


def test_wrong_current_original_and_unexpected_action_vocabulary_fail_closed():
    owner, labels, admission = setup_experience()
    with pytest.raises(ContextualShadowRejected, match="outside S vocabulary"):
        review(owner, labels, admission, cheap_action="OPTION_UNKNOWN")
    with pytest.raises(ContextualShadowRejected, match="foreign Action vocabulary"):
        review(
            owner, labels, admission,
            spec=ShadowSpecification(FEATURES, ("OPTION_A", "OPTION_C")),
        )
    with pytest.raises(ContextualShadowRejected, match="two declared"):
        ShadowSpecification(("alpha", "alpha"), ACTIONS)
    with pytest.raises(ContextualShadowRejected, match="current source"):
        current(tags=("unsorted", "alpha"))


def test_malformed_observed_memory_or_fake_goal_is_not_cognitive_training():
    owner, labels, admission = setup_experience()
    with pytest.raises(ValueError, match="goal evidence"):
        replace(labels[0], goal_reached="true")
    with pytest.raises(ContextualShadowRejected, match="training denied"):
        review(
            owner, (replace(labels[0], observed_memory_id="l1:forged"), *labels[1:]),
            admission,
        )


def test_predeclared_two_feature_restriction_does_not_consult_extra_tag_as_oracle():
    owner, labels, admission = setup_experience()
    x = review(owner, labels, admission)
    changed = review(
        owner, labels, admission,
        observation=current(tags=("alpha", "beta", "unseen_foreign_nuisance")),
    )
    assert x.proposed_action_ref == changed.proposed_action_ref == "OPTION_B"
    assert changed.goal_improvement_attested is False
