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


def test_predator_sensor_is_bounded_and_local() -> None:
    config = small_config(predator_sensor_range=4)
    direction, signal = predator_sensor(5, [7], config)
    assert direction == 1
    assert 0.0 < signal <= 1.0

    direction, signal = predator_sensor(5, [12], config)
    assert direction == 0
    assert signal == 0.0


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
    prey = [
        Agent(
            agent_id=1,
            parent_id=None,
            position=8,
            energy=10.0,
            genes=RewardGenes(0.0, 0.0, 0.0, 0.0),
        )
    ]
    assert move_predators([5], prey, random.Random(0), config) == [6]


def test_predation_is_world_consequence_not_intrinsic_reward() -> None:
    config = small_config(predator_kill_probability=1.0)
    agent = Agent(
        agent_id=1,
        parent_id=None,
        position=4,
        energy=10.0,
        genes=RewardGenes(0.0, 0.0, 0.0, 100.0),
    )
    survivors, killed = resolve_predation([agent], [4], random.Random(0), config)
    assert survivors == []
    assert killed == {1}


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
