"""#150 DEV: conservative interrupt-only triage for cached Mineflayer L0.

The caller must authenticate its typed original bridge stream and currently
ISSUED S49 Action. This is NOT a new action grant, executor or STOP writer.
A cached 'no signal' is never proof of world safety or TPS eligibility.
"""
from __future__ import annotations

from enum import Enum


class L0Interruption(str, Enum):
    CONTINUE_UNVERIFIED = "CONTINUE_UNVERIFIED"
    INTERRUPT_UNKNOWN = "INTERRUPT_UNKNOWN"
    INTERRUPT_LOW_HEALTH = "INTERRUPT_LOW_HEALTH"
    INTERRUPT_LOW_FOOD = "INTERRUPT_LOW_FOOD"
    INTERRUPT_KNOWN_HOSTILE = "INTERRUPT_KNOWN_HOSTILE"


_ASSESSMENT_TO_INTERRUPTION = {
    "UNKNOWN": L0Interruption.INTERRUPT_UNKNOWN,
    "LOW_HEALTH": L0Interruption.INTERRUPT_LOW_HEALTH,
    "LOW_FOOD": L0Interruption.INTERRUPT_LOW_FOOD,
    "KNOWN_NEAR_HOSTILE": L0Interruption.INTERRUPT_KNOWN_HOSTILE,
    "NO_KNOWN_URGENT_SIGNAL": L0Interruption.CONTINUE_UNVERIFIED,
}


class S49L0InterruptRejected(ValueError):
    """Malformed or out-of-authority shadow cannot be used to continue."""


def classify_s49_l0_interrupt(
    assessment: str, *,
    l0_shadow_evaluated: bool,
    l0_fresh_world_tick_attested: bool,
    authorized_action_issued: bool,
    tps_admission_granted: bool,
) -> L0Interruption:
    """Fail closed on incomplete/ambiguous cached hazard evidence.

    This function is applied only after the existing typed Mineflayer stream
    decoder checks one actual session-scoped PaperL0Shadow message.
    """
    if (
        type(assessment) is not str
        or assessment not in _ASSESSMENT_TO_INTERRUPTION
        or l0_shadow_evaluated is not True
        or l0_fresh_world_tick_attested is not False
        or authorized_action_issued is not False
        or tps_admission_granted is not False
    ):
        raise S49L0InterruptRejected("invalid or authority-claiming L0 shadow")
    return _ASSESSMENT_TO_INTERRUPTION[assessment]
