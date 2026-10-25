"""SelfBody motion feedback v0: typed original S16 outcomes, no new authority."""
from __future__ import annotations

import asyncio
import hashlib
from dataclasses import replace

import pytest

import test_action_feedback_qualification as s17
from adapters.mineflayer.execution import MineflayerCommand
from adapters.mineflayer.m02_paper_dev.s50_boundary import BoundaryRejected
from adapters.mineflayer.s49_paper_world_first_dev import CONFIRM, run
from adapters.mineflayer.s49_selfbody_motion_feedback_dev import (
    SelfBodyMotionState,
    apply_to_next_issued,
    propose_motion_correction,
)


def _original_closed(index: int, *, distance: float = 0.6269065734210617):
    # Existing typed S15/S16 fixture, with independent ordered native
    # evidence exactly as required by capture_native_action_evidence().
    *_, source, _, _ = s17.executed_closed_chain()
    aid = f"original-s49-move-{index}"
    sid = source.session_id
    shift = index * 100
    before, dispatch = source.before_observation, source.dispatch_receipt
    cleanup, after = source.cleanup_receipt, source.after_observation

    def native(frame, *, aid=None, **attrs):
        seq = frame.seq + shift
        return replace(
            frame, seq=seq,
            **({"action_id": aid} if aid is not None else {}),
            **attrs,
        )
    before = native(
        before, snapshot=replace(
            before.snapshot,
            position=replace(before.snapshot.position, x=0.0, z=0.0),
        ),
    )
    after = native(
        after, snapshot=replace(
            after.snapshot,
            position=replace(after.snapshot.position, x=distance, z=0.0),
        ),
    )
    dispatch = native(dispatch, aid=aid)
    cleanup = native(cleanup, aid=f"{aid}-s15-clear")
    return replace(
        source, action_id=aid,
        before_observation=before, dispatch_receipt=dispatch,
        cleanup_receipt=cleanup, after_observation=after,
        movement_distance=distance,
    )


def _three_closed():
    one = _original_closed(1)
    state = SelfBodyMotionState(one.session_id)
    outcomes = [one, _original_closed(2), _original_closed(3)]
    for outcome in outcomes:
        state = state.observe_closed(outcome, requested_duration_s=0.2)
    return state


def _issued_command(duration: float) -> MineflayerCommand:
    return MineflayerCommand(
        action_id="original-s49-move-4", binding_id="original-binding-4",
        action_ref="MOVE_BACKWARD", effect="set_control", control="back",
        state=True, duration_s=duration, cleanup_action_id="original-s49-move-4-s15-clear",
    )


def test_real_shape_source_to_motion_prediction_error_and_future_duration():
    state = _three_closed()
    assert len(state.samples) == 3
    assert state.samples[0].predicted_displacement_m is None
    assert state.samples[1].prediction_error_m == pytest.approx(0)
    assert state.samples[2].prediction_error_m == pytest.approx(0)
    assert state.estimated_m_per_requested_s == pytest.approx(3.1345328671053084)
    next_native = state.samples[-1].after_seq + 10
    candidate = 0.19648932318884205
    proposal = propose_motion_correction(
        state, current_native_seq=next_native,
        baseline_duration_s=candidate,
    )
    assert proposal.sample_count_before == 3
    assert proposal.source_action_id == "original-s49-move-3"
    assert proposal.predicted_displacement_before_m > proposal.goal_distance_m
    assert proposal.proposed_duration_s == pytest.approx(candidate * 0.75)
    assert proposal.predicted_displacement_after_m < proposal.predicted_displacement_before_m
    assert proposal.goal_source == "EXPLICIT_DEV_DISTANCE_GOAL_NOT_ORIGINAL_L0_INTENT"
    command = _issued_command(candidate)
    adjusted = apply_to_next_issued(
        proposal, command, current_session_id=state.session_id,
        current_native_seq=next_native,
    )
    assert adjusted.duration_s == proposal.proposed_duration_s
    assert adjusted.action_id == command.action_id
    assert adjusted.binding_id == command.binding_id
    assert adjusted.cleanup_action_id == command.cleanup_action_id
    assert command.duration_s == candidate
    later = state.observe_closed(
        _original_closed(4, distance=0.43023153716250917),
        requested_duration_s=adjusted.duration_s,
    )
    assert len(later.samples) == 4
    assert later.samples[-1].predicted_displacement_m == pytest.approx(
        proposal.predicted_displacement_after_m
    )
    assert later.samples[-1].prediction_error_m == pytest.approx(
        0.43023153716250917 - proposal.predicted_displacement_after_m
    )
    assert later.samples[-1].as_report()["world_tick_count_attested"] is False
    assert proposal.as_report()["new_action_issuer"] is False
    assert proposal.as_report()["s10_updated"] is False


@pytest.mark.parametrize("change", [
    "duplicate", "out_of_order", "foreign_session", "wrong_displacement",
    "wrong_cleanup", "wrong_dispatch", "foreign_provenance", "zero_duration",
    "unbounded_duration", "unexecuted",
])
def test_closed_outcomes_cannot_be_forged_or_reused(change):
    state = _three_closed()
    source = _original_closed(4)
    hold = 0.2
    if change == "duplicate":
        source = _original_closed(3)
    elif change == "out_of_order":
        source = _original_closed(2)
        source = replace(source, action_id="new-action")
    elif change == "foreign_session":
        state = SelfBodyMotionState("foreign-session", state.samples)
    elif change == "wrong_displacement":
        source = replace(source, movement_distance=0.9)
    elif change == "wrong_cleanup":
        source = replace(
            source,
            cleanup_receipt=replace(source.cleanup_receipt, action_id="wrong-clean"),
        )
    elif change == "wrong_dispatch":
        # Original typed S16 may reject a non-applied dispatch immediately,
        # before downstream SelfBody observes any forged receipt.
        with pytest.raises(ValueError):
            replace(
                source,
                dispatch_receipt=replace(
                    source.dispatch_receipt, result="rejected",
                ),
            )
        return
    elif change == "foreign_provenance":
        source = replace(
            source,
            before_observation=replace(
                source.before_observation,
                session_id="foreign-source",
            ),
        )
    elif change == "zero_duration":
        hold = 0.0
    elif change == "unbounded_duration":
        hold = 0.23
    elif change == "unexecuted":
        source = None
    with pytest.raises((BoundaryRejected, ValueError)):
        state.observe_closed(source, requested_duration_s=hold)


@pytest.mark.parametrize("change", [
    "insufficient_samples", "stale_probe", "foreign_command",
    "pre_modified_command", "same_action", "unbounded_goal", "bad_model",
])
def test_future_motion_correction_fail_closed(change):
    state = _three_closed()
    native = state.samples[-1].after_seq + 10
    duration = 0.19648932318884205
    goal = 0.45
    if change == "insufficient_samples":
        state = replace(state, samples=state.samples[:2])
    elif change == "stale_probe":
        native = state.samples[-1].after_seq
    elif change == "unbounded_goal":
        goal = 12.0
    elif change == "bad_model":
        duration = float("nan")
    if change in ("insufficient_samples", "stale_probe", "unbounded_goal", "bad_model"):
        with pytest.raises(BoundaryRejected):
            propose_motion_correction(
                state, current_native_seq=native,
                baseline_duration_s=duration, explicit_dev_goal_m=goal,
            )
        return
    correction = propose_motion_correction(
        state, current_native_seq=native, baseline_duration_s=duration,
    )
    command = _issued_command(duration)
    if change == "foreign_command":
        command = replace(command, action_id="different-issued-action")
        correction = replace(correction, source_action_id="different-issued-action")
    elif change == "pre_modified_command":
        command = replace(command, duration_s=0.1)
    elif change == "same_action":
        correction = replace(correction, source_action_id=command.action_id)
    with pytest.raises(BoundaryRejected):
        apply_to_next_issued(
            correction, command,
            current_session_id=(
                "foreign" if change == "foreign_command" else state.session_id
            ),
            current_native_seq=native,
        )


@pytest.mark.parametrize("fifth,gait,sixth,scenario", [
    (False, False, False, "ORIGINAL_P1"),
    (True, False, True, "ORIGINAL_P1"),
    (True, True, False, "ORIGINAL_P1"),
    (True, True, True, "UNCALIBRATED_STRESS_P1"),
])
def test_feedback_optin_requires_original_sixth_normal_world(
    tmp_path, fifth, gait, sixth, scenario,
):
    paper = tmp_path / "paper.jar"
    observer = tmp_path / "observer.jar"
    paper.write_bytes(b"fixture")
    observer.write_bytes(b"fixture-observer")
    out = tmp_path / "never-created"
    result = asyncio.run(run(
        out, paper, hashlib.sha256(paper.read_bytes()).hexdigest(),
        observer, hashlib.sha256(observer.read_bytes()).hexdigest(),
        confirmation=CONFIRM, actual_next_epoch=True,
        actual_fifth_epoch=fifth, compare_fifth_gait=gait,
        actual_sixth_motor=sixth, motor_scenario=scenario,
        selfbody_motion_feedback=True,
    ))
    assert result == 2
    assert not out.exists()
