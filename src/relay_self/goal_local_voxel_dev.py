"""DEV observer-local 7x6 local voxel Present and conservative L1 route choice.

This is a small grid of ACTUALLY loaded Mineflayer blocks, not a complete
map, general pathfinding, or a promise that the player's full body fits.
The two bounded 3-stage route templates are evaluated from the grid; no
operator left/right preference enters the selection.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from relay_self.goal_detour_dev import (
    L1DetourPlanDev,
    explicit_l1_detour_dev,
)
from relay_self.goal_navigation import GoalControlRejected, L2GoalProposal
from relay_self.provenance import Provenance
from relay_self.self_world import WorldOrigin, WorldReading

STATUS = frozenset(("CLEAR", "BLOCKED", "UNKNOWN"))


@dataclass(frozen=True, slots=True)
class VoxelColumnDev:
    dx: int
    dz: int
    feet: str
    head: str
    floor: str

    def __post_init__(self) -> None:
        if (
            type(self.dx) is not int or not -3 <= self.dx <= 3
            or type(self.dz) is not int or not 0 <= self.dz <= 5
            or any(value not in STATUS
                   for value in (self.feet,self.head,self.floor))
        ):
            raise GoalControlRejected("voxel column has missing/unknown semantics")


@dataclass(frozen=True, slots=True)
class NativeVoxelPresentDev:
    session_id: str
    native_seq: int
    request_id: str
    origin_x: float
    origin_z: float
    player_y: float
    coverage: str
    cells: tuple[VoxelColumnDev,...]
    provenance: Provenance

    def __post_init__(self) -> None:
        if (
            not isinstance(self.session_id,str) or not self.session_id
            or type(self.native_seq) is not int or self.native_seq<1
            or not isinstance(self.request_id,str) or not self.request_id
            or len(self.request_id)>128
            or any(type(v) is not float or not math.isfinite(v)
                   for v in (self.origin_x,self.origin_z,self.player_y))
            or self.coverage!="mineflayer_loaded_cache_fixed_7x6x3"
            or not isinstance(self.cells,tuple) or len(self.cells)!=42
            or tuple((cell.dx,cell.dz) for cell in self.cells)!=tuple(
                (dx,dz) for dz in range(6) for dx in range(-3,4)
            )
            or any(not isinstance(cell,VoxelColumnDev) for cell in self.cells)
            or self.provenance!=Provenance(
                "mineflayer",f"{self.session_id}:{self.native_seq}",
            )
        ):
            raise GoalControlRejected("incomplete/foreign native voxel Present")

    def observed(self, dx:int, dz:int) -> WorldReading:
        if (
            type(dx) is not int or type(dz) is not int
            or not -3<=dx<=3 or not 0<=dz<=5
        ):
            return WorldReading(WorldOrigin.UNKNOWN,None,(),())
        cell=self.cells[dz*7+dx+3]
        if (cell.dx,cell.dz)!=(dx,dz):
            raise GoalControlRejected("native voxel cell coverage mismatch")
        return WorldReading(
            WorldOrigin.OBSERVED,cell,
            (f"present:{self.session_id}:{self.native_seq}:{self.request_id}:voxel:{dx}:{dz}",),
            (self.provenance,),
        )


@dataclass(frozen=True, slots=True)
class VoxelWaypointChoiceDev:
    status: str
    reason: str
    left_state: str
    right_state: str
    selected_side: str|None
    source_seq: int
    sampled_voxel_columns: int
    plan: L1DetourPlanDev|None


def _corridor_state(present:NativeVoxelPresentDev, side:float) -> str:
    """Conservative point samples on 3 static path segments, <=0.15m apart.

    Absence of a floor, unknown cache or a solid occupied body cell does NOT
    become traversable. No claim about a full 0.6m body envelope is made.
    """
    points=((0.0,0.0),(side,1.1),(side,3.8),(0.0,4.0))
    any_unknown=False
    for (ax,az),(bx,bz) in zip(points,points[1:]):
        distance=math.hypot(bx-ax,bz-az)
        count=max(1,math.ceil(distance/0.15))
        for index in range(count+1):
            t=index/count
            dx=(ax+(bx-ax)*t)
            dz=(az+(bz-az)*t)
            cell_x=math.floor(present.origin_x+dx)-math.floor(present.origin_x)
            cell_z=math.floor(present.origin_z+dz)-math.floor(present.origin_z)
            reading=present.observed(cell_x,cell_z)
            if reading.origin is WorldOrigin.UNKNOWN:
                any_unknown=True
                continue
            column=reading.value
            assert isinstance(column,VoxelColumnDev)
            if (
                column.feet=="BLOCKED" or column.head=="BLOCKED"
                or column.floor=="CLEAR"
            ):
                return "BLOCKED"
            if (
                column.feet=="UNKNOWN" or column.head=="UNKNOWN"
                or column.floor=="UNKNOWN"
            ):
                any_unknown=True
    return "UNKNOWN" if any_unknown else "CLEAR"


def choose_voxel_waypoint_dev(
    present:NativeVoxelPresentDev, parent:L2GoalProposal,
    *,blocked_after_seq:int, blocked_action_id:str,
    provenance:Provenance,
) -> VoxelWaypointChoiceDev:
    if (
        not isinstance(present,NativeVoxelPresentDev)
        or not isinstance(parent,L2GoalProposal)
        or present.session_id!=parent.session_id
        or type(blocked_after_seq) is not int or blocked_after_seq<1
        or present.native_seq<=blocked_after_seq
        or not math.isclose(parent.target_x,present.origin_x,abs_tol=1e-8)
        or not math.isclose(parent.target_z,present.origin_z+4.0,abs_tol=1e-8)
        or not isinstance(blocked_action_id,str) or not blocked_action_id
        or not isinstance(provenance,Provenance)
        or provenance.source=="mineflayer"
    ):
        raise GoalControlRejected("voxel route needs original native blocked S16 lineage")
    left=_corridor_state(present,-2.5)
    right=_corridor_state(present,2.5)
    if (left,right) in (("BLOCKED","CLEAR"),("CLEAR","BLOCKED")):
        side="RIGHT" if right=="CLEAR" else "LEFT"
        plan=explicit_l1_detour_dev(
            parent,start_x=float(present.origin_x),
            start_z=float(present.origin_z),
            blocked_action_id=blocked_action_id,
            blocked_s16_seq=blocked_after_seq,
            provenance=provenance,
            lateral_offset_dev=2.5 if side=="RIGHT" else -2.5,
        )
        return VoxelWaypointChoiceDev(
            "SELECTED","NATIVE_VOXEL_TEMPLATE_SELECTED",
            left,right,side,present.native_seq,42,plan,
        )
    return VoxelWaypointChoiceDev(
        "DEFER","VOXEL_ROUTE_AMBIGUOUS_OR_UNKNOWN",
        left,right,None,present.native_seq,42,None,
    )
