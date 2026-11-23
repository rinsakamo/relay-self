"""Stage27i DEV: bounded L0 WALK/SNEAK choice inside one frozen MOVE Preset.

No extra L1, no new Skill and no inferred authorization. The one operator
DEV Preset names this finite gait profile *before* Gemma chooses the original
MOVE/PLACE invocation. L0 can only select between its two fixed locomotor
sub-actions, based on fresh original WorldBody distance. L2, not L0, would
have to propose a new Preset to change the threshold/duration.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from adapters.mineflayer.python_protocol import MineflayerObservation
from relay_self.p0d_stage27h_bounded_l0_move_dev import (
    Stage27hBoundedMoveLoop,
    Stage27hLoopStep,
)

# Name, target radius and threshold are an indivisible operator DEV profile.
# This is NOT a universal hardcoded skill or a learned self-adopted Preset.
STAGE27I_PRESET_ID = "OperatorPrecisionWalkSneakAt075"
STAGE27I_ARRIVAL_M = 0.15
STAGE27I_SNEAK_WITHIN_M = 0.75
STAGE27I_PULSE_S = 0.15


class Stage27iGaitRefusal(RuntimeError):
    """Original selected precision profile or fresh source unavailable."""


@dataclass(frozen=True, slots=True)
class Stage27iGaitDecision:
    gait_mode: str
    pulse_seconds: float
    horizontal_distance_m: float
    arrival_radius_m: float
    sneak_threshold_m: float
    target_contract_ref: str
    preset_ref: str
    native_seq: int
    l1_additional_calls: int = 0
    skill_succeeded: bool = False
    goal_succeeded: bool = False


def choose_stage27i_gait(
    loop: Stage27hBoundedMoveLoop,
    step: Stage27hLoopStep,
    probe: MineflayerObservation,
) -> Stage27iGaitDecision:
    """Select a *prebound* physical gait; no tuning, new Target or GPU call."""
    if (
        not isinstance(loop, Stage27hBoundedMoveLoop)
        or not isinstance(step, Stage27hLoopStep)
        or not isinstance(probe, MineflayerObservation)
        or step.status != "L0_CONTINUE_MOVE"
        or step.target_status != "OUTSIDE"
        or loop.terminal_status is not None
        or probe.kind != "probe" or not probe.request_id
        or probe.seq != step.last_native_seq
        or probe.seq != loop._ready_to_reserve_seq
        or probe.session_id != loop.prepared.native_session
        or loop._settlement_reserved != 0
    ):
        raise Stage27iGaitRefusal("no original ready L0 source for precision gait")
    target = loop.invocation.target.contract
    if target is None or target.anchor is None:
        raise Stage27iGaitRefusal("original place geometry absent")
    accepted = [
        x.preset for x in loop.owner.pattern_registry.accepted_presets
        if x.receipt.self_id == loop.owner.self_id
        and x.preset.preset_ref == loop.invocation.parameter_preset_ref
    ]
    if (
        len(accepted) != 1 or accepted[0].preset_id != STAGE27I_PRESET_ID
        or target.condition.min_horizontal_m != 0.0
        or target.condition.max_horizontal_m != STAGE27I_ARRIVAL_M
        or loop.invocation.budget.max_actions != 4
        or loop.invocation.budget.max_duration_ms != 15000
        or loop.invocation.budget.max_distance_m != 2.0
        or loop.invocation.budget.max_observations != 256
    ):
        raise Stage27iGaitRefusal("precision gait not bound to original Preset")
    start, end = probe.snapshot.position, target.anchor
    distance = math.hypot(end.x - start.x, end.z - start.z)
    if (
        not math.isfinite(distance)
        or step.target_gap_m is None
        or abs(step.target_gap_m - (distance - STAGE27I_ARRIVAL_M)) > 1e-6
        or distance <= STAGE27I_ARRIVAL_M
    ):
        raise Stage27iGaitRefusal("original TargetAssessment inconsistent")
    return Stage27iGaitDecision(
        "SNEAK" if distance <= STAGE27I_SNEAK_WITHIN_M else "WALK",
        STAGE27I_PULSE_S, distance, STAGE27I_ARRIVAL_M,
        STAGE27I_SNEAK_WITHIN_M, target.contract_ref,
        loop.invocation.parameter_preset_ref or "", probe.seq,
    )
