"""DEV-only SelfBody uncertainty: closed S16 residuals damp one next Action."""
from __future__ import annotations

from dataclasses import replace

import pytest

from adapters.mineflayer.m02_paper_dev.s50_boundary import BoundaryRejected
from adapters.mineflayer.s49_selfbody_motion_feedback_dev import (
    SelfBodyMotionState,
    apply_to_next_issued,
    propose_motion_correction,
)
from adapters.mineflayer.s49_selfbody_motion_uncertainty_dev import (
    UNCERTAINTY_FLOOR_M,
    guard_next_motion_correction_dev,
)
from test_s49_selfbody_motion_feedback_dev import _issued_command, _original_closed

NOMINAL = 0.19648932318884205


def _state(distances=(0.6269065734210617,) * 3):
    first = _original_closed(1, distance=distances[0])
    state = SelfBodyMotionState(first.session_id)
    for index, distance in enumerate(distances, 1):
        state = state.observe_closed(
            _original_closed(index, distance=distance), requested_duration_s=0.2,
        )
    return state


def _proposal(state):
    return propose_motion_correction(
        state, current_native_seq=state.samples[-1].after_seq + 10,
        baseline_duration_s=NOMINAL,
    )


def test_identical_history_still_keeps_uncertainty_floor_and_issued_identity():
    state = _state()
    original = _proposal(state)
    guarded, record = guard_next_motion_correction_dev(state, original)
    assert record.historical_closed_samples == 3
    assert record.historical_prediction_errors_used == 2
    assert record.observed_prediction_error_rms_m == pytest.approx(0)
    assert record.applied_uncertainty_floor_m == UNCERTAINTY_FLOOR_M
    assert record.robust_uncertainty_m == UNCERTAINTY_FLOOR_M
    assert record.stability_gain == pytest.approx(1 - 0.1 / 0.45)
    assert original.proposed_duration_s < guarded.proposed_duration_s < NOMINAL
    assert guarded.source_action_id == original.source_action_id
    assert guarded.source_session_id == original.source_session_id
    assert guarded.last_native_after_seq == original.last_native_after_seq
    assert guarded.predicted_displacement_after_m == pytest.approx(
        state.estimated_m_per_requested_s * guarded.proposed_duration_s
    )
    assert record.as_report()["stability_gain_is_probability"] is False
    assert record.as_report()["floor_empirically_calibrated"] is False
    assert record.as_report()["world_tick_alignment_attested"] is False
    original_command = _issued_command(NOMINAL)
    authorized = apply_to_next_issued(
        guarded, original_command, current_session_id=state.session_id,
        current_native_seq=state.samples[-1].after_seq + 10,
    )
    assert original_command.duration_s == NOMINAL
    assert authorized.duration_s == guarded.proposed_duration_s
    assert authorized.action_id == original_command.action_id
    assert authorized.binding_id == original_command.binding_id
    assert authorized.cleanup_action_id == original_command.cleanup_action_id


def test_higher_real_closed_prediction_error_reduces_correction_strength():
    stable = _state()
    noisy = _state((0.6269065734210617, 0.4302315371625083, 0.6269065734210617))
    stable_proposal = _proposal(stable)
    noisy_proposal = _proposal(noisy)
    stable_guard, stable_info = guard_next_motion_correction_dev(stable, stable_proposal)
    noisy_guard, noisy_info = guard_next_motion_correction_dev(noisy, noisy_proposal)
    assert noisy_info.observed_prediction_error_rms_m > 0.1
    assert noisy_info.stability_gain < stable_info.stability_gain
    assert abs(noisy_guard.proposed_duration_s - NOMINAL) < abs(
        noisy_proposal.proposed_duration_s - NOMINAL
    )
    assert abs(stable_guard.proposed_duration_s - NOMINAL) < abs(
        stable_proposal.proposed_duration_s - NOMINAL
    )
    assert noisy_info.source_action_id == noisy.samples[-1].action_id


def test_fourth_outcome_is_not_used_to_adjust_earlier_sixth_action():
    state = _state()
    earlier, info = guard_next_motion_correction_dev(state, _proposal(state))
    state_after = state.observe_closed(
        _original_closed(4, distance=0.4302315371625083),
        requested_duration_s=earlier.proposed_duration_s,
    )
    assert len(state_after.samples) == 4
    assert state_after.samples[-1].prediction_error_m is not None
    assert info.historical_closed_samples == 3
    assert info.source_action_id == state.samples[-1].action_id
    assert info.source_action_id != state_after.samples[-1].action_id
    assert info.guarded_duration_s == earlier.proposed_duration_s


@pytest.mark.parametrize("tamper", [
    "foreign_session", "foreign_last_action", "stale_source_seq",
    "shorter_history", "missing_prediction_error", "nan_prediction_error",
    "unbounded_proposal", "nan_proposal", "wrong_sample_count",
    "invalid_goal", "too_large_step",
])
def test_uncertainty_guard_rejects_forged_or_invalid_source(tamper):
    state = _state()
    proposal = _proposal(state)
    if tamper == "foreign_session":
        proposal = replace(proposal, source_session_id="another")
    elif tamper == "foreign_last_action":
        proposal = replace(proposal, source_action_id="another")
    elif tamper == "stale_source_seq":
        proposal = replace(proposal, last_native_after_seq=0)
    elif tamper == "shorter_history":
        state = replace(state, samples=state.samples[:2])
    elif tamper == "missing_prediction_error":
        state = replace(
            state, samples=(state.samples[0], replace(
                state.samples[1], prediction_error_m=None,
            ), state.samples[2]),
        )
    elif tamper == "nan_prediction_error":
        state = replace(
            state, samples=(state.samples[0], replace(
                state.samples[1], prediction_error_m=float("nan"),
            ), state.samples[2]),
        )
    elif tamper == "unbounded_proposal":
        proposal = replace(proposal, proposed_duration_s=1.0)
    elif tamper == "nan_proposal":
        proposal = replace(proposal, proposed_duration_s=float("nan"))
    elif tamper == "wrong_sample_count":
        proposal = replace(proposal, sample_count_before=20)
    elif tamper == "invalid_goal":
        proposal = replace(proposal, goal_distance_m=0.05)
    elif tamper == "too_large_step":
        proposal = replace(proposal, proposed_duration_s=0.08)
    with pytest.raises(BoundaryRejected):
        guard_next_motion_correction_dev(state, proposal)
