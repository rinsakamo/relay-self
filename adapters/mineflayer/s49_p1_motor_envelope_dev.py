"""DEV-only bounded motor envelope between P1 hypothesis and original S15 transport.

A motor envelope is not an Intent, S14/S16 grant, observed fatigue,
P1 World tick, independent receiver, or permission to execute. It can
only narrow timing on an ALREADY ISSUED original S49 control command.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, replace

from adapters.mineflayer.execution import (
    MOVE_BACKWARD_ACTION_REF,
    MOVE_BACKWARD_DURATION_S,
    MineflayerCommand,
)
from adapters.mineflayer.m02_paper_dev.s50_boundary import BoundaryRejected
from adapters.mineflayer.python_protocol import MineflayerObservation


@dataclass(frozen=True, slots=True)
class DevMotorEnvelope:
    """Bounded model candidate keyed by exact issued action and native probe."""

    session_id: str
    action_id: str
    probe_seq: int
    probe_request_id: str
    fifth_source_seq: int
    model_scenario: str
    hypothesis_profile_sha256: str
    model_fatigue: float
    model_efficiency: float
    nominal_duration_s: float
    constrained_duration_s: float

    def __post_init__(self) -> None:
        if (not self.session_id or not self.action_id or not self.probe_request_id
                or not self.model_scenario or not self.hypothesis_profile_sha256
                or type(self.probe_seq) is not int
                or type(self.fifth_source_seq) is not int
                or self.fifth_source_seq >= self.probe_seq
                or not all(math.isfinite(x) for x in (
                    self.model_fatigue, self.model_efficiency,
                    self.nominal_duration_s, self.constrained_duration_s,
                ))
                or not 0 < self.model_fatigue <= 1
                or not 0 < self.model_efficiency < 1
                or self.nominal_duration_s != MOVE_BACKWARD_DURATION_S
                or not 0.05 <= self.constrained_duration_s < self.nominal_duration_s
                or not math.isclose(
                    self.constrained_duration_s,
                    self.nominal_duration_s * self.model_efficiency,
                    rel_tol=1e-12, abs_tol=1e-12,
                )):
            raise BoundaryRejected("DEV motor envelope outside fixed original bounds")


def bind_motor_envelope_dev(
    command: MineflayerCommand,
    probe: MineflayerObservation,
    gait: dict,
    sensitivity: dict,
) -> DevMotorEnvelope:
    """Review exact SOURCE and action ID, but confer zero new authority."""
    if (not isinstance(command, MineflayerCommand)
            or not isinstance(probe, MineflayerObservation)
            or probe.kind != "probe"
            or not isinstance(gait, dict) or not isinstance(sensitivity, dict)
            or not isinstance(probe.request_id, str)
            or not probe.request_id.startswith(
                f"s49-actual:{probe.session_id}:event-"
            )
            or command.action_ref != MOVE_BACKWARD_ACTION_REF
            or command.duration_s != MOVE_BACKWARD_DURATION_S
            or command.action_id != (
                f"s49-native-move-{probe.request_id.rsplit('-', 1)[-1]}"
            )
            or sensitivity.get("status")
            != "DEV_SIXTH_MOTOR_SOURCE_BOUND_SENSITIVITY"
            or sensitivity.get("fifth_native_seq") != gait.get("fifth_native_seq")
            or sensitivity.get("fifth_native_request_id")
            != gait.get("fifth_native_request_id")
            or sensitivity.get("third_action_id")
            != gait.get("third_original_action_id")
            or sensitivity.get("third_observed_move_m")
            != gait.get("third_original_move_distance_m")
            or gait.get("same_native_world_input") is not True
            or gait.get("new_grants") != 0
            or sensitivity.get("action_permission") is not False
            or sensitivity.get("additional_issuers") != 0
            or sensitivity.get("additional_native_receivers") != 0
            or sensitivity.get("native_fatigue_measured") is not False
            or sensitivity.get("sensitivity_not_calibration") is not True
            or sensitivity.get("source_bound_tick") is not None
            or sensitivity.get("qualification_go") is not False
            or sensitivity.get("science_go") is not False
            or not isinstance(sensitivity.get("duration_s"), float)):
        raise BoundaryRejected("unbound S49 sixth motor P1 DEV scenario")
    return DevMotorEnvelope(
        session_id=probe.session_id,
        action_id=command.action_id,
        probe_seq=probe.seq,
        probe_request_id=probe.request_id,
        fifth_source_seq=sensitivity["fifth_native_seq"],
        model_scenario=sensitivity["scenario"],
        hypothesis_profile_sha256=sensitivity["hypothetical_profile_sha256"],
        model_fatigue=sensitivity["hypothetical_fatigue"],
        model_efficiency=sensitivity["hypothetical_efficiency"],
        nominal_duration_s=command.duration_s,
        constrained_duration_s=sensitivity["duration_s"],
    )


def apply_motor_envelope_dev(
    envelope: DevMotorEnvelope,
    command: MineflayerCommand,
    probe: MineflayerObservation,
) -> MineflayerCommand:
    """Constrain only duration on the same original issued S15 command."""
    if (not isinstance(envelope, DevMotorEnvelope)
            or not isinstance(command, MineflayerCommand)
            or not isinstance(probe, MineflayerObservation)
            or probe.kind != "probe"
            or probe.session_id != envelope.session_id
            or probe.seq != envelope.probe_seq
            or probe.request_id != envelope.probe_request_id
            or command.action_id != envelope.action_id
            or command.action_ref != MOVE_BACKWARD_ACTION_REF
            or command.duration_s != envelope.nominal_duration_s):
        raise BoundaryRejected("DEV motor envelope no longer bound to original Action")
    return replace(command, duration_s=envelope.constrained_duration_s)
