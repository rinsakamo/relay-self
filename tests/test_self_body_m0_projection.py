"""#537/#632 B0 owner-local SelfBody/M0 interoception, synthetic DEV-only.

No S49/S51 execution, World, native Action, actual P1 or M0 credit.
"""
from __future__ import annotations

import json
from dataclasses import FrozenInstanceError, replace
from types import SimpleNamespace

import pytest

from adapters.mineflayer import self_demo
from adapters.mineflayer.b0_energy_bridge import B0EnergyLedger
from adapters.mineflayer.self_body_m0_projection import (
    compose_b0_cognition_views,
    summarize_b0_cognition_views,
)
from adapters.mineflayer.self_body_p1_projection import P1OwnerSensorHandoff
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


def test_b0_cognition_epoch_summary_exposes_sensor_only():
    probe, ledger, decision = prepared()
    summary = summarize_b0_cognition_views(project(probe, ledger, decision))
    assert summary["classification"] == "DEV_ONLY_PRODUCER_LOCAL_M0_INTEROCEPTION"
    assert summary["native_source"] == (
        f"native-probe:{probe.session_id}:{probe.seq}:{probe.request_id}"
    )
    assert summary["world_source"] == (
        f"present:{probe.session_id}:{probe.seq}:{probe.request_id}"
    )
    assert summary["m0_energy_sensor"] == decision.sensor_reading
    assert summary["native_food"] == probe.snapshot.food
    assert summary["p1_fatigue"] is None
    assert summary["true_m0_energy_exposed"] is False
    assert summary["additional_native_reads"] == summary["additional_actions"] == 0
    assert "energy" not in summary and "true_m0_energy" not in summary


@pytest.mark.parametrize("attack", (
    None, "source", "sensor", "out_of_order", "p1_forged", "missing",
))
def test_b0_dev_appetite_epoch_trace_needs_all_native_and_sensor_sources(
    monkeypatch, tmp_path, attack,
):
    from test_self_dev import args as dev_args

    monkeypatch.setattr(self_demo.shutil, "which", lambda _: "/tool")
    monkeypatch.setattr(
        self_demo.subprocess, "run",
        lambda *a, **kw: SimpleNamespace(
            returncode=0, stdout="version", stderr="",
        ),
    )

    async def original_owner(report, server_log):
        sid = "native-s51-dev"
        ledger = B0EnergyLedger(sid)
        views = []
        trace = []
        for n, seq in enumerate((8, 19)):
            probe = replace(
                native_probe(seq, 3.0, sid=sid),
                request_id=f"b0-ground-appetite-{n:02d}",
            )
            decision = ledger.decide(probe)
            assert decision.kind == "WAIT"
            view = compose_b0_cognition_views(
                probe, ledger, decision, self_id="s51-b0-dev-self",
                epoch_id=f"b0-appetite-{seq}",
            )
            views.append(summarize_b0_cognition_views(view))
            trace.append({
                "probe_seq": seq, "kind": decision.kind,
                "food": probe.snapshot.food,
                "energy_sensor_reading": decision.sensor_reading,
                "metabolic_tick": decision.body_tick,
            })
            ledger.step("WAIT")
        last = replace(
            native_probe(47, 3.0, sid=sid),
            request_id="b0-next-l0-native",
        )
        decision = ledger.decide(last)
        next_view = summarize_b0_cognition_views(compose_b0_cognition_views(
            last, ledger, decision, self_id="s51-b0-dev-self",
            epoch_id="b0-next-probe-47",
        ))
        views.append(next_view)
        if attack == "source":
            views[0]["native_source"] = "native-probe:other:8:foreign"
        elif attack == "sensor":
            views[1]["m0_energy_sensor"] += 7
        elif attack == "out_of_order":
            views[0]["source_seq"] = 70
        elif attack == "p1_forged":
            views[0]["p1_fatigue"] = 0.0
        body = {
            "status": "PASS",
            "classification": "QUALIFIED",
            "session_id": sid,
            "server_exit": 0, "node_exit": 0,
            "ground_pickup": {"movement_outcomes": []},
            "ground_appetite_trace": trace,
            "next_native_probe": {
                "session_id": sid, "seq": 47,
                "request_id": "b0-next-l0-native",
                "snapshot": {
                    "food": last.snapshot.food, "health": last.snapshot.health,
                },
            },
            "next_l0": {
                "kind": decision.kind,
                "energy_sensor_reading": decision.sensor_reading,
            },
            "metabolism_after_eat": {
                "tick": ledger.body.tick, "credit_count": 0,
            },
            "dev_b0_cognition_next_epoch": next_view,
        }
        if attack != "missing":
            body["dev_b0_cognition_epochs"] = views
        report.write_text(json.dumps(body), encoding="utf-8")
        return 0

    monkeypatch.setattr(self_demo, "_run_b0_ground_dev", original_owner)
    opts = dev_args(tmp_path / (attack or "joined"))
    opts.dev_scenario = "b0-ground"
    result = self_demo._dev_run(opts)
    receipt = json.loads((opts.output_dir / "dev_receipt.json").read_text())
    assert result == (1 if attack not in (None, "missing") else 0)
    assert receipt["dev_b0_cognition_epoch_trace"] == (
        "ORDERED_PRODUCER_LOCAL_DEV" if attack is None
        else "NOT_OBSERVED" if attack == "missing"
        else "UNDETERMINED"
    )
    assert receipt["dev_b0_cognition_epoch_count"] == (
        3 if attack is None else 0
    )
    assert receipt["classification"] == "DEV_ONLY"
    assert receipt["engineering_qualified"] is False
    assert receipt["science_success"] is False
    assert receipt["m_energy_credited"] is False
    assert (opts.output_dir / "SHA256SUMS").is_file()


def _p1_owner_handoff(probe, **changes):
    """Synthetic only: the proposed P1 owner report is NOT World attested."""
    payload = dict(
        session_id=probe.session_id,
        native_seq=probe.seq,
        native_request_id=probe.request_id,
        owner_world_tick=41,
        profile_sha256="a" * 64,
        world_source_ref="p1-owner-dev:tick-41",
        sensor_reading=0.4,
        activity="WAIT",
        wait_interval_ref="p1-owner-dev:full-tick-idle-41",
    )
    payload.update(changes)
    return P1OwnerSensorHandoff(**payload)


def test_optional_p1_sensor_joins_same_body_world_without_wait_grant():
    probe, owner, decision = prepared()
    energy_before = owner.body
    p1 = _p1_owner_handoff(probe)
    joined = compose_b0_cognition_views(
        probe, owner, decision,
        self_id="dev-b0-self", epoch_id="epoch-8", p1_handoff=p1,
    )
    body, world = joined.body, joined.world
    summary = summarize_b0_cognition_views(joined)
    assert world.self_body is body
    assert body.observed("food").origin is BodyOrigin.OBSERVATION
    assert body.sensed("m0_energy_sensor").value == decision.sensor_reading
    reading = body.sensed("p1_fatigue_sensor")
    assert reading.origin is BodyOrigin.INTEROCEPTION
    assert reading.value == 0.4
    assert reading.source_refs[0] == body.observation.source_ref
    assert reading.provenance[-1].source == "p1-owner-local-unattested-sensor"
    assert body.observed("p1_fatigue").origin is BodyOrigin.UNKNOWN
    assert summary["p1_fatigue"] == 0.4
    assert summary["p1_sensor_origin"] == "interoception"
    assert summary["p1_source_scope"] == "PRODUCER_LOCAL_UNATTESTED"
    assert summary["qualification"] is False
    assert summary["additional_native_reads"] == 0
    assert summary["additional_actions"] == 0
    assert owner.body is energy_before  # no physical P1/M0 transition
    assert owner.credit_count == 0
    assert owner._last_decision_seq == probe.seq
    assert not hasattr(joined, "authorize_action")
    assert not hasattr(joined, "reconcile_wait")


def test_absent_p1_owner_keeps_unknown_and_existing_b0_path():
    probe, owner, decision = prepared()
    baseline = project(probe, owner, decision)
    s = summarize_b0_cognition_views(baseline)
    assert s["p1_fatigue"] is None
    assert s["p1_sensor_origin"] == "unknown"
    assert s["p1_source_scope"] == "UNKNOWN"
    assert len(baseline.body.interoceptions) == 1
    assert baseline.body.sensed("p1_fatigue_sensor").origin is BodyOrigin.UNKNOWN


@pytest.mark.parametrize("attack", [
    "session", "seq", "request", "tick_negative", "tick_bool",
    "profile_foreign", "world_ref_missing", "nan", "infinite",
    "bool_reading", "rest", "wait_without_interval",
    "move_with_wait_witness", "fight_with_wait_witness",
])
def test_p1_sensor_handoff_rejects_foreign_or_forged_correlation(attack):
    probe, owner, decision = prepared()
    changes = {
        "session": {"session_id": "foreign"},
        "seq": {"native_seq": probe.seq + 1},
        "request": {"native_request_id": "another-request"},
        "tick_negative": {"owner_world_tick": -1},
        "tick_bool": {"owner_world_tick": True},
        "profile_foreign": {"profile_sha256": "not-a-profile"},
        "world_ref_missing": {"world_source_ref": ""},
        "nan": {"sensor_reading": float("nan")},
        "infinite": {"sensor_reading": float("inf")},
        "bool_reading": {"sensor_reading": True},
        "rest": {"activity": "REST"},
        "wait_without_interval": {"wait_interval_ref": None},
        "move_with_wait_witness": {"activity": "MOVE"},
        "fight_with_wait_witness": {"activity": "FIGHT"},
    }[attack]
    before = owner.body
    with pytest.raises(InvalidSelfBodyData):
        compose_b0_cognition_views(
            probe, owner, decision,
            self_id="dev-b0-self", epoch_id="epoch-8",
            p1_handoff=_p1_owner_handoff(probe, **changes),
        )
    assert owner.body is before and owner.credit_count == 0


def test_p1_move_uses_no_idle_witness_and_cannot_claim_wait_recovery():
    probe, owner, decision = prepared()
    p1 = _p1_owner_handoff(
        probe, activity="MOVE", wait_interval_ref=None,
    )
    joined = compose_b0_cognition_views(
        probe, owner, decision,
        self_id="dev-b0-self", epoch_id="epoch-8", p1_handoff=p1,
    )
    reading = joined.body.sensed("p1_fatigue_sensor")
    assert reading.value == 0.4
    assert "MOVE" in reading.provenance[-1].reference
    assert not hasattr(joined, "recovered")
    assert not hasattr(joined.body, "physical_wait_authorized")
