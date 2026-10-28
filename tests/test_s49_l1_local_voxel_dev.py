"""Original bounded voxel cache and conservative L1 waypoint templates."""
from __future__ import annotations

import json
from dataclasses import replace

import pytest

from adapters.mineflayer.python_protocol import (
    MineflayerAdapterProtocolError,
    MineflayerLocalVoxelsDev,
    encode_local_voxels_dev,
    parse_mineflayer_line,
)
from relay_self.goal_local_voxel_dev import (
    NativeVoxelPresentDev,
    VoxelColumnDev,
    choose_voxel_waypoint_dev,
)
from relay_self.goal_navigation import (
    GoalControlRejected,
    GoalPurpose,
    L2GoalProposal,
)
from relay_self.provenance import Provenance
from relay_self.self_world import WorldOrigin


def grid(*,left_block=True,right_block=False,unknown=False,
         session="real-new-world",seq=34):
    cells=[]
    for dz in range(6):
        for dx in range(-3,4):
            feet="CLEAR"
            if dz==2 and -1<=dx<=1:
                feet="BLOCKED"
            if left_block and -3<=dx<=-2 and 1<=dz<=4:
                feet="BLOCKED"
            if right_block and 2<=dx<=3 and 1<=dz<=4:
                feet="BLOCKED"
            if unknown and dx==3 and dz==3:
                feet="UNKNOWN"
            cells.append(VoxelColumnDev(
                dx=dx,dz=dz,feet=feet,head="CLEAR",floor="BLOCKED",
            ))
    return NativeVoxelPresentDev(
        session_id=session,native_seq=seq,
        request_id=f"new-route-{seq}",
        origin_x=0.5,origin_z=10.5,
        player_x=0.5,player_z=11.5,player_y=64.0,
        coverage="mineflayer_loaded_cache_fixed_7x6x3",
        cells=tuple(cells),
        provenance=Provenance("mineflayer",f"{session}:{seq}"),
    )


def parent(session="real-new-world"):
    return L2GoalProposal(
        goal_id="approach-demo",intent_id="goal-navigate",
        session_id=session,target_x=0.5,target_z=14.5,
        purpose=GoalPurpose.APPROACH,
        minimum_tolerance_m=0.30,maximum_tolerance_m=0.55,
        danger_interrupt_m=1.5,
        provenance=Provenance("test-l2","current"),
    )


def decide(present):
    return choose_voxel_waypoint_dev(
        present,parent(),blocked_after_seq=33,
        blocked_action_id="goal-approach-demo-step-2",
        provenance=Provenance("test-l1","new-voxel"),
    )


def test_actual_present_right_route_generated_from_bounded_voxels():
    present=grid()
    reading=present.observed(3,2)
    assert reading.origin is WorldOrigin.OBSERVED
    assert reading.value.feet=="CLEAR"
    assert reading.source_refs==(
        f"present:{present.session_id}:{present.native_seq}:{present.request_id}:voxel:3:2",
    )
    assert present.observed(8,2).origin is WorldOrigin.UNKNOWN
    choice=decide(present)
    assert (choice.status,choice.reason)==(
        "SELECTED","NATIVE_VOXEL_TEMPLATE_SELECTED",
    )
    assert (choice.left_state,choice.right_state)==("BLOCKED","CLEAR")
    assert choice.selected_side=="RIGHT"
    assert [(stage.target_x,stage.target_z) for stage in choice.plan.stages]==[
        (3.0,11.6),(3.0,14.3),(0.5,14.5),
    ]
    assert choice.plan.source_s16_seq==33
    assert choice.plan.parent.goal_id=="approach-demo"


def test_opposite_voxels_select_left_new_waypoints():
    choice=decide(grid(left_block=False,right_block=True))
    assert (choice.left_state,choice.right_state)==("CLEAR","BLOCKED")
    assert choice.selected_side=="LEFT"
    assert choice.plan.stages[0].target_x==-2.0
    assert choice.plan.stages[1].target_x==-2.0
    assert choice.plan.stages[-1].target_x==0.5


@pytest.mark.parametrize("params",[
    {"left_block":False,"right_block":False},
    {"left_block":True,"right_block":True},
    {"left_block":True,"right_block":False,"unknown":True},
])
def test_ambiguous_blocked_and_unknown_not_interpreted_as_clear(params):
    choice=decide(grid(**params))
    assert choice.status=="DEFER"
    assert choice.plan is None


def test_floor_not_supported_or_body_head_blocked_defer():
    raw=grid()
    cells=list(raw.cells)
    ix=3*7+3+3
    cells[ix]=replace(cells[ix],floor="CLEAR")
    result=decide(replace(raw,cells=tuple(cells)))
    assert result.status=="DEFER"
    cells=list(raw.cells)
    cells[ix]=replace(cells[ix],head="BLOCKED")
    assert decide(replace(raw,cells=tuple(cells))).status=="DEFER"


@pytest.mark.parametrize("change",[
    {"session_id":"foreign"},
    {"native_seq":32},
    {"origin_x":2.5},
    {"origin_z":15.5},
])
def test_foreign_stale_or_shifted_present_never_selected(change):
    present=grid()
    if change.get("session_id")=="foreign":
        with pytest.raises(GoalControlRejected):
            replace(present,**change)
    else:
        with pytest.raises(GoalControlRejected):
            decide(replace(present,**change))


def test_reordered_missing_cells_rejected():
    raw=grid()
    with pytest.raises(GoalControlRejected):
        replace(raw,cells=raw.cells[:-1])
    with pytest.raises(GoalControlRejected):
        replace(raw,cells=raw.cells[::-1])


def test_native_voxel_packet_strict_exact_dimensions_and_cache_source():
    raw=grid()
    packet={
        "type":"local_voxels_dev","session_id":raw.session_id,
        "seq":raw.native_seq,"request_id":raw.request_id,
        "origin_x":raw.origin_x,"origin_z":raw.origin_z,
        "player_y":raw.player_y,
        "player_x":raw.player_x,"player_z":raw.player_z,
        "coverage":"mineflayer_loaded_cache_fixed_7x6x3",
        "x_min":-3,"x_max":3,"z_min":0,"z_max":5,
        "unknown_is_not_clear":True,
        "cells":[
            {"dx":c.dx,"dz":c.dz,"feet":c.feet,
             "head":c.head,"floor":c.floor} for c in raw.cells
        ],
    }
    decoded=parse_mineflayer_line(json.dumps(packet))
    assert isinstance(decoded,MineflayerLocalVoxelsDev)
    assert len(decoded.cells)==42
    assert json.loads(encode_local_voxels_dev(
        "request",origin_x=0.5,origin_z=10.5,
    ))=={
        "type":"observe_local_voxels_dev","request_id":"request",
        "origin_x":0.5,"origin_z":10.5,
    }
    for bad in (
        {**packet,"coverage":"full-world"},
        {**packet,"x_max":10},
        {**packet,"unknown_is_not_clear":False},
        {**packet,"cells":packet["cells"][:-1]},
        {**packet,"cells":packet["cells"][::-1]},
        {**packet,"additional":"fake-source"},
    ):
        with pytest.raises(MineflayerAdapterProtocolError):
            parse_mineflayer_line(json.dumps(bad))
