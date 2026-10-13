from __future__ import annotations

from dataclasses import replace

import pytest

from experiments.metabolism_m1 import food_schedule
from experiments.metabolism_m2 import (
    M2Config,
    Member,
    Traits,
    founder_population,
    paired_evolution,
    run_episode,
    run_evolution,
)
from experiments.metabolism_viability import MetabolismConfig


def test_m2_seeded_inheritance_and_disconnect_are_deterministic() -> None:
    one = paired_evolution(7)
    two = paired_evolution(7)
    assert one == two
    selected, disconnected = one["inherited"], one["disconnected"]
    assert selected.founder_traits == disconnected.founder_traits
    assert selected.samples[0].births == disconnected.samples[0].births
    assert selected.samples[0].meals == disconnected.samples[0].meals
    assert selected.holdout_founders == disconnected.holdout_founders
    assert selected.holdout_oracle == disconnected.holdout_oracle
    assert len(selected.samples) > 0


def test_exact_parent_child_energy_transfer_and_actual_mutation() -> None:
    config = M2Config(
        cohort_size=1, generations=1, horizon=32, maturation_ticks=1,
        mutation_sigma=0.5,
        reproduction_threshold=9,
        reproduction_transfer=6,
        physics=MetabolismConfig(
            capacity=20, initial_energy=8, basal_cost=0.1,
            move_cost=0, fight_cost=0, food_energy=4,
        ),
    )
    member = Member(2, None, Traits(cue_bias=10, sensor_coupling=0), 8)
    episode = run_episode(
        member=member, generation=0, config=config, seed=17,
        schedule=(1,) * config.horizon, passive_learning=False,
    )
    assert episode.births
    for birth in episode.births:
        assert birth.parent_id == member.member_id
        assert birth.child_id // 100 == birth.parent_id
        assert birth.parent_traits == member.traits
        assert birth.energy_before - birth.energy_after == pytest.approx(birth.child_energy)
        assert birth.child_energy == config.reproduction_transfer
        assert birth.energy_after > 0
    assert any(b.child_traits != member.traits for b in episode.births)


def test_no_mutation_is_exact_parent_inheritance_not_learned_memory() -> None:
    cfg = replace(
        M2Config(), mutation_sigma=0,
    )
    member = Member(3, None, Traits(10, 0), cfg.physics.initial_energy)
    episode = run_episode(
        member=member, generation=0, config=cfg, seed=2,
        schedule=(1,) * cfg.horizon, passive_learning=True,
    )
    assert episode.births
    assert all(b.child_traits == member.traits for b in episode.births)
    assert episode.forecast_updates > 0
    # No 'memory' is ever stored in a child birth; it only inherits traits.
    assert all(set(b.__dataclass_fields__) == {
        "generation", "parent_id", "child_id", "parent_traits",
        "child_traits", "energy_before", "energy_after", "child_energy",
    } for b in episode.births)


def test_passive_learning_on_off_cannot_change_selection_outcomes() -> None:
    off = run_evolution(seed=11, inheritance="inherited", passive_learning=False)
    on = run_evolution(seed=11, inheritance="inherited", passive_learning=True)
    assert off.final_traits == on.final_traits
    assert off.extinct == on.extinct
    assert off.holdout_final == on.holdout_final
    assert off.holdout_founders == on.holdout_founders
    assert [replace(s, forecast_updates=0) for s in on.samples] == list(off.samples)
    assert all(s.forecast_updates == 0 for s in off.samples)
    assert any(s.forecast_updates > 0 for s in on.samples)


def test_absent_world_food_leads_to_extinction_no_fabricated_children() -> None:
    cfg = M2Config(horizon=60, generations=3)
    empty = tuple((0,) * cfg.horizon for _ in range(cfg.generations))
    for inheritance in ("inherited", "disconnected"):
        result = run_evolution(
            seed=3, inheritance=inheritance, config=cfg, schedules=empty,
        )
        assert result.extinct
        assert result.final_traits == ()
        assert result.holdout_final is None
        assert len(result.samples) == 1
        assert result.samples[0].births == 0
        assert result.samples[0].next_agents == 0
        assert result.samples[0].deaths_from_starvation == cfg.cohort_size


def test_legacy_gene_slots_are_not_inherited_food_reward() -> None:
    # In this M2 experiment the two genes are logit intercept and sensor
    # coupling. World/evaluator has physical survival but NO Q reward update.
    cfg = M2Config(generations=2, cohort_size=4)
    result = run_evolution(seed=19, inheritance="inherited", config=cfg)
    assert len(result.founder_traits) == 4
    for sample in result.samples:
        assert sample.starting_agents >= 1
        assert sample.births == len(sample.lineage)
        assert sample.next_agents <= cfg.max_cohort
        assert all(b.child_energy == cfg.reproduction_transfer for b in sample.lineage)


def test_bottleneck_does_not_erase_counted_offspring() -> None:
    cfg = M2Config(cohort_size=2, max_cohort=2, generations=2)
    result = run_evolution(seed=5, inheritance="inherited", config=cfg)
    assert all(sample.next_agents <= cfg.max_cohort for sample in result.samples)
    assert all(sample.births >= sample.next_agents for sample in result.samples)


def test_heldout_oracle_remains_cheap_upper_bound_for_meals() -> None:
    cfg = M2Config(cohort_size=8, generations=2)
    out = run_evolution(seed=6, inheritance="inherited", config=cfg)
    assert out.holdout_oracle.mean_meals >= out.holdout_founders.mean_meals
    assert out.holdout_oracle.episodes == out.holdout_random.episodes
    assert out.holdout_wait.episodes == 3 * cfg.cohort_size


def test_fail_closed_schedules_and_genetics() -> None:
    with pytest.raises(ValueError):
        M2Config(reproduction_threshold=25)
    with pytest.raises(ValueError):
        M2Config(reproduction_transfer=0)
    with pytest.raises(ValueError):
        M2Config(sensor_gain=-1)
    with pytest.raises(ValueError):
        M2Config(exploratory_probability=2)
    with pytest.raises(ValueError):
        Traits(float("nan"), 0)
    with pytest.raises(ValueError):
        run_evolution(seed=1, inheritance="UNAUTHORIZED")
    with pytest.raises(ValueError, match="schedule"):
        run_evolution(seed=1, inheritance="inherited", schedules=((1, True),))
    member = founder_population(1, M2Config())[0]
    with pytest.raises(ValueError, match="schedule"):
        run_episode(
            member=member, generation=0, schedule=food_schedule(1, 2),
            config=M2Config(), seed=2, passive_learning=False,
        )
    with pytest.raises(ValueError, match="control"):
        run_episode(
            member=member, generation=0,
            schedule=food_schedule(1, M2Config().horizon),
            config=M2Config(), seed=2, passive_learning=False,
            control="REWARD",
        )
