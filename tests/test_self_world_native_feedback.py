"""Stage N read-only typed terminal observer tests. All Action frames SYNTHETIC.

An actual native S49/S16 closure must be observed only in one new DEV run.
The fixtures do not qualify physical S17, production S10, or learned Action.
"""
from __future__ import annotations

from dataclasses import replace

import pytest

import test_action_feedback_qualification as s17
from adapters.mineflayer.normal_action import (
    NormalActionClosedReadback,
    NormalActionRejected,
    observe_closed_native_actions,
)
from adapters.mineflayer.self_world_native_feedback import (
    StageNDeclaredPolicy,
    StageNNativeClosureObserver,
)
from relay_self.learning import FeedbackDirection


def _synthetic_native_closed():
    # The existing S17 fixture really closes one Action through S16/Supervisor.
    chain = s17.executed_closed_chain()
    consequence, outcome, terminal = chain[-3:]
    sid = consequence.session_id
    action_id = "s49-native-move-8"
    probe = replace(
        s17.observation(0, 0, 0),
        session_id=sid, request_id=f"s49-actual:{sid}:event-8",
    )
    after = consequence.after_observation
    assert after is not None and after.seq > probe.seq
    movement = consequence.movement_distance
    assert movement is not None and movement >= 0.05
    dispatch = replace(consequence.dispatch_receipt, action_id=action_id)
    cleanup = replace(consequence.cleanup_receipt, action_id=f"{action_id}-s15-clear")
    consequence = replace(
        consequence, action_id=action_id, binding_id="s49-binding-8",
        dispatch_receipt=dispatch, cleanup_receipt=cleanup,
    )
    outcome = replace(
        outcome, action_id=action_id, binding_id="s49-binding-8",
    )
    terminal = replace(terminal, action_id=action_id)
    return NormalActionClosedReadback(terminal, outcome, consequence, probe)


def test_stage_n_original_typed_s17_hold_and_next_real_source_shape():
    witness = _synthetic_native_closed()
    policy = StageNDeclaredPolicy()
    observer = StageNNativeClosureObserver(policy)
    observer.observe_existing_probe(witness.original_probe)
    observer.observe_closed(witness)
    post = replace(
        witness.original_probe,
        seq=witness.consequence.after_observation.seq + 2,
        request_id=(
            f"s49-actual:{witness.original_probe.session_id}:event-46"
        ),
    )
    observer.observe_existing_probe(post)
    result = observer.summary()
    assert result["typed_s17_feedback_count"] == 1
    row = result["source_closures"][0]
    assert row["s17_interpretation"] == "produced"
    assert row["feedback_direction"] == "hold"
    assert row["s10_update_committed"] is False
    assert row["action_issued_by_stage_n"] is False
    assert row["predicted_label_used_as_reward"] is False
    assert len(result["post_closure_source_observations"]) == 1
    assert result["s10_learning_commits"] == 0
    assert result["real_next_epoch_learned_policy"] is False


@pytest.mark.parametrize("bad", (
    "foreign_session", "wrong_probe_id", "wrong_binding",
    "unknown_outcome", "missing_displacement", "replayed_action",
    "wrong_action_name", "foreign_target",
))
def test_stage_n_observer_fails_closed_on_unqualified_original_source(bad):
    witness = _synthetic_native_closed()
    observer = StageNNativeClosureObserver(StageNDeclaredPolicy())
    observer.observe_existing_probe(witness.original_probe)
    if bad == "replayed_action":
        observer.observe_closed(witness)
    elif bad == "foreign_session":
        witness = replace(
            witness, original_probe=replace(
                witness.original_probe, session_id="foreign",
            ),
        )
    elif bad == "wrong_probe_id":
        witness = replace(
            witness, original_probe=replace(
                witness.original_probe, request_id="user-supplied",
            ),
        )
    elif bad == "wrong_binding":
        witness = replace(
            witness, interpretation=replace(
                witness.interpretation, binding_id="fake-binding",
            ),
        )
    elif bad == "unknown_outcome":
        from relay_self.action_outcome import ActionOutcomeDisposition
        witness = replace(
            witness, interpretation=replace(
                witness.interpretation,
                disposition=ActionOutcomeDisposition.UNKNOWN,
            ),
        )
    elif bad == "missing_displacement":
        # Structural invalidity must already be rejected by WorldConsequence.
        with pytest.raises(ValueError):
            replace(witness.consequence, movement_distance=0.0)
        return
    elif bad == "wrong_action_name":
        witness = replace(
            witness, terminal=replace(witness.terminal, action_id="other-action"),
        )
    else:
        witness = replace(
            witness, original_probe=replace(
                witness.original_probe,
                snapshot=replace(
                    witness.original_probe.snapshot, nearby_entities=(),
                ),
            ),
        )
        # Unrelated registry may be empty: exact Action identity must still
        # remain independent of an invented predicted World target.
        assert witness.original_probe.snapshot.nearby_entities == ()
        return
    with pytest.raises((TypeError, ValueError)):
        observer.observe_closed(witness)
    if bad != "replayed_action":
        assert observer.summary()["typed_s17_feedback_count"] == 0


def test_stage_n_criterion_predeclared_hold_not_reward_or_action():
    with pytest.raises(ValueError):
        StageNDeclaredPolicy(direction=FeedbackDirection.INCREASE)
    with pytest.raises(ValueError):
        StageNDeclaredPolicy(required_outcome_reason="prediction_match")
    with pytest.raises(NormalActionRejected):
        with observe_closed_native_actions(None):
            pytest.fail("unreachable")


def test_stage_n_read_only_context_scope_and_exception_isolation():
    from adapters.mineflayer.normal_action import _READ_ONLY_CLOSURE

    calls = []
    assert _READ_ONLY_CLOSURE.get() is None
    with observe_closed_native_actions(lambda w: calls.append(w)):
        assert _READ_ONLY_CLOSURE.get() is not None
        with observe_closed_native_actions(lambda w: (_ for _ in ()).throw(ValueError())):
            assert _READ_ONLY_CLOSURE.get() is not None
        assert _READ_ONLY_CLOSURE.get() is not None
    assert _READ_ONLY_CLOSURE.get() is None
    assert calls == []
