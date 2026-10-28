"""S16→S16→S16 feedback: residual from real second Action, safe stop."""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from adapters.mineflayer.execution import WorldConsequence, WorldConsequenceStatus
from adapters.mineflayer.s49_l0_observed_step_dev import (
    L0MotionFeedbackRejected,
    plan_residual_after_second_s16_dev,
)


def second(distance: float = 0.5593010031446095):
    c = Mock(spec=WorldConsequence)
    c.action_ref = "MOVE_FORWARD_SPRINT_DEV"
    c.status = WorldConsequenceStatus.EXECUTED
    c.session_id = "original-second-session"
    c.action_id = "second-original"
    c.before_observation = SimpleNamespace(session_id=c.session_id)
    c.after_observation = SimpleNamespace(session_id=c.session_id)
    c.dispatch_receipt = object()
    c.cleanup_receipt = object()
    c.cleanup_attempted = True
    c.movement_distance = distance
    return c


def compute(second_, **kwargs):
    return plan_residual_after_second_s16_dev(
        second_, second_input_s=0.1455216922965268, total_target_m=1.0,
        current_threat_distance_m=2.0, **kwargs,
    )


def test_bounded_micro_step_from_actual_second_not_first_speed():
    plan = compute(second())
    assert plan.decision == "OBSERVED_RESIDUAL_MICRO_STEP"
    assert plan.residual_m == pytest.approx(0.4406989968553905)
    assert plan.proposed_duration_s == pytest.approx(
        0.4406989968553905 * 0.1455216922965268 / 0.5593010031446095
    )
    assert plan.paper_node_tick_synchronized is False
    assert plan.absolute_world_goal_attested is False
    assert plan.qualification_go is False


def test_overshoot_and_deadband_stop_without_issuing_correction():
    for distance in (0.9, 1.0, 1.2):
        plan = compute(second(distance))
        assert plan.proposed_duration_s is None
        assert plan.decision == "STOP_AVOID_OVERSHOOT"


def test_threat_preempts_target_accuracy():
    plan = plan_residual_after_second_s16_dev(
        second(), second_input_s=0.1455216922965268, total_target_m=1.0,
        current_threat_distance_m=1.1,
    )
    assert plan.decision == "DANGER_L0_PRIORITY"
    assert plan.proposed_duration_s is None


def test_short_duration_clamped_and_no_long_action():
    plan = plan_residual_after_second_s16_dev(
        second(0.1), second_input_s=0.60, total_target_m=2.5,
        current_threat_distance_m=2,
    )
    assert plan.proposed_duration_s == 0.60
    fast = plan_residual_after_second_s16_dev(
        second(0.84), second_input_s=0.10, total_target_m=1.0,
        current_threat_distance_m=2.0, tolerance_m=0.05,
    )
    assert fast.proposed_duration_s == 0.10


@pytest.mark.parametrize("fault", [
    "not_world", "undetermined", "failed", "no_before", "no_after",
    "no_dispatch", "no_cleanup_receipt", "no_cleanup",
    "wrong_before_session", "wrong_after_session", "wrong_ref",
    "zero", "nan", "inf", "no_action",
])
def test_bad_second_action_fails_closed(fault):
    c = second()
    if fault == "not_world":
        c = object()
    elif fault == "undetermined":
        c.status = WorldConsequenceStatus.UNDETERMINED
    elif fault == "failed":
        c.status = WorldConsequenceStatus.FAILED
    elif fault == "no_before":
        c.before_observation = None
    elif fault == "no_after":
        c.after_observation = None
    elif fault == "no_dispatch":
        c.dispatch_receipt = None
    elif fault == "no_cleanup_receipt":
        c.cleanup_receipt = None
    elif fault == "no_cleanup":
        c.cleanup_attempted = False
    elif fault == "wrong_before_session":
        c.before_observation.session_id = "other"
    elif fault == "wrong_after_session":
        c.after_observation.session_id = "other"
    elif fault == "wrong_ref":
        c.action_ref = "MOVE_BACKWARD"
    elif fault == "zero":
        c.movement_distance = 0
    elif fault == "nan":
        c.movement_distance = float("nan")
    elif fault == "inf":
        c.movement_distance = float("inf")
    elif fault == "no_action":
        c.action_id = ""
    with pytest.raises(L0MotionFeedbackRejected):
        compute(c)


@pytest.mark.parametrize("name,value", [
    ("second_input_s",0), ("second_input_s",0.99),
    ("second_input_s",float("nan")), ("total_target_m",0),
    ("total_target_m",100), ("current_threat_distance_m",0),
    ("current_threat_distance_m",4), ("tolerance_m",-1),
])
def test_malformed_plan_parameters_fail(name,value):
    kwargs = dict(
        second_input_s=0.1455216922965268, total_target_m=1.0,
        current_threat_distance_m=2.0, tolerance_m=0.15,
    )
    kwargs[name]=value
    with pytest.raises(L0MotionFeedbackRejected):
        plan_residual_after_second_s16_dev(second(),**kwargs)


def test_third_is_original_host_epoch_and_requires_separate_grant():
    s49=Path("adapters/mineflayer/s49_normal_session_real_ci.py").read_text()
    exe=Path("adapters/mineflayer/normal_action.py").read_text()
    assert "dev_l0_residual_third_dev" in s49
    assert "dev_next_epoch != \"MOVE_AWAY\"" in s49
    assert "plan_residual_after_second_s16_dev(" in s49
    assert "third L0 requested action despite STOP/danger feedback" in s49
    assert 'os.environ.get("S49_L0_RESIDUAL_THIRD_DEV_ONLY") != "1"' in s49
    assert "self._count not in (1, 2)" in exe
    assert "self.require_authorizations(step, bound, probe, propose, issue)" in exe
