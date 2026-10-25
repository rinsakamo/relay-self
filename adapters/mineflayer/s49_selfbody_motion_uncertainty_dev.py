"""SelfBody Motion Feedback v0 DEV: conservative correction under variability.

Only historical *closed* original S16 Action outcomes influence the size of
an adjustment proposed for the *next already issued* original S49 command.
A floor models unresolved tick/time quantization as uncertainty, never
as measured Paper effective control ticks or a statistical confidence level.
No new Action, S10 state, body fatigue sensor or continuous motor loop.
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass, replace

from adapters.mineflayer.m02_paper_dev.s50_boundary import BoundaryRejected
from adapters.mineflayer.s49_selfbody_motion_feedback_dev import (
    MotionCorrection,
    SelfBodyMotionState,
)

# Deliberate bounded DEV heuristic, *not* calibrated from Minecraft clock.
UNCERTAINTY_FLOOR_M = 0.10


@dataclass(frozen=True, slots=True)
class MotionStabilityGuard:
    source_session_id: str
    source_action_id: str
    historical_closed_samples: int
    historical_prediction_errors_used: int
    observed_prediction_error_rms_m: float
    applied_uncertainty_floor_m: float
    robust_uncertainty_m: float
    stability_gain: float
    unguarded_duration_s: float
    guarded_duration_s: float
    baseline_duration_s: float
    predicted_guarded_displacement_m: float
    reason: str = "UNCERTAINTY_BOUND_DECREASES_ONE_ACTION_CORRECTION"

    def as_report(self) -> dict[str, object]:
        return {
            **asdict(self),
            "stability_gain_is_probability": False,
            "floor_empirically_calibrated": False,
            "world_tick_alignment_attested": False,
            "native_fatigue_measured": False,
            "new_action_issuer": False,
            "s10_updated": False,
            "qualification_go": False,
            "science_go": False,
        }


def guard_next_motion_correction_dev(
    state: SelfBodyMotionState,
    proposal: MotionCorrection,
) -> tuple[MotionCorrection, MotionStabilityGuard]:
    """Shrink only the adjustment, not the original Action permission.

    Online errors are computed *before* each respective original observed
    S16 sample, avoiding leakage of the next World outcome. A fixed,
    explicitly uncalibrated uncertainty floor stops artificially
    identical three training movements implying certainty.
    """
    if (not isinstance(state, SelfBodyMotionState)
            or not isinstance(proposal, MotionCorrection)
            or len(state.samples) < 3
            or state.session_id != proposal.source_session_id
            or state.samples[-1].action_id != proposal.source_action_id
            or state.samples[-1].after_seq != proposal.last_native_after_seq
            or len(state.samples) != proposal.sample_count_before
            or type(proposal.goal_distance_m) is not float
            or not math.isfinite(proposal.goal_distance_m)
            or proposal.goal_distance_m <= UNCERTAINTY_FLOOR_M
            or type(proposal.original_model_duration_s) is not float
            or type(proposal.proposed_duration_s) is not float
            or type(proposal.estimated_m_per_requested_s) is not float
            or not all(math.isfinite(v) for v in (
                proposal.original_model_duration_s,
                proposal.proposed_duration_s,
                proposal.estimated_m_per_requested_s,
            ))
            or proposal.estimated_m_per_requested_s <= 0
            or proposal.proposed_duration_s < 0.05
            or proposal.proposed_duration_s > 0.2
            or abs(proposal.proposed_duration_s - proposal.original_model_duration_s)
            > proposal.original_model_duration_s * 0.25 + 1e-12):
        raise BoundaryRejected("unstable SelfBody proposal or foreign closed Action source")
    prior_errors = [s.prediction_error_m for s in state.samples[1:]]
    if (len(prior_errors) != len(state.samples) - 1
            or any(type(e) is not float or not math.isfinite(e)
                   for e in prior_errors)):
        raise BoundaryRejected("SelfBody guard requires observed online prediction errors")
    rms = math.sqrt(sum(e * e for e in prior_errors) / len(prior_errors))
    uncertainty = max(UNCERTAINTY_FLOOR_M, rms)
    # A nonprobabilistic bounded damping factor. Even if empirically
    # zero-error, do not take the full correction in this DEV mode.
    gain = max(0.0, min(1.0, 1.0 - uncertainty / proposal.goal_distance_m))
    nominal = proposal.original_model_duration_s
    adjusted = nominal + gain * (proposal.proposed_duration_s - nominal)
    if (not math.isfinite(adjusted)
            or adjusted < min(nominal, proposal.proposed_duration_s) - 1e-12
            or adjusted > max(nominal, proposal.proposed_duration_s) + 1e-12):
        raise BoundaryRejected("uncertainty damping altered original correction bounds")
    guarded = replace(
        proposal,
        proposed_duration_s=adjusted,
        predicted_displacement_after_m=proposal.estimated_m_per_requested_s * adjusted,
    )
    return guarded, MotionStabilityGuard(
        source_session_id=state.session_id,
        source_action_id=state.samples[-1].action_id,
        historical_closed_samples=len(state.samples),
        historical_prediction_errors_used=len(prior_errors),
        observed_prediction_error_rms_m=rms,
        applied_uncertainty_floor_m=UNCERTAINTY_FLOOR_M,
        robust_uncertainty_m=uncertainty,
        stability_gain=gain,
        unguarded_duration_s=proposal.proposed_duration_s,
        guarded_duration_s=adjusted,
        baseline_duration_s=nominal,
        predicted_guarded_displacement_m=guarded.predicted_displacement_after_m,
    )
