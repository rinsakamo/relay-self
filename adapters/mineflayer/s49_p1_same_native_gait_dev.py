"""DEV cognition comparison on one already-received original L0 native probe.

This evaluates *conditional* Action duration budgets on the same World input.
It neither authorizes a MOVE nor alters the original S42 choice/executor.
Original third MOVE's aggregate distance drives the baseline P1 hypothesis.
The profile is uncalibrated, the World-tick gap unknown, and this is NOT a
native fatigue sensor, new process receiver, physical execution or science.
"""
from __future__ import annotations

import math

from adapters.mineflayer.execution import MOVE_BACKWARD_DURATION_S
from adapters.mineflayer.m02_paper_dev.s50_boundary import BoundaryRejected
from adapters.mineflayer.python_protocol import MineflayerObservation
from adapters.mineflayer.s49_p1_fifth_epoch_dev import (
    MODEL,
    ThirdMoveDevModel,
    project_fifth_l0_view_dev,
)
from experiments.fatigue_p1 import FatigueProfile, FatigueState, capability


def compare_fifth_p1_gait_dev(
    model: ThirdMoveDevModel,
    native: MineflayerObservation,
) -> dict[str, object]:
    """Counterfactual no-P1 vs original P1 movement duration on ONE real input."""
    if not isinstance(model, ThirdMoveDevModel):
        raise BoundaryRejected("same original third MOVE P1 model required")
    fifth = project_fifth_l0_view_dev(model, native)
    if (fifth["third_action_id"] != model.third_action_id
            or fifth["third_post_move_native_seq"] >= native.seq
            or fifth["p1_origin"] != "hypothesis"
            or fifth["model_only"] is not True
            or fifth["selfworld_body_same_object"] is not True
            or fifth["p1_model_fatigue"] != model.model_fatigue
            or fifth["p1_model_profile_sha256"] != model.model_profile_sha256
            or model.body.hypotheses[0].state.source_refs[0] != (
                f"s49-closed-action:{native.session_id}:{model.third_action_id}"
            )):
        raise BoundaryRejected("fifth native Self views not tied to third MOVE")

    profile = FatigueProfile(enabled=True, initial=0.0)
    if model.model_profile_sha256 != profile.sha256:
        raise BoundaryRejected("historical original P1 profile changed")
    state = FatigueState(
        native.session_id, profile.sha256, 1, model.model_fatigue,
    )
    cap = capability(profile, state)
    nominal = MOVE_BACKWARD_DURATION_S
    modeled = nominal * cap.efficiency
    if (not math.isfinite(modeled) or not 0 < modeled < nominal
            or cap.max_move_blocks_per_world_tick >=
            profile.nominal_move_limit_blocks
            or fifth["p1_model_sensor_pct"] != model.body.hypothetical(
                MODEL, "p1_sensor_pct",
            ).value):
        raise BoundaryRejected("third MOVE P1 cannot constrain hypothetical gait")

    return {
        "status": "DEV_SAME_NATIVE_PROBE_P1_GAIT_POLICY_COMPARISON",
        "session_id": native.session_id,
        "fifth_native_seq": native.seq,
        "fifth_native_request_id": native.request_id,
        "third_original_action_id": model.third_action_id,
        "third_original_move_distance_m": model.move_distance_m,
        "self_body_epoch_id": fifth["epoch_id"],
        "original_p1_model_sha256": profile.sha256,
        "p1_model_fatigue": model.model_fatigue,
        "baseline_nominal_command_duration_s": nominal,
        "fatigue_aware_candidate_duration_s": modeled,
        "modeled_duration_reduction_s": nominal - modeled,
        "baseline_one_tick_capacity_blocks": profile.nominal_move_limit_blocks,
        "modeled_one_tick_capacity_blocks": cap.max_move_blocks_per_world_tick,
        "same_native_world_input": True,
        "same_original_action_issuer": True,
        "s42_intent_changed": False,
        "original_l0_choice_changed": False,
        "candidate_executed": False,
        "model_is_native_fatigue": False,
        "world_tick_gap_interpolated": False,
        "source_bound_tick": None,
        "wait_ticks_admitted": 0,
        "new_grants": 0,
        "new_action_issuers": 0,
        "qualification_go": False,
        "science_go": False,
    }
