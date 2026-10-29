"""G4.1 native in-flight brake advisory for the original S49 reader.

No second issuer, gait mutation, or REACHED claim: an early control CLEAR
is followed by the original S16 and subsequent L0 settled observation.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from relay_self.goal_navigation import L1GoalDirective


@dataclass(frozen=True, slots=True)
class G41BrakeDecisionDev:
    action_id: str
    source_seq: int
    mode: str
    observed_error_m: float
    clearance_m: float
    brake_requested: bool
    reason: str
    reached_attested: bool = False
    actual_gait_attested: bool = False


def decide_g41_inflight_brake_dev(
    directive: L1GoalDirective, *, action_id: str, mode: str,
    session_id: str, source_seq: int, request_id: str, source: str,
    x: float, z: float, previous_seq: int,
    truncated: bool, danger_present: bool,
) -> G41BrakeDecisionDev:
    """One source-validated in-flight probe; no synthetic WorldTick."""
    if (
        not isinstance(directive, L1GoalDirective)
        or type(action_id) is not str or not action_id
        or type(mode) is not str or mode not in ("DASH", "RUN", "JOG", "WALK")
        or type(session_id) is not str
        or session_id != directive.proposal.session_id
        or type(source_seq) is not int or source_seq < 0
        or type(previous_seq) is not int or source_seq <= previous_seq
        or type(request_id) is not str
        or not request_id.startswith(action_id + "-inflight-")
        or source != "mineflayer"
        or type(truncated) is not bool or truncated
        or type(danger_present) is not bool or danger_present
        or type(x) not in (int, float) or not math.isfinite(x)
        or type(z) not in (int, float) or not math.isfinite(z)
    ):
        raise ValueError("G4.1 refuses foreign/stale/dangerous native motor probe")
    goal=directive.proposal
    error=math.hypot(goal.target_x-x, goal.target_z-z)
    clearance=error-directive.tolerance_m
    if clearance <= 0:
        brake,reason=True,"OBSERVED_TOLERANCE_BRAKE_FOR_SETTLE"
    elif mode in ("DASH", "RUN") and clearance <= 1.05:
        brake,reason=True,"FAST_GAIT_BRAKE_FOR_NEXT_G4_CHOICE"
    elif mode=="JOG" and clearance <= 0.35:
        brake,reason=True,"JOG_BRAKE_FOR_WALK"
    else:
        brake,reason=False,"CONTINUE_ORIGINAL_BOUNDED_ACTION"
    return G41BrakeDecisionDev(
        action_id=action_id,source_seq=source_seq,mode=mode,
        observed_error_m=error,clearance_m=clearance,
        brake_requested=brake,reason=reason,
    )
