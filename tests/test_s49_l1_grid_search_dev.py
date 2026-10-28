"""DEV bounded local BFS route planning from exact native voxel grid."""
from __future__ import annotations

from dataclasses import replace

import pytest

from relay_self.goal_grid_search_dev import (
    L1GridRoutePlanDev,
    choose_grid_route_dev,
)
from relay_self.goal_local_voxel_dev import NativeVoxelPresentDev
from relay_self.goal_navigation import (
    GoalControlRejected,
    GoalPurpose,
    L2GoalProposal,
)
from relay_self.provenance import Provenance
from test_s49_l1_local_voxel_dev import grid


def _goal(session="real-new-world"):
    return L2GoalProposal(
        goal_id="approach-demo",intent_id="goal-navigate",
        session_id=session,target_x=0.5,target_z=14.5,
        purpose=GoalPurpose.APPROACH,
        minimum_tolerance_m=0.3,maximum_tolerance_m=0.55,
        danger_interrupt_m=1.5,
        provenance=Provenance("test-L2","original-goal"),
    )


def _plan(visible:NativeVoxelPresentDev):
    return choose_grid_route_dev(
        visible,_goal(),blocked_after_seq=33,
        blocked_action_id="original-goal-action-step-2",
        provenance=Provenance("test-L1","observed-grid-bfs"),
    )


def test_cardinal_grid_search_from_new_native_position_right_side():
    decision=_plan(grid(left_block=True))
    assert decision.status=="SELECTED"
    assert decision.reason=="BFS_CARDINAL_NATIVE_OBSERVED_GRID"
    assert decision.evaluated_columns==42
    assert decision.visited_cells<=42
    assert isinstance(decision.plan,L1GridRoutePlanDev)
    path=decision.chosen_cell_path
    assert path[0]==(0,1)
    assert path[-1]==(0,4)
    assert all(abs(a[0]-b[0])+abs(a[1]-b[1])==1
               for a,b in zip(path,path[1:]))
    assert any(x>=2 for x,z in path)
    assert all(x>=0 for x,z in path)
    assert decision.plan.source_action_id=="original-goal-action-step-2"
    assert decision.plan.source_s16_seq==33
    assert len(decision.plan.stages)>=3
    assert decision.plan.stages[-1].target_x==0.5
    assert decision.plan.stages[-1].target_z==14.5
    assert decision.plan.subgoal(0).session_id=="real-new-world"


def test_opposite_obstacles_choose_left_without_predeclared_sides():
    decision=_plan(grid(left_block=False,right_block=True))
    assert decision.status=="SELECTED"
    assert any(x<=-2 for x,z in decision.chosen_cell_path)
    assert all(x<=0 for x,z in decision.chosen_cell_path)
    assert decision.plan.stages[-1].target_z==14.5


def test_no_path_with_two_blocked_side_corridors_defers():
    decision=_plan(grid(left_block=True,right_block=True))
    assert decision.status=="DEFER"
    assert decision.reason=="NO_OBSERVED_BODY_SAFE_GRID_ROUTE"
    assert decision.plan is None
    assert not decision.chosen_cell_path


def test_without_obstacle_search_has_straight_cardinal_route():
    raw=grid(left_block=False,right_block=False)
    changed=tuple(
        replace(c,feet="CLEAR") if c.dz==2 and -1<=c.dx<=1 else c
        for c in raw.cells
    )
    result=_plan(replace(raw,cells=changed))
    assert result.status=="SELECTED"
    assert all(x==0 for x,z in result.chosen_cell_path)
    assert result.plan.stages[-1].target_z==14.5


def test_unknown_and_missing_floor_are_not_walkable():
    visible=grid(left_block=True,right_block=False)
    changed=tuple(
        replace(c,feet="UNKNOWN")
        if c.dx>=2 else c for c in visible.cells
    )
    assert _plan(replace(visible,cells=changed)).status=="DEFER"
    changed=tuple(
        replace(c,floor="CLEAR")
        if c.dx>=2 else c for c in visible.cells
    )
    assert _plan(replace(visible,cells=changed)).status=="DEFER"


def test_incomplete_diagonal_not_connected_by_corner_cut():
    raw=grid(left_block=False,right_block=False)
    all_blocked=tuple(replace(c,feet="BLOCKED") for c in raw.cells)
    only=((0,1),(1,2),(0,4))
    changed=tuple(replace(c,feet="CLEAR") if (c.dx,c.dz) in only
                  else c for c in all_blocked)
    assert _plan(replace(raw,cells=changed)).status=="DEFER"


@pytest.mark.parametrize("changes",[
    {"session_id":"different-session"},
    {"native_seq":32},
    {"origin_x":0.0},
    {"origin_z":11.0},
    {"player_x":5.5},
    {"player_z":15.7},
])
def test_foreign_stale_unaligned_or_outside_native_grid_fails_closed(changes):
    visible=grid(left_block=True)
    with pytest.raises(GoalControlRejected):
        _plan(replace(visible,**changes))


def test_attested_grid_route_guard_against_reordered_or_diagonal_edges():
    chosen=_plan(grid()).plan
    assert chosen is not None
    with pytest.raises(GoalControlRejected):
        replace(chosen,cell_path=((0,1),(1,2),(0,4)))
    with pytest.raises(GoalControlRejected):
        replace(chosen,source_voxel_seq=33)
    with pytest.raises(GoalControlRejected):
        replace(chosen,stages=chosen.stages[:-1])
    with pytest.raises(GoalControlRejected):
        chosen.subgoal(len(chosen.stages))


def test_original_owner_and_waypoint_runner_share_one_source():
    from pathlib import Path

    owner=Path("adapters/mineflayer/s49_goal_executor_dev.py").read_text()
    runner=Path("adapters/mineflayer/s49_goal_waypoint_route_dev.py").read_text()
    loop=Path("adapters/mineflayer/s49_goal_loop_real_dev.py").read_text()
    assert "S49_L1_GRID_SEARCH_DEV_ONLY" in owner
    assert "self.supervisor.open_actions" in owner
    assert "ActionState.UNKNOWN" in owner
    assert "L1GridRoutePlanDev" in runner
    assert "range(len(plan.stages))" in runner
    assert "choose_grid_route_dev(" in loop
    assert "follow_l1_detour_dev(" in loop
