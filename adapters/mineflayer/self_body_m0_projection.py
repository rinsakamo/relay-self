"""DEV-only read of existing B0 M0 sensor alongside native SelfBody/World.

B0 true experimental energy never enters native observation. This is not a
physical fatigue P1 implementation, another M0 owner or an Action permission.
"""
from __future__ import annotations

from dataclasses import dataclass

from adapters.mineflayer.b0_energy_bridge import B0Decision, B0EnergyLedger
from adapters.mineflayer.present_projection import project_mineflayer_present
from adapters.mineflayer.self_body_p1_projection import (
    P1OwnerSensorHandoff,
    project_p1_sensor,
)
from adapters.mineflayer.python_protocol import MineflayerObservation
from adapters.mineflayer.self_body_projection import project_body_present
from adapters.mineflayer.self_world_projection import project_self_world_present
from experiments.metabolism_viability import observe_energy
from relay_self.provenance import Provenance
from relay_self.self_body import (
    BodyField,
    BodyInteroception,
    InvalidSelfBodyData,
    SelfBodyView,
    compose_self_body_view,
)
from relay_self.self_world import SelfWorldView, compose_self_world_view


@dataclass(frozen=True, slots=True)
class B0CognitionViews:
    """One passive epoch. The existing B0 L0 decision remains authoritative."""

    world: SelfWorldView
    body: SelfBodyView
    l0_kind: str
    sensor_tick: int
    source_scope: str = "B0_M0_OWNER_LOCAL_DEV_NOT_PHYSICAL_ATTESTATION"


def summarize_b0_cognition_views(views: B0CognitionViews) -> dict[str, object]:
    """Bounded read-only audit. Not a source attestation or energy grant."""
    if not isinstance(views, B0CognitionViews):
        raise InvalidSelfBodyData("typed B0 cognition views required")
    body, world = views.body, views.world
    if body.observation is None or world.observation is None or world.self_body is not body:
        raise InvalidSelfBodyData("body/world not source joined")
    sensing = body.sensed("m0_energy_sensor")
    if sensing.origin.value != "interoception" or len(sensing.provenance) != 2:
        raise InvalidSelfBodyData("M0 owner sensor not bound")
    p1 = body.sensed("p1_fatigue_sensor")
    return {
        "classification": "DEV_ONLY_PRODUCER_LOCAL_M0_INTEROCEPTION",
        "native_source": body.observation.source_ref,
        "world_source": world.observation.source_ref,
        "body_world_same_object": True,
        "source_seq": body.observation.native_seq,
        "l0_kind": views.l0_kind,
        "m0_tick": views.sensor_tick,
        "m0_energy_sensor": sensing.value,
        "m0_sensor_origin": sensing.origin.value,
        "m0_sensor_owner_source": sensing.provenance[-1].source,
        "native_food": body.observed("food").value,
        "native_health": body.observed("health").value,
        "p1_fatigue": p1.value,
        "p1_sensor_origin": p1.origin.value,
        "p1_source_scope": (
            "PRODUCER_LOCAL_UNATTESTED" if p1.value is not None
            else "UNKNOWN"
        ),
        "true_m0_energy_exposed": False,
        "s10_updates": 0,
        "additional_native_reads": 0,
        "additional_actions": 0,
        "qualification": False,
    }


def compose_b0_cognition_views(
    probe: MineflayerObservation,
    ledger: B0EnergyLedger,
    decision: B0Decision,
    *,
    self_id: str,
    epoch_id: str,
    p1_handoff: P1OwnerSensorHandoff | None = None,
) -> B0CognitionViews:
    """Read the already-decided M0 sensor, never re-decide or advance its tick.

    The actual B0 L0 consumed this sensor when deciding. This call provides
    a typed Cognition-facing view of precisely that sensor and native probe.
    """
    if not isinstance(probe, MineflayerObservation) or not isinstance(
        ledger, B0EnergyLedger
    ) or not isinstance(decision, B0Decision):
        raise InvalidSelfBodyData("original typed probe, ledger and L0 decision required")
    present = project_mineflayer_present(probe)
    if (
        not self_id or not epoch_id
        or ledger.session_id != present.session_id
        or ledger.body.terminal
        or decision.probe_seq != present.seq
        or ledger._last_decision_seq != present.seq
        or decision.body_tick != ledger.body.tick
        or present.provenance.reference != f"{present.session_id}:{present.seq}"
        or decision.sensor_reading != observe_energy(ledger.body, ledger.sensor).reading
    ):
        raise InvalidSelfBodyData("foreign, stale, terminal or forged M0 sensor source")
    owner_origin = Provenance(
        "b0-m0-owner-local-sensor",
        f"{present.session_id}:{decision.body_tick}:{decision.probe_seq}:"
        f"{present.request_id}",
    )
    sensor = BodyInteroception(
        field=BodyField("m0_energy_sensor", decision.sensor_reading),
        session_id=present.session_id,
        native_seq=present.seq,
        request_id=present.request_id,
        native_provenance=present.provenance,
        owner_tick=decision.body_tick,
        owner_provenance=owner_origin,
    )
    # P1 is an optional producer-exported, still-unattested sensor. It
    # cannot create physical WAIT evidence, fatigue recovery or M0 credit.
    sensors = (sensor,)
    if p1_handoff is not None:
        sensors += (project_p1_sensor(present, p1_handoff),)
    body = compose_self_body_view(
        self_id=self_id,
        session_id=present.session_id,
        epoch_id=epoch_id,
        observation=project_body_present(present),
        interoceptions=sensors,
    )
    world = compose_self_world_view(
        self_id=self_id,
        session_id=present.session_id,
        epoch_id=epoch_id,
        observation=project_self_world_present(present, observer_id=self_id),
        self_body=body,
    )
    if (
        world.self_body is not body
        or world.observation is None
        or body.observation is None
        or world.observation.native_seq != body.observation.native_seq
        or world.observation.request_id != body.observation.request_id
        or world.observation.provenance != body.observation.source_provenance
    ):
        raise InvalidSelfBodyData("B0 Body/World original native epoch did not join")
    return B0CognitionViews(world, body, decision.kind, decision.body_tick)
