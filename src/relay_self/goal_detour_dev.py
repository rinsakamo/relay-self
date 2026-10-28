"""DEV-only upper-L1 waypoint detour of an immutable original L2 goal.

The operator supplies waypoints AFTER a closed blocked native Action. This
is not Minecraft block perception, a learned L1, or real L2 replanning.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from relay_self.goal_navigation import (
    GoalControlRejected, GoalPurpose, L2GoalProposal,
)
from relay_self.provenance import Provenance


@dataclass(frozen=True, slots=True)
class L1DetourStageDev:
    stage_id: str
    target_x: float
    target_z: float

    def __post_init__(self) -> None:
        if (
            not isinstance(self.stage_id,str) or not self.stage_id
            or any(type(v) is not float or not math.isfinite(v)
                   for v in (self.target_x,self.target_z))
        ):
            raise GoalControlRejected("bounded finite L1 waypoint required")


@dataclass(frozen=True, slots=True)
class L1DetourPlanDev:
    parent: L2GoalProposal
    route_id: str
    revision: int
    source_action_id: str
    source_s16_seq: int
    reason: str
    stages: tuple[L1DetourStageDev,...]
    provenance: Provenance

    def __post_init__(self) -> None:
        if (
            not isinstance(self.parent,L2GoalProposal)
            or type(self.revision) is not int or self.revision!=1
            or not isinstance(self.route_id,str) or not self.route_id
            or not isinstance(self.source_action_id,str) or not self.source_action_id
            or type(self.source_s16_seq) is not int or self.source_s16_seq<1
            or self.reason!="NATIVE_MOTOR_UNDETERMINED_NO_BLOCK_SENSOR"
            or not isinstance(self.provenance,Provenance)
            or self.provenance.source=="mineflayer"
            or not isinstance(self.stages,tuple) or len(self.stages)!=3
            or any(not isinstance(s,L1DetourStageDev) for s in self.stages)
            or len({s.stage_id for s in self.stages})!=3
            or not math.isclose(
                self.stages[-1].target_x,self.parent.target_x,abs_tol=1e-9,
            )
            or not math.isclose(
                self.stages[-1].target_z,self.parent.target_z,abs_tol=1e-9,
            )
        ):
            raise GoalControlRejected("L1 detour requires lineage and parent restoration")

    def subgoal(self, index:int) -> L2GoalProposal:
        if type(index) is not int or not 0<=index<len(self.stages):
            raise GoalControlRejected("invalid L1 route stage")
        waypoint=self.stages[index]
        return L2GoalProposal(
            goal_id=f"{self.parent.goal_id}-route-{self.revision}-{waypoint.stage_id}",
            intent_id=self.parent.intent_id,
            session_id=self.parent.session_id,
            target_x=waypoint.target_x,
            target_z=waypoint.target_z,
            purpose=GoalPurpose.APPROACH,
            minimum_tolerance_m=self.parent.minimum_tolerance_m,
            maximum_tolerance_m=self.parent.maximum_tolerance_m,
            danger_interrupt_m=self.parent.danger_interrupt_m,
            provenance=self.provenance,
        )


def explicit_l1_detour_dev(
    original:L2GoalProposal, *,start_x:float,start_z:float,
    blocked_action_id:str,blocked_s16_seq:int,
    provenance:Provenance,
) -> L1DetourPlanDev:
    """The DEV operator supplies geometry; no world-block sensor is inferred."""
    if (
        not isinstance(original,L2GoalProposal)
        or type(start_x) is not float or not math.isfinite(start_x)
        or type(start_z) is not float or not math.isfinite(start_z)
        or not math.isclose(original.target_x,start_x,abs_tol=1e-9)
        or not math.isclose(original.target_z,start_z+4.0,abs_tol=1e-9)
    ):
        raise GoalControlRejected("fixed two-waypoint DEV bypass geometry only")
    return L1DetourPlanDev(
        parent=original,route_id=f"detour-{original.goal_id}",
        revision=1,source_action_id=blocked_action_id,
        source_s16_seq=blocked_s16_seq,
        reason="NATIVE_MOTOR_UNDETERMINED_NO_BLOCK_SENSOR",
        stages=(
            L1DetourStageDev("lateral-before-wall",start_x+2.5,start_z+1.1),
            L1DetourStageDev("past-wall",start_x+2.5,start_z+3.8),
            L1DetourStageDev("original-destination",start_x,start_z+4.0),
        ),
        provenance=provenance,
    )
