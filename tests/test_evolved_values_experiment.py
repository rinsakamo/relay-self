from __future__ import annotations

import random

import pytest

from experiments.evolved_values import (
    Agent,
    RewardGenes,
    SimulationConfig,
    apply_body_dynamics,
    make_child,
    run_simulation,
)


def test_physical_energy_and_intrinsic_reward_are_distinct() -> None:
    config = SimulationConfig(world_size=8, initial_population=1, initial_food=1)
    foods_a = {1}
    foods_b = {1}
    cautious = Agent(1, None, 0, 10.0, RewardGenes(food=-50.0, movement=20.0))
    eager = Agent(2, None, 0, 10.0, RewardGenes(food=50.0, movement=-20.0))

    cautious_result = apply_body_dynamics(cautious, 1, foods_a, config)
    eager_result = apply_body_dynamics(eager, 1, foods_b, config)

    assert cautious_result.physical_energy_delta == eager_result.physical_energy_delta
    assert cautious.energy == eager.energy
    assert cautious_result.intrinsic_reward != eager_result.intrinsic_reward


def test_child_inherits_mutated_reward_genes_and_energy_transfer() -> None:
    config = SimulationConfig(
        world_size=8,
        initial_population=1,
        initial_food=1,
        reproduction_threshold=20.0,
        reproduction_transfer=6.0,
        mutation_sigma=0.5,
    )
    parent = Agent(10, None, 3, 24.0, RewardGenes(food=1.0, movement=-0.5))
    child = make_child(parent, 11, random.Random(7), config)

    assert child.parent_id == 10
    assert child.energy == 6.0
    assert parent.energy == 18.0
    assert child.genes != parent.genes


def test_seeded_simulation_is_reproducible() -> None:
    config = SimulationConfig(sample_interval=25)
    first = run_simulation(seed=17, steps=100, config=config)
    second = run_simulation(seed=17, steps=100, config=config)

    assert first == second
    assert first.samples


def test_zero_energy_agent_dies_from_physical_dynamics() -> None:
    config = SimulationConfig(
        world_size=8,
        initial_population=1,
        initial_food=1,
        initial_energy=0.1,
        basal_cost=1.0,
        movement_cost=0.0,
        food_spawn_probability=0.0,
        maximum_age=10,
    )
    result = run_simulation(seed=3, steps=3, config=config)

    assert result.extinct is True
    assert result.deaths == 1
    assert result.final_population == 0


def test_invalid_configuration_fails_closed() -> None:
    with pytest.raises(ValueError, match="reproduction_threshold"):
        SimulationConfig(reproduction_threshold=5.0, reproduction_transfer=5.0)
