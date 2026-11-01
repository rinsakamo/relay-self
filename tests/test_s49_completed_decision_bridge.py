"""S49 post-owner completion bridge with original NormalWorldL0 typed steps.

Positive test uses original S42 near/far synthetic probes, original L0
decide() and a SYNTHETIC typed S16-shaped receipt. Real S49 qualification
and physical source are NOT claimed by this offline fixture.
"""
from __future__ import annotations

import inspect
from dataclasses import replace

import pytest

import test_postmain_s42_world_contrast as s42
from adapters.mineflayer.execution import WorldConsequence, WorldConsequenceStatus
from adapters.mineflayer.normal_action import (
    NormalActionReceipt,
    NormalWorldL0,
)
from adapters.mineflayer.python_protocol import MineflayerEffectResult
from adapters.mineflayer.s49_completed_decision_bridge import (
    S49CompletionRejected,
    bounded_original_s49_completion_row,
    read_original_s49_completions,
)
from adapters.mineflayer.s49_normal_session_real_ci import qualify
from relay_self.action import ActionEvent, ActionLifecycle, ActionState
from relay_self.provenance import Provenance
from relay_self.reactive_l0 import L0ActionGrant


def _synthetic_original_shape():
    retained, near, far, event1, event2 = s42._pair()
    probe1, probe2 = near.observation, far.observation
    l0 = NormalWorldL0(
        probe1.session_id, "escape-threat", retained,
        max_events=2, max_action_requests=1,
    )
    choice = l0._check(event1, probe1)
    grant = L0ActionGrant(
        authority_id="test-independent-grant", action_id="test-move-once",
        intent_id="escape-threat", session_id=probe1.session_id,
        event_seq=event1.seq, probe_seq=probe1.seq,
        entity_id=choice.entity_id, granted=True,
        provenance=Provenance("test", "not-physical-authorization"),
    )
    move = l0.decide(event1, probe1, grant=grant)
    wait = l0.decide(event2, probe2)
    assert move.asks_for_action and not wait.asks_for_action

    # Typed real-contract structures, with FIXTURE content. No actual S16,
    # Minecraft, action authority or independently attested World here.
    p = Provenance("test", "synthetic-action-evidence")
    terminal = ActionLifecycle(
        action_id=move.action_request_id,
        skill_execution_id="test-skill", intent_id="escape-threat",
        _events=(
            ActionEvent(ActionState.PROPOSED, 1, p),
            ActionEvent(ActionState.AUTHORIZED, 2, p, authority="test-owner"),
            ActionEvent(ActionState.ISSUED, 3, p, deadline_ns=10),
            ActionEvent(ActionState.OUTCOME, 4, p),
        ),
        _revision=3,
    )
    dispatch = MineflayerEffectResult(
        session_id=probe1.session_id, seq=probe1.seq + 1,
        provenance=probe1.provenance, action_id=move.action_request_id,
        effect="set_control", result="applied", error=None,
    )
    cleanup = MineflayerEffectResult(
        session_id=probe1.session_id, seq=probe1.seq + 2,
        provenance=probe1.provenance, action_id=move.action_request_id,
        effect="clear_controls", result="applied", error=None,
    )
    physical = WorldConsequence(
        action_id=move.action_request_id, binding_id="synthetic-binding",
        action_ref="MOVE_BACKWARD", status=WorldConsequenceStatus.EXECUTED,
        session_id=probe1.session_id, before_observation=probe1,
        dispatch_receipt=dispatch, cleanup_receipt=cleanup,
        after_observation=replace(probe1, seq=probe1.seq + 3),
        movement_distance=0.31, cleanup_attempted=True,
        error=None, provenance=p,
    )
    receipt = NormalActionReceipt(terminal, physical, probe1.provenance)
    return (move, wait), {
        probe1.seq: probe1, probe2.seq: probe2,
    }, {move.action_request_id: receipt}


def test_original_move_wait_steps_and_terminal_owner_objects_are_preserved():
    steps, probes, receipts = _synthetic_original_shape()
    before = tuple((id(s), id(probes[s.choice.probe_seq])) for s in steps)
    batch = read_original_s49_completions(steps, probes, receipts)
    assert batch.session_id == steps[0].choice.session_id
    assert tuple(s.step for s in batch.steps) == steps
    assert batch.steps[0].step is steps[0]
    assert batch.steps[0].probe is probes[steps[0].choice.probe_seq]
    assert batch.steps[0].action_receipt is next(iter(receipts.values()))
    assert batch.steps[1].action_receipt is None
    assert tuple((id(s), id(probes[s.choice.probe_seq])) for s in steps) == before
    row = bounded_original_s49_completion_row(batch)
    assert row["step_count"] == 2
    assert row["outcome_count"] == row["wait_count"] == 1
    assert row["decisions"][0]["s16_terminal"] == "outcome"
    assert row["decisions"][1]["s16_terminal"] is None
    assert row["new_native_reads"] == row["new_model_calls"] == 0
    assert row["new_action_issues"] == 0
    assert not row["source_attested"]
    assert not row["real_s42_epoch_supplied"]
    assert not row["real_b0_decision_supplied"]
    assert not row["real_l8_epoch_supplied"]
    assert "health" not in repr(row) and "food" not in repr(row)


@pytest.mark.parametrize("attack", [
    "missing_receipt", "wrong_receipt_action", "wrong_probe", "replayed_step",
    "missing_probe", "extra_receipt", "unknown_terminal", "foreign_session",
    "stale_choice", "missing_source", "wrong_consequence_session",
])
def test_fail_closed_on_foreign_or_replayed_source_or_terminal(attack):
    steps, probes, receipts = _synthetic_original_shape()
    steps = tuple(steps)
    probes = dict(probes)
    receipts = dict(receipts)
    action_id = steps[0].action_request_id
    original_receipt = receipts[action_id]
    if attack == "missing_receipt":
        receipts.clear()
    elif attack == "wrong_receipt_action":
        receipts[action_id] = replace(original_receipt,
            terminal=replace(original_receipt.terminal, action_id="other-action"))
    elif attack == "wrong_probe":
        seq = steps[0].choice.probe_seq
        probes[seq] = replace(probes[seq], request_id="wrong-probe-request")
    elif attack == "replayed_step":
        steps = (steps[0], steps[0])
    elif attack == "missing_probe":
        probes.pop(steps[1].choice.probe_seq)
    elif attack == "extra_receipt":
        receipts["other-action"] = original_receipt
    elif attack == "unknown_terminal":
        receipts[action_id] = replace(original_receipt,
            terminal=replace(original_receipt.terminal,
                _events=original_receipt.terminal.events[:-1] + (
                    ActionEvent(ActionState.UNKNOWN, 4,
                                Provenance("test", "unknown-terminal")),)))
    elif attack == "foreign_session":
        seq = steps[1].choice.probe_seq
        probes[seq] = replace(probes[seq], session_id="foreign")
    elif attack == "stale_choice":
        steps = (steps[1], steps[0])
    elif attack == "missing_source":
        probes.clear()
    elif attack == "wrong_consequence_session":
        receipts[action_id] = replace(original_receipt, consequence=replace(
            original_receipt.consequence, session_id="foreign"))
    with pytest.raises(S49CompletionRejected):
        read_original_s49_completions(steps, probes, receipts)


def test_optional_callback_signature_is_on_original_s49_qualify():
    signature = inspect.signature(qualify)
    assert "completed_l0" in signature.parameters
    assert signature.parameters["completed_l0"].default is None


def test_null_owner_path_is_not_misrepresented_as_completed_s42():
    steps, probes, receipts = _synthetic_original_shape()
    batch = read_original_s49_completions(steps, probes, receipts)
    row = bounded_original_s49_completion_row(batch)
    assert row["real_s42_epoch_supplied"] is False
    assert row["real_b0_decision_supplied"] is False
    assert row["real_l8_epoch_supplied"] is False
    assert "CognitiveWorkReceipt" not in repr(row)
    assert "L2" not in repr(row)
