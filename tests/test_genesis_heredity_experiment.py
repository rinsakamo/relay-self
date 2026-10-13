from __future__ import annotations

from dataclasses import fields

import pytest

from experiments.genesis_heredity import (
    BirthAuthorization,
    GenesisConfig,
    GenesisRegistry,
    Genome,
    MOutcome,
    MOutcomeBatch,
)


def registry_with_outcomes(
    *,
    seed: int = 7,
    count: int = 2,
    config: GenesisConfig | None = None,
    surplus: tuple[float, ...] | None = None,
) -> GenesisRegistry:
    registry = GenesisRegistry(seed=seed, config=config)
    registry.spawn_founders(count)
    levels = surplus or (1.0,) * count
    registry.record_m_outcomes(
        MOutcomeBatch(
            "m1",
            1,
            tuple(MOutcome(identifier, 1, "ALIVE", levels[identifier]) for identifier in range(count)),
        )
    )
    return registry


def permit(
    receipt: str = "paid-1",
    *,
    batch: str = "m1",
    tick: int = 1,
    count: int = 1,
    cost: float = 2.0,
) -> BirthAuthorization:
    return BirthAuthorization(receipt, batch, tick, count, count * cost)


def test_seeded_founders_bounded_and_replayable() -> None:
    a = GenesisRegistry(seed=23)
    b = GenesisRegistry(seed=23)
    c = GenesisRegistry(seed=24)
    assert a.spawn_founders(4) == b.spawn_founders(4)
    assert a.lineage != c.spawn_founders(4)
    assert a.active_ids == (0, 1, 2, 3)
    assert len({entry.genome for entry in a.lineage}) == 4
    with pytest.raises(ValueError, match="once"):
        a.spawn_founders(1)


def test_child_inherits_exact_genome_with_mutation_off_and_parent_stays_alive() -> None:
    registry = registry_with_outcomes()
    child = registry.spawn_children(permit(), mutate=False)[0]
    parent = registry.lineage[child.parent_id]
    assert child.parent_id in (0, 1)
    assert child.genome == parent.genome
    assert child.generation == 1
    assert child.birth_tick == 1
    assert child.birth_receipt == "paid-1"
    assert child.individual_id in registry.active_ids
    assert child.parent_id in registry.active_ids
    assert registry.births == 1
    assert not registry.deaths
    assert {field.name for field in fields(child)} == {
        "individual_id", "parent_id", "generation", "birth_tick", "genome", "birth_receipt"
    }


def test_mutation_has_bounded_individual_variation_and_deterministic_seed() -> None:
    a = registry_with_outcomes(seed=11)
    b = registry_with_outcomes(seed=11)
    ca = a.spawn_children(permit(count=3))
    cb = b.spawn_children(permit(count=3))
    assert ca == cb
    assert any(child.genome != a.lineage[child.parent_id].genome for child in ca)
    assert all(0 <= child.genome.sensor_gain <= 2 for child in ca)
    assert all(0 <= child.genome.exploration_rate <= 1 for child in ca)
    assert all(0.01 <= child.genome.learning_rate <= 1 for child in ca)


def test_mutation_multiplier_zero_and_random_genome_control() -> None:
    config = GenesisConfig(mutation_multiplier=0.0)
    registry = registry_with_outcomes(config=config)
    inherited = registry.spawn_children(permit("first"), mutate=True)[0]
    assert inherited.genome == registry.lineage[inherited.parent_id].genome
    random_genome = registry.spawn_children(
        permit("second"), inherit=False, mutate=False
    )[0]
    assert random_genome.genome != registry.lineage[random_genome.parent_id].genome


def test_weighted_parent_selection_is_not_a_combat_fitness_score() -> None:
    registry = registry_with_outcomes(surplus=(0.0, 9.0))
    children = registry.spawn_children(
        permit(count=5), selection="surplus_weighted", mutate=False
    )
    assert {child.parent_id for child in children} == {1}
    assert {child.generation for child in children} == {1}
    assert registry.active_ids == tuple(range(7))


def test_surplus_weighted_zero_signal_fails_but_uniform_still_works() -> None:
    registry = registry_with_outcomes(surplus=(0.0, 0.0))
    with pytest.raises(ValueError, match="zero surplus"):
        registry.spawn_children(permit(), selection="surplus_weighted")
    assert len(registry.spawn_children(permit(), selection="uniform")) == 1


def test_terminal_starvation_is_exactly_once_and_never_reproduces() -> None:
    registry = GenesisRegistry(seed=4)
    registry.spawn_founders(2)
    deaths = registry.record_m_outcomes(
        MOutcomeBatch(
            "m1",
            1,
            (MOutcome(0, 1, "STARVED"), MOutcome(1, 1, "ALIVE", 3)),
        )
    )
    assert len(deaths) == 1
    assert deaths[0].individual_id == 0
    assert deaths[0].reason == "STARVED"
    assert registry.active_ids == (1,)
    assert registry.spawn_children(permit(count=4), mutate=False)
    assert all(child.parent_id == 1 for child in registry.lineage[2:])
    # Next M observation covers only current active IDs (including newborns).
    living = registry.active_ids
    registry.record_m_outcomes(
        MOutcomeBatch("m2", 2, tuple(MOutcome(i, 2, "ALIVE", 1) for i in living))
    )
    assert registry.deaths == deaths
    with pytest.raises(ValueError, match="incomplete"):
        registry.record_m_outcomes(
            MOutcomeBatch("m3", 3, (MOutcome(0, 3, "STARVED"),))
        )


@pytest.mark.parametrize(
    "batch",
    [
        MOutcomeBatch("m2", 2, (MOutcome(0, 2, "ALIVE"),)),
        MOutcomeBatch("m2", 2, (
            MOutcome(0, 2, "ALIVE"), MOutcome(0, 2, "ALIVE")
        )),
        MOutcomeBatch("m2", 2, (
            MOutcome(0, 2, "ALIVE"), MOutcome(1, 1, "ALIVE")
        )),
        MOutcomeBatch("m1", 2, (
            MOutcome(0, 2, "ALIVE"), MOutcome(1, 2, "ALIVE")
        )),
    ],
)
def test_missing_duplicate_mismatched_and_reused_m_snapshots_fail(batch: MOutcomeBatch) -> None:
    registry = registry_with_outcomes()
    with pytest.raises(ValueError):
        registry.record_m_outcomes(batch)
    assert registry.active_ids == (0, 1)


@pytest.mark.parametrize(
    "authorization",
    [
        permit("wrong", batch="unrelated"),
        permit("wrong", tick=2),
        permit("wrong", cost=4),
    ],
)
def test_birth_requires_matching_current_paid_cost_receipt(authorization: BirthAuthorization) -> None:
    registry = registry_with_outcomes()
    with pytest.raises(ValueError):
        registry.spawn_children(authorization)
    assert registry.births == 0


def test_no_birth_without_m_outcomes_and_receipt_is_single_use() -> None:
    registry = GenesisRegistry(seed=3)
    registry.spawn_founders(1)
    with pytest.raises(ValueError, match="not bound"):
        registry.spawn_children(permit())
    registry.record_m_outcomes(MOutcomeBatch("m1", 1, (MOutcome(0, 1, "ALIVE"),)))
    registry.spawn_children(permit())
    with pytest.raises(ValueError, match="reused"):
        registry.spawn_children(permit())
    assert registry.births == 1


def test_population_cap_and_total_birth_cap_are_distinct() -> None:
    cap = registry_with_outcomes(config=GenesisConfig(max_active=3))
    with pytest.raises(ValueError, match="capacity"):
        cap.spawn_children(permit(count=2))
    limit = registry_with_outcomes(config=GenesisConfig(max_total_births=1))
    limit.spawn_children(permit())
    with pytest.raises(ValueError, match="total birth"):
        limit.spawn_children(permit("next"))


def test_stale_receipt_is_invalid_after_next_m_batch() -> None:
    registry = registry_with_outcomes()
    registry.record_m_outcomes(
        MOutcomeBatch("m2", 2, (MOutcome(0, 2, "ALIVE"), MOutcome(1, 2, "ALIVE")))
    )
    with pytest.raises(ValueError, match="not bound"):
        registry.spawn_children(permit())
    assert registry.spawn_children(permit("paid-2", batch="m2", tick=2))


def test_no_reward_memory_habit_qstate_or_energy_hidden_in_genome() -> None:
    assert tuple(_field.name for _field in fields(Genome)) == (
        "sensor_gain",
        "exploration_rate",
        "learning_rate",
    )
    registry = registry_with_outcomes()
    registry.spawn_children(permit())
    assert all(not hasattr(record, "q_values") for record in registry.lineage)
    assert all(not hasattr(record, "memory") for record in registry.lineage)
    assert all(not hasattr(record, "energy") for record in registry.lineage)


@pytest.mark.parametrize(
    "genome",
    [
        (float("nan"), 0.5, 0.1),
        (0.4, 2.0, 0.1),
        (0.4, 0.5, 0.0),
        (False, 0.5, 0.1),
    ],
)
def test_bad_genome_fails_closed(genome: tuple[float, float, float]) -> None:
    with pytest.raises(ValueError):
        Genome(*genome)


def test_invalid_m_and_authorization_inputs_rejected() -> None:
    with pytest.raises(ValueError):
        MOutcome(0, 1, "STARVED", 1)
    with pytest.raises(ValueError):
        MOutcome(0, 1, "HP_KO", 0)
    with pytest.raises(ValueError):
        MOutcome(0, 1, "ALIVE", float("nan"))
    with pytest.raises(ValueError):
        MOutcomeBatch("", 1, ())
    with pytest.raises(ValueError):
        BirthAuthorization("receipt", "m1", 1, 0, 2.0)
    with pytest.raises(ValueError):
        GenesisConfig(max_active=0)
    with pytest.raises(ValueError):
        GenesisRegistry(seed=True)


def test_fully_extinct_population_cannot_be_genetic_parent() -> None:
    registry = GenesisRegistry(seed=33)
    registry.spawn_founders(1)
    registry.record_m_outcomes(MOutcomeBatch("m1", 1, (MOutcome(0, 1, "STARVED"),)))
    assert registry.active_ids == ()
    with pytest.raises(ValueError, match="no fresh viable parents"):
        registry.spawn_children(permit())
