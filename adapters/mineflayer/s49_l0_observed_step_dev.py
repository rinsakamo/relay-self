"""DEV-only L0 observed-step correction from exact closed S16 World outcome.

The output is an input-hold *proposal* for the already independently
authorized next original S49 Action. It grants no Action, cannot change
direction, and makes no claim about synchronized ticks or absolute position.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from adapters.mineflayer.execution import WorldConsequence, WorldConsequenceStatus


class L0MotionFeedbackRejected(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class L0ObservedStepPlan:
    first_action_id: str
    session_id: str
    previous_observed_m: float
    previous_input_s: float
    requested_next_step_m: float
    observed_mean_mps: float
    requested_duration_s: float | None
    reason: str
    native_tick_phase_attested: bool = False
    actual_target_reached_attested: bool = False
    qualification_go: bool = False
    science_go: bool = False


def plan_next_l0_step_dev(
    previous: WorldConsequence, *, next_step_m: float,
    previous_input_s: float = 0.60, current_threat_distance_m: float,
) -> L0ObservedStepPlan:
    """Use genuine original S16 displacement, never an assumed input speed.

    Closed S16 evidence is necessary, but movement magnitude is not proof of
    goal-oriented movement. The original L0 independently decides if a second
    Action should be issued. In urgent danger, do not shorten its escape.
    """
    if (
        not isinstance(previous, WorldConsequence)
        or previous.action_ref != "MOVE_FORWARD_SPRINT_DEV"
        or previous.status is not WorldConsequenceStatus.EXECUTED
        or previous.before_observation is None
        or previous.after_observation is None
        or previous.dispatch_receipt is None
        or previous.cleanup_receipt is None
        or not previous.cleanup_attempted
        or previous.session_id != previous.before_observation.session_id
        or previous.session_id != previous.after_observation.session_id
        or not previous.action_id
    ):
        raise L0MotionFeedbackRejected("no current original closed native S16")
    if (
        type(next_step_m) not in (int, float)
        or not math.isfinite(next_step_m)
        or not 0.30 <= next_step_m <= 2.50
        or type(previous_input_s) not in (int, float)
        or not math.isfinite(previous_input_s)
        or previous_input_s != 0.60
        or type(current_threat_distance_m) not in (int, float)
        or not math.isfinite(current_threat_distance_m)
        or not 0 < current_threat_distance_m < 4.0
    ):
        raise L0MotionFeedbackRejected("invalid DEV target, prior input or live threat")
    distance = previous.movement_distance
    if (
        type(distance) not in (int, float)
        or not math.isfinite(distance)
        or not 0.05 <= distance <= 10.0
    ):
        raise L0MotionFeedbackRejected("missing bounded native S16 movement")
    observed_speed = distance / previous_input_s
    if not 0.1 <= observed_speed <= 25:
        raise L0MotionFeedbackRejected("invalid observed first Action speed")
    if current_threat_distance_m < 1.5:
        return L0ObservedStepPlan(
            first_action_id=previous.action_id, session_id=previous.session_id,
            previous_observed_m=distance, previous_input_s=previous_input_s,
            requested_next_step_m=next_step_m, observed_mean_mps=observed_speed,
            requested_duration_s=None, reason="DANGER_ORIGINAL_L0_ESCAPE_PRIORITY",
        )
    # Conservative fixed bounds are control limits, NOT the model of physics.
    # Overshoot/undershoot are read back from the next actual S16 outcome.
    requested = max(0.10, min(0.60, next_step_m / observed_speed))
    return L0ObservedStepPlan(
        first_action_id=previous.action_id, session_id=previous.session_id,
        previous_observed_m=distance, previous_input_s=previous_input_s,
        requested_next_step_m=next_step_m, observed_mean_mps=observed_speed,
        requested_duration_s=requested, reason="OBSERVED_SPEED_INPUT_CORRECTION",
    )
