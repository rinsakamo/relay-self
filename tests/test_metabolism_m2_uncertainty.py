from __future__ import annotations

from dataclasses import replace

import pytest

from experiments.metabolism_m2_costs import config_for_costs
from experiments.metabolism_m2_uncertainty import (
    ACTION_NAMES,
    M2D_SEEDS,
    POLICIES,
    M2DConfig,
    _Policy,
    frozen_family,
    make_world,
    run_episode,
)


def test_frozen_stochastic_world_is_reproducible_and_action_independent() -> None:
    assert M2D_SEEDS == (907, 1009, 1103, 1201, 1301, 1409, 1511, 1601)
    cfg = M2DConfig()
    for regime in ("persistent", "iid"):
        world = make_world(seed=907, regime=regime, config=cfg)
        before = world
        no_memory = run_episode(world=world, policy="current_cue", seed=907, config=cfg)
        memory = run_episode(world=world, policy="bayes", seed=907, config=cfg)
        scanning = run_episode(world=world, policy="scan_bayes", seed=907, config=cfg)
        assert world == before
        assert no_memory.observed_hints[0] == memory.observed_hints[0]
        assert scanning.observed_hints[0] == memory.observed_hints[0]
        assert world == make_world(seed=907, regime=regime, config=cfg)
        assert all(a in ACTION_NAMES for a in memory.action_trace)
        assert memory == run_episode(world=world, policy="bayes", seed=907, config=cfg)


def test_iid_bayes_history_knockout_is_equivalent_to_memoryless_cue() -> None:
    cfg = M2DConfig()
    for seed in M2D_SEEDS:
        world = make_world(seed=seed, regime="iid", config=cfg)
        memoryless = run_episode(
            world=world, policy="current_cue", seed=seed, config=cfg
        )
        bayes = run_episode(world=world, policy="bayes", seed=seed, config=cfg)
        knockout = run_episode(world=world, policy="bayes_reset", seed=seed, config=cfg)
        # In IID worlds Bayes posterior has no useful historical dependency;
        # the optimal current-cue classifier is identical to memory knockout.
        assert memoryless.action_trace == bayes.action_trace
        assert knockout.action_trace == memoryless.action_trace
        assert memoryless.meals == bayes.meals == knockout.meals
        assert memoryless.births == bayes.births == knockout.births


def test_persistent_bayes_reuses_history_and_knockout_alters_action() -> None:
    cfg = M2DConfig()
    outcomes = []
    for seed in M2D_SEEDS:
        world = make_world(seed=seed, regime="persistent", config=cfg)
        bayes = run_episode(world=world, policy="bayes", seed=seed, config=cfg)
        ablated = run_episode(
            world=world, policy="bayes_reset", seed=seed, config=cfg
        )
        outcomes.append(bayes.action_trace != ablated.action_trace)
    assert any(outcomes)
    # A change does not guarantee it helps: test guards mechanism, not science GO.


@pytest.mark.parametrize("regime", ("persistent", "iid"))
@pytest.mark.parametrize("seed", (907, 1103))
@pytest.mark.parametrize("policy", POLICIES)
def test_physical_conservation_including_injury_scan_and_birth(
    regime: str, seed: int, policy: str
) -> None:
    cfg = M2DConfig()
    world = make_world(seed=seed, regime=regime, config=cfg)
    result = run_episode(world=world, policy=policy, seed=seed, config=cfg)
    physics = config_for_costs("costly_both").physics
    assert (
        result.wait_ticks + result.move_ticks + result.fight_ticks + result.scans
        == result.ticks
    )
    assert result.intake == pytest.approx(physics.food_energy * result.meals)
    assert result.offspring_transfer == pytest.approx(
        config_for_costs("costly_both").reproduction_transfer * result.births
    )
    expected = (
        result.ticks * physics.basal_cost
        + result.move_ticks * physics.move_cost
        + result.fight_ticks * physics.fight_cost
        + result.scans * cfg.scan_cost
        + result.injuries * cfg.damage_cost
    )
    assert result.expenditure == pytest.approx(expected)
    recovered = (
        physics.initial_energy + result.intake - result.expenditure
        - result.overflow - result.offspring_transfer
        + result.terminal_shortfall
    )
    assert result.final_energy == pytest.approx(recovered, abs=1e-8)
    assert result.births <= config_for_costs("costly_both").births_per_parent
    if result.terminal:
        assert result.final_energy == 0


def test_delayed_scan_pays_energy_and_only_changes_next_cue() -> None:
    cfg = M2DConfig()
    scanner = _Policy("scan_bayes", "persistent", 1, cfg)
    # Contradictory weak observations can produce an ambiguous posterior.
    scanner.choose(hint=True, accuracy=cfg.cue_accuracy, sensed_energy=8)
    action, _ = scanner.choose(
        hint=False, accuracy=cfg.cue_accuracy, sensed_energy=8
    )
    assert action == "SCAN"
    assert cfg.scan_cost > 0
    assert cfg.scanned_accuracy > cfg.cue_accuracy


def test_full_suite_fixed_row_count_and_no_automatic_success() -> None:
    report = frozen_family()
    assert report == frozen_family()
    assert len(report["rows"]) == 2 * len(M2D_SEEDS) * len(POLICIES)
    assert len(report["aggregates"]) == 2 * len(POLICIES)
    assert report["classification"].endswith("NOT_VALUE_EMERGENCE")
    assert all(r["status"] == "DESCRIPTIVE_NOT_SCIENTIFIC_GO" for r in report["rows"])


def test_fail_closed_world_shape_policy_and_probabilities() -> None:
    cfg = M2DConfig()
    with pytest.raises(ValueError, match="unknown"):
        make_world(seed=3, regime="BEST_POSSIBLE", config=cfg)
    with pytest.raises(ValueError, match="probabilities"):
        M2DConfig(good_food_probability=float("nan"))
    with pytest.raises(ValueError):
        M2DConfig(cue_accuracy=0.92)
    with pytest.raises(ValueError):
        M2DConfig(scan_cost=-1)
    world = make_world(seed=907, regime="iid", config=cfg)
    with pytest.raises(ValueError, match="invalid policy"):
        run_episode(world=world, policy="EAT_FOR_REWARD", seed=907, config=cfg)
    with pytest.raises(ValueError, match="duration"):
        run_episode(
            world=replace(world, move_food=(True,)),
            policy="current_cue", seed=907, config=cfg,
        )
