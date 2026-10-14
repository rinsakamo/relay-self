"""M0.1 offline physical invariants; NOT authentic Minecraft evidence."""
from __future__ import annotations

import math

import pytest

from experiments.metabolism_m01_minecraft import (
    AdmittedFood, M01Profile, M01Rejected, WorldTickSample, advance,
    balance_residual, begin, ecological_ratios,
)


def config(**overrides):
    fields = {
        "profile_id": "offline-candidate-only", "capacity": 20.0,
        "initial_energy": 10.0, "basal_per_world_tick": 0.1,
        "movement_per_block": 1.0,
        "food_energy": (("rotten_flesh", 4.0), ("bread", 6.0)),
        "max_displacement_per_tick": 1.0,
    }
    fields.update(overrides)
    return M01Profile(**fields)


def sample(tick, x=0, *, session="s", food=()):
    return WorldTickSample(session, tick, (float(x), 0.0, 0.0), tuple(food))


def meal(action="a", session="s", item="rotten_flesh"):
    return AdmittedFood(session, action, item, 1, 0, 13, 17)


def test_wait_is_world_tick_based_and_independent_of_decision_count():
    profile = config()
    current = begin(profile, sample(100))
    # Arbitrarily many read-only model/L0 decisions do not advance M0.1.
    assert current == begin(profile, sample(100))
    for tick in range(101, 111):
        result = advance(profile, current, sample(tick))
        current = result.after
    assert current.energy == pytest.approx(9.0)
    assert current.total_basal == pytest.approx(1.0)
    assert current.total_movement == 0
    assert abs(balance_residual(profile, current)) < 1e-9


def test_distance_cost_is_real_displacement_not_action_proposals():
    profile = config()
    root = begin(profile, sample(0))
    still = advance(profile, root, sample(1)).after
    moved = advance(profile, root, sample(1, 0.5)).after
    assert still.energy == pytest.approx(9.9)
    assert moved.energy == pytest.approx(9.4)
    assert moved.total_distance == pytest.approx(0.5)
    assert moved.total_movement == pytest.approx(0.5)


def test_single_consumption_credit_once_exact_energy_balance():
    profile = config()
    root = begin(profile, sample(0))
    paid = advance(profile, root, sample(1, 0.5, food=(meal(),)))
    assert paid.intake == 4
    assert paid.after.energy == pytest.approx(13.4)
    assert paid.after.meals == 1
    assert paid.credited_action_ids == ("a",)
    assert abs(balance_residual(profile, paid.after)) < 1e-9
    with pytest.raises(M01Rejected, match="duplicate"):
        advance(profile, paid.after, sample(2, 0.5, food=(meal(),)))


def test_capacity_overflow_and_irreversible_terminal():
    profile = config(initial_energy=19, basal_per_world_tick=0.5)
    root = begin(profile, sample(0))
    paid = advance(profile, root, sample(1, food=(meal(),)))
    assert paid.overflow == 3
    assert paid.after.energy == 19.5
    assert abs(balance_residual(profile, paid.after)) < 1e-9
    weak = config(initial_energy=0.1, basal_per_world_tick=0.2)
    starved = advance(weak, begin(weak, sample(0)), sample(1))
    assert starved.terminal_now
    assert starved.after.energy == 0
    assert starved.shortfall == pytest.approx(0.1)
    assert abs(balance_residual(weak, starved.after)) < 1e-9
    with pytest.raises(M01Rejected, match="terminal"):
        advance(weak, starved.after, sample(2, food=(meal(),)))


@pytest.mark.parametrize("bad", [
    sample(0), sample(2), sample(1, session="foreign"),
    sample(1, 2), WorldTickSample("s", 1, (float("nan"), 0, 0)),
    sample(1, food=(meal(session="foreign"),)),
    sample(1, food=(meal(item="unknown"),)),
    sample(1, food=(meal("same"), meal("same"))),
])
def test_ambiguous_or_foreign_world_evidence_is_rejected(bad):
    profile = config()
    with pytest.raises(M01Rejected):
        advance(profile, begin(profile, sample(0)), bad)


def test_no_food_finishes_in_fixed_number_of_world_ticks():
    profile = config(initial_energy=0.3, basal_per_world_tick=0.1)
    current = begin(profile, sample(0))
    for tick in (1, 2, 3):
        after = advance(profile, current, sample(tick))
        current = after.after
    assert current.terminal
    assert current.world_tick == 3
    assert abs(balance_residual(profile, current)) < 1e-9


def test_ecological_ratios_diagnostic_no_calibrated_claim():
    profile = config()
    r = ecological_ratios(profile, "rotten_flesh", nominal_blocks_per_tick=0.2,
                          one_way_blocks=2)
    assert r["idle_survival_world_ticks"] == 100
    assert r["meal_idle_world_ticks"] == 40
    assert r["nominal_roundtrip_world_ticks"] == 20
    assert r["nominal_trip_net_energy"] == pytest.approx(-2)
    assert r["active_to_idle_cost_ratio"] == pytest.approx(3)
    with pytest.raises(M01Rejected):
        ecological_ratios(profile, "bread", nominal_blocks_per_tick=0,
                          one_way_blocks=1)


def test_invalid_profiles_fail_closed():
    for kw in (
        {"basal_per_world_tick": 0},
        {"movement_per_block": -1},
        {"capacity": float("nan")},
        {"initial_energy": 21},
        {"food_energy": (("bread", 6), ("bread", 6))},
        {"food_energy": (("rotten_flesh", math.inf),)},
    ):
        with pytest.raises(M01Rejected):
            config(**kw)
