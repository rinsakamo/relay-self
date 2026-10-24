"""Cross-branch P1 #626 + SelfBody #634 wiring in isolated synthetic DEV.

No World, no S/R tick attestation, no actual energy/fatigue source binding.
Original P1 modules in staging are blob-identical to Draft #626.
"""
from dataclasses import replace

import pytest

from adapters.mineflayer.b0_energy_bridge import B0EnergyLedger
from adapters.mineflayer.m02_paper_dev.s50_p1_wait import candidate_wait_ticks
from adapters.mineflayer.present_projection import project_mineflayer_present
from adapters.mineflayer.self_body_m0_projection import (
    compose_b0_cognition_views,
    summarize_b0_cognition_views,
)
from adapters.mineflayer.self_body_p1_projection import (
    P1NativeCorrelation,
    handoff_from_p1_owner_readout,
)
from experiments.fatigue_p1 import FatigueProfile, FatigueSensor, initial_state
from experiments.fatigue_p1_boundary import (
    P1BoundaryRejected,
    SActivityRequest,
    SourceBoundTick,
    preflight,
    reconcile,
)
from experiments.p1_selfbody_export import export_p1_sensed_tick
from relay_self.self_body import BodyOrigin, InvalidSelfBodyData
from test_s50_p1_wait import fixture as s50_wait_fixture
from test_self_live_think import native_probe


def original_wait_p1():
    profile = FatigueProfile(enabled=True, initial=0.8)
    prior = initial_state(profile, "joint-dev", world_tick=40)
    pre = preflight(
        profile, prior, SActivityRequest("joint-dev", 40, "WAIT"),
    )
    source = SourceBoundTick(
        "joint-dev", 41, "WAIT", "paper-dev:world-tick-41",
        wait_interval_ref="paper-dev:full-idle-tick-41",
    )
    tick = reconcile(profile, prior, pre, source)
    export = export_p1_sensed_tick(
        profile, prior, tick, FatigueSensor(gain=0, bias=0.3),
    )
    return profile, prior, tick, export


def native_and_owners(readout):
    probe = native_probe(8, 3.0, sid="joint-dev")
    original_m0 = B0EnergyLedger(probe.session_id)
    decision = original_m0.decide(probe)
    present = project_mineflayer_present(probe)
    correlation = P1NativeCorrelation(
        probe.session_id, probe.seq, probe.request_id,
        readout.world_tick, readout.world_source_ref,
    )
    return probe, original_m0, decision, present, correlation


def test_original_p1_wait_sensor_joins_original_m0_without_two_owners():
    profile, prior, tick, readout = original_wait_p1()
    assert tick.transition.after.fatigue == pytest.approx(0.7)
    assert tick.transition.recovered == pytest.approx(0.1)
    assert readout.sensor_reading == pytest.approx(0.3)  # blind sensor != truth
    probe, m0, decision, present, correlation = native_and_owners(readout)
    handoff = handoff_from_p1_owner_readout(present, readout, correlation)
    old_state = m0.body
    joined = compose_b0_cognition_views(
        probe, m0, decision, self_id="joint-dev-self", epoch_id="epoch-8",
        p1_handoff=handoff,
    )
    body = joined.body
    summary = summarize_b0_cognition_views(joined)
    assert joined.world.self_body is body
    assert body.observed("food").origin is BodyOrigin.OBSERVATION
    assert body.sensed("m0_energy_sensor").origin is BodyOrigin.INTEROCEPTION
    assert body.sensed("p1_fatigue_sensor").origin is BodyOrigin.INTEROCEPTION
    assert body.sensed("p1_fatigue_sensor").value == pytest.approx(0.3)
    assert body.observed("p1_fatigue").value is None
    assert summary["p1_source_scope"] == "PRODUCER_LOCAL_UNATTESTED"
    assert summary["true_m0_energy_exposed"] is False
    assert summary["additional_actions"] == summary["additional_native_reads"] == 0
    assert m0.body is old_state and m0.credit_count == 0
    # M0 basal is still paid on a separate simulated WAIT transition.
    # This does NOT turn M0 decision ticks into P1/Paper World ticks.
    m0.step("WAIT")
    assert m0.body.energy < old_state.energy


@pytest.mark.parametrize("field", (
    "session_id", "native_seq", "native_request_id",
    "world_tick", "world_source_ref",
))
def test_p1_original_readout_requires_explicit_matching_native_tick_pair(field):
    _, _, _, readout = original_wait_p1()
    _, _, _, present, correlation = native_and_owners(readout)
    fake = {
        "session_id": "foreign",
        "native_seq": correlation.native_seq + 1,
        "native_request_id": "foreign-request",
        "world_tick": 42,
        "world_source_ref": "foreign-world-source",
    }[field]
    with pytest.raises(InvalidSelfBodyData, match="not correlated"):
        handoff_from_p1_owner_readout(
            present, readout, replace(correlation, **{field: fake}),
        )


def test_p1_original_reconcile_cannot_mint_forged_recovery():
    profile, prior, tick, _ = original_wait_p1()
    forged = replace(
        tick, transition=replace(tick.transition, recovered=1.0),
    )
    with pytest.raises(P1BoundaryRejected, match="forged"):
        export_p1_sensed_tick(profile, prior, forged, FatigueSensor())


def test_blocked_move_is_never_an_idling_p1_recovery():
    profile = FatigueProfile(enabled=True, initial=0.8)
    before = initial_state(profile, "joint-dev", world_tick=40)
    pre = preflight(profile, before, SActivityRequest(
        "joint-dev", 40, "MOVE", requested_blocks=1, action_ref="move-1",
    ))
    source = SourceBoundTick(
        "joint-dev", 41, "MOVE", "paper-dev:world-tick-41",
        observed_blocks=0, blocked=True, action_ref="move-1",
        action_effect_ref="paper-dev:effect-move-1",
    )
    tick = reconcile(profile, before, pre, source)
    assert tick.transition.recovered == 0
    export = export_p1_sensed_tick(profile, before, tick, FatigueSensor())
    probe, m0, decision, present, correlation = native_and_owners(export)
    handoff = handoff_from_p1_owner_readout(present, export, correlation)
    assert handoff.activity == "MOVE" and handoff.wait_interval_ref is None
    joint = compose_b0_cognition_views(
        probe, m0, decision, self_id="joint-dev-self", epoch_id="epoch-8",
        p1_handoff=handoff,
    )
    assert joint.body.sensed("p1_fatigue_sensor").value == pytest.approx(0.8)
    assert not hasattr(joint, "reconcile_wait")


def test_s50_paper_wait_candidate_cannot_become_p1_authority():
    """Eight Paper point samples never authenticate full-tick WAIT."""
    candidate = candidate_wait_ticks(
        s50_wait_fixture(),
        marker_id="action-session",
        expected_world="world",
        source_action_terminal="outcome",
    )
    assert candidate["source_stationary_8_of_8"] is True
    assert len(candidate["samples"]) == 8
    assert candidate["wait_ticks_admitted"] == 0
    assert candidate["p1_fatigue_recovered"] == 0
    assert candidate["r_full_tick_activity_witness"] == "NOT_ATTESTED"
    assert candidate["r_action_free_interval_witness"] == "NOT_ATTESTED"
    assert candidate["source_original_authenticated_by_r"] is False
    assert candidate["m02_basal_continues"] is True
    assert all(
        x["p1_wait_recovery_admitted"] is False
        and x["full_tick_activity_proven"] is False
        for x in candidate["samples"]
    )
    _, _, _, readout = original_wait_p1()
    _, _, _, present, correlation = native_and_owners(readout)
    # A native S50 candidate is not the original P1 reconciled sensor
    # producer. It cannot be smuggled into the read-only SelfBody bridge.
    with pytest.raises(InvalidSelfBodyData, match="original P1 typed"):
        handoff_from_p1_owner_readout(present, candidate, correlation)
