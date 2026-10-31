"""Self-supervised native S49 motor predictor, NOT Goal/Habit learning."""
from __future__ import annotations

import pytest

from adapters.mineflayer.slm_motor_expectation_dev import (
    MotorExpectationRejected,
    MotorHistory,
    score_motor_expectation,
)
from adapters.mineflayer.slm_passive_dev import S49SLMDevOwner
from adapters.mineflayer.slm_prior_world_dev import PriorWorldReadback
from test_s49_slm_passive_dev import decide, setup


def history():
    return MotorHistory(
        source_session_id="older-real-world",
        source_stdout_sha256="a" * 64,
        original_action_ids=("older-a", "older-b"),
        displacement_m=(0.83, 0.63),
    )


def current_action(session="next-real-world", action="real-first", distance=0.63):
    return {
        "action": action, "source": session, "terminal": "outcome",
        "movement_m": distance,
        "execution_evidence": {
            "action_ref": "MOVE_BACKWARD", "status": "executed",
            "goal_success_attested": False,
        },
    }


def test_forecast_changes_with_past_real_motion_but_not_policy():
    past = history()
    out = score_motor_expectation(
        past, current_session_id="next-real-world",
        current_actions=[current_action(), current_action(action="real-second")],
    )
    assert out["status"] == "HELDOUT_SCORED"
    assert out["training_observations"] == 2
    assert out["holdout_observations"] == 2
    assert out["model_expected_m"] == pytest.approx(0.73)
    assert out["cheap_expected_m"] == pytest.approx(0.63)
    assert out["model_mae_m"] == pytest.approx(0.1)
    assert out["cheap_mae_m"] == pytest.approx(0.0)
    assert out["beats_cheap_control"] is False
    assert out["l8_learning_updates"] == out["s10_updates"] == 0
    assert out["action_authority"] is out["policy_changed"] is False
    assert out["real_goal_training_labels"] == 0


def test_current_future_action_does_not_leak_into_prediction():
    past = history()
    a = score_motor_expectation(past, current_session_id="next-real-world",
                                current_actions=[])
    b = score_motor_expectation(past, current_session_id="next-real-world",
                                current_actions=[current_action(distance=1.2)])
    assert a["status"] == "NO_CURRENT_MOTOR_OUTCOME"
    assert a["model_mae_m"] is None
    assert a["cheap_mae_m"] is None
    assert a["model_expected_m"] == b["model_expected_m"] == 0.73
    assert a["cheap_expected_m"] == b["cheap_expected_m"] == 0.63


@pytest.mark.parametrize("bad", (
    [],
    [current_action(action="bad", distance=-1)],
    [current_action(session="older-real-world")],
    [current_action(action="a", distance=float("nan"))],
    [{**current_action(), "terminal": "unknown"}],
    [{**current_action(), "source": "wrong-session"}],
    [{**current_action(), "execution_evidence": {
        **current_action()["execution_evidence"], "goal_success_attested": True,
    }}],
))
def test_unsafe_next_world_source_cannot_score(bad):
    if bad == []:
        assert score_motor_expectation(history(), current_session_id="next-real-world",
                                       current_actions=bad)["status"] == "NO_CURRENT_MOTOR_OUTCOME"
        return
    with pytest.raises(MotorExpectationRejected):
        score_motor_expectation(history(), current_session_id="next-real-world",
                                current_actions=bad)


def test_same_session_and_unbounded_observations_rejected():
    with pytest.raises(MotorExpectationRejected):
        score_motor_expectation(history(), current_session_id="older-real-world",
                                current_actions=[current_action()])
    with pytest.raises(MotorExpectationRejected):
        score_motor_expectation(history(), current_session_id="next-real-world",
                                current_actions=[current_action()] * 3)
    with pytest.raises(MotorExpectationRejected):
        MotorHistory("older", "a" * 64, ("id1", "id2"), (0.0, 0.63))


def test_previous_motor_requires_matching_verified_previous_world():
    hist = history()
    _, host, supervisor, native, event = setup()
    prev = PriorWorldReadback(
        session_id=hist.source_session_id,
        stdout_sha256=hist.source_stdout_sha256,
        original_action_ids=hist.original_action_ids,
        original_action_probe_seqs=(21, 48),
    )
    owner = S49SLMDevOwner(retention_enabled=True, prior_world=prev,
                            motor_history=hist)
    owner.bind(host, supervisor)
    orig = decide(owner, host, native, event)
    result = owner.finish([])
    assert orig.choice.selection.value == "MOVE_AWAY"
    assert result["observer_errors"] == 0
    assert result["one_l8_memory_owner"] is True
    assert result["l1_motor_expectation"]["status"] == "NO_CURRENT_MOTOR_OUTCOME"
    assert result["l8_training_admissions"] == 0
    assert host.action_requests == 1
    with pytest.raises(ValueError, match="same prior"):
        S49SLMDevOwner(prior_world=prev, motor_history=MotorHistory(
            "different-session", "a" * 64, ("older-a", "older-b"), (0.83, 0.63),
        ))
