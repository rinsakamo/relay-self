"""Native S16 XZ, not scalar sum: wrong direction and input-off drift guards."""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from adapters.mineflayer.execution import WorldConsequence, WorldConsequenceStatus
from adapters.mineflayer.normal_action import NormalActionRejected, NormalWorldL0
from adapters.mineflayer.python_protocol import MineflayerPosition
from adapters.mineflayer.s49_l0_native_xz_two_real_dev import review_native
from adapters.mineflayer.s49_l0_xz_goal_dev import (
    S49XZGoalRejected,
    assess_closed_second_xz,
    lock_goal_after_first_s16,
    plan_third_walk_xz,
    read_xz_goal,
)


def pos(x: float, z: float) -> MineflayerPosition:
    return MineflayerPosition(x=x, y=-60.0, z=z)


def native_consequence(first: bool = True, *,
                       after: MineflayerPosition | None = None):
    a = pos(-4.5, -4.5 if first else -1.1374763821)
    b = after or pos(-4.5, -1.4698428355 if first else -0.3224978367)
    c = Mock(spec=WorldConsequence)
    c.action_id = "native-first" if first else "native-second"
    c.action_ref = "MOVE_FORWARD_SPRINT_DEV"
    c.session_id = "native-same-session"
    c.status = WorldConsequenceStatus.EXECUTED
    c.before_observation = SimpleNamespace(
        session_id=c.session_id,seq=20 if first else 40,
        snapshot=SimpleNamespace(position=a),
    )
    c.after_observation = SimpleNamespace(
        session_id=c.session_id,seq=35 if first else 59,
        snapshot=SimpleNamespace(position=b),
    )
    c.dispatch_receipt = object()
    c.cleanup_receipt = object()
    c.cleanup_attempted = True
    import math
    c.movement_distance = math.hypot(b.x-a.x,b.z-a.z)
    return c


def test_goal_precommitted_from_first_xz_and_second_drift_included():
    first=native_consequence()
    goal=lock_goal_after_first_s16(first,target_offset_m=1.0)
    assert goal.target_x == -4.5
    assert goal.target_z == pytest.approx(-0.4698428355)
    assert goal.forward_z == pytest.approx(1)
    second=native_consequence(False)
    reading=assess_closed_second_xz(goal,second)
    assert reading.euclidean_error_m == pytest.approx(0.147345)
    assert reading.forward_remaining_m < 0
    assert reading.stop_reason == "STOP_PASSED_TARGET_XZ"
    # Old scalar "0.185m short" falsely implies a forward input is needed.
    assert 1.0-second.movement_distance == pytest.approx(0.1850214546)


def test_original_walk_scalar_distance_claim_was_not_xz_goal_reach():
    goal=lock_goal_after_first_s16(
        native_consequence(),target_offset_m=1.0,
    )
    after=read_xz_goal(
        goal,pos(-4.5,0.2300509835),
        session_id=goal.session_id,source_kind="third_s16_after",
        source_seq=91,
    )
    assert after.euclidean_error_m == pytest.approx(0.699893819)
    assert after.forward_remaining_m < 0
    assert after.stop_reason == "STOP_PASSED_TARGET_XZ"


def test_live_xz_target_two_meters_can_propose_bounded_walk():
    goal=lock_goal_after_first_s16(
        native_consequence(),target_offset_m=2.0,
    )
    second=native_consequence(False)
    live,hold=plan_third_walk_xz(
        goal,second,second_input_s=0.1980095313,
        live_position=pos(-4.5,-0.0194571146),
        live_probe_session_id=goal.session_id,live_probe_seq=68,
        current_threat_distance_m=2.0,
    )
    assert live.stop_reason is None
    assert live.forward_remaining_m == pytest.approx(0.5496142791)
    assert 0.1 <= hold <= 0.6


@pytest.mark.parametrize("position", [
    pos(-4.5,0.5), # already crossed goal
    pos(-4.5,-0.4698428355), # within deadband
    pos(-3.5,-1.0), # sideways drift
])
def test_third_forward_refused_when_past_or_off_axis(position):
    goal=lock_goal_after_first_s16(native_consequence(),target_offset_m=1.0)
    with pytest.raises(S49XZGoalRejected):
        plan_third_walk_xz(
            goal,native_consequence(False),second_input_s=0.198,
            live_position=position,live_probe_session_id=goal.session_id,
            live_probe_seq=68,current_threat_distance_m=2.0,
        )


@pytest.mark.parametrize("fault", [
    "foreign_session","stale_seq","danger","wrong_goal_session",
])
def test_stale_or_dangerous_native_fails_closed(fault):
    goal=lock_goal_after_first_s16(native_consequence(),target_offset_m=2.0)
    params=dict(
        second_input_s=0.198,live_position=pos(-4.5,-0.019),
        live_probe_session_id=goal.session_id,
        live_probe_seq=68,current_threat_distance_m=2.0,
    )
    if fault=="foreign_session":
        params["live_probe_session_id"]="foreign"
    elif fault=="stale_seq":
        params["live_probe_seq"]=45
    elif fault=="danger":
        params["current_threat_distance_m"]=1.1
    else:
        goal=replace(goal,session_id="foreign")
    with pytest.raises(S49XZGoalRejected):
        plan_third_walk_xz(goal,native_consequence(False),**params)


def test_l0_wait_goal_binds_original_source_once(monkeypatch):
    monkeypatch.setenv("S49_L0_XZ_GOAL_DEV_ONLY","1")
    monkeypatch.setenv("S49_L0_GOAL_WAIT_DEV_ONLY","1")
    h=object.__new__(NormalWorldL0)
    h.session_id="native-same-session"
    h.events=3
    h.action_requests=2
    h._used_action_ids={"native-first","native-second"}
    h._xz_goal_stop=None
    h._s16_stop_source=None
    goal=lock_goal_after_first_s16(native_consequence(),target_offset_m=1.0)
    h.bind_xz_stop_dev(goal=goal,second_action_id="native-second")
    assert h._xz_goal_stop == (goal,"native-second")
    with pytest.raises(NormalActionRejected):
        h.bind_xz_stop_dev(goal=goal,second_action_id="native-second")


def test_real_reviewer_rejects_unproven_native_sources():
    for mode in ("WALK","WAIT"):
        with pytest.raises(ValueError):
            review_native(mode,{"status":"FAIL"})


def test_no_new_issuer_and_source_first_goal_before_second_dispatch():
    runner=Path("adapters/mineflayer/s49_normal_session_real_ci.py").read_text()
    owner=Path("adapters/mineflayer/normal_action.py").read_text()
    assert "locked_before_second_physical_dispatch" in runner
    assert "plan_third_walk_xz(" in runner
    assert "assess_closed_second_xz(" in runner
    assert "host.bind_xz_stop_dev(" in runner
    assert "read_xz_goal(" in owner
    assert "self._xz_goal_stop" in owner
