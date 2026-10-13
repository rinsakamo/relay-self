from __future__ import annotations

from dataclasses import replace

import pytest

from experiments.metabolism_m2 import Member, Traits, run_episode, world_schedule
from experiments.metabolism_m2_costs import (
    COST_LEVELS,
    COST_SEEDS,
    config_for_costs,
    ledger_means,
)


def test_cost_matrix_is_fixed_ex_ante_and_independent_of_food_supply() -> None:
    assert COST_SEEDS == (503, 607, 709, 811)
    assert COST_LEVELS == (
        ("original", 0.12, 0.28),
        ("costly_move", 1.10, 0.28),
        ("costly_fight", 0.12, 1.45),
        ("costly_both", 1.10, 1.45),
    )
    baseline = config_for_costs("original")
    for name, move, fight in COST_LEVELS:
        cfg = config_for_costs(name)
        assert cfg.physics.move_cost == move
        assert cfg.physics.fight_cost == fight
        assert cfg.physics.food_energy == baseline.physics.food_energy
        assert cfg.physics.basal_cost == baseline.physics.basal_cost
        assert cfg.physics.capacity == baseline.physics.capacity
        assert cfg.reproduction_threshold == baseline.reproduction_threshold
        assert cfg.reproduction_transfer == baseline.reproduction_transfer
        assert cfg.mutation_sigma == baseline.mutation_sigma
        assert cfg.world_profile == baseline.world_profile == "scarce_active"
        assert world_schedule(503, cfg) == world_schedule(503, baseline)


@pytest.mark.parametrize("action", ("wait", "move", "fight", "oracle"))
@pytest.mark.parametrize("name", tuple(label for label, _, _ in COST_LEVELS))
def test_full_physical_ledger_conserves_energy_for_births_and_starvation(
    action: str, name: str
) -> None:
    cfg = config_for_costs(name)
    member = Member(1, None, Traits(0, 0), cfg.physics.initial_energy)
    trial = run_episode(
        member=member, generation=0,
        schedule=world_schedule(503, cfg), config=cfg,
        seed=503, passive_learning=False, control=action,
    )
    assert trial.wait_ticks + trial.move_ticks + trial.fight_ticks == trial.ticks
    assert trial.energy_intake == pytest.approx(trial.meals * cfg.physics.food_energy)
    action_costs = (
        trial.wait_ticks * cfg.physics.basal_cost
        + trial.move_ticks * (cfg.physics.basal_cost + cfg.physics.move_cost)
        + trial.fight_ticks * (cfg.physics.basal_cost + cfg.physics.fight_cost)
    )
    assert trial.energy_expenditure == pytest.approx(action_costs)
    net = (
        member.birth_energy + trial.energy_intake - trial.energy_expenditure
        - trial.energy_overflow - sum(b.child_energy for b in trial.births)
        + trial.terminal_shortfall
    )
    assert net == pytest.approx(trial.final_energy, abs=1e-8)
    assert trial.terminal_shortfall >= 0
    if trial.terminal:
        assert trial.final_energy == 0


def test_cost_asymmetry_is_observable_without_favoring_a_policy() -> None:
    seed = 503
    low = config_for_costs("original")
    high_move = config_for_costs("costly_move")
    high_fight = config_for_costs("costly_fight")
    for control, normal, expensive in (
        ("move", low, high_move), ("fight", low, high_fight)
    ):
        cheaper = ledger_means(seed=seed, config=normal, control=control)
        expensive_ = ledger_means(seed=seed, config=expensive, control=control)
        assert expensive_.mean_expenditure > cheaper.mean_expenditure or (
            expensive_.mean_final_energy < cheaper.mean_final_energy
        )
        assert cheaper.mean_intake >= 0
        assert expensive_.episodes == cheaper.episodes == 36


def test_costs_never_become_an_explicit_reward_or_learner_input() -> None:
    cfg = config_for_costs("costly_both")
    member = Member(2, None, Traits(1.2, -0.1), cfg.physics.initial_energy)
    off = run_episode(
        member=member, generation=0,
        schedule=world_schedule(607, cfg), config=cfg,
        seed=607, passive_learning=False,
    )
    on = run_episode(
        member=member, generation=0,
        schedule=world_schedule(607, cfg), config=cfg,
        seed=607, passive_learning=True,
    )
    assert replace(on, forecast_updates=0) == off
    assert on.forecast_updates > 0


def test_invalid_names_fail_closed_and_no_extinct_cohort_substitution() -> None:
    with pytest.raises(ValueError, match="unknown"):
        config_for_costs("optimised_after_results")
    with pytest.raises(ValueError, match="preregistered"):
        ledger_means(seed=101, config=config_for_costs("original"), control="move")
    with pytest.raises(ValueError, match="preregistered"):
        ledger_means(seed=503, config=config_for_costs("original"), control="reward")
    with pytest.raises(ValueError, match="extinct"):
        ledger_means(
            seed=503, config=config_for_costs("original"),
            control="move", members=(),
        )
