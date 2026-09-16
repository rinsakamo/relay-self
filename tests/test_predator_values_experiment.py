import random
from collections import Counter
from dataclasses import replace

from experiments.predator_values import (
    Agent,
    RewardGenes,
    SimulationConfig,
    conspecific_sensor,
    intrinsic_reward,
    move_predators,
    observe_state,
    predator_sensor,
    resolve_predation,
    run_simulation,
)


def small_config(**changes: object) -> SimulationConfig:
    return replace(
        SimulationConfig(),
        world_size=20,
        initial_population=10,
        initial_food=4,
        max_food=8,
        **changes,
    )


def prey(agent_id: int, position: int = 4) -> Agent:
    return Agent(
        agent_id=agent_id,
        parent_id=None,
        position=position,
        energy=10.0,
        genes=RewardGenes(0.0, 0.0, 0.0, 0.0),
    )


def test_predator_sensor_is_bounded_and_local() -> None:
    config = small_config(predator_sensor_range=4)
    direction, signal = predator_sensor(5, [7], config)
    assert direction == 1
    assert 0.0 < signal <= 1.0

    direction, signal = predator_sensor(5, [12], config)
    assert direction == 0
    assert signal == 0.0


def test_policy_state_preserves_predator_proximity_on_same_side() -> None:
    config = small_config(predator_sensor_range=4)
    counts = Counter({5: 1})

    near = observe_state(5, set(), counts, [6], config)
    far = observe_state(5, set(), counts, [9], config)

    assert near[:3] == far[:3]
    assert near[2] == 1
    assert near[3] == 4
    assert far[3] == 1


def test_policy_state_uses_zero_proximity_when_predator_is_not_sensed() -> None:
    config = small_config(predator_sensor_range=4)
    counts = Counter({5: 1})

    absent = observe_state(5, set(), counts, [], config)
    out_of_range = observe_state(5, set(), counts, [12], config)

    assert absent[2:] == (0, 0)
    assert out_of_range[2:] == (0, 0)


def test_policy_state_co_located_predator_has_maximum_proximity() -> None:
    config = small_config(predator_sensor_range=4)
    state = observe_state(5, set(), Counter({5: 1}), [5], config)

    assert state[2] == 0
    assert state[3] == config.predator_sensor_range + 1


def test_food_sensor_range_defaults_to_reduced_predator_range() -> None:
    config = SimulationConfig()
    assert config.food_sensor_range == 10
    assert config.food_sensor_range == config.predator_sensor_range


def test_policy_state_sees_food_direction_only_within_food_sensor_range() -> None:
    config = small_config(food_sensor_range=4)
    counts = Counter({5: 1})

    assert observe_state(5, {7}, counts, [], config)[0] == 1
    assert observe_state(5, {3}, counts, [], config)[0] == -1
    assert observe_state(5, {10}, counts, [], config)[0] == 0


def test_policy_state_has_neutral_food_direction_when_food_is_absent() -> None:
    config = small_config(food_sensor_range=4)
    assert observe_state(5, set(), Counter({5: 1}), [], config)[0] == 0


def test_conspecific_sensor_uses_other_prey() -> None:
    config = small_config(conspecific_sensor_range=4)
    direction, signal = conspecific_sensor(5, Counter({5: 1, 3: 1}), config)
    assert direction == -1
    assert 0.0 < signal <= 1.0


def test_sensor_reward_is_separate_from_physical_viability() -> None:
    config = small_config(sensor_reward_scale=0.5)
    genes = RewardGenes(food=0.0, movement=0.0, conspecific=2.0, predator=-3.0)

    reward = intrinsic_reward(
        genes,
        food_eaten=0,
        moved=0,
        conspecific_signal=0.25,
        predator_signal_value=0.5,
        config=config,
    )
    assert reward == 0.5 * (0.25 * 2.0 + 0.5 * -3.0)


def test_predator_chases_nearest_prey() -> None:
    config = small_config(predator_move_probability=1.0)
    assert move_predators([5], [prey(1, position=8)], random.Random(0), config) == [6]


def test_predation_is_world_consequence_not_intrinsic_reward() -> None:
    config = small_config(predator_kill_probability=1.0)
    agent = Agent(
        agent_id=1,
        parent_id=None,
        position=4,
        energy=10.0,
        genes=RewardGenes(0.0, 0.0, 0.0, 100.0),
    )
    survivors, killed, timers = resolve_predation(
        [agent], [4], [0], random.Random(0), config
    )
    assert survivors == []
    assert killed == {1}
    assert timers == [config.predator_eat_interval]


def test_one_predator_kills_at_most_one_prey_from_group() -> None:
    config = small_config(predator_kill_probability=1.0)
    population = [prey(1), prey(2), prey(3)]

    survivors, killed, _ = resolve_predation(
        population, [4], [0], random.Random(0), config
    )

    assert len(killed) == 1
    assert len(survivors) == 2


def test_two_predators_kill_at_most_two_distinct_prey() -> None:
    config = small_config(predator_kill_probability=1.0)
    population = [prey(1), prey(2), prey(3)]

    survivors, killed, _ = resolve_predation(
        population, [4, 4], [0, 0], random.Random(0), config
    )

    assert len(killed) == 2
    assert len(survivors) == 1
    assert len(set(killed)) == len(killed)


def test_predators_cannot_kill_same_prey_twice() -> None:
    config = small_config(predator_kill_probability=1.0)

    survivors, killed, _ = resolve_predation(
        [prey(1)], [4, 4], [0, 0], random.Random(0), config
    )

    assert survivors == []
    assert killed == {1}


def test_zero_predator_kill_probability_kills_none_and_does_not_reset_timer() -> None:
    config = small_config(predator_kill_probability=0.0)
    population = [prey(1), prey(2), prey(3)]

    survivors, killed, timers = resolve_predation(
        population, [4, 4], [0, 0], random.Random(0), config
    )

    assert survivors == population
    assert killed == set()
    assert timers == [-1, -1]


def test_successful_predation_resets_only_that_predators_timer() -> None:
    config = small_config(predator_kill_probability=1.0, predator_eat_interval=10)
    population = [prey(1, 4), prey(2, 8)]

    _, killed, timers = resolve_predation(
        population, [4, 8], [0, 5], random.Random(0), config
    )

    assert killed == {1}
    assert timers == [10, 4]


def test_positive_eat_timer_blocks_predation_and_decrements() -> None:
    config = small_config(predator_kill_probability=1.0)
    population = [prey(1)]

    survivors, killed, timers = resolve_predation(
        population, [4], [2], random.Random(0), config
    )

    assert survivors == population
    assert killed == set()
    assert timers == [1]


def test_timer_reaching_zero_is_eligible_on_following_step() -> None:
    config = small_config(predator_kill_probability=1.0)
    population = [prey(1)]

    survivors, killed, timers = resolve_predation(
        population, [4], [1], random.Random(0), config
    )
    assert survivors == population
    assert killed == set()
    assert timers == [0]

    survivors, killed, timers = resolve_predation(
        population, [4], timers, random.Random(0), config
    )
    assert survivors == []
    assert killed == {1}
    assert timers == [config.predator_eat_interval]


def test_predator_positions_and_timers_must_align() -> None:
    config = small_config()

    try:
        resolve_predation([prey(1)], [4, 4], [0], random.Random(0), config)
    except ValueError as error:
        assert str(error) == "predator positions and eat timers must have equal length"
    else:
        raise AssertionError("expected mismatched predator state to fail closed")


def test_seeded_simulation_is_reproducible_and_control_has_no_predation() -> None:
    config = replace(
        SimulationConfig(),
        initial_population=20,
        max_population=60,
        initial_predators=0,
        sample_interval=20,
    )
    first = run_simulation(seed=7, steps=80, config=config)
    second = run_simulation(seed=7, steps=80, config=config)

    assert first == second
    assert first.predation_deaths == 0
    assert first.samples


def test_predator_treatment_does_not_change_initial_prey_genes() -> None:
    base = replace(
        SimulationConfig(),
        initial_population=20,
        max_population=60,
        food_spawn_probability=0.0,
        reproduction_threshold=1_000.0,
        predator_move_probability=0.0,
        predator_kill_probability=0.0,
        sample_interval=1,
    )
    active = run_simulation(
        seed=11,
        steps=1,
        config=replace(base, initial_predators=2),
    )
    control = run_simulation(
        seed=11,
        steps=1,
        config=replace(base, initial_predators=0),
    )

    active_sample = active.samples[0]
    control_sample = control.samples[0]
    assert active_sample.population == control_sample.population
    assert active_sample.mean_food_reward == control_sample.mean_food_reward
    assert active_sample.mean_movement_reward == control_sample.mean_movement_reward
    assert active_sample.mean_conspecific_reward == control_sample.mean_conspecific_reward
    assert active_sample.mean_predator_reward == control_sample.mean_predator_reward