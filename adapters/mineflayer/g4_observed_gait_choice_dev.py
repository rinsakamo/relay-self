"""G4 DEV L0 gait selection at a fresh original goal observation.

This *advisory choice* uses the existing L2 goal, L1 tolerance and single
World-owned P1/M0 state. It never authorizes or issues an Action or predicts
an unobserved World outcome. S49 alone issues the physical motor request.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from experiments.fatigue_p1 import FatigueProfile, FatigueState
from experiments.p1_gait_dev import p1_motor_power_limit_dev
from relay_self.goal_navigation import (
    GoalDecisionKind,
    L0GoalDecision,
    L1GoalDirective,
)


@dataclass(frozen=True, slots=True)
class G4GaitChoiceDev:
    source_seq: int
    mode: str
    duration_s: float
    remaining_clearance_m: float
    tolerance_m: float
    p1_fraction: float
    m0_available: float
    estimated_dash_power: float
    reason: str
    claimed_applied_gait: bool = False
    qualified: bool = False


def choose_g4_observed_gait_dev(
    decision: L0GoalDecision, directive: L1GoalDirective, *,
    action_index: int, p1_profile: FatigueProfile, p1_state: FatigueState,
    m0_energy: float, threats_present: bool = False,
) -> G4GaitChoiceDev:
    """L0 per-Action DEV gait; tolerance is owned by existing L2/L1.

    RUN and DASH are coarse approaches. JOG and WALK approach a small
    remaining clearance at lower physical speed. A measured next probe,
    not this advisory calculation, determines actual progress/REACHED.
    """
    if (
        not isinstance(decision, L0GoalDecision)
        or not isinstance(directive, L1GoalDirective)
        or decision.kind is not GoalDecisionKind.MOVE
        or type(decision.source_seq) is not int or decision.source_seq < 0
        or type(action_index) is not int or not 1 <= action_index <= directive.max_actions
        or not isinstance(p1_profile, FatigueProfile)
        or not isinstance(p1_state, FatigueState)
        or not p1_profile.enabled
        or p1_state.session_id != directive.proposal.session_id
        or type(threats_present) is not bool or threats_present
        or type(m0_energy) not in (int, float) or not math.isfinite(m0_energy)
        or m0_energy <= 0
        or decision.input_duration_s is None
        or not math.isfinite(decision.input_duration_s)
        or not 0.10 <= decision.input_duration_s <= 0.35
        or not all(math.isfinite(x) for x in (
            decision.x, decision.z, decision.goal_error_m,
            decision.forward_remaining_m, decision.cross_track_m,
        ))
        or decision.forward_remaining_m <= 0
        or abs(decision.cross_track_m) > 0.30
        or decision.goal_error_m <= directive.tolerance_m
        or not math.isclose(
            math.hypot(directive.proposal.target_x-decision.x,
                       directive.proposal.target_z-decision.z),
            decision.goal_error_m, abs_tol=1e-6,
        )
    ):
        raise ValueError("G4 requires fresh positive forward L0 MOVE and body budget")
    clearance = decision.forward_remaining_m-directive.tolerance_m
    if clearance <= 0:
        raise ValueError("G4 refuses motion inside L1 tolerance")
    fraction = p1_state.fatigue/p1_profile.capacity
    if not math.isfinite(fraction) or not 0 <= fraction <= 1:
        raise ValueError("G4 invalid single P1 fatigue")
    # Reserve baseline and movement in the one M0 owner. This budget
    # is only a preflight choice, not proof of spendable actual DASH motor.
    extra = max(0.0, m0_energy-0.05)
    power = p1_motor_power_limit_dev(
        p1_profile, p1_state, 1.0, extra,
    )
    if clearance <= 0.60 or m0_energy <= 0.08 or fraction >= 0.90:
        mode, speed, reason = "WALK", 1.3, "PRECISION_OR_LIMITED_BODY"
    elif clearance <= 1.55 or fraction >= 0.72 or m0_energy <= 0.25:
        mode, speed, reason = "JOG", 4.32, "APPROACH_TOLERANCE_OR_CONSERVE"
    elif action_index == 1 and clearance >= 2.65 and power >= 0.99:
        mode, speed, reason = "DASH", 8.415, "FAR_GOAL_P1_M0_PERMIT"
    else:
        mode, speed, reason = "RUN", 5.61, "COARSE_APPROACH"
    # Do not allow a speed-class request to move past the tolerance band
    # under the nominal speed model. Real displacement is NOT guaranteed
    # and will always be corrected by the original next World observation.
    duration = float(max(0.10, min(
        decision.input_duration_s, 0.35, (clearance / speed)*0.75,
    )))
    return G4GaitChoiceDev(
        source_seq=decision.source_seq, mode=mode, duration_s=duration,
        remaining_clearance_m=clearance, tolerance_m=directive.tolerance_m,
        p1_fraction=fraction, m0_available=float(m0_energy),
        estimated_dash_power=power if mode == "DASH" else 0.0,
        reason=reason,
    )
