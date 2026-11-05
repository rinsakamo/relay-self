"""DEV direct SelfBody locomotor observations; no 'feeling' compression.

Consumes real original S49 S16 MOVE OUTCOME plus native after-probe; never
receives or guesses WorldBody true fatigue, physical rates, or server logs.
Only an observed output drop may REQUEST the existing S49 REST intent.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from adapters.mineflayer.execution import WorldConsequenceStatus
from adapters.mineflayer.normal_action import NormalActionReceipt
from adapters.mineflayer.present_projection import project_mineflayer_present
from adapters.mineflayer.python_protocol import MineflayerObservation
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


def direct_move_experience(
    receipt: NormalActionReceipt, correlated_probe: MineflayerObservation,
) -> DirectMoveExperience:
    # Original S15 uses send_observe() without request_id, so its internal
    # after-observation is NOT a qualified Body Present. An independently
    # requested native probe must follow the closed S16 before SelfBody reads.
    if not isinstance(receipt, NormalActionReceipt):
        raise DirectWorldBodyObservationRejected("original S49 S16 receipt required")
    consequence = receipt.consequence
    after = consequence.after_observation
    if (
        receipt.terminal.state is not ActionState.OUTCOME
        or consequence.status is not WorldConsequenceStatus.EXECUTED
        or receipt.terminal.action_id != consequence.action_id
        or consequence.movement_distance is None
        or not math.isfinite(consequence.movement_distance)
        or consequence.movement_distance <= 0
        or not isinstance(after, MineflayerObservation)
        or not isinstance(correlated_probe, MineflayerObservation)
        or correlated_probe.kind != "probe"
        or not correlated_probe.request_id
        or correlated_probe.session_id != consequence.session_id
        or correlated_probe.seq <= after.seq
        or correlated_probe.provenance.source != "mineflayer"
    ):
        raise DirectWorldBodyObservationRejected(
            "closed S16 + new later correlated SelfBody native probe required"
        )
    native = project_mineflayer_present(correlated_probe)
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


@dataclass(frozen=True, slots=True)
class DirectMotorRecoveryCheck:
    """Fallible SelfBody readout, never a WorldBody recovery certificate."""

    session_id: str
    pre_rest_first_action: str
    pre_rest_exhausted_action: str
    post_rest_action: str
    pre_rest_first_m: float
    pre_rest_exhausted_m: float
    post_rest_m: float
    recovery_over_exhausted_ratio: float
    recovery_over_first_ratio: float
    regained_motor_output: bool
    source_refs: tuple[str, str, str]
    worldbody_truth_accessed: bool = False


def check_post_rest_motor_output(
    first: DirectMoveExperience,
    exhausted: DirectMoveExperience,
    recovered_candidate: DirectMoveExperience,
    *,
    final_rest_probe_seq: int,
) -> DirectMotorRecoveryCheck:
    """Compare THREE original S16 MOVE outcomes + later SelfBody Present.

    The intermediate original S49 REST must have selected a safe intention and
    collected native stationary probes; the caller supplies the last original
    sample seq, not an operator's Paper WorldBody log. A third different MOVE
    must be authorized and closed by original S49; this function never issues
    a command or changes WorldBody recovery physics.
    """
    if (
        not all(isinstance(x, DirectMoveExperience) for x in (
            first, exhausted, recovered_candidate,
        ))
        or type(final_rest_probe_seq) is not int
        or final_rest_probe_seq < 0
        or len({
            first.session_id, exhausted.session_id,
            recovered_candidate.session_id,
        }) != 1
        or len({
            first.action_id, exhausted.action_id,
            recovered_candidate.action_id,
        }) != 3
        or not (
            first.native_seq < exhausted.native_seq
            < final_rest_probe_seq < recovered_candidate.native_seq
        )
        or any(
            x.hidden_worldbody_fatigue_accessed or x.worldbody_rate_accessed
            or not isinstance(x.source_ref, str)
            or not x.source_ref.startswith(
                f"native-probe:{x.session_id}:{x.native_seq}:"
            )
            or type(x.action_distance_m) not in (float, int)
            or not math.isfinite(x.action_distance_m)
            or not 0 < x.action_distance_m <= 32
            for x in (first, exhausted, recovered_candidate)
        )
        or exhausted.action_distance_m >= first.action_distance_m * 0.8
    ):
        raise DirectWorldBodyObservationRejected(
            "fresh original triple S16 and intervening REST native source required"
        )
    ratio_exhausted = (
        recovered_candidate.action_distance_m / exhausted.action_distance_m
    )
    ratio_first = recovered_candidate.action_distance_m / first.action_distance_m
    # Predeclared DEV output-only decision, neither absolute fatigue nor a
    # guarantee that REST caused the change. Independent World post-audit
    # establishes the separate server-state recovery time relation.
    regained = ratio_exhausted >= 1.8 and ratio_first >= 0.7
    return DirectMotorRecoveryCheck(
        session_id=first.session_id,
        pre_rest_first_action=first.action_id,
        pre_rest_exhausted_action=exhausted.action_id,
        post_rest_action=recovered_candidate.action_id,
        pre_rest_first_m=first.action_distance_m,
        pre_rest_exhausted_m=exhausted.action_distance_m,
        post_rest_m=recovered_candidate.action_distance_m,
        recovery_over_exhausted_ratio=ratio_exhausted,
        recovery_over_first_ratio=ratio_first,
        regained_motor_output=regained,
        source_refs=(
            first.source_ref, exhausted.source_ref, recovered_candidate.source_ref,
        ),
    )
