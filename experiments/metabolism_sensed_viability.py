"""M #616: source-scoped, read-only viability from fallible Energy observation.

No true M01State, no Body ledger, no Action, no reward, no behavior selector.
The result is CONDITIONAL on an explicit bounded-noise sensor assumption,
a hypothetical M0.1 cost quote and an existing M0 sensor reading; it does
NOT imply real World source authentication or guaranteed future success.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal

from experiments.metabolism_m01_minecraft import M01Profile
from experiments.metabolism_resource_projection import (
    SelfBodyResourceCosts,
    VisibleResourceQuote,
)
from experiments.metabolism_viability import Interoception

Affordability = Literal[
    "MODEL_AFFORDABLE", "MODEL_INSUFFICIENT", "MODEL_AMBIGUOUS", "UNKNOWN"
]


@dataclass(frozen=True)
class SensedCostAssessment:
    label: str
    estimated_world_ticks: int | None
    estimated_energy_cost: float | None
    affordability: Affordability
    reason: str


@dataclass(frozen=True)
class SensedViabilityView:
    session_id: str
    owner_world_tick: int
    model_energy_lower: float | None
    model_energy_upper: float | None
    assessments: tuple[SensedCostAssessment, ...]
    source_scope: str = "OFFLINE_MODEL_CONDITIONAL_NOT_WORLD_ATTESTED"


def _finite(value: object) -> bool:
    return type(value) in (float, int) and math.isfinite(value)


def _sensor_range(
    reading: float, sensor: Interoception, capacity: float,
    noise_bound: float | None,
) -> tuple[float, float] | None:
    """Inverse of deterministic rounding with outward numeric rounding.

    A None noise bound is UNKNOWN, not shorthand for zero. Gaussian/unbounded
    noise has no guaranteed interval and must also be passed as None.
    """
    if noise_bound is None or sensor.gain == 0:
        return None
    half_width = sensor.quantum / 2.0 + noise_bound
    if not math.isfinite(half_width):
        return None
    low = (reading - sensor.bias - half_width) / sensor.gain
    high = (reading - sensor.bias + half_width) / sensor.gain
    if not math.isfinite(low) or not math.isfinite(high):
        return None
    if high < 0 or low > capacity:
        return None  # sensor reading inconsistent with a body of this capacity
    # Avoid false certainty at a quantization or floating-point boundary.
    return (
        max(0.0, math.nextafter(low, -math.inf)),
        min(capacity, math.nextafter(high, math.inf)),
    )


def _assess(
    quote: VisibleResourceQuote, sensor_range: tuple[float, float] | None,
) -> SensedCostAssessment:
    cost = quote.estimated_energy_cost
    if cost is None:
        return SensedCostAssessment(
            quote.label, quote.world_ticks, None, "UNKNOWN", "UNKNOWN_CANDIDATE_COST"
        )
    if sensor_range is None:
        return SensedCostAssessment(
            quote.label, quote.world_ticks, cost, "UNKNOWN", "UNKNOWN_SENSOR_RANGE"
        )
    low, high = sensor_range
    # M0.1 terminal rule is raw_energy <= 0. Equality is not affordable.
    if low > cost:
        result = "MODEL_AFFORDABLE"
    elif high <= cost:
        result = "MODEL_INSUFFICIENT"
    else:
        result = "MODEL_AMBIGUOUS"
    return SensedCostAssessment(
        quote.label, quote.world_ticks, cost, result,
        "MODEL_ONLY_NO_FUTURE_OUTCOME_OR_ACTION_AUTHORITY",
    )


def assess_sensed_costs(
    profile: M01Profile,
    body_view: SelfBodyResourceCosts,
    sensor: Interoception,
    *,
    noise_bound: float | None = None,
) -> SensedViabilityView:
    """Only a *sensor reading*, candidate costs and the public capacity enter.

    Set noise_bound=0 only with an explicitly assumed deterministic M0 sensor.
    This does not accept the evaluator-private ResourceQuote or any true E.
    Failed sensor precision / unknown routes / unbounded noise yield UNKNOWN,
    never a fabricated feasibility policy.
    """
    if not isinstance(profile, M01Profile):
        raise ValueError("typed M0.1 profile required")
    if not isinstance(body_view, SelfBodyResourceCosts):
        raise ValueError("typed SelfBody resource view required")
    if not isinstance(sensor, Interoception):
        raise ValueError("typed M0 sensor required")
    if noise_bound is not None and (
        not _finite(noise_bound) or noise_bound < 0
    ):
        raise ValueError("noise bound must be finite nonnegative or unknown")
    if (
        not isinstance(body_view.session_id, str)
        or not body_view.session_id
        or type(body_view.owner_world_tick) is not int
        or body_view.owner_world_tick < 0
        or not _finite(body_view.observed_energy_reading)
        or not isinstance(body_view.quotes, tuple)
        or body_view.source_scope != "OFFLINE_ESTIMATE_NOT_PHYSICAL_OR_ACTION_AUTHORITY"
    ):
        raise ValueError("invalid or foreign producer scope")
    labels: set[str] = set()
    for quote in body_view.quotes:
        if (
            not isinstance(quote, VisibleResourceQuote)
            or not isinstance(quote.label, str)
            or not quote.label.strip()
            or quote.label in labels
            or (quote.world_ticks is not None
                and (type(quote.world_ticks) is not int or quote.world_ticks < 1))
            or (quote.estimated_energy_cost is not None
                and (not _finite(quote.estimated_energy_cost)
                     or quote.estimated_energy_cost < 0
                     or quote.world_ticks is None))
            or (quote.estimated_energy_cost is None and quote.world_ticks is not None)
        ):
            raise ValueError("invalid, ambiguous or duplicate cost quote")
        labels.add(quote.label)
    bounds = _sensor_range(
        body_view.observed_energy_reading, sensor, profile.capacity, noise_bound
    )
    return SensedViabilityView(
        body_view.session_id,
        body_view.owner_world_tick,
        bounds[0] if bounds else None,
        bounds[1] if bounds else None,
        tuple(_assess(q, bounds) for q in body_view.quotes),
    )
