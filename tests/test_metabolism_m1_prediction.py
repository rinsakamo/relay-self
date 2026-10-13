from __future__ import annotations

from dataclasses import replace

import pytest

from experiments.metabolism_m1 import M1Config, run_trial
from experiments.metabolism_m1_prediction import DeltaProbe, paired_probes, run_probe
from experiments.metabolism_viability import Interoception, MetabolismConfig


def abundant_config() -> M1Config:
    return M1Config(
        horizon=144,
        physics=MetabolismConfig(
            capacity=500.0,
            initial_energy=130.0,
            basal_cost=0.2,
            move_cost=0.15,
            fight_cost=0.4,
            food_energy=2.5,
        ),
        sensor=Interoception(quantum=0.01),
    )


def test_prediction_only_retention_changes_accuracy_not_behavior() -> None:
    cfg = abundant_config()
    on = run_probe(seed=19, preference="none", retained=True, config=cfg)
    off = run_probe(seed=19, preference="none", retained=False, config=cfg)
    assert on == run_probe(seed=19, preference="none", retained=True, config=cfg)
    assert on.trial.ticks == off.trial.ticks
    assert on.trial.completed_ticks == cfg.horizon
    assert on.scored_transitions == off.scored_transitions == cfg.horizon - 1
    assert on.learned_cells > 0
    assert off.learned_cells == 0
    assert on.mean_absolute_error is not None
    assert off.mean_absolute_error is not None
    assert on.mean_absolute_error < off.mean_absolute_error


def test_causal_directionality_is_an_explicit_appraisal_not_emergent() -> None:
    cfg = abundant_config()
    arms = paired_probes(43, cfg)
    passive = arms["passive_retained"]
    frozen = arms["passive_frozen"]
    higher = arms["directional_higher_retained"]
    lower = arms["directional_lower_retained"]
    assert passive.trial.ticks == frozen.trial.ticks
    assert higher.learned_cells > 0
    assert lower.learned_cells > 0
    assert tuple(t.action for t in higher.trial.ticks) != tuple(
        t.action for t in lower.trial.ticks
    )
    # The action difference is induced by explicitly installed maximization/
    # minimization, not the mere presence of a predictor.
    assert higher.trial.completed_ticks == lower.trial.completed_ticks == cfg.horizon


def test_blind_sensor_is_trivially_predictable_not_usefully_informative() -> None:
    cfg = replace(abundant_config(), sensor=Interoception(gain=0))
    blind = run_probe(seed=2, preference="none", retained=True, config=cfg)
    assert blind.observed_sensor_span == 0
    assert blind.mean_absolute_error == 0
    assert blind.learned_cells > 0


def test_probe_never_learns_terminal_censored_delta() -> None:
    cfg = M1Config(
        horizon=20,
        physics=MetabolismConfig(
            initial_energy=1, basal_cost=0.25, move_cost=0, fight_cost=0,
            food_energy=0.01,
        ),
    )
    result = run_probe(seed=5, preference="none", retained=True, config=cfg)
    assert result.trial.terminal
    assert result.scored_transitions == result.trial.completed_ticks - 1
    assert sum(t.terminal_now for t in result.trial.ticks) == 1


def test_estimator_uses_only_next_sensor_reading_and_has_no_hidden_target() -> None:
    model = DeltaProbe(retained=True)
    assert model.estimate(2, "MOVE") == 0
    model.arrive(10.0)
    model.commit(2, "MOVE", 10.0)
    model.arrive(13.0)
    assert model.estimate(2, "MOVE") == 3.0
    assert model.scored == 1
    assert model.sum_absolute_error == 3.0
    model.commit(2, "MOVE", 13.0)
    model.arrive(16.0)
    assert model.scored == 2
    assert model.sum_absolute_error == 3.0
    assert model.estimate(2, "MOVE") == 3.0
    assert model.counts == {(2, "MOVE"): 2}


def test_fail_closed_policy_and_experimental_action_hook() -> None:
    cfg = M1Config(horizon=1)
    with pytest.raises(ValueError, match="selector"):
        run_trial(seed=1, policy="external", learning=False, config=cfg)
    with pytest.raises(ValueError, match="selector"):
        run_trial(
            seed=1, policy="fixed_wait", learning=False, config=cfg,
            external_selector=lambda cue, reading: "WAIT",
        )
    with pytest.raises(ValueError, match="external experimental"):
        run_trial(
            seed=1, policy="external", learning=False, config=cfg,
            external_selector=lambda cue, reading: "CREATE_FOOD",
        )
    with pytest.raises(ValueError, match="appraisal"):
        run_probe(seed=1, preference="SURVIVE", retained=True)
    with pytest.raises(ValueError, match="exploration"):
        run_probe(seed=1, preference="none", retained=True, exploration=-0.1)


def test_sensing_noise_and_costs_are_declared_not_inferred() -> None:
    cfg = replace(abundant_config(), noise_sigma=0.5, observation_cost=0.1)
    on = run_probe(seed=19, preference="none", retained=True, config=cfg)
    off = run_probe(seed=19, preference="none", retained=False, config=cfg)
    assert on.trial.ticks == off.trial.ticks
    assert on.trial.total_expenditure == off.trial.total_expenditure
    assert on.mean_absolute_error is not None
