from dataclasses import replace

from experiments.learned_control_space import (
    analyze_learned_control_space,
    control_profile,
    grounded_value_vector,
    selected_action_is_greedy,
)
from experiments.predator_values import (
    RewardGenes,
    SimulationConfig,
    TransitionTrace,
    run_simulation,
)


def trace(
    *,
    action_values: tuple[float, float, float],
    action: int,
    step: int,
    agent_id: int,
    observed_state: tuple[int, int, int, int] = (0, 0, 0, 0),
) -> TransitionTrace:
    return TransitionTrace(
        step=step,
        agent_id=agent_id,
        parent_id=None,
        observed_state=observed_state,
        action_values=action_values,
        action=action,
        food_eaten=0,
        moved=0,
        physical_energy_delta=-0.05,
        reward_genes=RewardGenes(0.0, 0.0, 0.0, 0.0),
        energy_after_body_dynamics=10.0,
        age=1,
        survived_natural_filter=True,
        survived_predation=True,
        conspecific_signal=0.0,
        predator_signal=0.0,
        intrinsic_reward=0.0,
    )


def test_same_exact_value_and_state_can_have_different_learned_control_profiles() -> None:
    config = SimulationConfig()
    left = trace(
        action_values=(1.0, 0.0, 0.0),
        action=-1,
        step=1,
        agent_id=1,
    )
    right = trace(
        action_values=(0.0, 0.0, 1.0),
        action=1,
        step=2,
        agent_id=2,
    )

    assert grounded_value_vector(left, config=config) == grounded_value_vector(
        right,
        config=config,
    )
    assert left.observed_state == right.observed_state
    assert control_profile(left) != control_profile(right)

    analysis = analyze_learned_control_space(
        (left, right),
        config=config,
    )
    assert analysis.exact_value_buckets == 1
    assert analysis.exact_value_buckets_with_distinct_control == 1
    assert analysis.exact_state_buckets == 1
    assert analysis.exact_state_buckets_with_distinct_control == 1
    assert analysis.distinct_control_profiles == 2
    assert analysis.greedy_consistent_actions == 2
    assert analysis.non_greedy_actions == 0


def test_greedy_check_uses_pre_action_profile_and_allows_ties() -> None:
    tied = trace(
        action_values=(1.0, 1.0, 0.0),
        action=0,
        step=1,
        agent_id=1,
    )
    exploratory = trace(
        action_values=(1.0, 0.0, 0.0),
        action=1,
        step=2,
        agent_id=2,
    )

    assert selected_action_is_greedy(tied) is True
    assert selected_action_is_greedy(exploratory) is False


def test_seeded_simulation_shows_history_dependent_control_beyond_exact_value() -> None:
    config = replace(
        SimulationConfig(),
        world_size=24,
        initial_population=16,
        initial_food=6,
        max_food=12,
        max_population=48,
        sample_interval=20,
    )
    traces: list[TransitionTrace] = []

    baseline = run_simulation(
        seed=41,
        steps=120,
        config=config,
    )
    observed = run_simulation(
        seed=41,
        steps=120,
        config=config,
        trace_sink=traces.append,
    )

    assert observed == baseline

    analysis = analyze_learned_control_space(
        tuple(traces),
        config=config,
    )

    assert analysis.evaluated_transitions > 0
    assert analysis.distinct_control_profiles > 1
    assert analysis.exact_value_buckets_with_distinct_control > 0
    assert analysis.exact_state_buckets_with_distinct_control > 0
    assert (
        analysis.greedy_consistent_actions + analysis.non_greedy_actions
        == analysis.evaluated_transitions
    )
    assert analysis.all_zero_profiles < analysis.evaluated_transitions
