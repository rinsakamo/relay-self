"""M #616: route ranges and cheap baselines, not policy or survival evidence."""
from dataclasses import replace

import pytest

from experiments.fatigue_p1 import FatigueProfile
from experiments.fatigue_p1 import initial_state as fatigue_begin
from experiments.metabolism_m01_minecraft import M01Profile, WorldTickSample, begin
from experiments.metabolism_resource_projection import SelfBodyResourceCosts
from experiments.metabolism_route_bounds import (
    RouteBounds,
    compare_route_ranges,
    quote_route_range,
)
from experiments.metabolism_sensed_viability import assess_sensed_costs
from experiments.metabolism_viability import (
    BodyState,
    Interoception,
    observe_energy,
)


@pytest.fixture
def physical():
    profile = M01Profile(
        profile_id="m-route-test", capacity=20, initial_energy=8,
        basal_per_world_tick=0.1, movement_per_block=0.3,
        max_displacement_per_tick=1.0,
        food_energy=(("cooked_beef", 5.0), ("rotten_flesh", 3.5)),
    )
    body = begin(profile, WorldTickSample("r", 100, (0.0, 64.0, 0.0)))
    p1 = FatigueProfile(enabled=False)
    return profile, body, p1, fatigue_begin(p1, "r", world_tick=100)


def route(label="food", destination="FOOD_OPPORTUNITY", **changes):
    data = {
        "label": label, "destination": destination,
        "min_blocks": 5.0, "max_blocks": 5.0,
        "min_blocks_per_tick": 0.5, "max_blocks_per_tick": 0.5,
        "min_extra_wait_ticks": 0, "max_extra_wait_ticks": 0,
        "min_extra_energy": 0.0, "max_extra_energy": 0.0,
    }
    data.update(changes)
    return RouteBounds(**data)


def project(physical, option):
    profile, body, p1, p1_state = physical
    return quote_route_range(
        profile, body, option, fatigue_profile=p1, fatigue_state=p1_state
    )


def sensed(physical, true_energy, sensor=None, noise_bound=0):
    profile, _, _, _ = physical
    sensor = sensor or Interoception(quantum=1.0)
    observed = observe_energy(BodyState(true_energy, tick=100), sensor)
    public = SelfBodyResourceCosts("r", observed.tick, observed.reading, ())
    return assess_sensed_costs(profile, public, sensor, noise_bound=noise_bound)


def test_food_opportunity_requires_real_future_eat_not_prepayment(physical):
    q = project(physical, route())
    assert q.status == "BOUNDED_MODEL"
    assert q.destination == "FOOD_OPPORTUNITY"
    assert q.min_world_ticks == q.max_world_ticks == 10
    assert q.min_energy_cost == pytest.approx(2.5)
    assert q.max_energy_cost == pytest.approx(2.5)
    assert q.future_food_credited is False
    assert not hasattr(q, "meals")
    assert not hasattr(q, "selected_action")
    assert physical[1].energy == 8.0


def test_food_vs_goal_distinguishes_resource_feasibility_not_preference(physical):
    food = project(physical, route())
    goal = project(physical, route("goal", "GOAL",
                                   min_blocks=10, max_blocks=10))
    high = compare_route_ranges(sensed(physical, 8), (food, goal))
    low = compare_route_ranges(sensed(physical, 3), (food, goal))
    assert [x.affordability for x in high.results] == [
        "MODEL_AFFORDABLE_ALL_BOUNDS", "MODEL_AFFORDABLE_ALL_BOUNDS"
    ]
    assert [x.affordability for x in low.results] == [
        "MODEL_AFFORDABLE_ALL_BOUNDS", "MODEL_INSUFFICIENT_ALL_BOUNDS"
    ]
    assert [x.max_energy_cost for x in low.results] == pytest.approx([2.5, 5])
    assert not hasattr(low, "choice")
    assert not hasattr(low, "reward")


def test_bounded_distance_time_wait_and_hazard_costs(physical):
    q = project(physical, route(
        min_blocks=4, max_blocks=6,
        min_blocks_per_tick=0.4, max_blocks_per_tick=0.8,
        min_extra_wait_ticks=0, max_extra_wait_ticks=3,
        min_extra_energy=0.0, max_extra_energy=0.5,
    ))
    assert q.status == "BOUNDED_MODEL"
    assert q.min_world_ticks == 5
    assert q.max_world_ticks == 18
    assert q.min_energy_cost == pytest.approx(1.7)
    assert q.max_energy_cost == pytest.approx(4.1)
    mid = compare_route_ranges(sensed(physical, 3), (q,))
    assert mid.results[0].affordability == "MODEL_AMBIGUOUS"


def test_missing_cost_and_delay_bounds_are_unknown_not_free(physical):
    for changes in (
        {"min_extra_energy": None},
        {"max_extra_energy": None},
        {"max_extra_wait_ticks": None},
        {"min_blocks": None},
        {"max_blocks_per_tick": None},
    ):
        q = project(physical, route(**changes))
        assert q.status == "UNKNOWN"
        assert q.min_energy_cost is None
        assert q.max_energy_cost is None
        assert compare_route_ranges(sensed(physical, 8), (q,)).results[
            0
        ].affordability == "UNKNOWN"


def test_uncertified_g4_speed_and_missing_p1_are_unknown(physical):
    profile, state, p1, p1_state = physical
    fast = project(physical, route(max_blocks_per_tick=1.5))
    assert fast.status == "UNKNOWN"
    assert fast.reason == "UNQUALIFIED_GAIT_RATE"
    no_p1 = quote_route_range(profile, state, route())
    assert no_p1.status == "UNKNOWN"
    assert no_p1.reason == "UNKNOWN_P1_FATIGUE_STATE"
    assert p1_state.world_tick == state.world_tick
    with pytest.raises(ValueError):
        quote_route_range(profile, state, route(), fatigue_state=p1_state)


def test_blind_and_noisy_sensing_never_mint_viability(physical):
    q = project(physical, route())
    blind = Interoception(gain=0, bias=3)
    result = compare_route_ranges(sensed(physical, 8, blind), (q,))
    assert result.results[0].affordability == "UNKNOWN"
    ambiguous = compare_route_ranges(
        sensed(physical, 3, Interoception(quantum=1), noise_bound=2), (q,)
    )
    assert ambiguous.results[0].affordability == "MODEL_AMBIGUOUS"


def test_cheap_distance_only_baseline_misses_basal_and_time(physical):
    profile, _, _, _ = physical
    q = project(physical, route())
    cheap_cost = 5 * profile.movement_per_block
    assert cheap_cost == pytest.approx(1.5)
    assert q.min_energy_cost == pytest.approx(2.5)
    # Cheap distance-only would incorrectly label E=2 as sufficient.
    assert cheap_cost < 2.0 < q.min_energy_cost
    result = compare_route_ranges(sensed(physical, 2), (q,))
    assert result.results[0].affordability == "MODEL_INSUFFICIENT_ALL_BOUNDS"
    # This is a model failure case, not an empirical survival comparison.


def test_route_equality_with_sensed_energy_is_insufficient(physical):
    q = project(physical, route())
    # Exact-reading sensor (zero quantum error only approximately) deliberately
    # choose a narrow quantum and an energy value exactly at route model cost.
    narrow = Interoception(quantum=0.000001)
    result = compare_route_ranges(sensed(physical, 2.5, narrow), (q,))
    assert result.results[0].affordability == "MODEL_AMBIGUOUS"


def test_stale_cross_session_foreign_and_fake_food_credit_rejected(physical):
    q = project(physical, route())
    s = sensed(physical, 8)
    for forged in (
        replace(q, owner_world_tick=99),
        replace(q, session_id="foreign"),
        replace(q, future_food_credited=True),
        replace(q, source_scope="WORLD_ATTESTED"),
        replace(q, min_energy_cost=-1),
        replace(q, min_world_ticks=0),
        replace(q, max_energy_cost=1),
        replace(q, status="UNKNOWN"),
    ):
        with pytest.raises(ValueError):
            compare_route_ranges(s, (forged,))
    with pytest.raises(ValueError):
        compare_route_ranges(s, (q, q))
    with pytest.raises(ValueError):
        compare_route_ranges(replace(s, source_scope="REAL_WORLD"), (q,))


@pytest.mark.parametrize("changes", [
    {"min_blocks": -1},
    {"max_blocks": float("nan")},
    {"max_blocks": 4},
    {"min_blocks_per_tick": 0},
    {"max_blocks_per_tick": 0},
    {"min_blocks_per_tick": 0.9, "max_blocks_per_tick": 0.5},
    {"min_extra_wait_ticks": True},
    {"max_extra_wait_ticks": -1},
    {"min_extra_energy": -0.1},
    {"max_extra_energy": float("inf")},
    {"max_extra_energy": -1},
    {"min_extra_wait_ticks": 3, "max_extra_wait_ticks": 1},
])
def test_invalid_assumptions_rejected(changes):
    with pytest.raises(ValueError):
        route(**changes)


def test_zero_distance_no_forced_move_or_food_credit(physical):
    q = project(physical, route(min_blocks=0, max_blocks=0))
    assert q.status == "UNKNOWN"
    assert q.future_food_credited is False
    assert q.min_energy_cost is None


def test_no_true_energy_in_route_comparison_data(physical):
    q = project(physical, route())
    first = compare_route_ranges(sensed(physical, 8), (q,))
    second = compare_route_ranges(sensed(physical, 8), (q,))
    assert first == second
    assert not hasattr(first, "physical_energy")
    assert not hasattr(first.results[0], "true_energy")
    assert not hasattr(first.results[0], "model_energy_after")
