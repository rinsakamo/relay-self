from __future__ import annotations

from dataclasses import replace

import pytest

from experiments.metabolism_m1 import food_schedule
from experiments.metabolism_m2 import (
    M2Config,
    Member,
    Traits,
    run_episode,
    world_schedule,
)
from experiments.metabolism_m2_scarcity import (
    PROFILE,
    SCARCITY_SEEDS,
    run_scarcity,
    summarize,
)
from experiments.metabolism_viability import MetabolismConfig


def test_predeclared_world_has_no_free_wait_food_and_is_deterministic() -> None:
    assert SCARCITY_SEEDS == (101, 211, 307, 419)
    cfg = PROFILE
    assert cfg.physics == M2Config().physics
    assert cfg.reproduction_threshold == M2Config().reproduction_threshold
    assert cfg.reproduction_transfer == M2Config().reproduction_transfer
    for seed in (101, 211, 307, 419):
        schedule = world_schedule(seed, cfg)
        assert schedule == world_schedule(seed, cfg)
        assert set(schedule) == {0, 2, 3}
        assert len([cue for cue in schedule if cue != 0]) in (21, 22)
        assert all(cue == 0 or tick % 3 == next(
            i for i, value in enumerate(schedule[:3]) if value != 0
        ) for tick, cue in enumerate(schedule))


def test_wait_is_reproductive_null_even_with_food_encounters() -> None:
    cfg = PROFILE
    member = Member(1, None, Traits(0.0, 0.0), cfg.physics.initial_energy)
    schedule = world_schedule(101, cfg)
    result = run_episode(
        member=member, generation=0, schedule=schedule, config=cfg,
        seed=101, passive_learning=False, control="wait",
    )
    assert result.terminal
    assert result.meals == 0
    assert len(result.births) == 0
    assert result.ticks < cfg.horizon


def test_active_cheap_controllers_stay_valid_as_harder_nulls() -> None:
    cfg = PROFILE
    member = Member(1, None, Traits(0.0, 0.0), cfg.physics.initial_energy)
    schedule = world_schedule(101, cfg)
    moves = run_episode(
        member=member, generation=0, schedule=schedule, config=cfg,
        seed=101, passive_learning=False, control="move",
    )
    fights = run_episode(
        member=member, generation=0, schedule=schedule, config=cfg,
        seed=101, passive_learning=False, control="fight",
    )
    assert moves.meals > 0
    assert fights.meals > 0
    assert moves.births or fights.births
    assert all(b.energy_before - b.energy_after == pytest.approx(b.child_energy)
               for episode in (moves, fights) for b in episode.births)


def test_scarce_seed_result_is_stable_and_no_inferred_science_go() -> None:
    a = run_scarcity(101)
    assert a == run_scarcity(101)
    assert summarize(a) == summarize(a)
    assert a.inherited.founder_traits == a.disconnected.founder_traits
    assert a.inherited.samples[0] == a.disconnected.samples[0]
    assert a.cheap_wait.mean_births == 0
    assert a.cheap_oracle.mean_meals >= a.cheap_move.mean_meals
    assert a.cheap_oracle.mean_meals >= a.cheap_fight.mean_meals
    assert a.profile == "scarce_active"
    assert summarize(a)["decision"] == "DESCRIPTIVE_ONLY_SCIENCE_NO_GO"


def test_legacy_profile_and_previous_seed_family_are_not_reinterpreted() -> None:
    base = M2Config()
    assert base.world_profile == "legacy_uniform"
    assert world_schedule(7 + 44, base) == food_schedule(7 + 44, base.horizon)


def test_invalid_profiles_and_posthoc_seed_choice_fail_closed() -> None:
    with pytest.raises(ValueError, match="profile"):
        M2Config(world_profile="perfectly_tuned")
    with pytest.raises(ValueError, match="frozen"):
        run_scarcity(7)
    with pytest.raises(ValueError, match="scarcity"):
        run_scarcity(101, replace(PROFILE, world_profile="legacy_uniform"))
    with pytest.raises(ValueError):
        M2Config(physics=MetabolismConfig(capacity=5, initial_energy=4))
