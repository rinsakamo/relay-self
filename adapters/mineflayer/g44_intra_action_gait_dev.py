"""G4.4 DEV observed, source-correlated in-place gait transitions.

Transitions do not issue an S49 Action. An original S15 dispatcher checks
the original native probe, sends one tightly ordered sub-effect and waits
for its native typed ACK before another probe. L0 REACHED remains downstream.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from relay_self.goal_navigation import L1GoalDirective


@dataclass(frozen=True, slots=True)
class G44TransitionDecisionDev:
    action_id: str
    source_seq: int
    from_mode: str
    clearance_m: float
    target_mode: str | None
    reason: str
    applied_attested: bool = False
    paper_world_tick_gait_attested: bool = False
    reached_attested: bool = False


def decide_g44_intra_action_gait_dev(
    directive:L1GoalDirective,*,action_id:str,mode:str,
    session_id:str,source_seq:int,request_id:str,source:str,
    previous_seq:int,x:float,z:float,truncated:bool,danger_present:bool,
)->G44TransitionDecisionDev:
    if (
        not isinstance(directive,L1GoalDirective)
        or type(action_id) is not str or not action_id.startswith("goal-")
        or type(mode) is not str or mode not in ("RUN","JOG","WALK")
        or session_id!=directive.proposal.session_id
        or type(source_seq) is not int or source_seq<=previous_seq
        or type(previous_seq) is not int or previous_seq<0
        or type(request_id) is not str
        or not request_id.startswith(action_id+"-inflight-")
        or source!="mineflayer"
        or type(truncated) is not bool or truncated
        or type(danger_present) is not bool or danger_present
        or any(type(v) not in (float,int) or not math.isfinite(v)
               for v in (x,z))
    ):
        raise ValueError("G4.4 refuses stale/foreign/danger native gait")
    goal=directive.proposal
    clearance=math.hypot(x-goal.target_x,z-goal.target_z)-directive.tolerance_m
    if clearance<=0:
        target,reason="CLEAR","OBSERVED_TOLERANCE_RELEASE"
    elif mode=="RUN" and clearance<=1.95:
        target,reason="JOG","OBSERVED_RUN_TO_JOG"
    elif mode=="JOG" and clearance<=1.55:
        target,reason="WALK","OBSERVED_JOG_TO_WALK"
    else:
        target,reason=None,"CONTINUE_BOUNDED_S49_ACTION"
    return G44TransitionDecisionDev(
        action_id=action_id,source_seq=source_seq,from_mode=mode,
        clearance_m=clearance,target_mode=target,reason=reason,
    )
