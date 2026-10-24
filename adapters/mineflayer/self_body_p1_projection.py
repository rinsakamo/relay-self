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


@dataclass(frozen=True, slots=True)
class P1NativeCorrelation:
    """S/R-provided exact tick/probe pairing; a claim, not attestation."""

    session_id: str
    native_seq: int
    native_request_id: str
    world_tick: int
    world_source_ref: str


def handoff_from_p1_owner_readout(
    present: MinecraftPresent,
    readout: object,
    correlation: P1NativeCorrelation,
) -> P1OwnerSensorHandoff:
    """Accept ONLY the original P1 #626 producer's checked sensor readout.

    P1 #626 is a separate unmerged owner: until its original modules are
    integrated into the product checkout, this path fails closed. Even an
    original P1 typed readout is producer-local, not authenticated physical
    World evidence or permission for WAIT recovery.
    """
    try:
        from experiments.p1_selfbody_export import P1SelfBodyReadout
    except ImportError as exc:
        raise InvalidSelfBodyData("P1 owner exporter not integrated") from exc
    if not isinstance(readout, P1SelfBodyReadout):
        raise InvalidSelfBodyData("original P1 typed sensor export required")
    if readout.source_scope != "P1_PRODUCER_LOCAL_NOT_WORLD_ATTESTED":
        raise InvalidSelfBodyData("P1 readout cannot claim source attestation")
    if not isinstance(present, MinecraftPresent) or not isinstance(
        correlation, P1NativeCorrelation
    ):
        raise InvalidSelfBodyData("typed native Present and S/R tick correlation required")
    if (
        correlation.session_id != present.session_id
        or correlation.session_id != readout.session_id
        or type(correlation.native_seq) is not int
        or correlation.native_seq != present.seq
        or correlation.native_request_id != present.request_id
        or type(correlation.world_tick) is not int
        or correlation.world_tick != readout.world_tick
        or not isinstance(correlation.world_source_ref, str)
        or correlation.world_source_ref != readout.world_source_ref
    ):
        raise InvalidSelfBodyData("P1 owner tick not correlated to this native probe")
    handoff = P1OwnerSensorHandoff(
        session_id=readout.session_id,
        native_seq=present.seq,
        native_request_id=present.request_id,
        owner_world_tick=readout.world_tick,
        profile_sha256=readout.profile_sha256,
        world_source_ref=readout.world_source_ref,
        sensor_reading=readout.sensor_reading,
        activity=readout.activity,
        wait_interval_ref=readout.wait_interval_ref,
    )
    project_p1_sensor(present, handoff)  # validate source/probe shape
    return handoff


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
