"""P1-A fixed offline physics / negative controls (no runtime or policy)."""

from dataclasses import replace

import pytest

from experiments.fatigue_p1 import (
    FatigueFrame,
    FatigueProfile,
    FatigueRejected,
    FatigueSensor,
    Rate,
    advance,
    capability,
    initial_state,
    observe,
)
from experiments.metabolism_viability import MetabolismConfig, initial_body, metabolism_step


def step(profile, state, activity, **kwargs):
    return advance(profile, state, FatigueFrame(state.session_id, state.world_tick + 1,
                                                activity, **kwargs))


def test_defaults_are_off_and_legacy_action_effects_identical():
    profile = FatigueProfile()
    current = initial_state(profile, "s")
    for action in ("WAIT", "MOVE", "FIGHT"):
        kwargs = {"observed_blocks": 1} if action == "MOVE" else {}
        if action == "FIGHT":
            kwargs = {"observed_fight_events": 1}
        event = step(profile, current, action, **kwargs)
        assert event.after.fatigue == 0
        assert event.capacity_after == event.capacity_before
        assert event.capacity_after.efficiency == 1
        assert event.accumulated == event.recovered == 0
        current = event.after


def test_observed_distance_only_and_blockage_not_requested_block():
    cfg = FatigueProfile(enabled=True)
    state = initial_state(cfg, "s")
    none = step(cfg, state, "MOVE", observed_blocks=0, blocked=True)
    assert none.after.fatigue == 0 and none.frame.blocked
    partial = step(cfg, none.after, "MOVE", observed_blocks=.25, blocked=True)
    assert partial.after.fatigue == pytest.approx(.01)
    whole = step(cfg, partial.after, "MOVE", observed_blocks=1)
    assert whole.after.fatigue == pytest.approx(.05)
    assert whole.frame.blocked is False


def test_wait_recovers_physical_fatigue_every_real_world_tick():
    cfg = FatigueProfile(enabled=True, initial=.8)
    initial = initial_state(cfg, "s")
    first = step(cfg, initial, "WAIT")
    second = step(cfg, first.after, "WAIT")
    assert first.after.fatigue == pytest.approx(.7)
    assert second.after.fatigue == pytest.approx(.6)
    assert second.after.world_tick == 2
    assert first.recovered == pytest.approx(.1)
    assert second.recovered == pytest.approx(.1)
    empty_cfg = replace(cfg, initial=0)
    assert step(empty_cfg, initial_state(empty_cfg, "x"), "WAIT").recovered == 0


def test_wait_recovery_keeps_m0_basal_cost_independently():
    mcfg = MetabolismConfig()
    energy = initial_body(mcfg)
    after_energy = metabolism_step(energy, action="WAIT", consumed_food_units=0, config=mcfg)
    assert after_energy.expenditure == mcfg.basal_cost
    profile = FatigueProfile(enabled=True, initial=.5)
    body = step(profile, initial_state(profile, "m"), "WAIT")
    assert body.after.fatigue == pytest.approx(.4)
    assert after_energy.after.energy == energy.energy - mcfg.basal_cost
    assert not hasattr(body.after, "energy")


def test_blocked_move_does_not_recover_just_because_zero_distance():
    cfg = FatigueProfile(enabled=True, initial=.8)
    state = initial_state(cfg, "blocked")
    t = step(cfg, state, "MOVE", observed_blocks=0, blocked=True)
    assert t.after.fatigue == pytest.approx(.8)
    assert t.recovered == 0
    assert step(cfg, t.after, "WAIT").after.fatigue == pytest.approx(.7)


def test_fatigue_impairs_physical_envelope_without_any_built_in_wait_policy():
    cfg = FatigueProfile(enabled=True, initial=1.0)
    tired = initial_state(cfg, "s")
    c = capability(cfg, tired)
    assert c.efficiency == pytest.approx(.3)
    assert c.max_move_blocks_per_world_tick == pytest.approx(.3)
    assert c.fight_mechanically_possible is False
    recovered = tired
    for _ in range(7):
        recovered = step(cfg, recovered, "WAIT").after
    c2 = capability(cfg, recovered)
    assert c2.max_move_blocks_per_world_tick > c.max_move_blocks_per_world_tick
    assert c2.fight_mechanically_possible
    assert "WAIT" not in vars(c2)  # physical envelope does not command an action


def test_wait_recovery_rates_modifiable_standard_times_multiplier_plus_addition():
    cfg = FatigueProfile(enabled=True, move_per_block=Rate(.04, 2, .02),
                         wait_recovery_per_world_tick=Rate(.1, 2, .05))
    state = initial_state(cfg, "s")
    moving = step(cfg, state, "MOVE", observed_blocks=2)
    assert moving.accumulated == pytest.approx(.20)
    resting = step(cfg, moving.after, "WAIT")
    assert resting.recovered == pytest.approx(.20)  # floor at zero
    assert resting.after.fatigue == 0
    assert cfg.sha256 != FatigueProfile(enabled=True).sha256


def test_saturate_and_floor_and_deterministic_receipt():
    cfg = FatigueProfile(enabled=True, initial=.98)
    s = initial_state(cfg, "s")
    transition = step(cfg, s, "FIGHT", observed_fight_events=1)
    assert transition == step(cfg, s, "FIGHT", observed_fight_events=1)
    assert transition.accumulated == pytest.approx(.02)
    assert transition.after.fatigue == 1
    repeat = transition.after
    for _ in range(12):
        repeat = step(cfg, repeat, "WAIT").after
    assert repeat.fatigue == 0


def test_sensor_is_not_true_state_and_gain_zero_is_blind():
    cfg = FatigueProfile(enabled=True, initial=.87)
    state = initial_state(cfg, "s")
    assert observe(cfg, state, FatigueSensor()).reading == pytest.approx(.9)
    assert observe(cfg, state, FatigueSensor(gain=0, bias=4)).reading == 4
    assert state.fatigue == .87


@pytest.mark.parametrize("kwargs", [
    {"activity": "MOVE", "observed_blocks": -1},
    {"activity": "MOVE", "observed_blocks": float("nan")},
    {"activity": "WAIT", "observed_blocks": 1},
    {"activity": "WAIT", "blocked": True},
    {"activity": "REST"},
    {"activity": "MOVE", "observed_fight_events": 1},
    {"activity": "FIGHT", "observed_fight_events": 1.2},
    {"activity": "FIGHT", "observed_fight_events": True},
    {"activity": "RUN"},
])
def test_bad_provenance_shapes_fail_closed(kwargs):
    profile = FatigueProfile(enabled=True)
    state = initial_state(profile, "s")
    with pytest.raises(FatigueRejected):
        advance(profile, state, FatigueFrame("s", 1, **kwargs))


def test_world_time_and_session_cannot_be_derived_from_action_count():
    cfg = FatigueProfile(enabled=True)
    s = initial_state(cfg, "s", world_tick=41)
    for frame in (FatigueFrame("s", 41, "WAIT"), FatigueFrame("s", 43, "WAIT"),
                  FatigueFrame("other", 42, "WAIT")):
        with pytest.raises(FatigueRejected):
            advance(cfg, s, frame)
    after = step(cfg, s, "WAIT").after
    with pytest.raises(FatigueRejected):
        advance(replace(cfg, move_per_block=Rate(.05)), after,
                FatigueFrame("s", 43, "WAIT"))


@pytest.mark.parametrize("constructor,arguments", [
    (Rate, {"standard": -1}),
    (Rate, {"standard": float("nan")}),
    (Rate, {"standard": 1e308, "multiplier": 1e308}),
    (FatigueProfile, {"capacity": 0}),
    (FatigueProfile, {"enabled": False, "initial": .1}),
    (FatigueProfile, {"minimum_efficiency": -1}),
    (FatigueProfile, {"move_per_block": .3}),
    (FatigueSensor, {"quantum": 0}),
])
def test_bad_profile_rejected(constructor, arguments):
    with pytest.raises(FatigueRejected):
        constructor(**arguments)