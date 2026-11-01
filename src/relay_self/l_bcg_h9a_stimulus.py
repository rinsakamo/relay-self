"""H9a: opt-in two-arm *world stimulus*, not a learned L1 intervention.

Original S49 L0, Action issuer and native observation are unchanged. The
declared numeric arm is not evidence that Minecraft actually showed it.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

ARM_DISTANCES_M = (2.0, 3.5)
CHEAP_THRESHOLD_M = 3.0
ARM_TOLERANCE_M = 0.15


class H9aRejected(ValueError):
    """Out-of-scope DEV arm, unsafe coupling, or unqualified observation."""


@dataclass(frozen=True, slots=True)
class H9aStimulus:
    requested_near_m: float
    cheap_threshold_m: float = CHEAP_THRESHOLD_M
    observed_tolerance_m: float = ARM_TOLERANCE_M
    cause: str = "S49_EXISTING_OPERATOR_ZOMBIE_DISTANCE_ONLY"
    l0_policy_modified: bool = False
    action_authority: bool = False
    model_calls: int = 0
    formal_training_worlds: int = 0


def select_h9a_stimulus(
    distance_m: float | None, *,
    l_bcg_shadow_dev: bool,
    live_next_epoch_dev: bool,
    l22_settling_probes: int | None,
) -> H9aStimulus | None:
    """None means default S49 old staging; no H9a field or behavior changes."""
    if distance_m is None:
        return None
    if (
        type(distance_m) not in (float, int)
        or not isfinite(distance_m)
        or float(distance_m) not in ARM_DISTANCES_M
        or type(l_bcg_shadow_dev) is not bool or not l_bcg_shadow_dev
        or type(live_next_epoch_dev) is not bool or not live_next_epoch_dev
        or type(l22_settling_probes) is not int
        or not 3 <= l22_settling_probes <= 8
    ):
        raise H9aRejected("H9a requires explicit 2.0/3.5m and single-action L-BCG route B")
    return H9aStimulus(float(distance_m))


def verify_h9a_observed_distance(
    arm: H9aStimulus, *, original_s42_distance_m: float,
    original_l0_choice: str,
) -> bool:
    """True only when existing native S42 saw a distance within frozen band.

    This is an observational manipulation check, not physical attestation,
    goal success, counterfactual causality or a training label.
    """
    if (
        type(arm) is not H9aStimulus
        or type(original_s42_distance_m) not in (float, int)
        or not isfinite(original_s42_distance_m)
        or type(original_l0_choice) is not str
    ):
        raise H9aRejected("typed actual S42 readback required")
    if original_l0_choice != "MOVE_AWAY":
        return False
    return (
        abs(float(original_s42_distance_m) - arm.requested_near_m)
        <= arm.observed_tolerance_m
        and float(original_s42_distance_m) < 4.0
    )
