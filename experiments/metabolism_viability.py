"""Experiment-local, label-free energy dynamics for M Lane (#616).

No learning reward, agent objective, Minecraft action authorization, or live adapter.
The true body state remains evaluator-side; only observe_energy is sensor-facing.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, replace
from typing import Literal

Action = Literal["WAIT", "MOVE", "FIGHT"]


@dataclass(frozen=True)
class MetabolismConfig:
    capacity: float = 20.0
    initial_energy: float = 12.0
    basal_cost: float = 0.5
    move_cost: float = 0.25
    fight_cost: float = 1.0
    food_energy: float = 4.0

    def __post_init__(self) -> None:
        values = (
            self.capacity,
            self.initial_energy,
            self.basal_cost,
            self.move_cost,
            self.fight_cost,
            self.food_energy,
        )
        if not all(math.isfinite(v) for v in values):
            raise ValueError("non-finite metabolism parameter")
        if self.capacity <= 0 or not 0 < self.initial_energy <= self.capacity:
            raise ValueError("invalid energy capacity/initial_energy")
        if self.basal_cost <= 0 or self.move_cost < 0 or self.fight_cost < 0:
            raise ValueError("invalid energy expenditure")
        if self.food_energy <= 0:
            raise ValueError("food_energy must be positive")


@dataclass(frozen=True)
class BodyState:
    energy: float
    tick: int = 0
    meals: int = 0
    knockouts: int = 0
    terminal: bool = False


def initial_body(config: MetabolismConfig) -> BodyState:
    return BodyState(energy=config.initial_energy)


@dataclass(frozen=True)
class EnergyTransition:
    after: BodyState
    intake: float
    expenditure: float
    overflow: float
    terminal_now: bool


def metabolism_step(
    state: BodyState,
    *,
    action: Action,
    consumed_food_units: int,
    config: MetabolismConfig,
) -> EnergyTransition:
    """One tick: verified food intake first, then costs, then starvation.

    consumed_food_units is an already-verified World outcome supplied by the
    evaluator, never an agent's intention or unverified action proposal.
    """
    if state.terminal:
        raise ValueError("terminal body cannot advance")
    if not math.isfinite(state.energy) or not 0 < state.energy <= config.capacity:
        raise ValueError("invalid live body energy")
    if action not in ("WAIT", "MOVE", "FIGHT"):
        raise ValueError("unknown action")
    if type(consumed_food_units) is not int or consumed_food_units < 0:
        raise ValueError("food units must be a nonnegative integer")
    intake = consumed_food_units * config.food_energy
    if not math.isfinite(intake):
        raise ValueError("non-finite intake")
    available = state.energy + intake
    if not math.isfinite(available):
        raise ValueError("non-finite available energy")
    overflow = max(0.0, available - config.capacity)
    replenished = min(config.capacity, available)
    extra = {"WAIT": 0.0, "MOVE": config.move_cost, "FIGHT": config.fight_cost}[action]
    expenditure = config.basal_cost + extra
    raw_energy = replenished - expenditure
    terminal = raw_energy <= 0
    after = replace(
        state,
        energy=max(0.0, raw_energy),
        tick=state.tick + 1,
        meals=state.meals + consumed_food_units,
        terminal=terminal,
    )
    return EnergyTransition(after, intake, expenditure, overflow, terminal)


def combat_respawn(state: BodyState) -> BodyState:
    """HP-defeat-only respawn: no energy refill, meal, tick or memory reset."""
    if state.terminal:
        raise ValueError("starved body cannot respawn")
    return replace(state, knockouts=state.knockouts + 1)


@dataclass(frozen=True)
class Interoception:
    gain: float = 1.0
    bias: float = 0.0
    quantum: float = 1.0

    def __post_init__(self) -> None:
        if not all(math.isfinite(v) for v in (self.gain, self.bias, self.quantum)):
            raise ValueError("non-finite sensor parameter")
        if self.gain < 0 or self.quantum <= 0:
            raise ValueError("invalid sensor gain/quantum")


@dataclass(frozen=True)
class EnergyObservation:
    tick: int
    reading: float


def observe_energy(state: BodyState, sensor: Interoception) -> EnergyObservation:
    """Sensor projection, not utility/reward or access to true state.

    Deterministic gain/bias/quantization only; stochastic noise belongs to M1.
    """
    unrounded = sensor.bias + sensor.gain * state.energy
    if not math.isfinite(unrounded):
        raise ValueError("non-finite sensor reading")
    return EnergyObservation(state.tick, round(unrounded / sensor.quantum) * sensor.quantum)
