"""Unit tests: L2/L1 goal contract and L0 motor loop (no zombie trigger)."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from adapters.mineflayer.python_protocol import MineflayerObservation, MineflayerPosition
from relay_self.goal_navigation import (
    GoalControlRejected,
    GoalDecisionKind,
    GoalPurpose,
    L2GoalProposal,
    ObservedGoalL0,
    compile_l1_goal_dev,
)
from relay_self.provenance import Provenance


def proposal(*,target_z=2.6,purpose=GoalPurpose.APPROACH):
    return L2GoalProposal(
        goal_id="g1",intent_id="approach-g1",session_id="native-session",
        target_x=0.0,target_z=target_z,purpose=purpose,
        minimum_tolerance_m=0.30,maximum_tolerance_m=0.55,
        danger_interrupt_m=1.5,provenance=Provenance("l2-dev","goal"),
    )


def directive(goal=None):
    return compile_l1_goal_dev(
        goal or proposal(),current_x=0.0,current_z=0.0,
        provenance=Provenance("l1-dev","precision"),
    )


def native(seq,x=0.0,z=0.0, *, session="native-session",threat=None):
    reading=Mock(spec=MineflayerObservation)
    reading.seq=seq
    reading.session_id=session
    reading.kind="probe"
    reading.request_id=f"native-observe-{seq}"
    reading.provenance=Provenance("mineflayer",f"native-{seq}")
    reading.snapshot=SimpleNamespace(
        position=MineflayerPosition(x=x,y=-60.0,z=z),
        nearby_entities_coverage=SimpleNamespace(truncated=False),
        nearby_entities=(() if threat is None else
                         (SimpleNamespace(name="zombie",distance=threat),)),
    )
    return reading


def test_l1_precision_provided_before_l0_motion_and_changes_with_purpose():
    loose=directive()
    assert loose.tolerance_m == pytest.approx(0.364)
    assert loose.proposal.target_z == 2.6
    assert loose.max_actions == 6
    finer=directive(proposal(purpose=GoalPurpose.INTERACT))
    assert finer.tolerance_m == 0.30


def test_l0_continues_on_native_probes_without_new_zombie_events():
    l0=ObservedGoalL0(directive(),start_x=0.0,start_z=0.0)
    first=l0.decide(native(10))
    assert first.kind is GoalDecisionKind.MOVE
    assert first.input_duration_s is not None
    l0.admitted(first)
    following=l0.decide(native(20,z=0.7))
    assert following.kind is GoalDecisionKind.MOVE
    assert l0.actions == 1


def test_l0_reaches_only_after_second_stable_native_observation():
    l0=ObservedGoalL0(directive(),start_x=0.0,start_z=0.0)
    assert l0.decide(native(10,z=2.36)).kind is GoalDecisionKind.WAIT_VERIFY
    assert l0.decide(native(20,z=2.37)).kind is GoalDecisionKind.REACHED
    with pytest.raises(GoalControlRejected):
        l0.decide(native(30,z=2.37))


def test_l0_does_not_assume_arrival_if_world_drifts_after_clear():
    l0=ObservedGoalL0(directive(),start_x=0.0,start_z=0.0)
    assert l0.decide(native(10,z=2.38)).kind is GoalDecisionKind.WAIT_VERIFY
    assert l0.decide(native(11,z=2.8)).kind is GoalDecisionKind.WAIT_VERIFY
    assert l0.decide(native(12,z=2.81)).kind is GoalDecisionKind.REACHED


def test_l0_overshoot_and_lateral_drift_request_upper_layer_replan():
    for x,z in ((0.0,3.8),(0.5,0.6)):
        l0=ObservedGoalL0(directive(),start_x=0.0,start_z=0.0)
        assert l0.decide(native(10,x=x,z=z)).kind is GoalDecisionKind.NEEDS_REPLAN
        assert l0.actions == 0


@pytest.mark.parametrize("fault",["old_seq","foreign_session","truncated","unknown_kind"])
def test_stale_and_foreign_world_probe_fail_closed(fault):
    l0=ObservedGoalL0(directive(),start_x=0.0,start_z=0.0)
    l0.decide(native(10))
    r=native(11)
    if fault=="old_seq":
        r.seq=10
    elif fault=="foreign_session":
        r.session_id="foreign"
    elif fault=="truncated":
        r.snapshot.nearby_entities_coverage.truncated=True
    else:
        r.kind="entities"
    with pytest.raises(GoalControlRejected):
        l0.decide(r)


def test_threat_interrupts_even_if_goal_position_met():
    l0=ObservedGoalL0(directive(),start_x=0.0,start_z=0.0)
    result=l0.decide(native(10,z=2.6,threat=1.0))
    assert result.kind is GoalDecisionKind.INTERRUPT


def test_l0_nonprogress_and_action_capacity_escalate_to_l1_l2():
    l0=ObservedGoalL0(directive(),start_x=0.0,start_z=0.0)
    for seq,z in ((10,0),(20,0.005),(30,0.009)):
        c=l0.decide(native(seq,z=z))
        if seq!=30:
            l0.admitted(c)
    assert c.kind is GoalDecisionKind.NEEDS_REPLAN
    assert c.reason=="NONPROGRESS_WORLD"


def test_goal_invalid_authority_bounds():
    with pytest.raises(GoalControlRejected):
        proposal(target_z=float("nan"))
    with pytest.raises(GoalControlRejected):
        L2GoalProposal(
            goal_id="g",intent_id="g",session_id="s",
            target_x=0,target_z=2,purpose=GoalPurpose.APPROACH,
            minimum_tolerance_m=0.01,maximum_tolerance_m=1.2,
            danger_interrupt_m=0.1,
            provenance=Provenance("l2-dev","bad"),
        )
