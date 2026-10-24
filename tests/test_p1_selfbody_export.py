"""P1 source-bound sensor export unit tests; synthetic, no original World."""
from dataclasses import replace

import pytest

from experiments.fatigue_p1 import FatigueProfile, FatigueSensor, initial_state
from experiments.fatigue_p1_boundary import (
    P1BoundaryRejected,
    SActivityRequest,
    SourceBoundTick,
    preflight,
    reconcile,
)
from experiments.p1_selfbody_export import export_p1_sensed_tick


def make_wait():
    profile = FatigueProfile(enabled=True, initial=0.8)
    before = initial_state(profile, "p1-session", world_tick=10)
    request = SActivityRequest("p1-session", 10, "WAIT")
    cap = preflight(profile, before, request)
    source = SourceBoundTick(
        "p1-session", 11, "WAIT", "paper:11",
        wait_interval_ref="paper-idle:11",
    )
    return profile, before, reconcile(profile, before, cap, source)


def test_wait_sensor_is_separate_from_true_fatigue_and_basal():
    profile, before, tick = make_wait()
    readout = export_p1_sensed_tick(
        profile, before, tick, FatigueSensor(gain=0, bias=3),
    )
    assert tick.transition.recovered == pytest.approx(0.1)
    assert tick.transition.after.fatigue == pytest.approx(0.7)
    assert readout.sensor_reading == 3
    assert readout.world_tick == 11
    assert readout.wait_interval_ref == "paper-idle:11"
    assert readout.profile_sha256 == profile.sha256
    assert readout.source_scope == "P1_PRODUCER_LOCAL_NOT_WORLD_ATTESTED"
    assert "true_fatigue" not in vars(readout)
    assert "energy" not in vars(readout)
    assert "action_grant" not in vars(readout)


def test_blocked_move_is_not_rest_and_has_no_wait_witness():
    profile = FatigueProfile(enabled=True, initial=0.5)
    before = initial_state(profile, "p1-session", world_tick=10)
    request = SActivityRequest(
        "p1-session", 10, "MOVE", requested_blocks=1, action_ref="move-1",
    )
    cap = preflight(profile, before, request)
    source = SourceBoundTick(
        "p1-session", 11, "MOVE", "paper:11",
        observed_blocks=0.0, blocked=True,
        action_ref="move-1", action_effect_ref="paper:move-1:11",
    )
    tick = reconcile(profile, before, cap, source)
    assert tick.transition.recovered == 0
    readout = export_p1_sensed_tick(profile, before, tick, FatigueSensor())
    assert readout.activity == "MOVE"
    assert readout.wait_interval_ref is None
    assert readout.sensor_reading == pytest.approx(0.5)


@pytest.mark.parametrize("attack", [
    "wrong_before", "forged_after", "forged_recovered",
    "wrong_profile", "wrong_tick", "missing_wait", "mixed_move",
])
def test_export_recomputes_and_rejects_unqualified_transition(attack):
    profile, before, tick = make_wait()
    if attack == "wrong_before":
        before = replace(before, world_tick=9)
    elif attack == "forged_after":
        tick = replace(tick, transition=replace(
            tick.transition,
            after=replace(tick.transition.after, fatigue=0.0),
        ))
    elif attack == "forged_recovered":
        tick = replace(tick, transition=replace(
            tick.transition, recovered=0.8,
        ))
    elif attack == "wrong_profile":
        profile = replace(profile, capacity=3.0)
    elif attack == "wrong_tick":
        tick = replace(tick, source=replace(tick.source, world_tick=12))
    elif attack == "missing_wait":
        tick = replace(tick, source=replace(tick.source, wait_interval_ref=None))
    else:
        tick = replace(tick, source=replace(tick.source, action_ref="fake"))
    with pytest.raises((P1BoundaryRejected, ValueError)):
        export_p1_sensed_tick(profile, before, tick, FatigueSensor())
