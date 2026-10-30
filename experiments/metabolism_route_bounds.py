"""M #616: read-only bounded travel/resource scenarios, no choice or issuer.

M0.1 Energy and P1 are hypothetical models, not Minecraft hunger/exhaustion.
No food is credited merely because a route reaches a food opportunity.
Every route, timing and hazard-expenditure bound must be caller-supplied.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal

from experiments.fatigue_p1 import FatigueProfile, FatigueState
from experiments.metabolism_m01_minecraft import M01Profile, M01State
from experiments.metabolism_resource_projection import Candidate, quote_candidate
from experiments.metabolism_sensed_viability import SensedViabilityView

Destination = Literal["GOAL", "FOOD_OPPORTUNITY"]
RangeStatus = Literal["BOUNDED_MODEL", "UNKNOWN"]
ModelAffordability = Literal[
    "MODEL_AFFORDABLE_ALL_BOUNDS",
    "MODEL_INSUFFICIENT_ALL_BOUNDS",
    "MODEL_AMBIGUOUS",
    "UNKNOWN",
]


def _finite_nonnegative(value: object) -> bool:
    return type(value) in (int, float) and math.isfinite(value) and value >= 0


@dataclass(frozen=True)
class RouteBounds:
    """External assumptions, NOT a terrain reader or discovered food claim.

    None means UNKNOWN. Extra expense is in M0.1 hypothetical Energy units,
    not HP, native Minecraft saturation or M0.2 exhaustion.
    """

    label: str
    destination: Destination
    min_blocks: float | None
    max_blocks: float | None
    min_blocks_per_tick: float | None
    max_blocks_per_tick: float | None
    min_extra_wait_ticks: int | None
    max_extra_wait_ticks: int | None
    min_extra_energy: float | None
    max_extra_energy: float | None

    def __post_init__(self) -> None:
        if not isinstance(self.label, str) or not self.label.strip():
            raise ValueError("nonempty route label required")
        if self.destination not in ("GOAL", "FOOD_OPPORTUNITY"):
            raise ValueError("unknown route destination")
        for low, high in (
            (self.min_blocks, self.max_blocks),
            (self.min_blocks_per_tick, self.max_blocks_per_tick),
            (self.min_extra_energy, self.max_extra_energy),
        ):
            if low is None or high is None:
                continue
            if not _finite_nonnegative(low) or not _finite_nonnegative(high) or low > high:
                raise ValueError("invalid route interval")
        if self.min_blocks_per_tick is not None and (
            not _finite_nonnegative(self.min_blocks_per_tick)
            or self.min_blocks_per_tick == 0
        ):
            raise ValueError("invalid lower speed")
        if self.max_blocks_per_tick is not None and (
            not _finite_nonnegative(self.max_blocks_per_tick)
            or self.max_blocks_per_tick == 0
        ):
            raise ValueError("invalid upper speed")
        for value in (self.min_extra_wait_ticks, self.max_extra_wait_ticks):
            if value is not None and (type(value) is not int or value < 0):
                raise ValueError("invalid extra wait ticks")
        if (self.min_extra_wait_ticks is not None
                and self.max_extra_wait_ticks is not None
                and self.min_extra_wait_ticks > self.max_extra_wait_ticks):
            raise ValueError("reversed extra WAIT interval")
        for value in (
            self.min_blocks, self.max_blocks, self.min_extra_energy,
            self.max_extra_energy,
        ):
            if value is not None and not _finite_nonnegative(value):
                raise ValueError("nonfinite or negative scenario input")


@dataclass(frozen=True)
class RouteCostRange:
    label: str
    destination: Destination
    session_id: str
    owner_world_tick: int
    status: RangeStatus
    min_world_ticks: int | None
    max_world_ticks: int | None
    min_energy_cost: float | None
    max_energy_cost: float | None
    reason: str
    future_food_credited: bool = False
    source_scope: str = "OFFLINE_M01_P1_HYPOTHESIS_NOT_PHYSICAL_ATTESTATION"


@dataclass(frozen=True)
class SensedRouteAffordability:
    label: str
    destination: Destination
    affordability: ModelAffordability
    min_energy_cost: float | None
    max_energy_cost: float | None
    reason: str


@dataclass(frozen=True)
class RouteComparison:
    """Non-ranking comparison: no selected action, reward or utility."""

    session_id: str
    owner_world_tick: int
    results: tuple[SensedRouteAffordability, ...]
    source_scope: str = "OFFLINE_CONDITIONAL_RESOURCE_INFORMATION_ONLY"


def quote_route_range(
    profile: M01Profile,
    state: M01State,
    route: RouteBounds,
    *,
    fatigue_profile: FatigueProfile | None = None,
    fatigue_state: FatigueState | None = None,
) -> RouteCostRange:
    """Two corner-case projections, plus explicitly bounded extra costs.

    Bounds are conditional on monotone, unobstructed locomotion and the
    caller's exhaustive scenario intervals. Never silently add future food.
    Missing hazard/delay bounds -> UNKNOWN, not an optimistic zero.
    Extra WAIT ticks are assumed AFTER the MOVE, not interspersed with motion.
    Interleaved P1 recovery or uncertain interruption timing is out of model.
    """
    if not isinstance(route, RouteBounds):
        raise ValueError("typed route assumptions required")
    if not isinstance(state, M01State):
        raise ValueError("typed M0.1 state required")

    def unknown(reason: str) -> RouteCostRange:
        return RouteCostRange(
            route.label, route.destination, state.session_id, state.world_tick,
            "UNKNOWN", None, None, None, None, reason,
        )

    values = (
        route.min_blocks, route.max_blocks, route.min_blocks_per_tick,
        route.max_blocks_per_tick, route.min_extra_wait_ticks,
        route.max_extra_wait_ticks, route.min_extra_energy, route.max_extra_energy,
    )
    if any(x is None for x in values):
        return unknown("UNKNOWN_ROUTE_TIME_OR_EXTRA_COST_BOUNDS")
    if route.min_blocks <= 0:
        return unknown("ZERO_OR_UNRESOLVED_TRAVEL_DISTANCE")
    # Original M0.1 max displacement is an independent physics guard.
    # Unqualified G4 faster-than-limit mode must not create a numeric quote.
    if route.max_blocks_per_tick > profile.max_displacement_per_tick:
        return unknown("UNQUALIFIED_GAIT_RATE")
    if fatigue_state is None:
        return unknown("UNKNOWN_P1_FATIGUE_STATE")
    lower = quote_candidate(
        profile, state,
        Candidate(route.label, "MOVE", distance_blocks=route.min_blocks,
                  nominal_blocks_per_tick=route.max_blocks_per_tick),
        fatigue_profile=fatigue_profile, fatigue_state=fatigue_state,
    )
    upper = quote_candidate(
        profile, state,
        Candidate(route.label, "MOVE", distance_blocks=route.max_blocks,
                  nominal_blocks_per_tick=route.min_blocks_per_tick),
        fatigue_profile=fatigue_profile, fatigue_state=fatigue_state,
    )
    if lower.status == "UNKNOWN" or upper.status == "UNKNOWN":
        return unknown("UNBOUNDED_OR_UNQUALIFIED_P1_MOVEMENT")
    min_ticks = lower.world_ticks + route.min_extra_wait_ticks
    max_ticks = upper.world_ticks + route.max_extra_wait_ticks
    min_cost = lower.required_energy + (
        route.min_extra_wait_ticks * profile.basal_per_world_tick
    ) + route.min_extra_energy
    max_cost = upper.required_energy + (
        route.max_extra_wait_ticks * profile.basal_per_world_tick
    ) + route.max_extra_energy
    if (
        not math.isfinite(min_cost) or not math.isfinite(max_cost)
        or min_ticks > max_ticks or min_cost > max_cost
    ):
        return unknown("INVALID_COST_BOUND_ORDER")
    return RouteCostRange(
        route.label, route.destination, state.session_id, state.world_tick,
        "BOUNDED_MODEL", min_ticks, max_ticks, min_cost, max_cost,
        "CONDITIONAL_BOUNDS_NO_FUTURE_FOOD_OR_WORLD_GUARANTEE",
    )


def compare_route_ranges(
    sensed: SensedViabilityView, ranges: tuple[RouteCostRange, ...],
) -> RouteComparison:
    """Self-facing information, never use true host Energy for comparison.

    Even the strongest classification means only that all provided *model*
    scenarios and *assumed sensor* bounds agree; never guarantee survival.
    """
    if (
        not isinstance(sensed, SensedViabilityView)
        or sensed.source_scope != "OFFLINE_MODEL_CONDITIONAL_NOT_WORLD_ATTESTED"
        or not isinstance(sensed.session_id, str) or not sensed.session_id
        or type(sensed.owner_world_tick) is not int
        or sensed.owner_world_tick < 0
        or not isinstance(ranges, tuple)
    ):
        raise ValueError("valid sensed epoch and typed range tuple required")
    if (sensed.model_energy_lower is None) != (sensed.model_energy_upper is None):
        raise ValueError("partial energy sensor interval")
    if sensed.model_energy_lower is not None and (
        not _finite_nonnegative(sensed.model_energy_lower)
        or not _finite_nonnegative(sensed.model_energy_upper)
        or sensed.model_energy_lower > sensed.model_energy_upper
    ):
        raise ValueError("invalid sensed energy interval")
    seen: set[str] = set()
    results: list[SensedRouteAffordability] = []
    for r in ranges:
        if (
            not isinstance(r, RouteCostRange)
            or r.session_id != sensed.session_id
            or r.owner_world_tick != sensed.owner_world_tick
            or r.source_scope != "OFFLINE_M01_P1_HYPOTHESIS_NOT_PHYSICAL_ATTESTATION"
            or r.future_food_credited is not False
            or r.label in seen
            or r.destination not in ("GOAL", "FOOD_OPPORTUNITY")
        ):
            raise ValueError("foreign/duplicate/counterfeit food route")
        seen.add(r.label)
        if r.status == "UNKNOWN":
            if any(v is not None for v in (
                r.min_world_ticks, r.max_world_ticks,
                r.min_energy_cost, r.max_energy_cost,
            )):
                raise ValueError("unknown route cannot carry partial cost")
        elif r.status == "BOUNDED_MODEL":
            if (
                type(r.min_world_ticks) is not int
                or type(r.max_world_ticks) is not int
                or r.min_world_ticks < 1 or r.min_world_ticks > r.max_world_ticks
                or not _finite_nonnegative(r.min_energy_cost)
                or not _finite_nonnegative(r.max_energy_cost)
                or r.min_energy_cost > r.max_energy_cost
            ):
                raise ValueError("invalid bounded route cost")
        else:
            raise ValueError("unknown route status")
        if r.status == "UNKNOWN":
            status, reason = "UNKNOWN", r.reason
        elif sensed.model_energy_lower is None:
            status, reason = "UNKNOWN", "UNKNOWN_SENSOR_RANGE"
        elif sensed.model_energy_lower > r.max_energy_cost:
            status, reason = "MODEL_AFFORDABLE_ALL_BOUNDS", "MODEL_ONLY"
        elif sensed.model_energy_upper <= r.min_energy_cost:
            status, reason = "MODEL_INSUFFICIENT_ALL_BOUNDS", "MODEL_ONLY"
        else:
            status, reason = "MODEL_AMBIGUOUS", "OVERLAPPING_ASSUMED_BOUNDS"
        results.append(SensedRouteAffordability(
            r.label, r.destination, status, r.min_energy_cost,
            r.max_energy_cost, reason,
        ))
    return RouteComparison(sensed.session_id, sensed.owner_world_tick, tuple(results))
