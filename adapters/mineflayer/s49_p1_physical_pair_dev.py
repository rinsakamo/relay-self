"""Isolated DEV fatigue-rate sensitivity for matched scripted Minecraft worlds.

This is a *deliberately uncalibrated model counterfactual*, not a native
fatigue observation. Original S49 L0 choice, S14 authorization, P1 source,
and physical executor ownership remain untouched. No R/SCIENCE claims.
"""
from __future__ import annotations

import math

from adapters.mineflayer.execution import MOVE_BACKWARD_DURATION_S
from adapters.mineflayer.m02_paper_dev.s50_boundary import BoundaryRejected
from adapters.mineflayer.s49_p1_fifth_epoch_dev import ThirdMoveDevModel
from experiments.fatigue_p1 import (
    FatigueFrame,
    FatigueProfile,
    Rate,
    advance,
    capability,
    initial_state,
)

BASELINE = "ORIGINAL_P1"
STRESS = "UNCALIBRATED_STRESS_P1"
SENSITIVITY_RATE = 6.0


def evaluate_sixth_motor_sensitivity_dev(
    model: ThirdMoveDevModel,
    gait: dict,
    scenario: str,
) -> dict[str, object]:
    """One source-bound model input, fixed original S49 command intent.

    The counterfactual is computed from the same *observed third MOVE*
    distance, never by imputing physical WAIT, native fatigue, or new S10.
    """
    if (not isinstance(model, ThirdMoveDevModel)
            or not isinstance(gait, dict)
            or scenario not in (BASELINE, STRESS)
            or type(model.move_distance_m) is not float
            or not math.isfinite(model.move_distance_m)
            or model.move_distance_m < 0.05
            or gait.get("third_original_action_id") != model.third_action_id
            or gait.get("third_original_move_distance_m") != model.move_distance_m
            or gait.get("p1_model_fatigue") != model.model_fatigue
            or type(gait.get("fifth_native_seq")) is not int
            or gait["fifth_native_seq"] <= model.third_after_probe.seq
            or gait.get("fifth_native_request_id") is None
            or not gait["fifth_native_request_id"].startswith(
                f"s49-actual:{model.third_after_probe.session_id}:event-"
            )
            or gait.get("original_p1_model_sha256") != model.model_profile_sha256
            or gait.get("same_native_world_input") is not True
            or gait.get("candidate_executed") is not False
            or gait.get("new_grants") != 0):
        raise BoundaryRejected("P1 sensitivity input not source-bound to original third MOVE")
    if scenario == BASELINE:
        profile = FatigueProfile(enabled=True, initial=0.0)
    else:
        profile = FatigueProfile(
            enabled=True, initial=0.0,
            move_per_block=Rate(SENSITIVITY_RATE),
        )
    if scenario == BASELINE and profile.sha256 != model.model_profile_sha256:
        raise BoundaryRejected("original baseline P1 profile changed")
    transition = advance(
        profile,
        initial_state(profile, model.third_after_probe.session_id, world_tick=0),
        FatigueFrame(
            session_id=model.third_after_probe.session_id, world_tick=1,
            activity="MOVE", observed_blocks=model.move_distance_m,
        ),
    )
    speed = capability(profile, transition.after)
    duration = MOVE_BACKWARD_DURATION_S * speed.efficiency
    if (not math.isfinite(duration) or not 0 < duration < MOVE_BACKWARD_DURATION_S
            or (scenario == BASELINE and (
                transition.after.fatigue != model.model_fatigue
                or not math.isclose(
                    duration, gait["fatigue_aware_candidate_duration_s"],
                    rel_tol=1e-12,
                )
            ))
            or (scenario == STRESS and not duration <
                gait["fatigue_aware_candidate_duration_s"] / 2)):
        raise BoundaryRejected("sensitivity model lacks distinct bounded motor output")
    return {
        "status": "DEV_SIXTH_MOTOR_SOURCE_BOUND_SENSITIVITY",
        "scenario": scenario,
        "hypothetical_profile_sha256": profile.sha256,
        "hypothetical_move_rate_per_block": profile.move_per_block.value,
        "third_action_id": model.third_action_id,
        "third_observed_move_m": model.move_distance_m,
        "fifth_native_seq": gait["fifth_native_seq"],
        "fifth_native_request_id": gait["fifth_native_request_id"],
        "hypothetical_fatigue": transition.after.fatigue,
        "hypothetical_efficiency": speed.efficiency,
        "duration_s": duration,
        "original_nominal_duration_s": MOVE_BACKWARD_DURATION_S,
        "same_original_native_third_move_source": True,
        "sensitivity_not_calibration": True,
        "native_fatigue_measured": False,
        "zero_wait_ticks_imputed": True,
        "source_bound_tick": None,
        "action_permission": False,
        "additional_native_receivers": 0,
        "additional_issuers": 0,
        "qualification_go": False,
        "science_go": False,
    }
