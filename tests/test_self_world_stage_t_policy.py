"""Stage T: synthetic non-HOLD OFFLINE L0/S14 joint admission, no physical World."""
from __future__ import annotations

from dataclasses import replace

import pytest

import test_postmain_s42_world_contrast as s42
import test_self_world_stage_s_feedback as stage_s
from adapters.mineflayer.normal_action import NormalActionRejected, NormalWorldL0
from adapters.mineflayer.self_world_stage_s_feedback import (
    StageSPredeclaredSeparationRule,
    assess_stage_s_original_separation,
)
from adapters.mineflayer.self_world_stage_t_policy import (
    StageTDevJointRejected,
    preview_stage_t_joint_original_owner,
)
from relay_self.intent import IntentCommitment
from relay_self.learning import (
    LearningUpdateAuthority,
    LearningUpdateRule,
    commit_learning_update,
    propose_learning_update,
)
from relay_self.provenance import Provenance
from relay_self.reactive_l0 import L0ActionGrant, ReactiveL0Rejected
from relay_self.world_conditioned_choice import (
    WorldChoiceKind,
    WorldChoiceRejected,
)


def _fixture(*, increase: bool):
    original, _, _, event, _ = s42._pair()
    witness = stage_s._synthetic_targeted_witness(
        0.0 if increase else 0.5,
        1.0 if increase else 0.0,
    )
    sid = witness.original_probe.session_id
    eid = witness.original_probe.snapshot.nearby_entities[0].entity_id
    before = replace(
        event, session_id=sid, seq=8,
        snapshot=witness.original_probe.snapshot,
    )
    probe = replace(witness.original_probe, seq=9)
    host = NormalWorldL0(
        sid, "escape-threat", original, max_events=3, max_action_requests=2,
    )
    token = object()
    host.bind_stage_t_dev_preview(token=token)
    grant = L0ActionGrant(
        authority_id="synthetic-action-predecessor-not-physical",
        action_id=witness.terminal.action_id, intent_id="escape-threat",
        session_id=sid, event_seq=before.seq, probe_seq=probe.seq,
        entity_id=eid, granted=True,
        provenance=Provenance("stage-t-synthetic", "independent-action-grant"),
    )
    step = host.decide(before, probe, grant=grant)
    assert step.choice.selection is WorldChoiceKind.MOVE_AWAY
    assert step.action_request_id == witness.terminal.action_id
    assessment = assess_stage_s_original_separation(
        witness, StageSPredeclaredSeparationRule(),
    )
    assert assessment.typed_s17 is not None
    assert assessment.typed_s17.feedback is not None
    proposal = propose_learning_update(
        original, assessment.typed_s17.feedback,
        LearningUpdateRule("stage-t-dev-risk-weight-one-step", 1, 1),
    )
    synthetic_grant = LearningUpdateAuthority(
        f"stage-t-synthetic-only-{'increase' if increase else 'decrease'}",
        "risk_weight",
        Provenance("stage-t-synthetic", "not-an-external-s10-issuer"),
    )
    commit = commit_learning_update(
        original, proposal, synthetic_grant,
        provenance=Provenance("stage-t-synthetic", "not-physical-S10"),
    )
    intent = IntentCommitment()
    intent.commit(
        "escape-threat", objective="synthetic original S49 threat",
        at_ns=1, provenance=Provenance("stage-t-synthetic", "intent-only"),
    )
    second_entity = replace(
        witness.original_probe.snapshot.nearby_entities[0],
        entity_id=eid + 10,
    )
    after_snapshot = replace(
        witness.original_probe.snapshot,
        nearby_entities=(second_entity,),
    )
    frame = replace(before, seq=30, snapshot=after_snapshot)
    next_probe = replace(
        probe, seq=31, request_id=f"s49-actual:{sid}:event-30",
        snapshot=after_snapshot,
    )
    kwargs = {"host": host, "event": frame, "probe": next_probe, "intent": intent}
    return host, token, assessment, commit, kwargs


@pytest.mark.parametrize(("increase","target","candidate","changed"), (
    (False, 3, "WAIT", True),
    (True, 5, "MOVE_AWAY", False),
))
def test_t_exact_original_l0_and_original_s14_joint_directional_preview(
    increase, target, candidate, changed,
):
    host, token, assessment, commit, kwargs = _fixture(increase=increase)
    assert host.retained.revision == 1 and host.action_requests == 1
    assert host._stage_t_dev_commit is None
    host.install_stage_t_dev_preview(
        token=token, commit=commit, typed_s17=assessment.typed_s17,
    )
    assert host.retained is commit.new_state
    result = preview_stage_t_joint_original_owner(**kwargs)
    assert result.original_revision == 1
    assert result.committed_revision == 2
    assert result.retained_value == target
    assert result.original_l0_candidate == "MOVE_AWAY"
    assert result.new_l0_candidate == candidate
    assert result.new_s14_candidate == candidate
    assert result.s14_admission == "admitted"
    assert result.l0_and_s14_same_owner_identity
    assert result.policy_choice_changed is changed
    assert not result.actual_action_issued and not result.new_action_request_created
    assert not result.physical_world_ran
    assert not result.issuer_independently_attested
    assert not result.scientific_on_off_sham_confirmed
    assert host.action_requests == 1 and host.events == 1
    if not increase:
        # Changed WAIT is a *real* alternate original L0 selection but
        # creates no new Action grant or issue (synthetic World only).
        step = host.decide(kwargs["event"], kwargs["probe"])
        assert step.choice.selection is WorldChoiceKind.WAIT
        assert not step.asks_for_action and step.grant is None
        assert host.action_requests == 1
    else:
        with pytest.raises(ReactiveL0Rejected):
            host.decide(kwargs["event"], kwargs["probe"])
        assert host.action_requests == 1


@pytest.mark.parametrize("case", (
    "no_predecessor", "wrong_token", "copied_original", "copied_new",
    "fake_criterion", "feedback_swapped", "wrong_rule", "bound_wrong",
    "no_signed_action", "double_install", "stage_r_cross_bind",
))
def test_t_policy_rejects_unauthorized_sham_or_wrong_owner(case):
    host, token, assessment, commit, kwargs = _fixture(increase=False)
    typed = assessment.typed_s17
    assert typed is not None and typed.feedback is not None
    if case == "no_predecessor":
        host._used_action_ids.clear()
    elif case == "wrong_token":
        token = object()
    elif case == "copied_original":
        commit = replace(commit, previous_state=replace(commit.previous_state))
    elif case == "copied_new":
        commit = replace(commit, new_state=replace(commit.new_state))
    elif case == "fake_criterion":
        typed = replace(
            typed, criterion_provenance=Provenance("sham", "prediction-match"),
        )
    elif case == "feedback_swapped":
        typed = replace(
            typed, feedback=replace(typed.feedback, feedback_id="sham-feedback"),
        )
    elif case == "wrong_rule":
        commit = replace(
            commit, proposal=replace(
                commit.proposal,
                rule=LearningUpdateRule("unregistered-learning-rule", 1, 1),
            ),
        )
    elif case == "bound_wrong":
        commit = replace(
            commit, proposal=replace(commit.proposal, expected_value=5),
        )
    elif case == "no_signed_action":
        typed = replace(typed, action_id="s49-native-move-17")
    elif case == "stage_r_cross_bind":
        host._stage_r_dev_token = object()
    try:
        with pytest.raises((NormalActionRejected, WorldChoiceRejected)):
            if case != "double_install":
                host.install_stage_t_dev_preview(
                    token=token, commit=commit, typed_s17=typed,
                )
            else:
                host.install_stage_t_dev_preview(
                    token=token, commit=commit, typed_s17=typed,
                )
                host.install_stage_t_dev_preview(
                    token=token, commit=commit, typed_s17=typed,
                )
    finally:
        if case != "double_install":
            assert host.retained.revision == 1
            assert host._stage_t_dev_commit is None


@pytest.mark.parametrize("case", (
    "stale_native", "foreign_session", "split_l0_owner",
    "expired_intent", "wrong_source_kind", "changed_entity_id",
))
def test_t_post_install_joint_native_and_s14_cannot_accept_confound(case):
    host, token, assessment, commit, kwargs = _fixture(increase=False)
    host.install_stage_t_dev_preview(
        token=token, commit=commit, typed_s17=assessment.typed_s17,
    )
    if case == "stale_native":
        kwargs["probe"] = replace(kwargs["probe"], seq=kwargs["event"].seq)
    elif case == "foreign_session":
        kwargs["probe"] = replace(kwargs["probe"], session_id="foreign")
    elif case == "split_l0_owner":
        host.retained = replace(host.retained)
    elif case == "expired_intent":
        kwargs["intent"].complete(
            "escape-threat", reason="done", at_ns=2,
            provenance=Provenance("stage-t-synthetic", "completed"),
        )
    elif case == "wrong_source_kind":
        kwargs["probe"] = replace(kwargs["probe"], kind="entities", request_id=None)
    else:
        e=kwargs["probe"].snapshot.nearby_entities[0]
        kwargs["probe"] = replace(
            kwargs["probe"], snapshot=replace(
                kwargs["probe"].snapshot, nearby_entities=(
                    replace(e, entity_id=e.entity_id+100),
                ),
            ),
        )
    with pytest.raises((StageTDevJointRejected, WorldChoiceRejected, ValueError)):
        preview_stage_t_joint_original_owner(**kwargs)


def test_t_off_baseline_does_not_adopt_synthetic_commit_without_opt_in():
    state, near, _, event, _ = s42._pair()
    host = NormalWorldL0(near.observation.session_id, "escape-threat", state)
    assert host.retained is state
    with pytest.raises(NormalActionRejected):
        host.install_stage_t_dev_preview(
            token=object(), commit=None, typed_s17=None,
        )
    assert host._stage_t_dev_commit is None
    assert host._stage_r_dev_token is None
    assert host.events == 0 and host.action_requests == 0
