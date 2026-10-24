"""#537/#632 B0 owner-local SelfBody/M0 interoception, synthetic DEV-only.

No S49/S51 execution, World, native Action, actual P1 or M0 credit.
"""
from __future__ import annotations

from dataclasses import FrozenInstanceError, replace

import pytest

from adapters.mineflayer.b0_energy_bridge import B0EnergyLedger
from adapters.mineflayer.self_body_m0_projection import compose_b0_cognition_views
from experiments.metabolism_viability import Interoception
from relay_self.self_body import (
    BodyOrigin,
    InvalidSelfBodyData,
    compose_self_body_view,
)
from test_self_live_think import native_probe


def prepared(*, sid: str = "dev-b0", sensor: Interoception | None = None):
    probe = native_probe(8, 3.0, sid=sid)
    owner = B0EnergyLedger(sid, sensor=sensor)
    decision = owner.decide(probe)
    return probe, owner, decision


def project(probe, owner, decision):
    return compose_b0_cognition_views(
        probe, owner, decision, self_id="dev-b0-self", epoch_id="epoch-8",
    )


def test_b0_interoception_is_not_physical_world_observation_or_p1():
    probe, ledger, decision = prepared()
    views = project(probe, ledger, decision)
    body, world = views.body, views.world
    assert world.self_body is body
    assert views.l0_kind == decision.kind
    assert views.sensor_tick == decision.body_tick == ledger.body.tick
    assert world.observation.native_seq == body.observation.native_seq == probe.seq
    assert world.observation.provenance == body.observation.source_provenance
    assert body.observed("food").origin is BodyOrigin.OBSERVATION
    assert body.observed("health").origin is BodyOrigin.OBSERVATION
    energy = body.sensed("m0_energy_sensor")
    assert energy.origin is BodyOrigin.INTEROCEPTION
    assert energy.value == decision.sensor_reading
    assert energy.source_refs[0] == body.observation.source_ref
    assert energy.provenance[0] == probe.provenance
    assert energy.provenance[1].source == "b0-m0-owner-local-sensor"
    assert body.observed("energy").origin is BodyOrigin.UNKNOWN
    assert body.observed("m0_energy_sensor").origin is BodyOrigin.UNKNOWN
    assert body.sensed("p1_fatigue").origin is BodyOrigin.UNKNOWN
    assert world.observed_entity("entity-999").value is None
    assert not hasattr(body, "authorize_action")
    assert not hasattr(views, "issue_action")
    with pytest.raises(FrozenInstanceError):
        views.l0_kind = "EAT"


def test_sensor_is_owner_interoception_not_secret_ledger_truth():
    probe, ledger, decision = prepared(
        sensor=Interoception(gain=0.0, bias=17.0, quantum=1.0),
    )
    views = project(probe, ledger, decision)
    sensed = views.body.sensed("m0_energy_sensor")
    assert sensed.value == 17.0
    assert sensed.value != ledger.body.energy
    assert views.body.observed("energy").value is None
    assert views.body.sensed("true_m0_energy").value is None


@pytest.mark.parametrize("attack", (
    "foreign_owner", "foreign_probe", "forged_sensor", "forged_tick",
    "forged_seq", "advanced_tick", "other_epoch", "terminated",
))
def test_sensor_source_or_tick_mismatch_denied(attack):
    probe, ledger, decision = prepared()
    if attack == "foreign_owner":
        ledger = B0EnergyLedger("foreign-session")
    elif attack == "foreign_probe":
        probe = replace(probe, session_id="foreign-session")
    elif attack == "forged_sensor":
        decision = replace(decision, sensor_reading=decision.sensor_reading + 10)
    elif attack == "forged_tick":
        decision = replace(decision, body_tick=decision.body_tick + 1)
    elif attack == "forged_seq":
        decision = replace(decision, probe_seq=decision.probe_seq + 1)
    elif attack == "advanced_tick":
        ledger.step("WAIT")
    elif attack == "other_epoch":
        ledger._last_decision_seq = probe.seq + 1
    else:
        ledger.body = replace(ledger.body, terminal=True)
    with pytest.raises((InvalidSelfBodyData, ValueError)):
        project(probe, ledger, decision)


@pytest.mark.parametrize("tamper", ("session", "seq", "request", "native_provenance"))
def test_core_rejects_interoceptive_source_mismatch(tamper):
    probe, ledger, decision = prepared()
    body = project(probe, ledger, decision).body
    sensor = body.interoceptions[0]
    if tamper == "session":
        sensor = replace(sensor, session_id="other")
    elif tamper == "seq":
        sensor = replace(sensor, native_seq=99)
    elif tamper == "request":
        sensor = replace(sensor, request_id="foreign-request")
    else:
        from relay_self.provenance import Provenance
        sensor = replace(sensor, native_provenance=Provenance("fake", "other"))
    with pytest.raises(InvalidSelfBodyData):
        compose_self_body_view(
            session_id=body.session_id, epoch_id=body.epoch_id,
            self_id=body.self_id, observation=body.observation,
            interoceptions=(sensor,),
        )


def test_interoception_cannot_be_promoted_without_native_present():
    probe, ledger, decision = prepared()
    body = project(probe, ledger, decision).body
    with pytest.raises(InvalidSelfBodyData, match="sensor cannot exist"):
        compose_self_body_view(
            session_id=body.session_id, epoch_id=body.epoch_id,
            interoceptions=body.interoceptions,
        )
