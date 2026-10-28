"""L1 explicit detour revision and same original S49 Action owner refusal."""
from __future__ import annotations

import math
from dataclasses import replace
from pathlib import Path

import pytest

from relay_self.goal_detour_dev import (
    L1DetourStageDev,
    explicit_l1_detour_dev,
)
from relay_self.goal_navigation import (
    GoalControlRejected,
    GoalPurpose,
    L2GoalProposal,
)
from relay_self.provenance import Provenance


def parent():
    return L2GoalProposal(
        goal_id="original",intent_id="intent-goal",session_id="native-session",
        target_x=0.5,target_z=14.5,purpose=GoalPurpose.APPROACH,
        minimum_tolerance_m=0.30,maximum_tolerance_m=0.55,
        danger_interrupt_m=1.5,provenance=Provenance("dev-l2","original"),
    )


def route():
    return explicit_l1_detour_dev(
        parent(),start_x=0.5,start_z=10.5,
        blocked_action_id="original-unknown-2",blocked_s16_seq=31,
        provenance=Provenance("dev-l1","operator-route"),
    )


def test_detour_preserves_parent_goal_and_monotonic_revision():
    p=route()
    assert p.revision==1
    assert p.source_action_id=="original-unknown-2"
    assert [s.stage_id for s in p.stages]==[
        "lateral-before-wall","past-wall","original-destination",
    ]
    assert [(s.target_x,s.target_z) for s in p.stages]==[
        (3.0,11.6),(3.0,14.3),(0.5,14.5),
    ]
    assert p.subgoal(0).goal_id!=p.parent.goal_id
    assert p.subgoal(1).goal_id!=p.subgoal(0).goal_id
    assert p.subgoal(2).goal_id!=p.parent.goal_id
    assert p.subgoal(2).target_x==p.parent.target_x
    assert p.subgoal(2).target_z==p.parent.target_z
    assert all(
        s.session_id==p.parent.session_id and s.intent_id==p.parent.intent_id
        for s in (p.subgoal(0),p.subgoal(1),p.subgoal(2))
    )


@pytest.mark.parametrize("mutation",[
    lambda p:replace(p,revision=0),
    lambda p:replace(p,source_action_id=""),
    lambda p:replace(p,source_s16_seq=-1),
    lambda p:replace(p,reason="BLOCK_DETECTED_BY_SELF"),
    lambda p:replace(p,stages=p.stages[:2]),
    lambda p:replace(p,stages=p.stages[:2]+(
        L1DetourStageDev("not-parent",3.0,15.2),)),
    lambda p:replace(p,stages=(p.stages[0],p.stages[0],p.stages[2])),
])
def test_invalid_l1_detour_lineage_fails_closed(mutation):
    with pytest.raises(GoalControlRejected):
        mutation(route())


def test_no_fake_block_observation_and_no_new_motor_issuer():
    runner=Path("adapters/mineflayer/s49_goal_loop_real_dev.py").read_text()
    owner=Path("adapters/mineflayer/s49_goal_executor_dev.py").read_text()
    loop=Path("adapters/mineflayer/s49_goal_waypoint_route_dev.py").read_text()
    assert "explicit_l1_detour_dev(" in runner
    assert "follow_l1_detour_dev(" in runner
    assert "executor.adopt_waypoint_dev(" in loop
    assert "executor.execute_goal_step(" in loop
    assert "self.supervisor.open_actions" in owner
    assert "ActionState.UNKNOWN" in owner
    assert "ActionState.OUTCOME" in owner
    assert '"obstacle_block_perception_attested":False' in loop
    assert "client_obstacle_block_detection_attested" in runner


def test_waypoint_and_heading_are_bounded():
    p=route()
    for i in range(3):
        g=p.subgoal(i)
        assert math.isfinite(g.target_x) and math.isfinite(g.target_z)
    with pytest.raises(GoalControlRejected):
        p.subgoal(3)
    with pytest.raises(GoalControlRejected):
        p.subgoal(-1)
    with pytest.raises(GoalControlRejected):
        explicit_l1_detour_dev(
            parent(),start_x=1.5,start_z=10.5,
            blocked_action_id="blocked",blocked_s16_seq=31,
            provenance=Provenance("dev","bad-original-anchoring"),
        )
