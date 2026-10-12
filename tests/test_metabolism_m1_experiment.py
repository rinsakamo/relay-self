from __future__ import annotations

from dataclasses import replace

import pytest

from experiments.metabolism_m1 import M1Config, food_schedule, paired_suite, run_trial
from experiments.metabolism_viability import Interoception, MetabolismConfig


def test_same_seed_same_experiment_and_paired_world_schedule() -> None:
    one = paired_suite(17)
    two = paired_suite(17)
    assert one == two
    schedule = food_schedule(17, M1Config().horizon)
    assert one["reward_free_learning_on"].ticks
    for result in one.values():
        assert tuple(t.opportunity for t in result.ticks) == schedule[: result.completed_ticks]
        assert result.completed_ticks <= result.requested_ticks
        assert sum(t.food_eaten for t in result.ticks) == result.meals


def test_reward_free_q_has_no_covert_energy_or_food_supervision() -> None:
    suite = paired_suite(31)
    on = suite["reward_free_learning_on"]
    off = suite["reward_free_learning_off"]
    assert on.ticks == off.ticks
    assert on.meals == off.meals
    assert on.completed_ticks == off.completed_ticks
    assert on.q_nonzero == off.q_nonzero == 0
    assert on.q_updates >= 0
    assert off.q_updates == 0
    # A sensor with no coupling into rewarded choices does not create value.
    blind = suite["blind_reward_free"]
    assert tuple(t.action for t in blind.ticks) == tuple(t.action for t in on.ticks)


def test_explicit_food_signal_is_labeled_positive_control_only() -> None:
    cfg = M1Config(
        horizon=36,
        physics=MetabolismConfig(
            capacity=50, initial_energy=40, basal_cost=0.1,
            move_cost=0.0, fight_cost=0.0, food_energy=2.0,
        ),
    )
    opportunities = (1, 2, 3) * 12
    positive = run_trial(seed=7, policy="q_food", learning=True, config=cfg, schedule=opportunities)
    no_train = run_trial(seed=7, policy="q_food", learning=False, config=cfg, schedule=opportunities)
    no_reward = run_trial(seed=7, policy="q_zero", learning=True, config=cfg, schedule=opportunities)
    assert positive.q_nonzero > 0
    assert positive.q_updates > 0
    assert no_train.q_nonzero == no_train.q_updates == 0
    assert no_reward.q_nonzero == 0
    # Do not assert that overt food teaching is naturally emergent or beats cheap baselines.


def test_fixed_cue_is_a_strong_engineered_oracle_and_not_learned_value() -> None:
    cfg = M1Config(
        horizon=8,
        physics=MetabolismConfig(
            capacity=20, initial_energy=16, basal_cost=0.1,
            move_cost=0.1, fight_cost=0.2, food_energy=2.0,
        ),
    )
    schedule = (0, 1, 2, 3, 0, 1, 2, 3)
    result = run_trial(seed=4, policy="fixed_cue", learning=False, config=cfg, schedule=schedule)
    assert result.meals == 6
    assert result.q_updates == result.q_nonzero == 0
    assert not result.terminal


def test_blind_interoception_changes_explicit_reactive_coupling_only() -> None:
    cfg = M1Config(horizon=1, reactive_threshold=7)
    full = run_trial(seed=4, policy="reactive", learning=False, config=cfg, schedule=(3,))
    blind = run_trial(
        seed=4,
        policy="reactive",
        learning=False,
        config=replace(cfg, sensor=Interoception(gain=0)),
        schedule=(3,),
    )
    assert full.ticks[0].action == "WAIT"
    assert blind.ticks[0].action == "FIGHT"
    assert full.meals == 0 and blind.meals == 1


def test_sensing_has_real_explicit_physical_cost() -> None:
    cfg = M1Config(horizon=2)
    no_cost = run_trial(seed=1, policy="fixed_wait", learning=False, config=cfg, schedule=(0, 0))
    with_cost = run_trial(
        seed=1, policy="fixed_wait", learning=False,
        config=replace(cfg, observation_cost=0.25), schedule=(0, 0),
    )
    assert no_cost.ticks[0].reading == with_cost.ticks[0].reading
    assert with_cost.total_expenditure - no_cost.total_expenditure == pytest.approx(0.5)
    assert no_cost.final_energy - with_cost.final_energy == pytest.approx(0.5)


def test_absent_food_enforces_one_terminal_without_resurrection() -> None:
    cfg = M1Config(
        horizon=20,
        physics=MetabolismConfig(
            initial_energy=1.0, basal_cost=0.25,
            move_cost=0.0, fight_cost=0.0,
        ),
    )
    result = run_trial(
        seed=8, policy="random", learning=False, config=cfg, schedule=(0,) * 20,
    )
    assert result.terminal
    assert result.completed_ticks == 4
    assert result.final_energy == 0
    assert sum(t.terminal_now for t in result.ticks) == 1
    assert result.meals == 0


@pytest.mark.parametrize(
    "bad",
    [
        M1Config(horizon=1),
    ],
)
def test_external_world_schedule_must_be_authentic_shape(bad: M1Config) -> None:
    for schedule in ((True,), (9,), (), (-1,), (0, 1)):
        with pytest.raises(ValueError, match="schedule"):
            run_trial(seed=1, policy="random", learning=False, config=bad, schedule=schedule)


def test_invalid_configuration_and_unknown_controller_fail_closed() -> None:
    with pytest.raises(ValueError):
        M1Config(horizon=0)
    with pytest.raises(ValueError):
        M1Config(noise_sigma=-1.0)
    with pytest.raises(ValueError):
        M1Config(observation_cost=float("inf"))
    with pytest.raises(ValueError, match="policy"):
        run_trial(seed=1, policy="APPRAISE", learning=False)
