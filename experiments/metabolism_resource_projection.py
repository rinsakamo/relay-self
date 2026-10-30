"""M #616: bounded, read-only candidate costs over existing M0.1/P1 physics.

No World reads, ledger writes, food credits, reward, Action policy, or issuer.
This is a counterfactual quote, NEVER a source-verified physical outcome.
M0.2 exhaustion is a separate unit, never converted into M0.1 energy.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal

from experiments.fatigue_p1 import (
    FatigueFrame,
    FatigueProfile,
    FatigueState,
    advance as advance_fatigue,
    capability,
)
from experiments.metabolism_m01_minecraft import M01Profile, M01State
from experiments.metabolism_m02_exhaustion import (
    Profile as M02Profile,
    cost as exhaustion_cost,
    observed_land_motion_cost,
)
from experiments.metabolism_viability import EnergyObservation

Kind = Literal["WAIT", "MOVE"]
Status = Literal["ESTIMATED_FEASIBLE", "ESTIMATED_EXHAUSTION", "UNKNOWN"]
_MAX_PROJECTION_TICKS = 512


def _nonnegative_number(value: object) -> bool:
    return type(value) in (int, float) and math.isfinite(value) and value >= 0


@dataclass(frozen=True)
class Candidate:
    """An externally proposed option; no goal, food or gait is chosen here."""

    label: str
    kind: Kind
    wait_ticks: int | None = None
    distance_blocks: float | None = None
    nominal_blocks_per_tick: float | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.label, str) or not self.label.strip():
            raise ValueError("candidate label required")
        if self.kind == "WAIT":
            if (type(self.wait_ticks) is not int or self.wait_ticks < 1
                    or self.distance_blocks is not None
                    or self.nominal_blocks_per_tick is not None):
                raise ValueError("WAIT requires ticks only")
        elif self.kind == "MOVE":
            if self.wait_ticks is not None:
                raise ValueError("MOVE cannot be WAIT")
            if self.distance_blocks is not None and not _nonnegative_number(self.distance_blocks):
                raise ValueError("invalid proposed displacement")
            if self.nominal_blocks_per_tick is not None and (
                not _nonnegative_number(self.nominal_blocks_per_tick)
                or self.nominal_blocks_per_tick == 0
            ):
                raise ValueError("invalid nominal speed")
        else:
            raise ValueError("unrecognized physical activity")


@dataclass(frozen=True)
class ResourceQuote:
    """Evaluator-private projected viability; never forward true E to SelfBody."""

    label: str
    session_id: str
    owner_world_tick: int
    planned_distance_blocks: float | None
    status: Status
    world_ticks: int | None
    basal_energy: float | None
    movement_energy: float | None
    required_energy: float | None
    projected_energy_after: float | None
    projected_fatigue_after: float | None
    reason: str


@dataclass(frozen=True)
class VisibleResourceQuote:
    """Only cost/uncertainty, no private physical energy or feasibility label."""

    label: str
    world_ticks: int | None
    estimated_energy_cost: float | None
    reason: str


@dataclass(frozen=True)
class SelfBodyResourceCosts:
    session_id: str
    owner_world_tick: int
    observed_energy_reading: float
    quotes: tuple[VisibleResourceQuote, ...]
    source_scope: str = "OFFLINE_ESTIMATE_NOT_PHYSICAL_OR_ACTION_AUTHORITY"


def _validate_body(profile: M01Profile, state: M01State) -> None:
    if (not isinstance(profile, M01Profile) or not isinstance(state, M01State)
            or state.profile_id != profile.profile_id
            or not isinstance(state.session_id, str) or not state.session_id
            or type(state.world_tick) is not int or state.world_tick < 0
            or not _nonnegative_number(state.energy)
            or state.energy <= 0 or state.energy > profile.capacity
            or state.terminal):
        raise ValueError("valid live M0.1 physical state required")


def quote_candidate(
    profile: M01Profile,
    state: M01State,
    candidate: Candidate,
    *,
    fatigue_profile: FatigueProfile | None = None,
    fatigue_state: FatigueState | None = None,
) -> ResourceQuote:
    """Project known movement/WAIT costs with existing P1 advance, without writes.

    Unknown distances/speeds and excessive horizons return UNKNOWN, never an
    invented route. Food at a destination is NOT credited before an EAT outcome.
    """
    _validate_body(profile, state)
    if not isinstance(candidate, Candidate):
        raise ValueError("typed candidate required")
    if (fatigue_profile is None) != (fatigue_state is None):
        raise ValueError("P1 profile/state must be supplied together")
    if fatigue_state is not None and (
        fatigue_state.session_id != state.session_id
        or fatigue_state.world_tick != state.world_tick
    ):
        raise ValueError("foreign or stale P1 state")
    # Validate P1 profile digest and state even for UNKNOWN candidates.
    if fatigue_state is not None:
        capability(fatigue_profile, fatigue_state)

    def unknown(reason: str) -> ResourceQuote:
        return ResourceQuote(candidate.label, state.session_id, state.world_tick,
                             candidate.distance_blocks if candidate.kind == "MOVE" else 0.0,
                             "UNKNOWN", None, None, None, None, None, None, reason)

    if candidate.kind == "MOVE" and (
        candidate.distance_blocks is None or candidate.nominal_blocks_per_tick is None
    ):
        return unknown("UNKNOWN_ROUTE_OR_SPEED")
    if candidate.kind == "WAIT" and candidate.wait_ticks > _MAX_PROJECTION_TICKS:
        return unknown("HORIZON_EXCEEDED")
    if candidate.kind == "MOVE" and candidate.distance_blocks > (
        _MAX_PROJECTION_TICKS * candidate.nominal_blocks_per_tick
    ):
        return unknown("HORIZON_EXCEEDED")

    remaining = candidate.distance_blocks if candidate.kind == "MOVE" else 0.0
    elapsed = 0
    movement = 0.0
    p1 = fatigue_state
    while True:
        if candidate.kind == "WAIT":
            if elapsed >= candidate.wait_ticks:
                break
            step = 0.0
        else:
            if elapsed and remaining <= 1e-9:
                break
            if elapsed >= _MAX_PROJECTION_TICKS:
                return unknown("HORIZON_EXCEEDED")
            if candidate.distance_blocks == 0.0:
                step = 0.0  # blocked MOVE still pays basal; never P1 WAIT recovery
            else:
                max_step = candidate.nominal_blocks_per_tick
                if p1 is not None:
                    max_step = min(max_step, capability(fatigue_profile, p1).max_move_blocks_per_world_tick)
                if max_step <= 0:
                    return unknown("P1_MOBILITY_UNAVAILABLE")
                step = min(remaining, max_step)
                remaining = max(0.0, remaining - step)
            movement += step * profile.movement_per_block
        elapsed += 1
        if p1 is not None:
            p1 = advance_fatigue(
                fatigue_profile, p1,
                FatigueFrame(
                    session_id=state.session_id, world_tick=state.world_tick + elapsed,
                    activity=candidate.kind, observed_blocks=step,
                    blocked=(candidate.kind == "MOVE" and step == 0.0),
                ),
            ).after
    basal = elapsed * profile.basal_per_world_tick
    required = basal + movement
    if not math.isfinite(required):
        return unknown("NONFINITE_ESTIMATE")
    feasible = required < state.energy  # equality is irreversible starvation in M0.1
    return ResourceQuote(
        candidate.label, state.session_id, state.world_tick,
        candidate.distance_blocks if candidate.kind == "MOVE" else 0.0,
        "ESTIMATED_FEASIBLE" if feasible else "ESTIMATED_EXHAUSTION",
        elapsed, basal, movement, required, max(0.0, state.energy - required),
        p1.fatigue if p1 is not None else None,
        "BOUNDED_HYPOTHETICAL_NOT_WORLD_ATTESTED",
    )


def visible_costs(
    session_id: str,
    observed: EnergyObservation,
    quotes: tuple[ResourceQuote, ...],
) -> SelfBodyResourceCosts:
    """Consumer sees source-bound sensor reading, but not evaluator's true E.

    Viability derived using private true energy is intentionally NOT exported.
    The SelfBody owner decides whether/how to interpret a noisy sensor.
    """
    if (not isinstance(session_id, str) or not session_id
            or not isinstance(observed, EnergyObservation)
            or type(observed.tick) is not int or observed.tick < 0
            or not math.isfinite(observed.reading)
            or not isinstance(quotes, tuple)
            or any(not isinstance(q, ResourceQuote)
                   or q.session_id != session_id
                   or q.owner_world_tick != observed.tick for q in quotes)):
        raise ValueError("typed M0 owner observation and quotes required")
    return SelfBodyResourceCosts(
        session_id, observed.tick, observed.reading,
        tuple(VisibleResourceQuote(q.label, q.world_ticks, q.required_energy, q.reason)
              for q in quotes),
    )


def quote_m02_exhaustion(
    profile: M02Profile, quote: ResourceQuote, *,
    land_gait: Literal["WALK", "SPRINT"] | None = None,
) -> float | None:
    """Separate M0.2 exhaustion units; NEVER add to M0.1 energy.

    G4/S owner must explicitly map gait; JOG/DASH are not guessed to be SPRINT.
    No real-world billing happens here. An unknown quote stays unknown.
    """
    if not isinstance(quote, ResourceQuote):
        raise ValueError("typed quote required")
    if quote.status == "UNKNOWN":
        return None
    if type(quote.world_ticks) is not int or quote.world_ticks < 1:
        raise ValueError("quote lacks complete World-time estimate")
    basal = exhaustion_cost(profile, "BASAL", quote.world_ticks)
    distance_blocks = quote.planned_distance_blocks
    if not _nonnegative_number(distance_blocks):
        raise ValueError("validated planned distance required")
    if distance_blocks == 0:
        return basal
    if land_gait not in ("WALK", "SPRINT"):
        return None
    return basal + observed_land_motion_cost(profile, land_gait, distance_blocks)
