"""L next-epoch bridge: synthetic source-shaped fixtures, never real World facts."""
from __future__ import annotations

import json
from dataclasses import replace

import pytest

import test_experience_bridge as l1
import test_contextual_shadow as l5
from relay_self.action_outcome import ActionOutcomeDisposition
from relay_self.contextual_shadow import ContextualStatus, ShadowSpecification
from relay_self.experience_bridge import qualify_episode
from relay_self.habit_shadow import GoalSourceAdmission
from relay_self.learning_epoch import LearningEpochRejected, advance_learning_epoch
from relay_self.provenance import Provenance


def new_training(*, constant_winner=None, contradicted=None):
    """Rebuild the L5 saved source-shaped episodes through actual L1/S16 API."""
    retained, labels, admission = l5.setup_experience(
        constant_winner=constant_winner, contradicted=contradicted
    )
    arrivals = []
    for stored in retained.memories:
        data = json.loads(stored.content)
        action, outcome = l1.terminal(
            action_id=data["action_id"], session=data["session_id"],
            action_ref=data["action_ref"],
        )
        arrivals.append(qualify_episode(
            action, outcome, world_revision=data["world_revision"],
            evidence_sha256=data["evidence_sha256"],
            cue_tags=tuple(data["cue_tags"]),
        ))
    return tuple(arrivals), labels, admission, retained


def advance(*, arrivals=None, labels=None, admission=None, owner=None,
            before=(), retained=True, observation=None, **kw):
    return advance_learning_epoch(
        owner if owner is not None else l1.identity(),
        current_self_id=kw.pop("current_self_id", "test-self"),
        current=observation or l5.current(),
        admitted_current_probe_sha256=kw.pop(
            "admitted_current_probe_sha256", frozenset({"a" * 64})
        ),
        specification=ShadowSpecification(l5.FEATURES, l5.ACTIONS),
        no_memory_action_ref="OPTION_A",
        previous_goal_labels=before,
        new_episodes=arrivals if arrivals is not None else (),
        new_goal_labels=labels if labels is not None else (),
        source_admission=admission if admission is not None else GoalSourceAdmission(
            frozenset(), frozenset()
        ),
        integration_provenance=Provenance("synthetic", "L-next-epoch-test"),
        retention_enabled=retained,
        **kw,
    )


def test_retained_outcomes_change_following_epoch_l1_candidate_without_issuing():
    episodes, goals, admission, expected_owner = new_training()
    initial = l1.identity()
    off = advance(arrivals=episodes, labels=goals, admission=admission, retained=False)
    on = advance(arrivals=episodes, labels=goals, admission=admission)
    assert off.cognition == initial
    assert off.candidate_action_ref == "OPTION_A"
    assert off.advice.status is ContextualStatus.NO_GOAL_DATA
    assert off.retained_memory_ids == ()
    assert tuple(m.content for m in on.cognition.memories) == tuple(
        m.content for m in expected_owner.memories
    )
    assert len(on.retained_memory_ids) == len(on.cognition.memories) == 16
    assert on.candidate_action_ref == "OPTION_B"
    assert on.candidate_origin == "l1_experience_shadow"
    assert on.advice.status is ContextualStatus.SHADOW_DIFFERENCE
    assert on.advice.proposed_action_ref != off.candidate_action_ref
    assert on.advice.exact_cue_cheap_ref is None
    assert on.advice.singleton_cheap_ref is None
    assert on.advice.global_cheap_ref is None
    assert not on.action_authority
    assert not on.physical_goal_improvement_attested
    assert on.learning_updates == on.habit_grants == 0
    assert initial.memories == ()

    # A third epoch uses the same owner-local Memory rather than re-learning.
    following = advance(
        owner=on.cognition, before=goals, admission=admission,
        observation=l5.current(session="later-session", sha="b" * 64),
        admitted_current_probe_sha256=frozenset({"b" * 64}),
    )
    assert following.candidate_action_ref == "OPTION_B"
    assert following.retained_memory_ids == ()
    assert following.cognition is on.cognition
    assert following.advice.action_authority is False


def test_simple_cheap_rule_equal_or_better_is_not_promoted_to_habit():
    episodes, goals, admission, _ = new_training(constant_winner="OPTION_B")
    result = advance(arrivals=episodes, labels=goals, admission=admission)
    assert result.advice.status is ContextualStatus.CHEAP_EQUIVALENT
    assert result.candidate_action_ref == "OPTION_B"
    assert result.candidate_origin == "cheap_memory_rule"
    assert result.advice.global_cheap_ref == "OPTION_B"
    assert result.habit_grants == result.learning_updates == 0


def test_conflicting_goals_abstain_and_preserve_baseline():
    episodes, goals, admission, _ = new_training(contradicted=(True, True))
    result = advance(arrivals=episodes, labels=goals, admission=admission)
    assert result.advice.status is ContextualStatus.INSUFFICIENT
    assert result.candidate_action_ref == "OPTION_A"
    assert result.candidate_origin == "s_owned_no_memory_baseline"
    assert result.advice.proposed_action_ref is None


@pytest.mark.parametrize("case", [
    "foreign_self", "same_session", "future_revision", "unknown_outcome",
    "unadmitted_action", "unadmitted_goal", "wrong_label", "replay",
])
def test_bad_new_experience_never_produces_l1_training(case):
    episodes, goals, admission, _ = new_training()
    episodes, goals = (episodes[0],), (goals[0],)
    kw = {}
    if case == "foreign_self":
        kw["current_self_id"] = "another-self"
    elif case == "same_session":
        kw["observation"] = l5.current(session="session-0")
    elif case == "future_revision":
        kw["observation"] = replace(l5.current(), source_revision=4)
    elif case == "unknown_outcome":
        episodes = (replace(episodes[0], episode=replace(
            episodes[0].episode, disposition=ActionOutcomeDisposition.UNKNOWN,
        )),)
    elif case == "unadmitted_action":
        admission = replace(admission, admitted_action_sha256=frozenset())
    elif case == "unadmitted_goal":
        admission = replace(admission, admitted_goal_sha256=frozenset())
    elif case == "wrong_label":
        goals = (replace(goals[0], observed_memory_id="l1:wrong"),)
    elif case == "replay":
        episodes, goals = (episodes[0], episodes[0]), (goals[0], goals[0])
    with pytest.raises(ValueError):
        advance(arrivals=episodes, labels=goals, admission=admission, **kw)


def test_unverified_current_original_never_selects_retained_candidate():
    episodes, goals, admission, _ = new_training()
    result = advance(
        arrivals=episodes, labels=goals, admission=admission,
        admitted_current_probe_sha256=frozenset(),
    )
    assert result.advice.status is ContextualStatus.UNVERIFIED
    assert result.candidate_action_ref == "OPTION_A"
    assert result.advice.proposed_action_ref is None


def test_previous_training_not_in_existing_memory_cannot_be_laundered():
    episodes, goals, admission, _ = new_training()
    with pytest.raises(ValueError):
        advance(owner=l1.identity(), before=goals, admission=admission)
    # Memory without the independent S/V goal admissions cannot become training.
    admitted = GoalSourceAdmission(admission.admitted_action_sha256, frozenset())
    result = advance(
        arrivals=episodes, labels=goals,
        admission=admission,
    )
    no_goal = advance(owner=result.cognition, before=goals, admission=admitted)
    assert no_goal.advice.status is ContextualStatus.UNVERIFIED
    assert no_goal.candidate_action_ref == "OPTION_A"


def test_retention_update_is_transactional_and_no_habit_s10_mutation():
    episodes, goals, admission, _ = new_training()
    original = l1.identity()
    with pytest.raises(ValueError):
        advance(
            owner=original, arrivals=(episodes[0], episodes[0]),
            labels=(goals[0], goals[0]), admission=admission,
        )
    assert original.memories == ()
    successful = advance(arrivals=episodes, labels=goals, admission=admission)
    assert successful.cognition.appraisal_dispositions == ()
    assert len(successful.cognition.memories) == 16
    assert successful.learning_updates == successful.habit_grants == 0


def test_malformed_batch_type_cannot_be_silent_retention():
    with pytest.raises(LearningEpochRejected):
        advance(arrivals=[], labels=())
    with pytest.raises(LearningEpochRejected):
        advance(current_self_id="foreign")
