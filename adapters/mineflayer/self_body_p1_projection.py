"""Candidate P1 sensor -> SelfBody adapter; no physical WAIT authentication.

The P1 owner is Draft #626, *not* duplicated here. A supplied source pointer
cannot certify full-tick idle behavior; S/R must attest it independently.
This module never calculates fatigue, recovers WAIT, changes M0, or issues Action.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from adapters.mineflayer.present_projection import MinecraftPresent
from relay_self.provenance import Provenance
from relay_self.self_body import BodyField, BodyInteroception, InvalidSelfBodyData


@dataclass(frozen=True, slots=True)
class P1OwnerSensorHandoff:
    """Owner-exported P1 sensor joined to a later received native probe.

    Source/time/correlation fields are *claims*. This handoff is NOT a
    substitute for S/R authentication of a full physical World tick.
    The fatigue reading is a quantized/blindable sensor, never true Fatigue.
    """

    session_id: str
    native_seq: int
    native_request_id: str
    owner_world_tick: int
    profile_sha256: str
    world_source_ref: str
    sensor_reading: float
    activity: str
    wait_interval_ref: str | None = None


def project_p1_sensor(
    present: MinecraftPresent, handoff: P1OwnerSensorHandoff,
) -> BodyInteroception:
    """Correlate one P1 sensor to Present without promoting physical proof."""
    if not isinstance(present, MinecraftPresent) or not isinstance(
        handoff, P1OwnerSensorHandoff
    ):
        raise InvalidSelfBodyData("P1 needs typed native Present and owner handoff")
    if (
        handoff.session_id != present.session_id
        or type(handoff.native_seq) is not int or handoff.native_seq != present.seq
        or handoff.native_request_id != present.request_id
        or not isinstance(handoff.native_request_id, str)
        or type(handoff.owner_world_tick) is not int or handoff.owner_world_tick < 0
        or not isinstance(handoff.profile_sha256, str)
        or len(handoff.profile_sha256) != 64
        or any(ch not in "0123456789abcdef" for ch in handoff.profile_sha256)
        or not isinstance(handoff.world_source_ref, str)
        or not handoff.world_source_ref.strip()
        or type(handoff.sensor_reading) not in (int, float)
        or not math.isfinite(handoff.sensor_reading)
        or handoff.activity not in ("WAIT", "MOVE", "FIGHT")
        or present.provenance.source != "mineflayer"
        or present.provenance.reference != f"{present.session_id}:{present.seq}"
    ):
        raise InvalidSelfBodyData("P1 owner profile/time/native source mismatch")
    if handoff.activity == "WAIT":
        if (
            not isinstance(handoff.wait_interval_ref, str)
            or not handoff.wait_interval_ref.strip()
        ):
            raise InvalidSelfBodyData("P1 WAIT needs an original idle witness pointer")
    elif handoff.wait_interval_ref is not None:
        raise InvalidSelfBodyData("P1 MOVE/FIGHT cannot carry a WAIT witness")
    # The source/ref is only a correlation pointer: a string alone proves
    # neither physical inactivity nor a genuine P1 transition.
    origin = Provenance(
        "p1-owner-local-unattested-sensor",
        f"{handoff.profile_sha256}:{handoff.owner_world_tick}:"
        f"{handoff.activity}:{handoff.world_source_ref}",
    )
    return BodyInteroception(
        field=BodyField("p1_fatigue_sensor", handoff.sensor_reading),
        session_id=present.session_id,
        native_seq=present.seq,
        request_id=present.request_id,
        native_provenance=present.provenance,
        owner_tick=handoff.owner_world_tick,
        owner_provenance=origin,
    )
