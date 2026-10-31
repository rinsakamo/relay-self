"""L7 S42 choice vs L1 offline comparator: synthetic fixtures, no World/Action."""
from __future__ import annotations

import json
from dataclasses import replace

import pytest

import test_contextual_shadow as l5
import test_experience_bridge as l1
import test_postmain_s42_world_contrast as s42
from relay_self.contextual_shadow import ShadowContext, ShadowSpecification
from relay_self.experience_bridge import qualify_episode
from relay_self.l1_s_choice_shadow import (
    SChoiceContrastStatus,
    SChoiceShadowRejected,
    compare_s_choice_with_l1,
)
from relay_self.learning_epoch import advance_learning_epoch
from relay_self.provenance import Provenance
from relay_self.world_conditioned_choice import (
    WorldChoiceKind,
    select_world_conditioned_choice,
)

ACTIONS = ("MOVE_AWAY", "WAIT")


def training(*, constant_winner=None, contradicted=None):
    """Retain L5's existing synthetic original-shaped goal labels; remap refs."""
    owner, labels, admission = l5.setup_experience(
        constant_winner=constant_winner, contradicted=contradicted
    )
    episodes = []
    for memory in owner.memories:
        data = json.loads(memory.content)
        action_ref = {
            "OPTION_A": "MOVE_AWAY",
            "OPTION_B": "WAIT",
        }[data["action_ref"]]
        action, outcome = l1.terminal(
            action_id=data["action_id"], session=data["session_id"],
            action_ref=action_ref,
        )
        episodes.append(qualify_episode(
            action, outcome, world_revision=data["world_revision"],
            evidence_sha256=data["evidence_sha256"],
            cue_tags=tuple(data["cue_tags"]),
        ))
    return tuple(episodes), labels, admission


def scenario(*, near=True, enabled=True, tags=("alpha", "beta", "novel_cue"),
             constant_winner=None, contradicted=None):
    retained, near_native, far_native, _, _ = s42._pair()
    native = near_native if near else far_native
    s_choice = select_world_conditioned_choice(
        native, retained,
        expected_session_id=native.observation.session_id,
        expected_entity_id=native.entity_id,
    )
    episodes, goals, admission = training(
        constant_winner=constant_winner, contradicted=contradicted
    )
    current = ShadowContext(
        session_id=s_choice.session_id,
        source_revision=128,  # fixture's S-assigned revision, NOT Paper WorldTick
        original_probe_sha256="a" * 64,
        cue_tags=tags,
        source_provenance=s_choice.provenance,
    )
    before = l1.identity()
    learned = advance_learning_epoch(
        before,
        current_self_id=before.identity.self_id,
        current=current,
        admitted_current_probe_sha256=frozenset({"a" * 64}),
        specification=ShadowSpecification(("alpha", "beta"), ACTIONS),
        no_memory_action_ref=s_choice.selection.value,
        previous_goal_labels=(),
        new_episodes=episodes,
        new_goal_labels=goals,
        source_admission=admission,
        integration_provenance=Provenance("synthetic", "l7-read-only"),
        retention_enabled=enabled,
    )
    return before, retained, native, s_choice, learned


def compare(retained, native, s_choice, learned, enabled=True):
    return compare_s_choice_with_l1(
        native=native, retained=retained, s_choice=s_choice,
        learning=learned, retention_enabled=enabled,
    )


def test_same_native_s_choice_with_memory_off_vs_on_shows_l1_difference():
    before, retained, native, s_choice, learning = scenario()
    assert s_choice.selection is WorldChoiceKind.MOVE_AWAY
    off_before, off_retained, off_native, off_s, off_learning = scenario(
        enabled=False
    )
    assert off_s == s_choice
    assert off_native == native
    assert off_retained == retained
    assert len(off_learning.cognition.memories) == 0
    off = compare(off_retained, off_native, off_s, off_learning, enabled=False)
    on = compare(retained, native, s_choice, learning)
    assert off.status is SChoiceContrastStatus.WITHHELD
    assert off.l1_shadow_ref is None
    assert on.status is SChoiceContrastStatus.L1_DIFFERS
    assert on.l1_shadow_ref == "WAIT"
    assert on.s_choice is WorldChoiceKind.MOVE_AWAY
    assert on.candidate_differs
    assert on.source_revision == 128
    assert on.probe_seq == native.observation.seq
    assert on.original_probe_sha256 == "a" * 64
    assert on.s_choice_kept and not on.action_authority
    assert on.action_issues == on.learning_updates == on.habit_grants == 0
    assert len(learning.cognition.memories) == 16
    assert before.memories == off_before.memories == ()


def test_far_native_wait_remains_s_choice_even_if_l1_proposes_move():
    _, retained, native, s_choice, learned = scenario(
        near=False, tags=("alpha", "novel_cue"),
    )
    assert s_choice.selection is WorldChoiceKind.WAIT
    result = compare(retained, native, s_choice, learned)
    assert result.status is SChoiceContrastStatus.L1_DIFFERS
    assert result.l1_shadow_ref == "MOVE_AWAY"
    assert result.s_choice is WorldChoiceKind.WAIT
    assert result.s_choice_kept
    assert result.action_issues == 0


def test_l1_agrees_with_s_and_no_action_promotion():
    _, retained, native, s_choice, learned = scenario(
        near=False,
    )
    result = compare(retained, native, s_choice, learned)
    assert result.status is SChoiceContrastStatus.AGREES
    assert result.l1_shadow_ref == "WAIT"
    assert not result.candidate_differs
    assert result.action_issues == result.habit_grants == 0


def test_cheap_majority_matches_shadow_without_learning_advantage():
    _, retained, native, s_choice, learned = scenario(
        constant_winner="OPTION_B",
    )
    result = compare(retained, native, s_choice, learned)
    assert result.status is SChoiceContrastStatus.CHEAP_DIFFERS
    assert result.l1_shadow_ref == "WAIT"
    assert learned.advice.global_cheap_ref == "WAIT"
    assert result.s_choice is WorldChoiceKind.MOVE_AWAY


def test_conflicting_goal_abstains_and_s_decision_is_unchanged():
    _, retained, native, s_choice, learned = scenario(
        contradicted=(True, True)
    )
    result = compare(retained, native, s_choice, learned)
    assert result.status is SChoiceContrastStatus.INSUFFICIENT
    assert result.l1_shadow_ref is None
    assert not result.candidate_differs
    assert result.action_issues == result.learning_updates == 0


@pytest.mark.parametrize("fault", [
    "foreign_session", "wrong_provenance", "wrong_probe_digest",
    "wrong_baseline", "wrong_candidate", "tampered_s_choice",
    "wrong_native", "wrong_retained", "false_grant", "wrong_flag",
])
def test_foreign_stale_mutated_or_unauthorized_join_fails_closed(fault):
    _, retained, native, s_choice, learned = scenario()
    enabled = True
    if fault == "foreign_session":
        learned = replace(
            learned, current=replace(learned.current, session_id="foreign"),
        )
    elif fault == "wrong_provenance":
        learned = replace(
            learned, current=replace(
                learned.current,
                source_provenance=Provenance("synthetic", "other-probe"),
            ),
        )
    elif fault == "wrong_probe_digest":
        learned = replace(learned, admitted_current_probe_sha256=frozenset())
    elif fault == "wrong_baseline":
        learned = replace(learned, no_memory_action_ref="WAIT")
    elif fault == "wrong_candidate":
        learned = replace(learned, candidate_action_ref="MOVE_AWAY")
    elif fault == "tampered_s_choice":
        s_choice = replace(s_choice, selection=WorldChoiceKind.WAIT)
    elif fault == "wrong_native":
        _, _, other, _, _ = scenario(near=False)
        native = other
    elif fault == "wrong_retained":
        retained = replace(retained, revision=0, last_update=None)
    elif fault == "false_grant":
        learned = replace(learned, action_authority=True)
    elif fault == "wrong_flag":
        enabled = False
    with pytest.raises(SChoiceShadowRejected):
        compare(retained, native, s_choice, learned, enabled=enabled)


def test_foreign_result_and_same_context_cannot_overwrite_l0():
    _, retained, native, s_choice, learned = scenario()
    first = compare(retained, native, s_choice, learned)
    again = compare(retained, native, s_choice, learned)
    assert first == again
    assert s_choice.selection is WorldChoiceKind.MOVE_AWAY
    assert learned.candidate_action_ref == "WAIT"
    assert first.s_choice_kept and first.action_issues == 0
