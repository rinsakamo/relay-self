"""M1 resource estimates: OFFLINE_ONLY; never an actual World receipt."""
from dataclasses import replace
from pathlib import Path

import pytest

from experiments.fatigue_p1 import FatigueProfile, Rate
from experiments.fatigue_p1 import initial_state as initial_fatigue
from experiments.metabolism_m01_minecraft import M01Profile, WorldTickSample, begin
from experiments.metabolism_m02_exhaustion import load_profile
from experiments.metabolism_resource_projection import (
    Candidate,
    quote_candidate,
    quote_m02_exhaustion,
    visible_costs,
)
from experiments.metabolism_viability import EnergyObservation


@pytest.fixture
def physical():
    profile = M01Profile(
        profile_id="m-test", capacity=20.0, initial_energy=8.0,
        basal_per_world_tick=0.1, movement_per_block=0.3,
        food_energy=(("rotten_flesh", 3.5), ("cooked_beef", 5.0)),
    )
    return profile, begin(profile, WorldTickSample("s", 10, (0.0, 0.0, 0.0)))


@pytest.fixture
def fatigue():
    profile = FatigueProfile(
        enabled=True, initial=0.5, move_per_block=Rate(0.04),
        wait_recovery_per_world_tick=Rate(0.1),
    )
    return profile, initial_fatigue(profile, "s", world_tick=10)


def test_wait_pays_basal_while_p1_recovers_without_energy_refill(physical, fatigue):
    profile, body = physical
    fp, fs = fatigue
    q = quote_candidate(profile, body, Candidate("rest", "WAIT", wait_ticks=3),
                        fatigue_profile=fp, fatigue_state=fs)
    assert q.status == "ESTIMATED_FEASIBLE"
    assert q.world_ticks == 3
    assert q.basal_energy == pytest.approx(0.3)
    assert q.movement_energy == 0
    assert q.projected_energy_after == pytest.approx(7.7)
    assert q.projected_fatigue_after == pytest.approx(0.2)
    assert body.energy == 8.0 and fs.fatigue == 0.5


def test_move_charges_measured_length_and_world_time_not_one_action(physical, fatigue):
    profile, body = physical
    fp, fs = fatigue
    q = quote_candidate(profile, body, Candidate("forage", "MOVE", distance_blocks=4.0,
                                                  nominal_blocks_per_tick=0.5),
                        fatigue_profile=fp, fatigue_state=fs)
    assert q.status == "ESTIMATED_FEASIBLE"
    assert q.world_ticks == 8
    assert q.movement_energy == pytest.approx(1.2)
    assert q.basal_energy == pytest.approx(0.8)
    assert q.required_energy == pytest.approx(2.0)
    assert q.projected_energy_after == pytest.approx(6.0)
    assert q.projected_fatigue_after > fs.fatigue


def test_same_world_different_energy_changes_viability_not_policy(physical):
    profile, body = physical
    choice = Candidate("goal", "MOVE", distance_blocks=5.0,
                       nominal_blocks_per_tick=0.5)
    full = quote_candidate(profile, body, choice)
    low = quote_candidate(profile, replace(body, energy=1.0), choice)
    assert full.required_energy == low.required_energy
    assert full.status == "ESTIMATED_FEASIBLE"
    assert low.status == "ESTIMATED_EXHAUSTION"
    assert low.projected_energy_after == 0


def test_exact_energy_boundary_is_terminal_risk(physical):
    profile, body = physical
    q = quote_candidate(profile, replace(body, energy=0.1),
                        Candidate("idle", "WAIT", wait_ticks=1))
    assert q.status == "ESTIMATED_EXHAUSTION"
    assert q.projected_energy_after == 0


def test_blocked_move_is_not_wait_fatigue_recovery(physical, fatigue):
    profile, body = physical
    fp, fs = fatigue
    q = quote_candidate(profile, body, Candidate("blocked", "MOVE",
                        distance_blocks=0.0, nominal_blocks_per_tick=0.5),
                        fatigue_profile=fp, fatigue_state=fs)
    assert q.world_ticks == 1 and q.basal_energy == pytest.approx(0.1)
    assert q.movement_energy == 0.0
    assert q.projected_fatigue_after == fs.fatigue


def test_unknown_route_and_speed_do_not_become_zero_cost(physical):
    profile, body = physical
    for c in (Candidate("missing-route", "MOVE", nominal_blocks_per_tick=0.5),
              Candidate("missing-speed", "MOVE", distance_blocks=3.0)):
        q = quote_candidate(profile, body, c)
        assert q.status == "UNKNOWN"
        assert q.required_energy is None and q.projected_energy_after is None


def test_horizon_and_invalid_physical_state_fail_closed(physical):
    profile, body = physical
    long_wait = quote_candidate(profile, body, Candidate("wait", "WAIT", wait_ticks=513))
    assert long_wait.status == "UNKNOWN"
    with pytest.raises(ValueError):
        quote_candidate(profile, replace(body, terminal=True), Candidate("wait", "WAIT", wait_ticks=1))
    with pytest.raises(ValueError):
        quote_candidate(profile, replace(body, energy=0), Candidate("wait", "WAIT", wait_ticks=1))
    with pytest.raises(ValueError):
        quote_candidate(replace(profile, profile_id="other"), body, Candidate("wait", "WAIT", wait_ticks=1))


def test_p1_source_and_profile_fences(physical, fatigue):
    profile, body = physical
    fp, fs = fatigue
    c = Candidate("wait", "WAIT", wait_ticks=1)
    for invalid in (replace(fs, world_tick=9), replace(fs, session_id="foreign")):
        with pytest.raises(ValueError):
            quote_candidate(profile, body, c, fatigue_profile=fp, fatigue_state=invalid)
    with pytest.raises(ValueError):
        quote_candidate(profile, body, c, fatigue_profile=fp)


def test_sensor_public_view_never_exports_true_energy_or_evaluator_status(physical):
    profile, body = physical
    c = Candidate("goal", "MOVE", distance_blocks=5, nominal_blocks_per_tick=0.5)
    private = quote_candidate(profile, replace(body, energy=1.0), c)
    public = visible_costs("s", EnergyObservation(tick=10, reading=3.0), (private,))
    assert public.observed_energy_reading == 3.0
    assert public.quotes[0].estimated_energy_cost == private.required_energy
    assert not hasattr(public.quotes[0], "status")
    assert not hasattr(public.quotes[0], "projected_energy_after")
    assert "OFFLINE" in public.source_scope
    with pytest.raises(ValueError):
        visible_costs("s", EnergyObservation(tick=11, reading=3.0), (private,))
    with pytest.raises(ValueError):
        visible_costs("other", EnergyObservation(tick=10, reading=3.0), (private,))


def test_m02_is_separate_exhaustion_unit_and_requires_explicit_land_gait(physical):
    profile, body = physical
    native = load_profile(Path(__file__).resolve().parents[1] /
                          "experiments/config/m02_relay_ecology_v1.json")
    q = quote_candidate(profile, body, Candidate("walk", "MOVE", distance_blocks=2,
                                                 nominal_blocks_per_tick=0.5))
    assert quote_m02_exhaustion(native, q) is None
    assert quote_m02_exhaustion(native, q, land_gait="WALK") == pytest.approx(0.024)
    assert quote_m02_exhaustion(native, q, land_gait="SPRINT") == pytest.approx(0.204)
    idle = quote_candidate(profile, body, Candidate("wait", "WAIT", wait_ticks=2))
    assert quote_m02_exhaustion(native, idle) == pytest.approx(0.002)
    unknown = quote_candidate(profile, body, Candidate("unknown", "MOVE"))
    assert quote_m02_exhaustion(native, unknown) is None


@pytest.mark.parametrize("bad", [
    lambda: Candidate("", "WAIT", wait_ticks=1),
    lambda: Candidate("bad", "WAIT", wait_ticks=0),
    lambda: Candidate("bad", "WAIT", wait_ticks=True),
    lambda: Candidate("bad", "MOVE", distance_blocks=-1),
    lambda: Candidate("bad", "MOVE", distance_blocks=float("nan")),
    lambda: Candidate("bad", "MOVE", distance_blocks=1, nominal_blocks_per_tick=0),
    lambda: Candidate("bad", "MOVE", distance_blocks=1, nominal_blocks_per_tick=True),
    lambda: Candidate("bad", "RUN", distance_blocks=1, nominal_blocks_per_tick=1),
])
def test_invalid_candidates_reject(bad):
    with pytest.raises(ValueError):
        bad()
