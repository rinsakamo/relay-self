"""M0.1 Minecraft-granularity *offline* accounting proposal.

World-tick and displacement based; no Action authorization, provenance
attestation, Minecraft launcher, sensor policy, reward or learned goal.
Input food receipts MUST be independently admitted by S/R before real use.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, replace


class M01Rejected(ValueError):
    """Unknown, discontinuous or incompatible physical evidence."""


def _finite_nonnegative(value: float) -> bool:
    return type(value) in (int, float) and math.isfinite(value) and value >= 0


@dataclass(frozen=True)
class M01Profile:
    profile_id: str
    capacity: float
    initial_energy: float
    basal_per_world_tick: float
    movement_per_block: float
    food_energy: tuple[tuple[str, float], ...]
    max_displacement_per_tick: float = 1.0

    def __post_init__(self) -> None:
        if not isinstance(self.profile_id, str) or not self.profile_id.strip():
            raise M01Rejected("named immutable profile required")
        if (
            not _finite_nonnegative(self.capacity) or self.capacity <= 0
            or not _finite_nonnegative(self.initial_energy)
            or not 0 < self.initial_energy <= self.capacity
            or not _finite_nonnegative(self.basal_per_world_tick)
            or self.basal_per_world_tick <= 0
            or not _finite_nonnegative(self.movement_per_block)
            or not _finite_nonnegative(self.max_displacement_per_tick)
            or self.max_displacement_per_tick <= 0
        ):
            raise M01Rejected("invalid M0.1 rate/capacity")
        seen: set[str] = set()
        if not isinstance(self.food_energy, tuple) or not self.food_energy:
            raise M01Rejected("explicit food-specific energy catalog required")
        for entry in self.food_energy:
            if (
                not isinstance(entry, tuple) or len(entry) != 2
                or not isinstance(entry[0], str) or not entry[0]
                or entry[0] in seen or not _finite_nonnegative(entry[1])
            ):
                raise M01Rejected("invalid/duplicate food entry")
            seen.add(entry[0])

    def food_value(self, item: str) -> float:
        for name, value in self.food_energy:
            if name == item:
                return value
        raise M01Rejected("unknown food type")


@dataclass(frozen=True)
class AdmittedFood:
    """Caller-asserted S51-shaped consumption; NOT self-authenticating."""

    session_id: str
    action_id: str
    item: str
    count_before: int
    count_after: int
    food_before: int
    food_after: int

    def validate(self, session_id: str, profile: M01Profile) -> float:
        if (
            self.session_id != session_id
            or not isinstance(self.action_id, str) or not self.action_id
            or type(self.count_before) is not int
            or type(self.count_after) is not int
            or self.count_before - self.count_after != 1
            or self.count_after < 0
            or type(self.food_before) is not int
            or type(self.food_after) is not int
            or not 0 <= self.food_before < self.food_after <= 20
        ):
            raise M01Rejected("consumption requires typed S51-like food+stock delta")
        return profile.food_value(self.item)


@dataclass(frozen=True)
class WorldTickSample:
    session_id: str
    world_tick: int  # monotonic World age, NOT time-of-day or wall clock
    xyz: tuple[float, float, float]
    consumed: tuple[AdmittedFood, ...] = ()

    def validate(self) -> None:
        if (
            not isinstance(self.session_id, str) or not self.session_id
            or type(self.world_tick) is not int or self.world_tick < 0
            or not isinstance(self.xyz, tuple) or len(self.xyz) != 3
            or any(not _finite_nonnegative(abs(x)) for x in self.xyz)
            or not isinstance(self.consumed, tuple)
            or any(not isinstance(c, AdmittedFood) for c in self.consumed)
        ):
            raise M01Rejected("invalid monotonic World tick/3D position/receipt")


@dataclass(frozen=True)
class M01State:
    session_id: str
    profile_id: str
    world_tick: int
    xyz: tuple[float, float, float]
    energy: float
    meals: int = 0
    terminal: bool = False
    credited_actions: frozenset[str] = frozenset()
    total_intake: float = 0.0
    total_basal: float = 0.0
    total_movement: float = 0.0
    total_distance: float = 0.0
    total_overflow: float = 0.0
    total_shortfall: float = 0.0


@dataclass(frozen=True)
class M01Transition:
    after: M01State
    intake: float
    basal: float
    movement: float
    measured_blocks: float
    overflow: float
    shortfall: float
    credited_action_ids: tuple[str, ...]
    terminal_now: bool


def begin(profile: M01Profile, sample: WorldTickSample) -> M01State:
    """Establish a World baseline without pretending the spawn probe is a tick."""
    sample.validate()
    if sample.consumed:
        raise M01Rejected("initial baseline cannot mint food")
    return M01State(sample.session_id, profile.profile_id,
                    sample.world_tick, sample.xyz, profile.initial_energy)


def advance(
    profile: M01Profile, state: M01State, sample: WorldTickSample,
) -> M01Transition:
    """Precisely ONE consecutive World tick, independent of decision count.

    Feed first, capacity clamp, pay tick-basal and measured displacement,
    then irreversible starvation. A sparse/missing World tick fails closed.
    """
    sample.validate()
    if state.terminal:
        raise M01Rejected("terminal body cannot reenter")
    if (
        state.profile_id != profile.profile_id
        or sample.session_id != state.session_id
        or sample.world_tick != state.world_tick + 1
    ):
        raise M01Rejected("foreign session/profile or nonconsecutive World tick")
    blocks = math.dist(state.xyz, sample.xyz)
    if blocks > profile.max_displacement_per_tick:
        raise M01Rejected("teleport/unknown movement: no distance attestation")
    credited = set(state.credited_actions)
    ids: list[str] = []
    intake = 0.0
    for receipt in sample.consumed:
        value = receipt.validate(sample.session_id, profile)
        if receipt.action_id in credited:
            raise M01Rejected("duplicate S51 food action: no second credit")
        credited.add(receipt.action_id)
        ids.append(receipt.action_id)
        intake += value
    if not math.isfinite(intake):
        raise M01Rejected("nonfinite food input")
    replenished = state.energy + intake
    overflow = max(0.0, replenished - profile.capacity)
    payable = min(replenished, profile.capacity)
    basal = profile.basal_per_world_tick
    movement = blocks * profile.movement_per_block
    expenditure = basal + movement
    raw = payable - expenditure
    shortfall = max(0.0, -raw)
    next_state = replace(
        state, world_tick=sample.world_tick, xyz=sample.xyz,
        energy=max(0.0, raw), meals=state.meals + len(ids),
        terminal=raw <= 0, credited_actions=frozenset(credited),
        total_intake=state.total_intake + intake,
        total_basal=state.total_basal + basal,
        total_movement=state.total_movement + movement,
        total_distance=state.total_distance + blocks,
        total_overflow=state.total_overflow + overflow,
        total_shortfall=state.total_shortfall + shortfall,
    )
    return M01Transition(next_state, intake, basal, movement, blocks,
                         overflow, shortfall, tuple(ids), raw <= 0)


def balance_residual(profile: M01Profile, state: M01State) -> float:
    """Should be zero to numerical tolerance, including starvation shortfall."""
    return (
        profile.initial_energy + state.total_intake
        - state.total_basal - state.total_movement
        - state.total_overflow + state.total_shortfall - state.energy
    )


def ecological_ratios(
    profile: M01Profile, item: str, *, nominal_blocks_per_tick: float,
    one_way_blocks: float,
) -> dict[str, float]:
    """Descriptive dimensionless diagnostics, NOT behavioral targets/rewards."""
    if (
        not _finite_nonnegative(nominal_blocks_per_tick)
        or nominal_blocks_per_tick <= 0
        or not _finite_nonnegative(one_way_blocks)
    ):
        raise M01Rejected("positive speed and nonnegative forage radius required")
    meal = profile.food_value(item)
    trip_distance = 2 * one_way_blocks
    trip_ticks = trip_distance / nominal_blocks_per_tick
    travel_basal = trip_ticks * profile.basal_per_world_tick
    travel_movement = trip_distance * profile.movement_per_block
    return {
        "idle_survival_world_ticks": profile.initial_energy / profile.basal_per_world_tick,
        "meal_idle_world_ticks": meal / profile.basal_per_world_tick,
        "travel_basal_to_meal_ratio": travel_basal / meal if meal else math.inf,
        "travel_movement_to_meal_ratio": travel_movement / meal if meal else math.inf,
        "nominal_roundtrip_world_ticks": trip_ticks,
        "nominal_trip_net_energy": meal - travel_basal - travel_movement,
        "active_to_idle_cost_ratio": (
            1 + nominal_blocks_per_tick * profile.movement_per_block
            / profile.basal_per_world_tick
        ),
    }
