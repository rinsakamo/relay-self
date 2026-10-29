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
    x: float, z: float, previous_seq: int, action_start_error_m: float,
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
        or type(action_start_error_m) not in (int, float)
        or not math.isfinite(action_start_error_m)
        or action_start_error_m < 0
    ):
        raise ValueError("G4.1 refuses foreign/stale/dangerous native motor probe")
    goal=directive.proposal
    error=math.hypot(goal.target_x-x, goal.target_z-z)
    clearance=error-directive.tolerance_m
    # Require physically observed forward progress before an early
    # brake. Otherwise a zero-displacement short pulse can produce UNKNOWN.
    progressed=action_start_error_m-error
    if mode=="WALK":
        brake,reason=False,"WALK_FIXED_PULSE_THEN_NATIVE_S16_SETTLE"
    elif progressed < 0.08:
        brake,reason=False,"WAIT_FOR_MEASURED_MOTOR_PROGRESS"
    elif clearance <= 0:
        brake,reason=True,"OBSERVED_TOLERANCE_BRAKE_FOR_SETTLE"
    elif mode in ("DASH", "RUN") and clearance <= 1.05:
        brake,reason=True,"FAST_GAIT_BRAKE_FOR_NEXT_G4_CHOICE"
    elif mode=="JOG" and clearance <= 0.60:
        brake,reason=True,"JOG_BRAKE_FOR_WALK"
    else:
        brake,reason=False,"CONTINUE_ORIGINAL_BOUNDED_ACTION"
    return G41BrakeDecisionDev(
        action_id=action_id,source_seq=source_seq,mode=mode,
        observed_error_m=error,clearance_m=clearance,
        brake_requested=brake,reason=reason,
    )

def g41_feedback_window_duration_dev(
    mode: str, clearance_m: float, original_duration_s: float,
) -> float:
    """Give short precision Actions sufficient time for native feedback.

    The same original S49 Action remains bounded to <=0.35s. WALK does
    not poll mid-pulse: it relies on existing S16 and L0 settled follow-up.
    """
    if (
        mode not in ("DASH", "RUN", "JOG", "WALK")
        or type(clearance_m) not in (int, float)
        or not math.isfinite(clearance_m) or clearance_m <= 0
        or type(original_duration_s) is not float
        or not math.isfinite(original_duration_s)
        or not 0.10 <= original_duration_s <= 0.35
    ):
        raise ValueError("G4.1 feedback window requires a bounded G4 action")
    floor=(0.24 if mode=="JOG" and clearance_m<=1.0
           else 0.20 if mode=="WALK"
           else 0.10)
    return float(max(original_duration_s, floor))
