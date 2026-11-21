from __future__ import annotations

import math
from collections import Counter, defaultdict
from dataclasses import dataclass

from experiments.predator_values import (
    SimulationConfig,
    TransitionTrace,
)


@dataclass(frozen=True, order=True)
class ValueSignSignature:
    """Direction-only signature of already-grounded value contributions."""

    physical_energy: int
    food: int
    movement: int
    conspecific: int
    predator: int


@dataclass(frozen=True)
class RecurrenceAnalysis:
    evaluated_transitions: int
    unique_signatures: int
    recurrent_signatures: int
    recurrent_transitions: int
    exact_intrinsic_value_ambiguities: int
    intrinsic_sign_ambiguity_buckets: int
    signature_counts: tuple[tuple[ValueSignSignature, int], ...]


def _sign(value: float) -> int:
    return (value > 0.0) - (value < 0.0)


def value_components(
    trace: TransitionTrace,
    *,
    config: SimulationConfig,
) -> tuple[float, float, float, float]:
    """Reconstruct the four terms already summed by intrinsic_reward()."""

    if (
        trace.conspecific_signal is None
        or trace.predator_signal is None
        or trace.intrinsic_reward is None
    ):
        raise ValueError("transition has no evaluated intrinsic reward")

    genes = trace.reward_genes
    food = trace.food_eaten * genes.food
    movement = trace.moved * genes.movement
    conspecific = (
        config.sensor_reward_scale
        * trace.conspecific_signal
        * genes.conspecific
    )
    predator = (
        config.sensor_reward_scale
        * trace.predator_signal
        * genes.predator
    )

    reconstructed = food + movement + conspecific + predator
    if not math.isclose(
        reconstructed,
        trace.intrinsic_reward,
        rel_tol=1e-12,
        abs_tol=1e-12,
    ):
        raise ValueError("trace intrinsic reward does not match reconstructed components")
    return food, movement, conspecific, predator


def value_sign_signature(
    trace: TransitionTrace,
    *,
    config: SimulationConfig,
) -> ValueSignSignature:
    """Reduce only contribution direction; do not assign affective semantics."""

    food, movement, conspecific, predator = value_components(
        trace,
        config=config,
    )
    return ValueSignSignature(
        physical_energy=_sign(trace.physical_energy_delta),
        food=_sign(food),
        movement=_sign(movement),
        conspecific=_sign(conspecific),
        predator=_sign(predator),
    )


def analyze_recurrence(
    traces: tuple[TransitionTrace, ...],
    *,
    config: SimulationConfig,
) -> RecurrenceAnalysis:
    """Count exact sign-pattern recurrence and simple scalar reductions."""

    evaluated = tuple(
        trace
        for trace in traces
        if trace.intrinsic_reward is not None
    )
    pairs = tuple(
        (trace, value_sign_signature(trace, config=config))
        for trace in evaluated
    )
    counts = Counter(signature for _, signature in pairs)

    exact_intrinsic: dict[float, set[ValueSignSignature]] = defaultdict(set)
    intrinsic_sign: dict[int, set[ValueSignSignature]] = defaultdict(set)
    for trace, signature in pairs:
        assert trace.intrinsic_reward is not None
        exact_intrinsic[trace.intrinsic_reward].add(signature)
        intrinsic_sign[_sign(trace.intrinsic_reward)].add(signature)

    recurrent = {
        signature: count
        for signature, count in counts.items()
        if count >= 2
    }
    return RecurrenceAnalysis(
        evaluated_transitions=len(evaluated),
        unique_signatures=len(counts),
        recurrent_signatures=len(recurrent),
        recurrent_transitions=sum(recurrent.values()),
        exact_intrinsic_value_ambiguities=sum(
            len(signatures) > 1
            for signatures in exact_intrinsic.values()
        ),
        intrinsic_sign_ambiguity_buckets=sum(
            len(signatures) > 1
            for signatures in intrinsic_sign.values()
        ),
        signature_counts=tuple(sorted(counts.items())),
    )
