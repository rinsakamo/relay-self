"""Strict single-episode route memory for L1-style DEV reuse.

A successful *physical* first-World episode supplies relative route offsets.
This is episodic template recall with explicit environmental matching, not
learned geometry, block perception, autonomous exploration or production L1.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from relay_self.goal_detour_dev import L1DetourPlanDev, L1DetourStageDev
from relay_self.goal_navigation import GoalControlRejected, L2GoalProposal
from relay_self.provenance import Provenance


@dataclass(frozen=True, slots=True)
class L1RouteEpisodeDev:
    source_session_id: str
    source_goal_id: str
    source_blocked_action_id: str
    source_blocked_after_seq: int
    original_goal_offset_x: float
    original_goal_offset_z: float
    source_reason: str
    stages: tuple[tuple[str, float, float], ...]
    source_native_actions: int
    source_final_error_m: float
    source_final_tolerance_m: float

    def __post_init__(self) -> None:
        if (
            not isinstance(self.source_session_id,str) or not self.source_session_id
            or not isinstance(self.source_goal_id,str) or not self.source_goal_id
            or not isinstance(self.source_blocked_action_id,str)
            or not self.source_blocked_action_id
            or type(self.source_blocked_after_seq) is not int
            or self.source_blocked_after_seq < 1
            or self.source_reason!="NATIVE_MOTOR_UNDETERMINED_NO_BLOCK_SENSOR"
            or any(type(v) is not float or not math.isfinite(v) for v in (
                self.original_goal_offset_x,self.original_goal_offset_z,
                self.source_final_error_m,self.source_final_tolerance_m,
            ))
            or type(self.source_native_actions) is not int
            or not 3<=self.source_native_actions<=18
            or not 0<=self.source_final_error_m<=self.source_final_tolerance_m<=1
            or not isinstance(self.stages,tuple) or len(self.stages)!=3
            or any(
                not isinstance(s,tuple) or len(s)!=3
                or not isinstance(s[0],str) or not s[0]
                or any(type(v) is not float or not math.isfinite(v) for v in s[1:])
                or abs(s[1])>6 or abs(s[2])>7
                for s in self.stages
            )
            or len({s[0] for s in self.stages})!=3
            or not math.isclose(
                self.stages[-1][1],self.original_goal_offset_x,abs_tol=1e-8,
            )
            or not math.isclose(
                self.stages[-1][2],self.original_goal_offset_z,abs_tol=1e-8,
            )
            or not math.isclose(self.original_goal_offset_x,0.0,abs_tol=1e-8)
            or not math.isclose(self.original_goal_offset_z,4.0,abs_tol=1e-8)
        ):
            raise GoalControlRejected("route memory is not a bounded successful episode")


def select_route_from_episode_dev(
    episode:L1RouteEpisodeDev, original:L2GoalProposal,
    *,start_x:float,start_z:float,
    blocked_action_id:str,blocked_s16_seq:int,
    blocked_reason:str,blocked_terminal:str,
    blocked_consequence:str,provenance:Provenance,
)->L1DetourPlanDev:
    """Require a NEW native uncertain motor and matching XZ goal geometry.

    A transfer is relative to this World origin. The earlier XZ coordinates
    must never become coordinates in the later Minecraft session.
    """
    if (
        not isinstance(episode,L1RouteEpisodeDev)
        or not isinstance(original,L2GoalProposal)
        or not isinstance(provenance,Provenance)
        or original.session_id==episode.source_session_id
        or original.goal_id!=episode.source_goal_id
        or any(type(v) is not float or not math.isfinite(v)
               for v in (start_x,start_z))
        or not math.isclose(
            original.target_x-start_x,episode.original_goal_offset_x,
            abs_tol=1e-8,
        )
        or not math.isclose(
            original.target_z-start_z,episode.original_goal_offset_z,
            abs_tol=1e-8,
        )
        or blocked_reason!="MOTOR_CONSEQUENCE_UNDETERMINED"
        or blocked_terminal!="unknown"
        or blocked_consequence!="undetermined"
        or type(blocked_s16_seq) is not int or blocked_s16_seq<1
        or not isinstance(blocked_action_id,str) or not blocked_action_id
        or not blocked_action_id.endswith("-step-2")
        or provenance.source=="mineflayer"
    ):
        raise GoalControlRejected("no matching native experience for new Goal")
    return L1DetourPlanDev(
        parent=original,
        route_id=f"recalled-{original.goal_id}",
        revision=1,
        source_action_id=blocked_action_id,
        source_s16_seq=blocked_s16_seq,
        reason="NATIVE_MOTOR_UNDETERMINED_NO_BLOCK_SENSOR",
        stages=tuple(
            L1DetourStageDev(
                stage_id=stage_id,
                target_x=float(start_x+offset_x),
                target_z=float(start_z+offset_z),
            )
            for stage_id,offset_x,offset_z in episode.stages
        ),
        provenance=provenance,
    )
