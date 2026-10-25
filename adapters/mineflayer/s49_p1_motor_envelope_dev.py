"""DEV-only typed bridge: hypothetical P1 motor capacity -> issued S49 timing.

Only the *original* owner may call this after issuing S14/S15/S16 Action.
This pure adapter neither decides L0, issues an Action, owns a native
receiver nor attests native fatigue. A DEV caller must separately enforce
single-use and original session lifetime.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, replace

from adapters.mineflayer.execution import (
    MOVE_BACKWARD_DURATION_S,
    MineflayerCommand,
)
from adapters.mineflayer.m02_paper_dev.s50_boundary import BoundaryRejected
from adapters.mineflayer.python_protocol import MineflayerObservation
from adapters.mineflayer.s49_p1_physical_pair_dev import BASELINE, STRESS


@dataclass(frozen=True, slots=True)
class DevMotorEnvelope:
    """Read-only, exact-Action model timing candidate; NOT Action authority."""

    session_id: str
    sixth_probe_seq: int
    fifth_model_probe_seq: int
    issued_action_id: str
    third_source_action_id: str
    scenario: str
    model_profile_sha256: str
    native_fatigue_measured: bool
    nominal_duration_s: float
    candidate_duration_s: float


def apply_issued_p1_motor_envelope_dev(
    issued: MineflayerCommand,
    sixth_probe: MineflayerObservation,
    sensitivity: dict,
    *,
    expected_third_action_id: str,
    expected_fifth_seq: int,
) -> tuple[MineflayerCommand, DevMotorEnvelope]:
    """Change only duration of a *validated, already-issued* MOVE command.

    The already-issued Action command and native sixth probe identities must
    correlate. If not, refuse rather than mint an Action or control command.
    """
    if (not isinstance(issued, MineflayerCommand)
            or not isinstance(sixth_probe, MineflayerObservation)
            or not isinstance(sensitivity, dict)
            or type(expected_fifth_seq) is not int or expected_fifth_seq < 0
            or not isinstance(expected_third_action_id, str)
            or not expected_third_action_id
            or sixth_probe.kind != "probe"
            or sixth_probe.provenance.source != "mineflayer"
            or sixth_probe.snapshot.nearby_entities_coverage.truncated
            or not sixth_probe.request_id
            or not sixth_probe.request_id.startswith(
                f"s49-actual:{sixth_probe.session_id}:event-"
            )
            or sixth_probe.seq <= expected_fifth_seq
            or sensitivity.get("status")
            != "DEV_SIXTH_MOTOR_SOURCE_BOUND_SENSITIVITY"
            or sensitivity.get("scenario") not in (BASELINE, STRESS)
            or sensitivity.get("third_action_id") != expected_third_action_id
            or sensitivity.get("fifth_native_seq") != expected_fifth_seq
            or sensitivity.get("native_fatigue_measured") is not False
            or sensitivity.get("action_permission") is not False
            or sensitivity.get("source_bound_tick") is not None
            or sensitivity.get("additional_issuers") != 0
            or sensitivity.get("additional_native_receivers") != 0
            or sensitivity.get("qualification_go") is not False
            or sensitivity.get("science_go") is not False
            or sensitivity.get("original_nominal_duration_s")
            != MOVE_BACKWARD_DURATION_S
            or issued.duration_s != MOVE_BACKWARD_DURATION_S
            or issued.action_ref != "MOVE_BACKWARD"
            or issued.control != "back"
            or issued.cleanup_action_id == issued.action_id):
        raise BoundaryRejected("P1 envelope lacks original issued Action/native source")
    native_event = sixth_probe.request_id.rsplit("event-", 1)[-1]
    if (not native_event.isdecimal()
            or issued.action_id != f"s49-native-move-{native_event}"):
        raise BoundaryRejected("P1 envelope mismatches sixth issued Action ID")
    duration = sensitivity.get("duration_s")
    if (type(duration) is not float
            or not math.isfinite(duration)
            or not 0 < duration < MOVE_BACKWARD_DURATION_S):
        raise BoundaryRejected("P1 envelope duration must be bounded model output")
    profile_sha = sensitivity.get("hypothetical_profile_sha256")
    if not isinstance(profile_sha, str) or len(profile_sha) != 64:
        raise BoundaryRejected("P1 envelope model profile hash missing")
    envelope = DevMotorEnvelope(
        sixth_probe.session_id, sixth_probe.seq, expected_fifth_seq,
        issued.action_id, expected_third_action_id, sensitivity["scenario"],
        profile_sha, False, MOVE_BACKWARD_DURATION_S, duration,
    )
    return replace(issued, duration_s=duration), envelope
