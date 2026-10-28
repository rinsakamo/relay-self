"""DEV original S49 L0: prior native S16 -> next physical input duration.

These unit tests use typed-shape witnesses; an actual S16 owner/World is
separately required by the native workflow before any physical claim.
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock
from pathlib import Path

import pytest

from adapters.mineflayer.execution import WorldConsequence, WorldConsequenceStatus
from adapters.mineflayer.s49_l0_observed_step_dev import (
    L0MotionFeedbackRejected,
    plan_next_l0_step_dev,
)


def previous_consequence(distance: float = 3.6):
    previous = Mock(spec=WorldConsequence)
    previous.action_ref = "MOVE_FORWARD_SPRINT_DEV"
    previous.status = WorldConsequenceStatus.EXECUTED
    previous.session_id = "genuine-original-test-session"
    previous.action_id = "original-16"
    previous.before_observation = SimpleNamespace(session_id=previous.session_id)
    previous.after_observation = SimpleNamespace(session_id=previous.session_id)
    previous.dispatch_receipt = object()
    previous.cleanup_receipt = object()
    previous.cleanup_attempted = True
    previous.movement_distance = distance
    return previous


def test_feedback_uses_observed_movement_not_assumed_speed():
    p = plan_next_l0_step_dev(
        previous_consequence(3.6), next_step_m=1.2,
        current_threat_distance_m=2.1,
    )
    assert p.previous_observed_m == 3.6
    assert p.observed_mean_mps == pytest.approx(6)
    assert p.requested_duration_s == pytest.approx(0.2)
    assert p.reason == "OBSERVED_SPEED_INPUT_CORRECTION"
    assert p.native_tick_phase_attested is False
    assert p.actual_target_reached_attested is False
    assert p.qualification_go is False


def test_correction_saturates_to_bounded_input_not_nondeterministic_ticks():
    slow = plan_next_l0_step_dev(
        previous_consequence(0.12), next_step_m=2.5,
        current_threat_distance_m=2.0,
    )
    fast = plan_next_l0_step_dev(
        previous_consequence(8.0), next_step_m=0.3,
        current_threat_distance_m=2.0,
    )
    assert slow.requested_duration_s == 0.60
    assert fast.requested_duration_s == 0.10


def test_nearby_danger_prioritizes_original_l0_escape():
    p = plan_next_l0_step_dev(
        previous_consequence(), next_step_m=1.0,
        current_threat_distance_m=1.1,
    )
    assert p.requested_duration_s is None
    assert p.reason == "DANGER_ORIGINAL_L0_ESCAPE_PRIORITY"


@pytest.mark.parametrize("fault", [
    "no_world", "failed", "unknown", "no_before", "no_after", "no_receipt",
    "no_cleanup", "wrong_session_before", "wrong_session_after", "no_action",
    "short", "zero", "nan", "infinite", "bad_action_ref",
])
def test_invalid_prior_outcome_never_triggers_input_adjustment(fault):
    p = previous_consequence()
    if fault == "no_world":
        p = object()
    elif fault == "failed":
        p.status = WorldConsequenceStatus.FAILED
    elif fault == "unknown":
        p.status = WorldConsequenceStatus.UNDETERMINED
    elif fault == "no_before":
        p.before_observation = None
    elif fault == "no_after":
        p.after_observation = None
    elif fault == "no_receipt":
        p.dispatch_receipt = None
    elif fault == "no_cleanup":
        p.cleanup_receipt = None
    elif fault == "wrong_session_before":
        p.before_observation.session_id = "other"
    elif fault == "wrong_session_after":
        p.after_observation.session_id = "other"
    elif fault == "no_action":
        p.action_id = ""
    elif fault == "short":
        p.movement_distance = 0.04
    elif fault == "zero":
        p.movement_distance = 0.0
    elif fault == "nan":
        p.movement_distance = float("nan")
    elif fault == "infinite":
        p.movement_distance = float("inf")
    else:
        p.action_ref = "MOVE_BACKWARD"
    with pytest.raises(L0MotionFeedbackRejected):
        plan_next_l0_step_dev(
            p, next_step_m=1.0, current_threat_distance_m=2.0,
        )


@pytest.mark.parametrize("params", [
    {"next_step_m": 0.0, "current_threat_distance_m": 2.0},
    {"next_step_m": 20.0, "current_threat_distance_m": 2.0},
    {"next_step_m": float("nan"), "current_threat_distance_m": 2.0},
    {"next_step_m": 1.0, "current_threat_distance_m": float("inf")},
    {"next_step_m": 1.0, "current_threat_distance_m": 0.0},
    {"next_step_m": 1.0, "current_threat_distance_m": 4.0},
])
def test_bad_world_condition_refuses(params):
    with pytest.raises(L0MotionFeedbackRejected):
        plan_next_l0_step_dev(previous_consequence(), **params)


def test_original_s49_single_owner_and_s15_bound_verified_by_source():
    # No extra receiver or retry loop: S49 itself owns the next calculation.
    runner = Path("adapters/mineflayer/s49_normal_session_real_ci.py").read_text()
    executor = Path("adapters/mineflayer/normal_action.py").read_text()
    assert "first_feedback_receipt.consequence" in runner
    assert "plan_next_l0_step_dev(" in runner
    assert 'os.environ.get("S49_L0_OBSERVED_FEEDBACK_DEV_ONLY") != "1"' in runner
    assert "dev_next_duration_s" in executor
    assert "self._count != 1" in executor
    assert "replace(command, duration_s=dev_next_duration_s)" in executor
    assert "self.require_authorizations(step, bound, probe, propose, issue)" in executor
