"""P1 DEV-calibrated gait profile. Configuration only; P1 owns all physics.

No independent fatigue owner, no Action authority, no device/medical claim.
Legacy profile remains available and unmodified for historical evidence.
"""

from experiments.fatigue_p1 import FatigueProfile, Rate

P1_WORLD_REFERENCE_TPS = 20
P1_RECOVERY_TAU_WORLD_SECONDS = 40.0
P1_WALK_FATIGUE_PER_BLOCK = 0.0001


def calibrated_walk_profile_dev() -> FatigueProfile:
    """Slow low-intensity walking load plus 40-s exponential WAIT recovery.

    An engineering starting point, *not* a validated human endurance curve.
    DASH/RUN intensity and recovery during submaximal locomotion remain
    separate owner-reviewed calibration work, not inferred from this WALK.
    """
    return FatigueProfile(
        enabled=True,
        move_per_block=Rate(P1_WALK_FATIGUE_PER_BLOCK),
        recovery_time_constant_world_seconds=P1_RECOVERY_TAU_WORLD_SECONDS,
    )
