"""P1-A: deterministic virtual-Body fatigue, independent of M0/M0.2 energy.

Physics and evaluator-facing receipts only. A cap is NOT an S Action grant;
Self policy, source authentication and World application remain S/R-owned.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass
from typing import Literal

Activity = Literal["WAIT", "REST", "MOVE", "FIGHT"]


class FatigueRejected(ValueError):
    """Invalid profile, clock, provenance shape, or virtual body state."""


def _nonnegative(value: object) -> bool:
    return type(value) in (int, float) and math.isfinite(value) and value >= 0


@dataclass(frozen=True)
class Rate:
    """Positive physical rate: standard × multiplier + additional."""

    standard: float
    multiplier: float = 1.0
    additional: float = 0.0

    def __post_init__(self) -> None:
        if not all(_nonnegative(v) for v in (self.standard, self.multiplier, self.additional)):
            raise FatigueRejected("rate parameters must be finite nonnegative numbers")
        if not math.isfinite(self.value):
            raise FatigueRejected("nonfinite effective fatigue rate")

    @property
    def value(self) -> float:
        return self.standard * self.multiplier + self.additional


@dataclass(frozen=True)
class FatigueProfile:
    """Frozen, independent profile; no energy units or fitness objective."""

    enabled: bool = False  # opt in: legacy M0/M0.2 behavior unchanged
    capacity: float = 1.0  # dimensionless virtual fatigue units
    initial: float = 0.0
    move_per_block: Rate = Rate(0.04)
    fight_per_event: Rate = Rate(0.20)
    rest_per_world_tick: Rate = Rate(0.10)
    impairment_per_fraction: Rate = Rate(0.70)
    minimum_efficiency: float = 0.20
    nominal_move_limit_blocks: float = 1.0
    minimum_fight_efficiency: float = 0.50

    def __post_init__(self) -> None:
        if type(self.enabled) is not bool:
            raise FatigueRejected("enabled must be boolean")
        if not _nonnegative(self.capacity) or self.capacity <= 0:
            raise FatigueRejected("capacity must be positive")
        if not _nonnegative(self.initial) or self.initial > self.capacity:
            raise FatigueRejected("invalid initial fatigue")
        if not all(isinstance(getattr(self, name), Rate) for name in (
            "move_per_block", "fight_per_event", "rest_per_world_tick",
            "impairment_per_fraction",
        )):
            raise FatigueRejected("invalid rate")
        if (not _nonnegative(self.minimum_efficiency)
                or not 0 < self.minimum_efficiency <= 1
                or not _nonnegative(self.minimum_fight_efficiency)
                or not 0 <= self.minimum_fight_efficiency <= 1
                or not _nonnegative(self.nominal_move_limit_blocks)
                or self.nominal_move_limit_blocks <= 0):
            raise FatigueRejected("invalid capability limits")
        if not self.enabled and self.initial != 0:
            raise FatigueRejected("OFF profile must start at zero fatigue")

    @property
    def sha256(self) -> str:
        data = json.dumps(asdict(self), sort_keys=True, separators=(",", ":"),
                          allow_nan=False)
        return hashlib.sha256(data.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class FatigueState:
    session_id: str
    profile_sha256: str
    world_tick: int
    fatigue: float


@dataclass(frozen=True)
class BodyCapability:
    """Physical capacity envelope, not an instruction to REST or S authorization."""

    efficiency: float
    max_move_blocks_per_world_tick: float
    fight_mechanically_possible: bool


def capability(profile: FatigueProfile, state: FatigueState) -> BodyCapability:
    _check_state(profile, state)
    reduction = profile.impairment_per_fraction.value * state.fatigue / profile.capacity
    effective = max(profile.minimum_efficiency, 1.0 - reduction) if profile.enabled else 1.0
    effective = min(1.0, effective)
    return BodyCapability(
        efficiency=effective,
        max_move_blocks_per_world_tick=profile.nominal_move_limit_blocks * effective,
        fight_mechanically_possible=effective >= profile.minimum_fight_efficiency,
    )


def initial_state(profile: FatigueProfile, session_id: str, *, world_tick: int = 0) -> FatigueState:
    if not isinstance(session_id, str) or not session_id.strip():
        raise FatigueRejected("nonempty session id required")
    if type(world_tick) is not int or world_tick < 0:
        raise FatigueRejected("nonnegative World tick required")
    return FatigueState(session_id, profile.sha256, world_tick, profile.initial)


def _check_state(profile: FatigueProfile, state: FatigueState) -> None:
    if not isinstance(state, FatigueState) or state.profile_sha256 != profile.sha256:
        raise FatigueRejected("wrong or changed fatigue profile")
    if (not isinstance(state.session_id, str) or not state.session_id
            or type(state.world_tick) is not int or state.world_tick < 0
            or not _nonnegative(state.fatigue) or state.fatigue > profile.capacity
            or (not profile.enabled and state.fatigue != 0)):
        raise FatigueRejected("invalid body state")


@dataclass(frozen=True)
class FatigueFrame:
    """S/R-supplied outcome for ONE consecutive observed World tick.

    Source authentication is outside this pure module. MOVE is measured actual
    distance (not requested 1-block steering or Paper WALK event count).
    blocked is an outcome label; zero movement never receives a distance bill.
    """

    session_id: str
    world_tick: int
    activity: Activity
    observed_blocks: float = 0.0
    blocked: bool = False
    observed_fight_events: int = 0


@dataclass(frozen=True)
class FatigueTransition:
    before: FatigueState
    after: FatigueState
    frame: FatigueFrame
    accumulated: float
    recovered: float
    capacity_before: BodyCapability
    capacity_after: BodyCapability


def advance(profile: FatigueProfile, state: FatigueState, frame: FatigueFrame) -> FatigueTransition:
    """Evaluator-only deterministic physics; one tick, no energy bookkeeping.

    Accumulation and REST recovery do not occur in the same frame. Clipping is
    exact at [0, capacity]. WAIT performs neither but does not stop M0 basal.
    """
    _check_state(profile, state)
    if (not isinstance(frame, FatigueFrame)
            or frame.session_id != state.session_id
            or type(frame.world_tick) is not int
            or frame.world_tick != state.world_tick + 1):
        raise FatigueRejected("foreign session or nonconsecutive World tick")
    if (frame.activity not in ("WAIT", "REST", "MOVE", "FIGHT")
            or not _nonnegative(frame.observed_blocks)
            or type(frame.blocked) is not bool
            or type(frame.observed_fight_events) is not int
            or not 0 <= frame.observed_fight_events <= 1):
        raise FatigueRejected("invalid activity or World outcome")
    if (frame.activity != "MOVE" and (frame.observed_blocks or frame.blocked)):
        raise FatigueRejected("non-MOVE cannot claim displacement or blockage")
    if frame.activity != "FIGHT" and frame.observed_fight_events:
        raise FatigueRejected("non-FIGHT cannot claim combat events")
    before_capacity = capability(profile, state)
    gain = 0.0
    recovery = 0.0
    if profile.enabled:
        if frame.activity == "MOVE":
            gain = frame.observed_blocks * profile.move_per_block.value
        elif frame.activity == "FIGHT":
            gain = frame.observed_fight_events * profile.fight_per_event.value
        elif frame.activity == "REST":
            recovery = min(state.fatigue, profile.rest_per_world_tick.value)
    if not math.isfinite(gain):
        raise FatigueRejected("nonfinite fatigue debit")
    gained = min(profile.capacity - state.fatigue, gain)
    next_state = FatigueState(
        state.session_id, state.profile_sha256, frame.world_tick,
        max(0.0, min(profile.capacity, state.fatigue + gained - recovery)),
    )
    return FatigueTransition(state, next_state, frame, gained, recovery,
                             before_capacity, capability(profile, next_state))


@dataclass(frozen=True)
class FatigueSensor:
    gain: float = 1.0
    bias: float = 0.0
    quantum: float = 0.1

    def __post_init__(self) -> None:
        if (not _nonnegative(self.gain) or type(self.bias) not in (int, float)
                or not math.isfinite(self.bias) or not _nonnegative(self.quantum)
                or self.quantum <= 0):
            raise FatigueRejected("invalid fatigue sensor")


@dataclass(frozen=True)
class FatigueObservation:
    world_tick: int
    reading: float


def observe(profile: FatigueProfile, state: FatigueState, sensor: FatigueSensor) -> FatigueObservation:
    """Separate, possibly blind interoception; never pass evaluator state to Self."""
    _check_state(profile, state)
    if not isinstance(sensor, FatigueSensor):
        raise FatigueRejected("typed sensor required")
    projection = sensor.bias + sensor.gain * state.fatigue
    if not math.isfinite(projection):
        raise FatigueRejected("nonfinite projection")
    scaled = round(projection / sensor.quantum) * sensor.quantum
    if not math.isfinite(scaled):
        raise FatigueRejected("nonfinite quantization")
    return FatigueObservation(state.world_tick, scaled)