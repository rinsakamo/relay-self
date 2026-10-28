"""Bounded 4-neighbour L1 path search from native observer-local voxel Present.

Grid has 42 candidate XZ cells. Only exact loaded, body/head CLEAR and solid
floor support columns may be entered. A 0.30m avatar radius at cell centers
has at least 0.19m clearance from the XZ cell edge; cardinal moves never cut
diagonal corners. No new movement authority, learning or complete-world claim.
"""
from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass

from relay_self.goal_detour_dev import L1DetourStageDev
from relay_self.goal_local_voxel_dev import NativeVoxelPresentDev, VoxelColumnDev
from relay_self.goal_navigation import (
    GoalControlRejected,
    GoalPurpose,
    L2GoalProposal,
)
from relay_self.provenance import Provenance
from relay_self.self_world import WorldOrigin


@dataclass(frozen=True, slots=True)
class L1GridRoutePlanDev:
    parent: L2GoalProposal
    route_id: str
    revision: int
    source_action_id: str
    source_s16_seq: int
    reason: str
    stages: tuple[L1DetourStageDev,...]
    provenance: Provenance
    source_voxel_seq: int
    source_voxel_request_id: str
    cell_path: tuple[tuple[int,int],...]
    no_diagonal_edges: bool
    body_radius_m: float

    def __post_init__(self) -> None:
        if (
            not isinstance(self.parent,L2GoalProposal)
            or not isinstance(self.route_id,str) or not self.route_id
            or type(self.revision) is not int or self.revision!=1
            or not isinstance(self.source_action_id,str) or not self.source_action_id
            or type(self.source_s16_seq) is not int or self.source_s16_seq<1
            or self.reason!="NATIVE_GRID_SEARCH_AFTER_MOTOR_UNKNOWN"
            or not isinstance(self.provenance,Provenance)
            or self.provenance.source=="mineflayer"
            or type(self.source_voxel_seq) is not int
            or self.source_voxel_seq<=self.source_s16_seq
            or not isinstance(self.source_voxel_request_id,str)
            or not self.source_voxel_request_id
            or self.no_diagonal_edges is not True
            or type(self.body_radius_m) is not float
            or self.body_radius_m!=0.30
            or not isinstance(self.cell_path,tuple)
            or not 2<=len(self.cell_path)<=42
            or any(not isinstance(p,tuple) or len(p)!=2
                   or not all(type(v) is int for v in p)
                   or not -3<=p[0]<=3 or not 0<=p[1]<=5
                   for p in self.cell_path)
            or any(abs(b[0]-a[0])+abs(b[1]-a[1])!=1
                   for a,b in zip(self.cell_path,self.cell_path[1:]))
            or not isinstance(self.stages,tuple)
            or not 1<=len(self.stages)<=12
            or any(not isinstance(s,L1DetourStageDev) for s in self.stages)
            or len({s.stage_id for s in self.stages})!=len(self.stages)
            or not math.isclose(self.stages[-1].target_x,
                                self.parent.target_x,abs_tol=1e-8)
            or not math.isclose(self.stages[-1].target_z,
                                self.parent.target_z,abs_tol=1e-8)
        ):
            raise GoalControlRejected("unbounded/unlinked native grid L1 route")

    def subgoal(self,index:int)->L2GoalProposal:
        if type(index) is not int or not 0<=index<len(self.stages):
            raise GoalControlRejected("invalid source grid route stage")
        stage=self.stages[index]
        return L2GoalProposal(
            goal_id=f"{self.parent.goal_id}-grid-{self.revision}-{stage.stage_id}",
            intent_id=self.parent.intent_id,
            session_id=self.parent.session_id,
            target_x=stage.target_x,target_z=stage.target_z,
            purpose=GoalPurpose.APPROACH,
            minimum_tolerance_m=self.parent.minimum_tolerance_m,
            maximum_tolerance_m=self.parent.maximum_tolerance_m,
            danger_interrupt_m=self.parent.danger_interrupt_m,
            provenance=self.provenance,
        )


@dataclass(frozen=True, slots=True)
class L1GridSearchDecisionDev:
    status: str
    reason: str
    voxel_source_seq: int
    evaluated_columns: int
    visited_cells: int
    chosen_cell_path: tuple[tuple[int,int],...]
    plan: L1GridRoutePlanDev|None


def _walkable(grid:NativeVoxelPresentDev,node:tuple[int,int])->bool:
    reading=grid.observed(*node)
    if reading.origin is not WorldOrigin.OBSERVED:
        return False
    column=reading.value
    if not isinstance(column,VoxelColumnDev):
        return False
    return (
        column.feet=="CLEAR"
        and column.head=="CLEAR"
        and column.floor=="BLOCKED"
    )


def _find_path(
    grid:NativeVoxelPresentDev,start:tuple[int,int],
    end:tuple[int,int],
)->tuple[tuple[tuple[int,int],...],int]:
    if not _walkable(grid,start) or not _walkable(grid,end):
        return (),0
    frontier=deque([start])
    previous={start:None}
    # This fixed neighbour order is deterministic, not L1 prior knowledge of
    # which side was the "correct" route.
    delta=((1,0),(0,1),(-1,0),(0,-1))
    while frontier and len(previous)<=42:
        node=frontier.popleft()
        if node==end:
            break
        for dx,dz in delta:
            candidate=(node[0]+dx,node[1]+dz)
            if candidate in previous or not _walkable(grid,candidate):
                continue
            previous[candidate]=node
            frontier.append(candidate)
    if end not in previous:
        return (),len(previous)
    path=[]
    step=end
    while step is not None:
        path.append(step)
        step=previous[step]
    path.reverse()
    return tuple(path),len(previous)


def _turns(path:tuple[tuple[int,int],...])->tuple[tuple[int,int],...]:
    result=[]
    for i in range(1,len(path)-1):
        prior=path[i-1]
        here=path[i]
        nxt=path[i+1]
        if (here[0]-prior[0],here[1]-prior[1]) != (
            nxt[0]-here[0],nxt[1]-here[1]
        ):
            result.append(here)
    result.append(path[-1])
    return tuple(result)


def choose_grid_route_dev(
    present:NativeVoxelPresentDev,parent:L2GoalProposal,
    *,blocked_after_seq:int,blocked_action_id:str,
    provenance:Provenance,
)->L1GridSearchDecisionDev:
    if (
        not isinstance(present,NativeVoxelPresentDev)
        or not isinstance(parent,L2GoalProposal)
        or present.session_id!=parent.session_id
        or type(blocked_after_seq) is not int or blocked_after_seq<1
        or present.native_seq<=blocked_after_seq
        or not isinstance(blocked_action_id,str) or not blocked_action_id
        or not isinstance(provenance,Provenance)
        or provenance.source=="mineflayer"
        or not math.isclose(parent.target_x,present.origin_x,abs_tol=1e-8)
        or not math.isclose(parent.target_z,present.origin_z+4.0,abs_tol=1e-8)
        or abs(present.origin_x-(math.floor(present.origin_x)+0.5))>0.03
        or abs(present.origin_z-(math.floor(present.origin_z)+0.5))>0.03
    ):
        raise GoalControlRejected("native grid search requires aligned fresh blocked S16")
    nearest=(round(present.player_x-present.origin_x),
             round(present.player_z-present.origin_z))
    if (
        not -3<=nearest[0]<=3 or not 0<=nearest[1]<=5
        or math.hypot(
            present.player_x-(present.origin_x+nearest[0]),
            present.player_z-(present.origin_z+nearest[1]),
        )>0.45
    ):
        raise GoalControlRejected("native body outside centered local voxel grid")
    goal=(0,4)
    path,visited=_find_path(present,nearest,goal)
    if not path or len(path)<2:
        return L1GridSearchDecisionDev(
            "DEFER","NO_OBSERVED_BODY_SAFE_GRID_ROUTE",
            present.native_seq,42,visited,(),None,
        )
    corners=_turns(path)
    if not 1<=len(corners)<=12:
        return L1GridSearchDecisionDev(
            "DEFER","GRID_ROUTE_EXCEEDS_WAYPOINT_BUDGET",
            present.native_seq,42,visited,path,None,
        )
    stages=tuple(
        L1DetourStageDev(
            stage_id=f"grid-turn-{i}",
            target_x=float(present.origin_x+x),
            target_z=float(present.origin_z+z),
        ) for i,(x,z) in enumerate(corners)
    )
    plan=L1GridRoutePlanDev(
        parent=parent,route_id=f"native-grid-{parent.goal_id}",
        revision=1,source_action_id=blocked_action_id,
        source_s16_seq=blocked_after_seq,
        reason="NATIVE_GRID_SEARCH_AFTER_MOTOR_UNKNOWN",
        stages=stages,provenance=provenance,
        source_voxel_seq=present.native_seq,
        source_voxel_request_id=present.request_id,
        cell_path=path,no_diagonal_edges=True,
        body_radius_m=0.30,
    )
    return L1GridSearchDecisionDev(
        "SELECTED","BFS_CARDINAL_NATIVE_OBSERVED_GRID",
        present.native_seq,42,visited,path,plan,
    )
