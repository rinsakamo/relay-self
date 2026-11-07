"""Offline C1->S10->next-Intent source-shaped tests; never a live World claim."""
from dataclasses import replace

import pytest

from adapters.mineflayer.bug0_intent_motion_learning import (
    IntentMotionRejected,
    MotionComparison,
    close_motion_intent_experience,
    forecast_from_retained,
    learn_from_motion_experience,
)
from adapters.mineflayer.execution import WorldConsequenceStatus
from adapters.mineflayer.normal_action import NormalActionReceipt
from relay_self.epoch_continuation import StaleRetainedSnapshot
from relay_self.intent import IntentCommitment
from relay_self.learning import (
    InvalidLearningAuthority,
    LearningPreferenceState,
    LearningUpdateAuthority,
    LearningUpdateRule,
)
from relay_self.provenance import Provenance
from test_s49_completed_decision_bridge import _synthetic_original_shape


def _scenario():
    _, _, receipts = _synthetic_original_shape()
    receipt = next(iter(receipts.values()))
    native = receipt.consequence.before_observation
    p = Provenance("test", "synthetic-not-world-attested")
    intent = IntentCommitment()
    intent.commit("escape-threat", objective="move away", at_ns=1, provenance=p)
    intent.complete("escape-threat", reason="attempt assessed", at_ns=2, provenance=p)
    state = LearningPreferenceState(
        target_id="motion_decimeters", value=7, minimum=0, maximum=10,
        revision=0, origin_provenance=p,
    )
    forecast = forecast_from_retained(
        state, state, self_id="self-a", intent_id="escape-threat",
        session_id=native.session_id, native_probe_seq=native.seq,
        expected_revision=state.revision, source_provenance=native.provenance,
    )
    return intent, forecast, (receipt,), state


def _close(intent, forecast, receipts):
    return close_motion_intent_experience(
        intent, forecast, receipts, attempt_id="attempt-one", tolerance_m=0.05,
    )


def _learn(exp, state, authority=None):
    if authority is None:
        authority = LearningUpdateAuthority(
            authority_id="self-owned-s10-update", target_id=state.target_id,
            provenance=Provenance("test", "technical-owner-custody"),
        )
    return learn_from_motion_experience(
        exp, state, LearningUpdateRule("motion-rule", 1, 1), authority,
        provenance=Provenance("test", "post-experience-update"),
    )


def test_one_intent_one_motion_experience_then_next_intent_uses_revised_owner():
    intent, forecast, receipts, state = _scenario()
    assert forecast.predicted_total_m == 0.7
    exp = _close(intent, forecast, receipts)
    assert exp.measured_total_m == pytest.approx(0.31)
    assert exp.comparison is MotionComparison.SHORTER
    assert len(exp.action_receipts) == 1
    assert exp.intent_goal_verified is False

    committed = _learn(exp, state)
    assert committed.previous_state is state
    assert committed.new_state.revision == 1
    assert committed.new_state.value == 6
    assert committed.record.feedback_id == "intent-motion:" + exp.experience_id

    # Next Intent's read consumes the actual new S10 snapshot, not an LLM
    # explanation and not an updated text-only copy.
    next_observation = receipts[0].consequence.after_observation
    subsequent = forecast_from_retained(
        committed.new_state, committed.new_state,
        self_id="self-a", intent_id="next-escape-intent",
        session_id=next_observation.session_id,
        native_probe_seq=next_observation.seq,
        expected_revision=1,
        source_provenance=next_observation.provenance,
    )
    assert subsequent.predicted_total_m == 0.6
    assert subsequent.predicted_total_m != forecast.predicted_total_m

    # Old original experience cannot update again even after another revision.
    with pytest.raises(IntentMotionRejected):
        _learn(exp, committed.new_state)
    with pytest.raises(StaleRetainedSnapshot):
        forecast_from_retained(
            committed.new_state, state, self_id="self-a", intent_id="another",
            session_id=next_observation.session_id,
            native_probe_seq=next_observation.seq, expected_revision=1,
            source_provenance=next_observation.provenance,
        )


def test_two_distinct_moves_still_one_intent_experience():
    intent, forecast, receipts, _ = _scenario()
    first = receipts[0]
    old_after = first.consequence.after_observation
    before2 = replace(old_after, seq=old_after.seq + 2)
    after2 = replace(before2, seq=before2.seq + 3)
    second = NormalActionReceipt(
        terminal=replace(first.terminal, action_id="second-physical-action"),
        consequence=replace(
            first.consequence, action_id="second-physical-action",
            before_observation=before2, after_observation=after2,
            movement_distance=0.24,
        ),
        source=before2.provenance,
    )
    exp = _close(intent, forecast, (first, second))
    assert exp.experience_id.endswith("attempt-one")
    assert len(exp.action_receipts) == 2
    assert exp.measured_total_m == pytest.approx(0.55)
    assert exp.comparison is MotionComparison.SHORTER


@pytest.mark.parametrize("mutation", [
    "duplicate_action", "foreign_session", "foreign_intent",
    "post_action_forecast", "wrong_native_source", "stale_after",
])
def test_source_or_action_mismatch_fails_closed(mutation):
    intent, forecast, receipts, _ = _scenario()
    receipt = receipts[0]
    if mutation == "duplicate_action":
        receipts = (receipt, receipt)
    if mutation == "foreign_session":
        receipts = (replace(
            receipt, consequence=replace(receipt.consequence, session_id="foreign-session"),
        ),)
    if mutation == "foreign_intent":
        receipts = (replace(
            receipt, terminal=replace(receipt.terminal, intent_id="foreign-intent"),
        ),)
    if mutation == "post_action_forecast":
        forecast = replace(
            forecast,
            source_probe_seq=receipt.consequence.after_observation.seq,
        )
    if mutation == "wrong_native_source":
        forecast = replace(
            forecast, source_provenance=Provenance("test", "foreign-source"),
        )
    if mutation == "stale_after":
        receipts = (replace(
            receipt, consequence=replace(
                receipt.consequence,
                after_observation=receipt.consequence.before_observation,
            ),
        ),)
    with pytest.raises(IntentMotionRejected):
        _close(intent, forecast, receipts)


def test_no_experience_from_unexecuted_intent_or_no_physical_action():
    intent, forecast, receipts, _ = _scenario()
    with pytest.raises(IntentMotionRejected):
        _close(intent, forecast, ())
    unclosed = IntentCommitment()
    unclosed.commit(
        "escape-threat", objective="deferred", at_ns=1,
        provenance=Provenance("test", "deferred"),
    )
    with pytest.raises(IntentMotionRejected):
        _close(unclosed, forecast, receipts)


def test_undetermined_action_means_no_learning_and_no_invented_success():
    intent, forecast, receipts, state = _scenario()
    uncertain = replace(
        receipts[0], consequence=replace(
            receipts[0].consequence,
            status=WorldConsequenceStatus.UNDETERMINED,
        ),
    )
    exp = _close(intent, forecast, (uncertain,))
    assert exp.comparison is MotionComparison.UNKNOWN
    assert exp.measured_total_m is None
    with pytest.raises(IntentMotionRejected):
        _learn(exp, state)


def test_denied_learning_owner_authority_does_not_update():
    intent, forecast, receipts, state = _scenario()
    exp = _close(intent, forecast, receipts)
    denied = LearningUpdateAuthority(
        authority_id="denied", target_id=state.target_id,
        provenance=Provenance("test", "denied"), granted=False,
    )
    with pytest.raises(InvalidLearningAuthority):
        _learn(exp, state, authority=denied)
    assert state.revision == 0 and state.value == 7


def test_wrong_target_and_revision_do_not_cross_self_or_owner():
    intent, forecast, receipts, state = _scenario()
    exp = _close(intent, forecast, receipts)
    other = replace(state, target_id="different-target")
    with pytest.raises(IntentMotionRejected):
        _learn(exp, other)
    with pytest.raises(IntentMotionRejected):
        _learn(exp, replace(state, revision=2))


def test_same_intent_owner_accepts_latest_attempt_and_rejects_old_replay():
    intent, first, receipts, _ = _scenario()
    intent.commit("next-escape-intent", objective="move again", at_ns=3,
                  provenance=Provenance("test", "next"))
    intent.complete("next-escape-intent", reason="attempt assessed", at_ns=4,
                    provenance=Provenance("test", "next"))
    with pytest.raises(IntentMotionRejected):
        _close(intent, first, receipts)
    second = replace(first, intent_id="next-escape-intent")
    second_receipt = replace(receipts[0], terminal=replace(
        receipts[0].terminal, intent_id="next-escape-intent"))
    assert _close(intent, second, (second_receipt,)).terminal_kind.value == "completed"
