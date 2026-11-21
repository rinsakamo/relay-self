from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from experiments.predator_values import (
    ACTIONS,
    SimulationConfig,
    TransitionTrace,
)
from experiments.value_trajectory_recurrence import value_components

GroundedValueVector = tuple[float, float, float, float, float]
ControlProfile = tuple[float, float, float]


@dataclass(frozen=True)
class LearnedControlSpaceAnalysis:
    evaluated_transitions: int
    exact_value_buckets: int
    exact_value_buckets_with_distinct_control: int
    exact_state_buckets: int
    exact_state_buckets_with_distinct_control: int
    distinct_control_profiles: int
    repeated_nonzero_control_profiles: int
    all_zero_profiles: int
    greedy_consistent_actions: int
    non_greedy_actions: int


def grounded_value_vector(
    trace: TransitionTrace,
    *,
    config: SimulationConfig,
) -> GroundedValueVector:
    """Preserve the raw already-grounded value contributions without binning."""

    food, movement, conspecific, predator = value_components(
        trace,
        config=config,
    )
    return (
        trace.physical_energy_delta,
        food,
        movement,
        conspecific,
        predator,
    )


def control_profile(trace: TransitionTrace) -> ControlProfile:
    """Return the pre-action learned values for ACTIONS=(-1, 0, 1)."""

    values = trace.action_values
    if (
        not isinstance(values, tuple)
        or len(values) != len(ACTIONS)
        or not all(isinstance(value, float) for value in values)
    ):
        raise ValueError("action_values must be one float per primitive action")
    return values


def selected_action_is_greedy(trace: TransitionTrace) -> bool:
    """Check the selected action against the pre-action Q-profile."""

    profile = control_profile(trace)
    best = max(profile)
    greedy_actions = {
        action
        for action, value in zip(ACTIONS, profile, strict=True)
        if value == best
    }
    return trace.action in greedy_actions


def analyze_learned_control_space(
    traces: tuple[TransitionTrace, ...],
    *,
    config: SimulationConfig,
) -> LearnedControlSpaceAnalysis:
    """Test exact current-value/state reductions before any clustering."""

    evaluated = tuple(
        trace for trace in traces if trace.intrinsic_reward is not None
    )

    by_value: dict[GroundedValueVector, set[ControlProfile]] = defaultdict(set)
    by_state: dict[tuple[int, int, int, int], set[ControlProfile]] = defaultdict(set)
    profile_counts: dict[ControlProfile, int] = defaultdict(int)

    all_zero = 0
    greedy = 0
    non_greedy = 0

    for trace in evaluated:
        profile = control_profile(trace)
        by_value[grounded_value_vector(trace, config=config)].add(profile)
        by_state[trace.observed_state].add(profile)
        profile_counts[profile] += 1

        if all(value == 0.0 for value in profile):
            all_zero += 1
        if selected_action_is_greedy(trace):
            greedy += 1
        else:
            non_greedy += 1

    repeated_nonzero = sum(
        count >= 2 and any(value != 0.0 for value in profile)
        for profile, count in profile_counts.items()
    )

    return LearnedControlSpaceAnalysis(
        evaluated_transitions=len(evaluated),
        exact_value_buckets=len(by_value),
        exact_value_buckets_with_distinct_control=sum(
            len(profiles) > 1 for profiles in by_value.values()
        ),
        exact_state_buckets=len(by_state),
        exact_state_buckets_with_distinct_control=sum(
            len(profiles) > 1 for profiles in by_state.values()
        ),
        distinct_control_profiles=len(profile_counts),
        repeated_nonzero_control_profiles=repeated_nonzero,
        all_zero_profiles=all_zero,
        greedy_consistent_actions=greedy,
        non_greedy_actions=non_greedy,
    )
