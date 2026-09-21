from dataclasses import replace

import pytest

from experiments.predator_values import (
    RewardGenes,
    SimulationConfig,
    TransitionTrace,
    run_simulation,
)
from experiments.value_trajectory_recurrence import (
    ValueSignSignature,
    analyze_recurrence,
    value_components,
    value_sign_signature,
)


def trace(
    *,
    intrinsic_reward: float,
    genes: RewardGenes,
    food_eaten: int = 0,
    moved: int = 0,
    physical_energy_delta: float = -0.05,
    conspecific_signal: float = 0.0,
    predator_signal: float = 0.0,
    step: int = 1,
) -> TransitionTrace:
    return TransitionTrace(
        step=step,
        agent_id=step,
        parent_id=None,
        observed_state=(0, 0, 0, 0),
        action=0,
        food_eaten=food_eaten,
        moved=moved,
        physical_energy_delta=physical_energy_delta,
        reward_genes=genes,
        energy_after_body_dynamics=10.0,
        age=1,
        survived_natural_filter=True,
        survived_predation=True,
        conspecific_signal=conspecific_signal,
        predator_signal=predator_signal,
        intrinsic_reward=intrinsic_reward,
    )


def test_value_signature_uses_only_existing_reward_terms_and_physical_delta() -> None:
    config = SimulationConfig(sensor_reward_scale=0.25)
    sample = trace(
        intrinsic_reward=1.0,
        genes=RewardGenes(
            food=2.0,
            movement=-1.0,
            conspecific=4.0,
            predator=-4.0,
        ),
        food_eaten=1,
        moved=1,
        physical_energy_delta=9.87,
        conspecific_signal=0.5,
        predator_signal=0.5,
    )

    assert value_components(sample, config=config) == (
        2.0,
        -1.0,
        0.5,
        -0.5,
    )
    assert value_sign_signature(sample, config=config) == ValueSignSignature(
        physical_energy=1,
        food=1,
        movement=-1,
        conspecific=1,
        predator=-1,
    )


def test_value_component_reconstruction_fails_closed_on_inconsistent_trace() -> None:
    config = SimulationConfig()
    sample = trace(
        intrinsic_reward=99.0,
        genes=RewardGenes(0.0, 0.0, 0.0, 0.0),
    )

    with pytest.raises(
        ValueError,
        match="does not match reconstructed components",
    ):
        value_components(sample, config=config)


def test_recurrence_analysis_exposes_scalar_reduction_counterexample() -> None:
    config = SimulationConfig(sensor_reward_scale=0.25)
    mixed = trace(
        intrinsic_reward=1.0,
        genes=RewardGenes(2.0, -1.0, 4.0, -4.0),
        food_eaten=1,
        moved=1,
        physical_energy_delta=9.87,
        conspecific_signal=0.5,
        predator_signal=0.5,
        step=1,
    )
    mixed_repeat = replace(mixed, step=2, agent_id=2)
    simple = trace(
        intrinsic_reward=1.0,
        genes=RewardGenes(1.0, 0.0, 0.0, 0.0),
        food_eaten=1,
        physical_energy_delta=9.95,
        step=3,
    )

    analysis = analyze_recurrence(
        (mixed, mixed_repeat, simple),
        config=config,
    )

    assert analysis.evaluated_transitions == 3
    assert analysis.unique_signatures == 2
    assert analysis.recurrent_signatures == 1
    assert analysis.recurrent_transitions == 2
    assert analysis.exact_intrinsic_value_ambiguities == 1
    assert analysis.intrinsic_sign_ambiguity_buckets == 1


def test_seeded_predator_trace_has_recurrent_label_free_value_signatures() -> None:
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

    run_simulation(
        seed=31,
        steps=60,
        config=config,
        trace_sink=traces.append,
    )
    analysis = analyze_recurrence(tuple(traces), config=config)

    assert analysis.evaluated_transitions > 0
    assert analysis.unique_signatures > 1
    assert analysis.recurrent_signatures > 0
    assert analysis.recurrent_transitions > analysis.recurrent_signatures
    assert analysis.intrinsic_sign_ambiguity_buckets > 0
