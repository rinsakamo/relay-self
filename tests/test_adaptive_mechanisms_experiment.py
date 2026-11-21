from dataclasses import replace

import pytest

from experiments.adaptive_mechanisms import (
    FAST,
    MEDIUM,
    SLOW,
    CacheEntry,
    SimulationConfig,
    Task,
    choose_mechanism,
    generate_tasks,
    mechanism_action,
    run_condition,
    run_paired,
)


def task(**changes: object) -> Task:
    values = {
        "episode": 0,
        "phase": "learning",
        "context": 2,
        "base_action": 0,
        "hidden_regime": 0,
        "regime_signal": 0,
        "uncertainty": 0.45,
        "deadline": 10,
        "target_action": 0,
    }
    values.update(changes)
    return Task(**values)


def test_task_generation_is_seeded_and_regime_shift_changes_target() -> None:
    config = SimulationConfig(episodes=12, learning_end=4, regime_shift_at=8, context_count=2)
    first = generate_tasks(seed=7, config=config)
    second = generate_tasks(seed=7, config=config)

    assert first == second
    before = first[6]
    after = first[8]
    assert before.context == after.context
    assert before.base_action == after.base_action
    assert before.hidden_regime == 0
    assert after.hidden_regime == 1
    assert before.target_action != after.target_action


def test_adaptive_selector_uses_slow_for_uncached_uncertain_task_when_time_allows() -> None:
    config = SimulationConfig()
    selected = choose_mechanism(
        condition="adaptive",
        task=task(uncertainty=config.high_uncertainty, deadline=config.relaxed_deadline),
        cache={},
        config=config,
    )
    assert selected == SLOW


def test_adaptive_selector_uses_fast_after_expensive_solution_is_cached() -> None:
    config = SimulationConfig()
    current = task()
    cache = {current.context: CacheEntry(action=current.target_action, learned_at_episode=0)}

    assert (
        choose_mechanism(condition="adaptive", task=current, cache=cache, config=config)
        == FAST
    )
    action, cache_hit = mechanism_action(FAST, current, cache)
    assert cache_hit is True
    assert action == current.target_action


def test_tight_deadline_prevents_adaptive_slow_selection() -> None:
    config = SimulationConfig()
    selected = choose_mechanism(
        condition="adaptive",
        task=task(deadline=config.tight_deadline),
        cache={},
        config=config,
    )
    assert selected == FAST


def test_medium_uses_noisy_regime_signal_without_hidden_regime_truth() -> None:
    current = task(base_action=1, hidden_regime=1, regime_signal=0, target_action=0)
    action, cache_hit = mechanism_action(MEDIUM, current, {})
    assert cache_hit is False
    assert action == 1
    assert action != current.target_action


def test_adaptive_invalidates_stale_cache_and_re_escalates() -> None:
    config = SimulationConfig(
        episodes=6,
        context_count=1,
        learning_end=2,
        regime_shift_at=4,
        high_uncertainty_probability=1.0,
        tight_deadline_probability=0.0,
        medium_deadline_probability=0.0,
    )
    result = run_condition(seed=3, condition="adaptive", config=config)

    assert result.phase_mechanism_counts["learning"][SLOW] == 1
    assert result.phase_mechanism_counts["stable"][FAST] == 2
    assert result.escalation_episodes == (4,)
    assert result.re_escalation_episodes == (5,)
    assert result.shift_recovery_episode == 5
    assert result.cache_invalidations == 1


def test_stable_repetition_amortizes_to_fast_without_free_selector() -> None:
    config = SimulationConfig(
        episodes=9,
        context_count=1,
        learning_end=3,
        regime_shift_at=6,
        high_uncertainty_probability=1.0,
        tight_deadline_probability=0.0,
        medium_deadline_probability=0.0,
        selector_cost=0.5,
    )
    result = run_condition(seed=1, condition="adaptive", config=config)

    assert result.phase_mechanism_counts["learning"][SLOW] == 1
    assert result.phase_mechanism_counts["stable"][SLOW] == 0
    assert result.phase_mechanism_counts["stable"][FAST] == 3
    assert result.cheap_reuses >= 1
    assert result.selector_overhead == config.selector_cost * config.episodes


def test_paired_conditions_share_exact_same_generated_task_sequence() -> None:
    config = SimulationConfig(episodes=12, learning_end=4, regime_shift_at=8)
    paired = run_paired(seed=11, config=config)
    reference = [
        (record.episode, record.context, record.target_action)
        for record in paired["cheap_only"].trace
    ]

    for result in paired.values():
        observed = [
            (record.episode, record.context, record.target_action) for record in result.trace
        ]
        assert observed == reference


def test_condition_run_is_reproducible() -> None:
    first = run_condition(seed=5, condition="adaptive")
    second = run_condition(seed=5, condition="adaptive")
    assert first == second


def test_unknown_condition_fails_closed() -> None:
    with pytest.raises(ValueError, match="condition"):
        run_condition(seed=0, condition="unknown")


def test_configuration_rejects_invalid_phase_order() -> None:
    with pytest.raises(ValueError, match="phase boundaries"):
        replace(SimulationConfig(), learning_end=170, regime_shift_at=160)
