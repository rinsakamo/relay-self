"""G4 observed-distance gait choice: body limits, precision and no new issuer."""
import asyncio
from dataclasses import replace

import pytest

from adapters.mineflayer.g4_observed_gait_choice_dev import (
    choose_g4_observed_gait_dev,
)
from adapters.mineflayer.normal_action import NormalActionRejected
from adapters.mineflayer.s49_goal_executor_dev import S49GoalExecutorDev
from experiments.fatigue_p1 import FatigueProfile, initial_state
from relay_self.goal_navigation import (
    GoalDecisionKind, GoalPurpose, L0GoalDecision, L1GoalDirective,
    L2GoalProposal,
)
from relay_self.provenance import Provenance


SID = "g4-dev-session"


def policy(error, *, tol=.4, action=1, fatigue=0., energy=12.,
           threats=False):
    proposal=L2GoalProposal(
        "g4", "goal", SID, 0., 4., GoalPurpose.APPROACH,
        .30,.55,1.5,Provenance("l2-g4","proposal"),
    )
    directive=L1GoalDirective(
        proposal,float(tol),6,18,Provenance("l1-g4","tolerance"),
    )
    choice=L0GoalDecision(
        GoalDecisionKind.MOVE,action*3,0.,4.-error,float(error),
        float(error),0.,.35,"OBSERVED_GOAL_DISTANCE",
    )
    profile=FatigueProfile(enabled=True)
    state=initial_state(profile,SID,world_tick=action)
    state=replace(state,fatigue=fatigue*profile.capacity)
    return choose_g4_observed_gait_dev(
        choice,directive,action_index=action,p1_profile=profile,
        p1_state=state,m0_energy=energy,threats_present=threats,
    )


def test_g4_far_first_action_dash_when_p1_and_m0_permit():
    c=policy(4.)
    assert c.mode=="DASH"
    assert c.estimated_dash_power==pytest.approx(1.)
    assert c.duration_s>=.1 and c.duration_s<=.35
    assert c.tolerance_m==.4
    assert c.source_seq==3
    assert c.claimed_applied_gait is False and c.qualified is False


@pytest.mark.parametrize("error,action,mode", [
    (3.2,2,"RUN"),
    (1.7,2,"JOG"),
    (0.7,3,"WALK"),
])
def test_g4_observed_clearance_changes_physical_requested_mode(error,action,mode):
    c=policy(error,action=action)
    assert c.mode==mode
    assert .1<=c.duration_s<=.35
    assert c.remaining_clearance_m==pytest.approx(error-.4)


@pytest.mark.parametrize("fatigue,energy,mode", [
    (.95,12.,"WALK"),
    (.80,12.,"JOG"),
    (.10,.07,"WALK"),
    (.10,.20,"JOG"),
])
def test_g4_single_p1_m0_limits_override_coarse_speed(fatigue,energy,mode):
    assert policy(4.,fatigue=fatigue,energy=energy).mode==mode


def test_g4_no_motion_from_goal_tolerance(monkeypatch):
    with pytest.raises(ValueError,match="inside L1 tolerance"):
        policy(.35)
    with pytest.raises(ValueError,match="positive forward"):
        policy(4.,threats=True)


def test_g4_action_gates_reject_without_original_t2_owner(monkeypatch):
    monkeypatch.setenv("S49_G4_OBSERVED_GAIT_DEV_ONLY","1")
    monkeypatch.setenv("S49_L1_G1_OBSERVATION_DEV_ONLY","1")
    monkeypatch.setenv("S49_SPRINT_MOTOR_DEV_ONLY","1")
    executor=object.__new__(S49GoalExecutorDev)
    executor._t2_boundary_dev=None
    with pytest.raises(NormalActionRejected,match="G4 mode requires"):
        asyncio.run(executor.execute_goal_step(
            None,directive=None,decision=None,probe=None,
            propose=None,issue=None,g4_mode_dev="DASH",
        ))


def test_g4_unknown_motor_mode_refused_before_io(monkeypatch):
    monkeypatch.setenv("S49_G4_OBSERVED_GAIT_DEV_ONLY","1")
    executor=object.__new__(S49GoalExecutorDev)
    with pytest.raises(NormalActionRejected,match="G4 mode requires"):
        asyncio.run(executor.execute_goal_step(
            None,directive=None,decision=None,probe=None,
            propose=None,issue=None,g4_mode_dev="TELEPORT",
        ))
