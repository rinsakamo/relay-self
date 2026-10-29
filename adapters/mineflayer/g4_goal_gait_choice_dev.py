"""G4 DEV: bounded observed-goal L0 gait *proposal*, never Action authority.

Use the original L1 distance tolerance and current single T2 P1/M0 state.
Minecraft sneak=provisional WALK, ordinary forward=JOG, sprint=RUN;
the first full-power Paper modifier on original sprint Action can be DASH.
No native velocity calibration, packet attestation, or Action issuance here.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal

from experiments.fatigue_p1 import FatigueProfile, FatigueState
from experiments.p1_gait_dev import p1_motor_power_limit_dev
from relay_self.goal_navigation import (
    GoalDecisionKind, L0GoalDecision, L1GoalDirective,
)

G4Mode = Literal["WALK", "JOG", "RUN", "DASH"]


@dataclass(frozen=True, slots=True)
class G4L0GaitChoiceDev:
    gait: G4Mode
    source_seq: int
    goal_id: str
    goal_error_m: float
    l1_tolerance_m: float
    remaining_outside_tolerance_m: float
    p1_world_tick: int
    p1_fatigue_fraction: float
    m0_energy_available: float
    input_duration_s: float
    reason: str
    learned_policy: bool = False
    motor_applied: bool = False
    full_tick_gait_attested: bool = False


def choose_g4_l0_gait_dev(
    decision: L0GoalDecision, directive: L1GoalDirective, *,
    profile: FatigueProfile, fatigue: FatigueState,
    m0_energy: float, first_action: bool, dash_paper_available: bool,
) -> G4L0GaitChoiceDev:
    """Pure single-step selection from the current observed L0+P1/M0 facts.

    All thresholds are DEV *control hypotheses*, not measured braking
    distances. Unclassified gait ticks are already conservatively accounted
    by the existing original T2 owner; this function cannot backfill them.
    """
    if (
        not isinstance(decision, L0GoalDecision)
        or decision.kind is not GoalDecisionKind.MOVE
        or not isinstance(directive, L1GoalDirective)
        or not isinstance(profile, FatigueProfile) or not profile.enabled
        or not isinstance(fatigue, FatigueState)
        or fatigue.session_id != directive.proposal.session_id
        or fatigue.profile_sha256 != profile.sha256
        or type(fatigue.world_tick) is not int or fatigue.world_tick < 0
        or type(first_action) is not bool or type(dash_paper_available) is not bool
        or type(m0_energy) not in (float, int) or not math.isfinite(m0_energy)
        or m0_energy <= 0
        or type(decision.input_duration_s) is not float
        or not math.isfinite(decision.input_duration_s)
        or not 0.10 <= decision.input_duration_s <= 0.35
        or not all(math.isfinite(x) for x in (
            decision.goal_error_m, decision.forward_remaining_m,
            decision.cross_track_m))
        or decision.goal_error_m <= directive.tolerance_m
        or decision.forward_remaining_m <= directive.tolerance_m
        or abs(decision.cross_track_m) > 0.30
    ):
        raise ValueError("G4 requires fresh admitted MOVE and same-session body budget")
    margin = decision.forward_remaining_m - directive.tolerance_m
    fatigue_fraction = fatigue.fatigue / profile.capacity
    if not 0 <= fatigue_fraction <= 1:
        raise ValueError("G4 P1 fatigue state out of range")
    spendable_extra = max(0.0, m0_energy - 0.04)
    power = p1_motor_power_limit_dev(
        profile, fatigue, 1.0, spendable_extra,
    )
    # DASH is a one-shot physical Paper modifier. If we cannot pay the full
    # observed 0.010/tick cost, the original S49 may still choose RUN/JOG,
    # but it must NOT arm the Paper DASH plugin based on model-only intent.
    if (first_action and dash_paper_available and margin > 1.6
            and fatigue_fraction <= .50 and m0_energy > .10
            and power >= 1 - 1e-9):
        gait: G4Mode = "DASH"
        reason = "FAR_FULL_POWER_PAPER_DASH_DEV"
    elif margin > 1.6 and fatigue_fraction <= .75 and m0_energy > .08:
        gait = "RUN"
        reason = "FAR_RUN_BOUNDED"
    elif margin > .65 and fatigue_fraction <= .90 and m0_energy > .04:
        gait = "JOG"
        reason = "MIDRANGE_ORDINARY_FORWARD"
    else:
        gait = "WALK"
        reason = "NEAR_TOLERANCE_OR_BODY_LIMIT_SNEAK"
    duration = decision.input_duration_s
    if gait == "WALK":
        # Reduce expected overshoot; never pretend nominal speed is a
        # measured actual motor speed. S49 still closes on actual S16 source.
        duration = float(min(duration, max(.10, min(.35, margin / 1.3 * .60))))
    return G4L0GaitChoiceDev(
        gait=gait,
        source_seq=decision.source_seq,
        goal_id=directive.proposal.goal_id,
        goal_error_m=decision.goal_error_m,
        l1_tolerance_m=directive.tolerance_m,
        remaining_outside_tolerance_m=margin,
        p1_world_tick=fatigue.world_tick,
        p1_fatigue_fraction=fatigue_fraction,
        m0_energy_available=float(m0_energy),
        input_duration_s=float(duration),
        reason=reason,
    )
