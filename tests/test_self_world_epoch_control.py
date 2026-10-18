"""Stage Q DEV/OFFLINE one committed owner for original S42 choice and S14.

Entire suite is synthetic: no actual Minecraft S49 executor or S10 issuer.
"""
from __future__ import annotations

from dataclasses import replace

import pytest

import test_action_feedback_qualification as s17
import test_postmain_s42_world_contrast as s42
import test_self_world_epoch_handoff as p_fixture
from adapters.mineflayer.s34_native_world_cognition_ci import _native_threat
from adapters.mineflayer.self_world_epoch_control import (
    StageQDevBoundaryRejected,
    stage_q_dev_joint_choice_admission,
)
from adapters.mineflayer.self_world_epoch_handoff import (
    prepare_stage_p_offline_dual_read,
)
from relay_self.intent import IntentCommitment
from relay_self.learning import propose_learning_update
from relay_self.provenance import Provenance
from relay_self.world_conditioned_choice import (
    WorldChoiceKind,
    WorldChoiceRejected,
    select_stage_q_dev_committed_world_choice,
    select_world_conditioned_choice,
)


def _stage_q():
    original, args = p_fixture._rehearsal()
    baseline, near, _, _, _ = s42._pair()
    assert original.retained.revision == 0
    args.update(
        previous_owner=baseline,
        current_l0_owner=baseline,
        current_s14_owner=baseline,
        proposal=propose_learning_update(
            baseline, args["interpretation"].feedback, s17.learning_rule(),
        ),
        next_probe=replace(
            args["next_probe"], snapshot=near.observation.snapshot,
        ),
    )
    p = prepare_stage_p_offline_dual_read(**args)
    probe = p.following_native_observation
    native = _native_threat(
        probe, probe.request_id, expected_entity_id=near.entity_id,
    )
    intent = IntentCommitment()
    intent.commit(
        "escape-threat", objective="synthetic near zombie",
        at_ns=1, provenance=Provenance("stage-q-synthetic", "intent-only"),
    )
    kwargs = {
        "stage_p": p,
        "previous_l0_owner": baseline,
        "previous_s14_owner": baseline,
        "native": native,
        "intent": intent,
    }
    return original, kwargs


def test_q_original_frozen_choice_still_rejects_successor():
    original, kwargs = _stage_q()
    result = kwargs["stage_p"]
    current = result.committed.new_state
    native = kwargs["native"]
    assert current.revision == 2 and current.value == 4
    with pytest.raises(WorldChoiceRejected, match="frozen governed rev1"):
        select_world_conditioned_choice(
            native, current, expected_session_id=native.observation.session_id,
            expected_entity_id=native.entity_id,
        )
    assert original.retained.revision == 0  # no host takeover


def test_q_same_original_choice_and_s14_admission_on_rev2_hold():
    original, kwargs = _stage_q()
    result = kwargs["stage_p"]
    outcome = stage_q_dev_joint_choice_admission(**kwargs)
    assert outcome.exact_l0_s14_identity
    assert outcome.exact_native_source_identity
    assert outcome.retained_revision == 2
    assert outcome.retained_value == 4  # unchanged HOLD, not reward
    assert outcome.choice.selection is WorldChoiceKind.MOVE_AWAY
    assert outcome.choice.wait_score == 8
    assert outcome.choice.move_score == 7
    assert outcome.l0_selected_candidate == "MOVE_AWAY"
    assert outcome.s14_selected_candidate == "MOVE_AWAY"
    assert outcome.s14_admission_status == "admitted"
    assert not outcome.choice.action_authorized
    assert not outcome.minecraft_action_issued
    assert not outcome.learning_grant_independently_attested
    assert not outcome.installed_in_original_s49
    assert not outcome.causal_learning_observed
    assert original.retained.revision == 0
    assert result.committed.new_state is result.l0_read.snapshot
    assert result.committed.new_state is result.s14_read.snapshot


@pytest.mark.parametrize("case", (
    "old_l0", "old_s14", "copied_old_owner", "reconstructed_new_owner",
    "wrong_next_native_identity", "foreign_next_native_session",
    "old_revision", "tampered_value", "missing_provenance",
    "foreign_intent", "missing_intent", "next_wait",
))
def test_q_joint_rejects_identity_source_or_intent_confounds(case):
    _, kwargs = _stage_q()
    p = kwargs["stage_p"]
    current = p.committed.new_state
    if case == "old_l0":
        kwargs["previous_l0_owner"] = current
    elif case == "old_s14":
        kwargs["previous_s14_owner"] = current
    elif case == "copied_old_owner":
        kwargs["previous_l0_owner"] = replace(
            kwargs["previous_l0_owner"],
        )
    elif case == "reconstructed_new_owner":
        kwargs["stage_p"] = replace(
            p, s14_read=replace(
                p.s14_read, snapshot=replace(current),
            ),
        )
    elif case == "wrong_next_native_identity":
        kwargs["native"] = replace(
            kwargs["native"],
            observation=replace(kwargs["native"].observation),
        )
    elif case == "foreign_next_native_session":
        kwargs["native"] = replace(
            kwargs["native"],
            observation=replace(
                kwargs["native"].observation, session_id="other-session",
            ),
        )
    elif case == "old_revision":
        kwargs["stage_p"] = replace(
            p, l0_read=replace(
                p.l0_read, revision=1,
            ),
        )
    elif case == "tampered_value":
        kwargs["stage_p"] = replace(
            p, committed=replace(
                p.committed, new_state=replace(current, value=3, last_update=None),
            ),
        )
    elif case == "missing_provenance":
        kwargs["stage_p"] = replace(
            p, committed=replace(
                p.committed, new_state=replace(current, last_update=None),
            ),
        )
    elif case == "foreign_intent":
        foreign = IntentCommitment()
        foreign.commit(
            "foreign", objective="not escape", at_ns=1,
            provenance=Provenance("stage-q-synthetic", "foreign"),
        )
        kwargs["intent"] = foreign
    elif case == "missing_intent":
        kwargs["intent"] = IntentCommitment()
    elif case == "next_wait":
        n = kwargs["native"]
        entity = n.observation.snapshot.nearby_entities[0]
        origin = n.observation.snapshot.position
        far_position = replace(
            entity.position, x=origin.x + 10.0, y=origin.y, z=origin.z,
        )
        snapshot = replace(
            n.observation.snapshot,
            nearby_entities=(
                replace(entity, distance=10.0, position=far_position),
            ),
        )
        changed_probe = replace(n.observation, snapshot=snapshot)
        kwargs["stage_p"] = replace(
            p, following_native_observation=changed_probe,
        )
        kwargs["native"] = _native_threat(
            changed_probe, changed_probe.request_id,
            expected_entity_id=entity.entity_id,
        )
    with pytest.raises((StageQDevBoundaryRejected, WorldChoiceRejected, ValueError)):
        stage_q_dev_joint_choice_admission(**kwargs)


@pytest.mark.parametrize("case", (
    "missing_commit", "old_retained", "foreign_previous_owner",
    "copied_successor", "misbound_feedback", "wrong_action_target",
))
def test_q_opt_in_choice_fails_closed_without_exact_qualified_s10_lineage(case):
    _, kwargs = _stage_q()
    p = kwargs["stage_p"]
    native = kwargs["native"]
    old = p.committed.previous_state
    current = p.committed.new_state
    commit = p.committed
    if case == "missing_commit":
        commit = None
    elif case == "old_retained":
        current = old
    elif case == "foreign_previous_owner":
        old = replace(old)
    elif case == "copied_successor":
        current = replace(current)
    elif case == "misbound_feedback":
        commit = replace(
            commit, proposal=replace(
                commit.proposal,
                expected_revision=0,
            ),
        )
    elif case == "wrong_action_target":
        commit = replace(
            commit, proposal=replace(
                commit.proposal, feedback=replace(
                    commit.proposal.feedback,
                    feedback_id="sham-feedback",
                ),
            ),
        )
    with pytest.raises(WorldChoiceRejected):
        select_stage_q_dev_committed_world_choice(
            native, current, commit=commit, original_owner=old,
            expected_session_id=native.observation.session_id,
            expected_entity_id=native.entity_id,
        )
