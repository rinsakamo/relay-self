"""Finite CPU approach recommendation from target conditions and Body evidence.

No motor, World read, inferred physics, source promotion, or new Action issuer.
A gait exists only if WorldBody supplied a bounded calibrated stop-distance
envelope; a caller must separately authorize and issue any proposed control.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum

from relay_self.common_io import ScopeRef
from relay_self.provenance import Provenance
from relay_self.target_contract import (
    TargetAssessment,
    TargetBodyObservation,
    TargetConditionStatus,
    TargetContract,
    TargetContractRefusal,
    evaluate_target,
)


class GaitMode(str, Enum):
    SNEAK = "SNEAK"
    WALK = "WALK"
    JOG = "JOG"
    RUN = "RUN"
    DASH = "DASH"


class ApproachPhase(str, Enum):
    APPROACH = "APPROACH"
    DECELERATE = "DECELERATE"
    STOP_RECOMMENDED = "STOP_RECOMMENDED"
    VERIFY_STILLNESS = "VERIFY_STILLNESS"
    TARGET_CONDITION_OBSERVED = "TARGET_CONDITION_OBSERVED"
    REPLAN = "REPLAN"
    HOLD_UNKNOWN = "HOLD_UNKNOWN"


@dataclass(frozen=True, slots=True)
class GaitCalibration:
    mode: GaitMode
    observed_speed_mps: float
    conservative_stop_distance_m: float
    provenance: Provenance

    def __post_init__(self) -> None:
        if (not isinstance(self.mode, GaitMode)
                or not isinstance(self.provenance, Provenance)):
            raise TargetContractRefusal("gait needs WorldBody mode and source")
        for name, value, limit in (
            ("speed", self.observed_speed_mps, 40),
            ("stop distance", self.conservative_stop_distance_m, 20),
        ):
            if (type(value) not in (int, float) or not math.isfinite(value)
                    or not 0 <= value <= limit):
                raise TargetContractRefusal(f"invalid calibrated gait {name}")
        if self.observed_speed_mps == 0:
            raise TargetContractRefusal("zero speed is not an approach gait")


@dataclass(frozen=True, slots=True)
class BodyApproachCapabilities:
    scope: ScopeRef
    observed_seq: int
    max_age_seq: int
    position_uncertainty_m: float
    gaits: tuple[GaitCalibration, ...]
    provenance: Provenance

    def __post_init__(self) -> None:
        if (not isinstance(self.scope, ScopeRef)
                or not self.scope.world_session_id
                or not isinstance(self.provenance, Provenance)):
            raise TargetContractRefusal("Body capabilities require original scope/source")
        if (type(self.observed_seq) is not int or self.observed_seq < 0
                or type(self.max_age_seq) is not int or not 0 <= self.max_age_seq <= 64):
            raise TargetContractRefusal("invalid Body capability freshness")
        if (type(self.position_uncertainty_m) not in (int, float)
                or not math.isfinite(self.position_uncertainty_m)
                or not 0 <= self.position_uncertainty_m <= 2):
            raise TargetContractRefusal("invalid position uncertainty")
        if (type(self.gaits) is not tuple or not 1 <= len(self.gaits) <= 5
                or any(not isinstance(g, GaitCalibration) for g in self.gaits)
                or len({g.mode for g in self.gaits}) != len(self.gaits)):
            raise TargetContractRefusal("bounded unique calibrated gaits required")


@dataclass(frozen=True, slots=True)
class ApproachRecommendation:
    phase: ApproachPhase
    target_contract_ref: str
    target_assessment: TargetAssessment
    requested_gait: GaitMode | None
    gap_m: float | None
    reason: str
    physical_issued: bool = False
    action_authorized: bool = False
    goal_succeeded: bool = False


def recommend_approach(
    contract: TargetContract,
    observed: TargetBodyObservation,
    capability: BodyApproachCapabilities,
    *,
    current_gait: GaitMode | None = None,
    route_clear: bool | None = None,
) -> ApproachRecommendation:
    """Pure, bounded controller. Returned phase is NOT a motor instruction.

    Without live route evidence and a source-fresh stop-distance calibration
    the only safe recommendation is HOLD. No threshold is borrowed from another
    Goal's precision; all ranges belong to TargetContract.condition.
    """
    if not isinstance(capability, BodyApproachCapabilities):
        raise TargetContractRefusal("typed Body approach capability required")
    if current_gait is not None and not isinstance(current_gait, GaitMode):
        raise TargetContractRefusal("unknown current gait")
    if route_clear is not None and type(route_clear) is not bool:
        raise TargetContractRefusal("route clearance must be evidence or UNKNOWN")
    assessment = evaluate_target(contract, observed)

    def answer(phase: ApproachPhase, reason: str, *,
               gait: GaitMode | None = None) -> ApproachRecommendation:
        return ApproachRecommendation(
            phase, contract.contract_ref, assessment,
            gait, assessment.gap_to_envelope_m, reason,
        )

    if (capability.scope != contract.scope
            or capability.observed_seq > observed.seq
            or observed.seq - capability.observed_seq > capability.max_age_seq
            or capability.observed_seq < contract.bound_seq):
        return answer(ApproachPhase.HOLD_UNKNOWN, "foreign/stale gait capability")
    if assessment.status is TargetConditionStatus.CONDITION_OBSERVED:
        return answer(
            ApproachPhase.TARGET_CONDITION_OBSERVED,
            "observed Target condition only; no Skill/Goal success",
        )
    if assessment.status is TargetConditionStatus.SETTLING:
        return answer(
            ApproachPhase.VERIFY_STILLNESS,
            "keep observing the requested Body speed/STOP stillness",
        )
    if assessment.status in (
        TargetConditionStatus.VERTICAL_MISMATCH,
        TargetConditionStatus.TOO_CLOSE,
        TargetConditionStatus.BLOCKED,
        TargetConditionStatus.ALIGN_REQUIRED,
    ):
        return answer(
            ApproachPhase.REPLAN, "requires geometry/path/facing reconsideration",
        )
    if assessment.status is not TargetConditionStatus.OUTSIDE:
        return answer(ApproachPhase.HOLD_UNKNOWN, assessment.reason)
    if (route_clear is not True or observed.speed_mps is None
            or assessment.gap_to_envelope_m is None):
        return answer(
            ApproachPhase.HOLD_UNKNOWN,
            "fresh Body speed and route clearance required before approach",
        )
    gap = assessment.gap_to_envelope_m
    # Choose the highest measured speed with space to stop before overshooting
    # the target's closest acceptable boundary. The calibration is an input,
    # not an assumed Minecraft movement-speed constant.
    candidates = sorted(
        capability.gaits,
        key=lambda g: g.observed_speed_mps, reverse=True,
    )
    fits = [
        g for g in candidates
        if g.conservative_stop_distance_m + capability.position_uncertainty_m < gap
    ]
    if not fits:
        return answer(
            ApproachPhase.STOP_RECOMMENDED,
            "insufficient calibrated stopping space; do not issue forward",
        )
    chosen = fits[0]
    current_speed = next(
        (g.observed_speed_mps for g in capability.gaits if g.mode is current_gait),
        None,
    )
    if current_gait is not None and current_speed is None:
        return answer(ApproachPhase.HOLD_UNKNOWN, "current gait not calibrated")
    phase = (
        ApproachPhase.DECELERATE
        if current_speed is not None and chosen.observed_speed_mps < current_speed
        else ApproachPhase.APPROACH
    )
    return answer(
        phase, "Target-specific envelope and measured stopping margin",
        gait=chosen.mode,
    )
