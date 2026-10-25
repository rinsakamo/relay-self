"""DEV-only read-only motor-duration proposal for an *already issued* S49 command.

This belongs between an uncalibrated P1 capability hypothesis and S15
transport; it does not authorize/issue Actions, receive native frames,
attest World ticks, or infer measured fatigue. Default S49 is unchanged.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, replace

from adapters.mineflayer.execution import (
    MOVE_BACKWARD_ACTION_REF,
    MOVE_BACKWARD_CONTROL,
    MOVE_BACKWARD_DURATION_S,
    MOVE_BACKWARD_EFFECT,
    MineflayerCommand,
)
from adapters.mineflayer.m02_paper_dev.s50_boundary import BoundaryRejected
from adapters.mineflayer.s49_p1_physical_pair_dev import BASELINE, STRESS


@dataclass(frozen=True, slots=True)
class DevMotorBudget:
    """A constraint on control duration, never Action permission."""

    session_id: str
    issued_action_id: str
    sixth_native_seq: int
    fifth_native_seq: int
    third_original_action_id: str
    model_profile_sha256: str
    scenario: str
    nominal_duration_s: float
    candidate_duration_s: float

    def apply_to_issued(self, command: MineflayerCommand) -> MineflayerCommand:
        """Pure replacement; the sole original S49 executor remains caller."""
        if (not isinstance(command, MineflayerCommand)
                or command.action_id != self.issued_action_id
                or command.action_ref != MOVE_BACKWARD_ACTION_REF
                or command.effect != MOVE_BACKWARD_EFFECT
                or command.control != MOVE_BACKWARD_CONTROL
                or command.state is not True
                or command.duration_s != self.nominal_duration_s
                or not 0 < self.candidate_duration_s < command.duration_s):
            raise BoundaryRejected("motor proposal is not bound to original issued MOVE")
        updated = replace(command, duration_s=self.candidate_duration_s)
        if (updated.action_id != command.action_id
                or updated.binding_id != command.binding_id
                or updated.cleanup_action_id != command.cleanup_action_id
                or updated.action_ref != command.action_ref
                or updated.control != command.control):
            raise BoundaryRejected("proposal may change duration alone")
        return updated


def propose_issued_motor_budget_dev(
    sensitivity: dict[str, object], *,
    session_id: str, sixth_native_seq: int, issued_action_id: str,
) -> DevMotorBudget:
    """Fail-closed boundary for a model-only proposal, not native physiology.

    Sixth Action source identity remains checked by the original caller.
    Reject any profile that claims to authorize, observe fatigue natively,
    or interpolate missing World ticks.
    """
    if (not isinstance(sensitivity, dict)
            or type(session_id) is not str or not session_id
            or type(issued_action_id) is not str or not issued_action_id
            or type(sixth_native_seq) is not int or sixth_native_seq < 1
            or sensitivity.get("status") != "DEV_SIXTH_MOTOR_SOURCE_BOUND_SENSITIVITY"
            or sensitivity.get("scenario") not in (BASELINE, STRESS)
            or type(sensitivity.get("fifth_native_seq")) is not int
            or sensitivity["fifth_native_seq"] >= sixth_native_seq
            or sensitivity.get("third_action_id") is None
            or type(sensitivity.get("hypothetical_profile_sha256")) is not str
            or len(sensitivity["hypothetical_profile_sha256"]) != 64
            or sensitivity.get("same_original_native_third_move_source") is not True
            or sensitivity.get("sensitivity_not_calibration") is not True
            or sensitivity.get("native_fatigue_measured") is not False
            or sensitivity.get("zero_wait_ticks_imputed") is not True
            or sensitivity.get("source_bound_tick") is not None
            or sensitivity.get("action_permission") is not False
            or sensitivity.get("additional_native_receivers") != 0
            or sensitivity.get("additional_issuers") != 0
            or sensitivity.get("qualification_go") is not False
            or sensitivity.get("science_go") is not False):
        raise BoundaryRejected("P1 hypothetical capability cannot issue actions")
    nominal = sensitivity.get("original_nominal_duration_s")
    candidate = sensitivity.get("duration_s")
    if (type(nominal) is not float or nominal != MOVE_BACKWARD_DURATION_S
            or type(candidate) is not float or not math.isfinite(candidate)
            or not 0 < candidate < nominal):
        raise BoundaryRejected("P1 candidate command duration outside original bounds")
    return DevMotorBudget(
        session_id=session_id,
        issued_action_id=issued_action_id,
        sixth_native_seq=sixth_native_seq,
        fifth_native_seq=sensitivity["fifth_native_seq"],
        third_original_action_id=sensitivity["third_action_id"],
        model_profile_sha256=sensitivity["hypothetical_profile_sha256"],
        scenario=sensitivity["scenario"],
        nominal_duration_s=nominal,
        candidate_duration_s=candidate,
    )
