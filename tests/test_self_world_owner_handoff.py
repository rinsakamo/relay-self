"""Stage O original live L0 retained identity, no S10 authority: offline tests.

The source/probe/action fixtures here are synthetic, not physical S49 proof.
"""
from __future__ import annotations

from dataclasses import replace

import pytest

import test_action_feedback_qualification as s17
from adapters.mineflayer.normal_action import (
    NormalActionRejected,
    NormalWorldL0,
    observe_original_retained_owner,
)
from adapters.mineflayer.self_world_owner_handoff import StageOOwnerReadback
from relay_self.epoch_continuation import (
    StaleRetainedSnapshot,
    read_retained_preference,
)
from relay_self.learning import (
    FeedbackDirection,
    LearningFeedback,
    MissingLearningAuthority,
    commit_learning_update,
    propose_learning_update,
)
from relay_self.provenance import Provenance


def _same_native_probe(session_id, seq, event):
    return replace(
        s17.observation(seq, 0, 0),
        session_id=session_id,
        request_id=f"s49-actual:{session_id}:event-{event}",
    )


def test_stage_o_original_l0_owner_reference_is_identical_across_three_sources():
    state = s17.learning_state()
    holder = StageOOwnerReadback()
    with observe_original_retained_owner(holder.receive_original_owner):
        host = NormalWorldL0("actual-session", "escape-threat", state)
        assert host.retained is state
    for seq, event in ((9, 8), (21, 20), (48, 47)):
        holder.observe_existing_probe(_same_native_probe("actual-session", seq, event))
    summary = holder.summary()
    assert summary["captured_original_l0_retained_identity"] is True
    assert summary["source_read_count"] == 3
    assert summary["original_owner_target"] == "risk_weight"
    assert summary["original_owner_revision"] == 0
    assert summary["original_owner_value"] == 3
    assert all(x["exact_original_owner_identity"] for x in summary["same_owner_source_reads"])
    assert summary["s10_update_authority"] is False
    assert summary["s10_commits"] == 0
    assert summary["s49_l0_retained_mutated"] is False
    assert summary["additional_native_actions"] == 0
    assert host.retained is state
    assert host.events == 0 and host.action_requests == 0


def test_stage_o_tap_optin_and_failure_cannot_veto_original_l0():
    original = s17.learning_state()
    calls = []
    holder = StageOOwnerReadback()
    with observe_original_retained_owner(lambda reading: calls.append(reading)):
        host = NormalWorldL0("s49", "escape-threat", original)
    assert host.retained is original
    assert len(calls) == 1
    assert calls[0].owner_snapshot is original
    # Outside the scope, there is no observer or hidden owner-sharing channel.
    second = NormalWorldL0("s49", "escape-threat", original)
    assert second.retained is original
    assert len(calls) == 1
    with observe_original_retained_owner(
        lambda reading: (_ for _ in ()).throw(ValueError("observer failure")),
    ):
        third = NormalWorldL0("s49", "escape-threat", original)
    assert third.retained is original
    assert third.events == 0
    with pytest.raises(NormalActionRejected):
        with observe_original_retained_owner(None):
            pytest.fail("unreachable")
    # A foreign caller cannot pass any arbitrary object as genuine readback.
    with pytest.raises(TypeError):
        holder.receive_original_owner({"session_id": "fake"})


@pytest.mark.parametrize("mode", (
    "duplicate_owner", "foreign_intent", "wrong_target",
    "foreign_session", "replay_seq", "invented_request",
))
def test_stage_o_fails_closed_foreign_owner_or_native_source(mode):
    state = s17.learning_state()
    holder = StageOOwnerReadback()
    with observe_original_retained_owner(holder.receive_original_owner):
        NormalWorldL0("same-session", "escape-threat", state)
        if mode == "duplicate_owner":
            # The second controller cannot silently share another owner grant.
            NormalWorldL0("same-session", "escape-threat", state)
    if mode == "duplicate_owner":
        # Original L0 remains free; passive tap fails closed on second capture.
        assert holder.summary()["source_read_count"] == 0
        return
    if mode == "foreign_intent":
        with pytest.raises(TypeError):
            holder.receive_original_owner(object())
        return
    if mode == "wrong_target":
        with pytest.raises(TypeError):
            holder.observe_existing_probe(123)
        return
    native = _same_native_probe("same-session", 9, 8)
    if mode == "foreign_session":
        native = replace(native, session_id="other")
    elif mode == "replay_seq":
        holder.observe_existing_probe(native)
    else:
        native = replace(native, request_id="uncorrelated-or-forged")
    with pytest.raises((TypeError, ValueError)):
        holder.observe_existing_probe(native)


def test_stage_o_equal_looking_owner_copy_and_missing_grant_are_not_authority():
    owner = s17.learning_state()
    holder = StageOOwnerReadback()
    with observe_original_retained_owner(holder.receive_original_owner):
        host = NormalWorldL0("session", "escape-threat", owner)
    same_values_different_object = replace(owner)
    assert same_values_different_object is not owner
    with pytest.raises(StaleRetainedSnapshot):
        read_retained_preference(
            owner, same_values_different_object,
            required_target_id="risk_weight",
            expected_revision=0, provenance=Provenance("stage-o-test", "counterfeit"),
        )

    feedback = LearningFeedback(
        feedback_id="stage-o-dev-feedback-not-a-grant",
        target_id="risk_weight", direction=FeedbackDirection.HOLD,
        provenance=Provenance("stage-o-dev-test", "feedback"),
    )
    proposal = propose_learning_update(owner, feedback, s17.learning_rule())
    with pytest.raises(MissingLearningAuthority):
        commit_learning_update(
            owner, proposal, None,
            provenance=Provenance("stage-o-dev-test", "forbidden-commit"),
        )
    assert host.retained is owner
    assert host.retained.revision == 0
    assert holder.summary()["s10_commits"] == 0


def test_stage_o_typed_s17_hold_prepares_only_then_s10_synthetic_authority():
    """Offline fixture: proposal != commit != original L0 owner transfer."""
    import test_self_world_native_feedback as n_fixture
    from adapters.mineflayer.self_world_native_feedback import (
        StageNDeclaredPolicy,
        StageNNativeClosureObserver,
    )
    from relay_self.learning import (
        LearningUpdateAuthority,
        ReplayLearningFeedback,
    )

    witness = n_fixture._synthetic_native_closed()
    sid = witness.original_probe.session_id
    state = s17.learning_state()
    holder = StageOOwnerReadback()
    with observe_original_retained_owner(holder.receive_original_owner):
        host = NormalWorldL0(sid, "escape-threat", state)

    n = StageNNativeClosureObserver(StageNDeclaredPolicy())
    n.observe_existing_probe(witness.original_probe)
    holder.observe_existing_probe(witness.original_probe)
    typed = n.observe_closed(witness)
    assert typed.feedback is not None
    rule = s17.learning_rule()
    proposal = holder.prepare_original_hold(typed, rule)
    assert proposal.expected_revision == state.revision == 0
    assert proposal.proposed_value == state.value == 3
    assert holder.summary()["typed_hold_proposal_count"] == 1
    assert holder.summary()["proposals_are_commits"] is False

    # Neither the typed S17 result nor a proposal owns S10 authorization.
    with pytest.raises(MissingLearningAuthority):
        commit_learning_update(
            state, proposal, None,
            provenance=Provenance("stage-o-offline", "missing-permission"),
        )
    # Only in this SYNTHETIC negative/positive comparison does the test
    # supply an explicitly synthetic, independently predeclared S10 grant.
    granted = LearningUpdateAuthority(
        "synthetic-test-authority-not-world", "risk_weight",
        Provenance("stage-o-offline", "synthetic-authority"),
    )
    accepted = commit_learning_update(
        state, proposal, granted,
        provenance=Provenance("stage-o-offline", "synthetic-commit"),
    )
    assert accepted.new_state is not state
    assert accepted.new_state.revision == 1
    assert accepted.new_state.value == state.value  # HOLD is not improvement
    # No owner transfer: original physical L0 continues using rev0.
    assert host.retained is state
    assert host.retained.revision == 0
    with pytest.raises(StaleRetainedSnapshot):
        read_retained_preference(
            accepted.new_state, host.retained, required_target_id="risk_weight",
            expected_revision=1,
            provenance=Provenance("stage-o-offline", "stale-l0-input"),
        )
    with pytest.raises(ReplayLearningFeedback):
        propose_learning_update(accepted.new_state, typed.feedback, rule)
    with pytest.raises(ValueError, match="replayed"):
        holder.prepare_original_hold(typed, rule)
    assert holder.summary()["s10_commits"] == 0
    assert holder.summary()["additional_native_actions"] == 0


@pytest.mark.parametrize("kind", (
    "no_original_owner", "no_native_probe", "sham_feedback",
    "wrong_action", "foreign_s17_source", "foreign_outcome_ref",
    "scalar_reward_attempt",
))
def test_stage_o_hold_preview_negative_controls(kind):
    """No forged source, replay, sham or arbitrary scalar learning policy."""
    import test_self_world_native_feedback as n_fixture
    from adapters.mineflayer.self_world_native_feedback import (
        StageNDeclaredPolicy,
        StageNNativeClosureObserver,
    )
    from relay_self.action_feedback import LearningFeedbackInterpretationStatus
    from relay_self.learning import LearningUpdateRule

    witness = n_fixture._synthetic_native_closed()
    sid = witness.original_probe.session_id
    holder = StageOOwnerReadback()
    if kind != "no_original_owner":
        with observe_original_retained_owner(holder.receive_original_owner):
            NormalWorldL0(sid, "escape-threat", s17.learning_state())
    if kind != "no_native_probe":
        holder.observe_existing_probe(witness.original_probe) if (
            kind != "no_original_owner"
        ) else None
    n = StageNNativeClosureObserver(StageNDeclaredPolicy())
    n.observe_existing_probe(witness.original_probe)
    typed = n.observe_closed(witness)
    if kind == "sham_feedback":
        typed = replace(
            typed, status=LearningFeedbackInterpretationStatus.NOT_APPLICABLE,
            feedback=None,
        )
    elif kind == "wrong_action":
        typed = replace(typed, action_id="s49-native-move-999")
    elif kind == "foreign_s17_source":
        typed = replace(
            typed, provenance=Provenance(
                "stage-n-native-typed-closure", f"foreign:{typed.action_id}",
            ),
        )
    elif kind == "foreign_outcome_ref":
        # Maintain S17 type invariants so the Stage O source gate, not
        # the S17 dataclass constructor, rejects the forged outcome.
        typed = replace(
            typed, outcome_ref="action-outcome:counterfeit",
            feedback=replace(
                typed.feedback, consequence_ref="action-outcome:counterfeit",
            ),
        )
    elif kind == "scalar_reward_attempt":
        typed = replace(
            typed, feedback=replace(
                typed.feedback, direction=s17.FeedbackDirection.INCREASE,
            ),
        )
    with pytest.raises((TypeError, ValueError)):
        holder.prepare_original_hold(typed, LearningUpdateRule("hold-rule", 1, 1))
    assert holder.summary()["typed_hold_proposal_count"] == 0
    assert holder.summary()["s10_commits"] == 0
