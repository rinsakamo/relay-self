"""DEV direct SelfBody locomotor observations; no 'feeling' compression.

Consumes real original S49 S16 MOVE OUTCOME plus native after-probe; never
receives or guesses WorldBody true fatigue, physical rates, or server logs.
Only an observed output drop may REQUEST the existing S49 REST intent.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from adapters.mineflayer.normal_action import NormalActionReceipt
from adapters.mineflayer.present_projection import project_mineflayer_present
from adapters.mineflayer.self_body_projection import project_body_present
from relay_self.action import ActionState
from relay_self.self_body import BodyOrigin, compose_self_body_view


class DirectWorldBodyObservationRejected(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class DirectMoveExperience:
    session_id: str
    action_id: str
    native_seq: int
    action_distance_m: float
    source_ref: str
    observed_fields: tuple[str, ...]
    hidden_worldbody_fatigue_accessed: bool = False
    worldbody_rate_accessed: bool = False


@dataclass(frozen=True, slots=True)
class DirectRestRequest:
    session_id: str
    first_action_id: str
    last_action_id: str
    first_move_m: float
    last_move_m: float
    output_ratio: float
    rest_requested: bool
    reason: str
    worldbody_truth_accessed: bool = False


def direct_move_experience(receipt: NormalActionReceipt) -> DirectMoveExperience:
    if (
        not isinstance(receipt, NormalActionReceipt)
        or receipt.terminal.state is not ActionState.OUTCOME
        or receipt.consequence.movement_distance is None
        or not math.isfinite(receipt.consequence.movement_distance)
        or receipt.consequence.movement_distance <= 0
        or receipt.consequence.after_observation is None
    ):
        raise DirectWorldBodyObservationRejected("original S16 MOVE outcome required")
    native = project_mineflayer_present(receipt.consequence.after_observation)
    observed = project_body_present(native)
    view = compose_self_body_view(
        session_id=observed.session_id,
        epoch_id=f"worldbody-direct:{receipt.terminal.action_id}",
        observation=observed,
    )
    for field in ("position_x", "position_y", "position_z", "health", "food"):
        reading = view.observed(field)
        if (
            reading.origin is not BodyOrigin.OBSERVATION
            or reading.source_refs != (observed.source_ref,)
        ):
            raise DirectWorldBodyObservationRejected("body Present missing actual source")
    return DirectMoveExperience(
        session_id=observed.session_id,
        action_id=receipt.terminal.action_id,
        native_seq=observed.native_seq,
        action_distance_m=receipt.consequence.movement_distance,
        source_ref=observed.source_ref,
        observed_fields=("position_x", "position_y", "position_z", "health", "food"),
    )


def rest_from_observed_motor_output(
    first: DirectMoveExperience, last: DirectMoveExperience,
) -> DirectRestRequest:
    if (
        not isinstance(first, DirectMoveExperience)
        or not isinstance(last, DirectMoveExperience)
        or first.session_id != last.session_id
        or first.action_id == last.action_id
        or first.native_seq >= last.native_seq
        or first.hidden_worldbody_fatigue_accessed
        or last.hidden_worldbody_fatigue_accessed
        or first.worldbody_rate_accessed or last.worldbody_rate_accessed
        or not 0 < first.action_distance_m <= 32
        or not 0 < last.action_distance_m <= 32
    ):
        raise DirectWorldBodyObservationRejected("fresh two-action S16 direct body pair required")
    ratio = last.action_distance_m / first.action_distance_m
    # DEV heuristic deliberately based only on measured output. This is NOT
    # a sensor reading of actual fatigue and cannot mutate World laws.
    rest = ratio < 0.80
    return DirectRestRequest(
        session_id=first.session_id, first_action_id=first.action_id,
        last_action_id=last.action_id,
        first_move_m=first.action_distance_m,
        last_move_m=last.action_distance_m,
        output_ratio=ratio,
        rest_requested=rest,
        reason="OBSERVED_MOTOR_OUTPUT_LOSS" if rest else "NO_OUTPUT_LOSS_PROVEN",
    )
