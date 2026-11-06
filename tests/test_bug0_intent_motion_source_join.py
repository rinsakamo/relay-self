"""Real S49 *source shape* for C1: selection probe != S15 internal before.

All records are synthetic typed fixture substitutions. No genuine World, no
original S49 owner live callback, and no learning claim from physical reality.
"""
from dataclasses import replace

import pytest

from adapters.mineflayer.bug0_intent_motion_learning import (
    IntentMotionRejected,
    MotionComparison,
    close_motion_intent_experience,
    learn_from_motion_experience,
)
from adapters.mineflayer.execution import WorldConsequenceStatus
from adapters.mineflayer.normal_action import NormalActionReceipt
from relay_self.learning import (
    LearningUpdateAuthority,
    LearningUpdateRule,
)
from relay_self.provenance import Provenance
from test_bug0_intent_motion_learning import _scenario


def _s49_two_probe_shape():
    intent, forecast, (receipt,), state = _scenario()
    selected = receipt.consequence.before_observation
    # The original S49 runner owns a correlated choice probe.
    # S15's execute_mineflayer_command subsequently calls send_observe()
    # again; its resulting before/after packets are distinct observations
    # with their own native sequence and source references.
    internal = replace(
        selected, seq=selected.seq + 2, request_id=None,
    )
    dispatch = replace(receipt.consequence.dispatch_receipt, seq=selected.seq + 3)
    clear = replace(receipt.consequence.cleanup_receipt, seq=selected.seq + 4)
    after = replace(
        receipt.consequence.after_observation, seq=selected.seq + 5,
        request_id=None,
    )
    source_shaped = NormalActionReceipt(
        receipt.terminal,
        replace(
            receipt.consequence, before_observation=internal,
            dispatch_receipt=dispatch, cleanup_receipt=clear,
            after_observation=after,
        ),
        selected.provenance,  # the actual executor stores the *choice* source
    )
    return intent, forecast, (source_shaped,), (selected,), state


def _close(intent, forecast, receipts, decisions):
    return close_motion_intent_experience(
        intent, forecast, receipts, attempt_id="source-join", tolerance_m=0.05,
        decision_probes=decisions,
    )


def test_s49_distinct_selection_and_s15_internal_before_join_and_s10_reuse():
    intent, forecast, receipts, decisions, state = _s49_two_probe_shape()
    assert decisions[0].seq < receipts[0].consequence.before_observation.seq
    assert decisions[0].provenance != receipts[0].consequence.before_observation.provenance
    experience = _close(intent, forecast, receipts, decisions)
    assert experience.decision_probes[0] is decisions[0]
    assert experience.comparison is MotionComparison.SHORTER
    assert experience.measured_total_m == pytest.approx(0.31)
    assert not experience.intent_goal_verified
    committed = learn_from_motion_experience(
        experience, state,
        LearningUpdateRule("motion-source-join-rule", 1, 1),
        LearningUpdateAuthority(
            "owner-revision-bound", "motion_decimeters",
            Provenance("test", "dev-technical-owner-grant"),
        ),
        provenance=Provenance("test", "update-after-synthetic-closure"),
    )
    assert committed.new_state.revision == 1
    assert committed.new_state.value == 6


def test_real_shaped_s49_receipt_cannot_silently_relabel_s15_before_as_choice():
    intent, forecast, receipts, decisions, _ = _s49_two_probe_shape()
    # The child must receive the actual original decision probe explicitly.
    with pytest.raises(IntentMotionRejected):
        close_motion_intent_experience(
            intent, forecast, receipts, attempt_id="source-join",
        )
    # Nor can it pass S15 before as a fake L0-selected source.
    with pytest.raises(IntentMotionRejected):
        _close(intent, forecast, receipts, (
            receipts[0].consequence.before_observation,
        ))


@pytest.mark.parametrize("case", [
    "foreign_session", "wrong_source", "wrong_request",
    "stale_selection", "selection_after_internal_before",
    "internal_before_relabel", "missing_before", "wrong_receipt_source",
    "duplicate_selection", "replay_old_after", "incorrect_forecast_source",
])
def test_s49_selection_to_s15_negative_controls(case):
    intent, forecast, receipts, decisions, _ = _s49_two_probe_shape()
    receipt = receipts[0]
    chosen = decisions[0]
    internal = receipt.consequence.before_observation
    if case == "foreign_session":
        decisions = (replace(chosen, session_id="foreign-session"),)
    elif case == "wrong_source":
        receipts = (replace(
            receipt, source=Provenance("test", "not-mineflayer"),
        ),)
    elif case == "wrong_request":
        decisions = (replace(chosen, request_id=None),)
    elif case == "stale_selection":
        decisions = (replace(chosen, seq=forecast.source_probe_seq - 1),)
    elif case == "selection_after_internal_before":
        decisions = (replace(chosen, seq=internal.seq + 1),)
    elif case == "internal_before_relabel":
        receipts = (replace(receipt, consequence=replace(
            receipt.consequence, before_observation=chosen,
        )),)
    elif case == "missing_before":
        receipts = (replace(receipt, consequence=replace(
            receipt.consequence, status=WorldConsequenceStatus.FAILED,
            error="missing S15 before source", before_observation=None,
        )),)
    elif case == "wrong_receipt_source":
        receipts = (replace(
            receipt, source=Provenance("mineflayer", "other-decision"),
        ),)
    elif case == "duplicate_selection":
        decisions = (chosen, chosen)
    elif case == "replay_old_after":
        receipts = (replace(receipt, consequence=replace(
            receipt.consequence,
            after_observation=replace(
                receipt.consequence.after_observation, seq=internal.seq,
            ),
        )),)
    elif case == "incorrect_forecast_source":
        forecast = replace(
            forecast, source_provenance=Provenance("mineflayer", "post-hoc"),
        )
    with pytest.raises(IntentMotionRejected):
        _close(intent, forecast, receipts, decisions)


def test_two_real_shaped_moves_still_one_experience_not_two():
    intent, forecast, first_pair, first_decisions, _ = _s49_two_probe_shape()
    r1 = first_pair[0]
    old_after = r1.consequence.after_observation
    chosen2 = replace(
        first_decisions[0], seq=old_after.seq + 2,
        request_id="next-correlated-choice",
    )
    internal2 = replace(
        r1.consequence.before_observation,
        seq=chosen2.seq + 2,
    )
    after2 = replace(
        old_after, seq=internal2.seq + 3,
    )
    second = NormalActionReceipt(
        terminal=replace(r1.terminal, action_id="second-s49-physical-action"),
        consequence=replace(
            r1.consequence, action_id="second-s49-physical-action",
            before_observation=internal2,
            dispatch_receipt=replace(
                r1.consequence.dispatch_receipt, seq=internal2.seq + 1,
            ),
            cleanup_receipt=replace(
                r1.consequence.cleanup_receipt, seq=internal2.seq + 2,
            ),
            after_observation=after2, movement_distance=0.28,
        ),
        source=chosen2.provenance,
    )
    experience = _close(
        intent, forecast, (r1, second), (first_decisions[0], chosen2),
    )
    assert len(experience.action_receipts) == 2
    assert len(experience.decision_probes) == 2
    assert experience.measured_total_m == pytest.approx(0.59)
    assert experience.comparison is MotionComparison.SHORTER


def test_wrong_number_of_decisions_fails_closed():
    intent, forecast, receipts, _, _ = _s49_two_probe_shape()
    with pytest.raises(IntentMotionRejected):
        _close(intent, forecast, receipts, ())
