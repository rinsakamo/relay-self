"""DEV-only single-P1 gait dynamics for the compressed Minecraft World.

Alternative per-World-tick transition to fatigue_p1.advance(), not an
additional fatigue gauge or a change to frozen P1/S49 source. Use exactly ONE
transition per externally verified World tick. An applied gait / output must
be established by the World owner; this module never grants or issues Action.
M0's extra DASH energy is a *charge proposal*, not an M0 ledger posting.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, fields
from typing import Literal

from experiments.fatigue_p1 import (
    FatigueProfile,
    FatigueRejected,
    FatigueState,
    capability,
)

Gait = Literal["WAIT", "WALK", "JOG", "RUN", "DASH"]
Direction = Literal["forward", "side", "back"]
WORLD_TICK_SECONDS = 0.05


def _finite_nonnegative(value: object) -> bool:
    return type(value) in (int, float) and math.isfinite(value) and value >= 0


@dataclass(frozen=True, slots=True)
class GaitRatesDev:
    """Illustrative DEV rates, not human physiology or Minecraft calibration.

    Normalized fatigue fraction per second; capacity scaling is automatic.
    Constant-speed net recovery follows dF/dt = L(v) - k(v)*F.
    The full DASH load is derived from the 20-second design anchor.
    """

    walk_speed_m_s: float = 1.3
    jog_speed_m_s: float = 4.32
    run_speed_m_s: float = 5.61
    max_dash_multiplier: float = 1.5
    full_dash_limit_seconds: float = 20.0
    dash_load_curve: float = 1.2
    wait_recovery_per_s: float = 0.12
    walk_recovery_per_s: float = 0.10
    jog_recovery_per_s: float = 0.06
    run_recovery_per_s: float = 0.025
    dash_recovery_per_s: float = 0.02
    walk_load_per_s: float = 0.0
    jog_load_per_s: float = 0.002
    run_load_per_s: float = 0.004
    additional_dash_m0_per_s: float = 0.20

    def __post_init__(self) -> None:
        for name in (field.name for field in fields(self)):
            value = getattr(self, name)
            if not _finite_nonnegative(value):
                raise FatigueRejected(f"invalid gait rate: {name}")
        if (self.walk_speed_m_s <= 0
                or not self.walk_speed_m_s < self.jog_speed_m_s < self.run_speed_m_s
                or self.max_dash_multiplier <= 1
                or self.full_dash_limit_seconds <= WORLD_TICK_SECONDS
                or self.dash_load_curve <= 0
                or min(
                    self.wait_recovery_per_s, self.walk_recovery_per_s,
                    self.jog_recovery_per_s, self.run_recovery_per_s,
                    self.dash_recovery_per_s,
                ) <= 0
                or not self.walk_load_per_s <= self.jog_load_per_s <= self.run_load_per_s
                or self.dash_recovery_per_s >= 1):
            raise FatigueRejected("invalid ordered gait speeds, loads or recovery")

    @property
    def full_dash_load_per_s(self) -> float:
        # Exact continuous-time solution reaches normalized F=1 at 20 seconds.
        k = self.dash_recovery_per_s
        return k / (-math.expm1(-k * self.full_dash_limit_seconds))


@dataclass(frozen=True, slots=True)
class GaitTickDev:
    """Externally established *applied* locomotion for one World tick.

    Not a Self request. Direction and applied output are independently
    checked by the S49/World owner before constructing this DEV input.
    Merely supplying this shape is NOT source authentication.
    """

    session_id: str
    world_tick: int
    gait: Gait
    direction: Direction = "forward"
    applied_dash_power: float = 0.0
    available_extra_m0_energy: float | None = None


@dataclass(frozen=True, slots=True)
class DashBudgetDev:
    """Physical-only preflight envelope, NEVER an Action issuance or grant."""

    permitted_power: float
    admitted_gait: Gait
    fatigue_limited: bool
    energy_limited: bool


@dataclass(frozen=True, slots=True)
class GaitTransitionDev:
    before: FatigueState
    after: FatigueState
    frame: GaitTickDev
    accumulated: float
    recovered: float
    added_m0_charge: float
    nominal_forward_speed_m_s: float
    directional_speed_cap_m_s: float
    exhausted: bool
    source_authenticated: bool = False
    m0_ledger_posted: bool = False
    new_action_issuer: bool = False


def _check(profile: FatigueProfile, state: FatigueState) -> None:
    # The current P1 model is still the ONLY fatigue state.
    capability(profile, state)
    if not profile.enabled:
        raise FatigueRejected("DEV gait model requires explicitly enabled P1")


def dash_budget_dev(
    profile: FatigueProfile,
    state: FatigueState,
    requested_power: float,
    available_extra_m0_energy: float,
    *,
    rates: GaitRatesDev = GaitRatesDev(),
    direction: Direction = "forward",
) -> DashBudgetDev:
    """Limit DASH demand before authorized S49 issuance; never execute it.

    M0 budget here means spendable *extra* energy after normal basal/MOVE cost.
    It is not an unverified body energy sensor.
    """
    _check(profile, state)
    if (not isinstance(rates, GaitRatesDev)
            or direction not in ("forward", "side", "back")
            or not _finite_nonnegative(requested_power)
            or requested_power > 1
            or not _finite_nonnegative(available_extra_m0_energy)):
        raise FatigueRejected("invalid DASH demand or extra M0 budget")
    fatigue_limited = state.fatigue >= profile.capacity - 1e-10
    # A DASH *stance* survives lateral/backward locomotion; no boost is spent.
    # Paper must separately enforce the physical directional speed ceilings.
    if direction != "forward":
        return DashBudgetDev(0.0, "DASH", fatigue_limited, False)
    energy_limit = (
        min(1.0, available_extra_m0_energy /
            (rates.additional_dash_m0_per_s * WORLD_TICK_SECONDS))
        if rates.additional_dash_m0_per_s else 1.0
    )
    permitted = 0.0 if fatigue_limited else min(requested_power, energy_limit)
    return DashBudgetDev(
        permitted_power=permitted,
        admitted_gait="DASH" if permitted > 0 else "RUN",
        fatigue_limited=fatigue_limited,
        energy_limited=energy_limit < requested_power,
    )


def p1_motor_power_limit_dev(
    profile: FatigueProfile, state: FatigueState,
    requested_power: float, available_extra_m0_energy: float,
    *, rates: GaitRatesDev = GaitRatesDev(),
) -> float:
    """Single existing P1 fatigue dimension limits applied forward DASH.

    DEV-only motor fade: full power to F=0.5 capacity, linearly declining
    to zero at capacity. No new fatigue gauge or Action authorization.
    """
    budget = dash_budget_dev(
        profile, state, requested_power, available_extra_m0_energy,
        rates=rates, direction="forward",
    )
    fatigue_bound = min(1.0, max(0.0, 2 * (1 - state.fatigue / profile.capacity)))
    return min(budget.permitted_power, fatigue_bound)


def advance_gait_dev(
    profile: FatigueProfile,
    state: FatigueState,
    frame: GaitTickDev,
    *,
    rates: GaitRatesDev = GaitRatesDev(),
) -> GaitTransitionDev:
    """One verified World tick: load AND recovery affect one existing P1 F.

    A real executor must enforce the DASH motor mode and report the applied
    input/World tick. This calculation changes neither S49 nor Paper speed.
    """
    _check(profile, state)
    if (not isinstance(rates, GaitRatesDev)
            or not isinstance(frame, GaitTickDev)
            or frame.session_id != state.session_id
            or type(frame.world_tick) is not int
            or frame.world_tick != state.world_tick + 1
            or frame.gait not in ("WAIT", "WALK", "JOG", "RUN", "DASH")
            or frame.direction not in ("forward", "side", "back")
            or not _finite_nonnegative(frame.applied_dash_power)
            or frame.applied_dash_power > 1):
        raise FatigueRejected("invalid gait tick / actual motor observation")
    if frame.gait == "DASH":
        if frame.direction != "forward":
            if frame.applied_dash_power != 0 or frame.available_extra_m0_energy is not None:
                raise FatigueRejected("side/back DASH stance cannot spend forward boost")
            # Retain DASH mode, but use ordinary RUN load and a reduced cap.
            # No fake full-power expenditure while merely strafing/retreating.
            load = rates.run_load_per_s
            recovery_rate = rates.run_recovery_per_s
            nominal_speed = rates.jog_speed_m_s
            m0_extra = 0.0
        else:
            if frame.applied_dash_power <= 0 or frame.available_extra_m0_energy is None:
                raise FatigueRejected("forward DASH requires actual output and M0 budget")
            budget = dash_budget_dev(
                profile, state, frame.applied_dash_power,
                frame.available_extra_m0_energy, rates=rates,
            )
            if budget.permitted_power + 1e-10 < frame.applied_dash_power:
                raise FatigueRejected("DASH exceeded physical P1/M0 admission")
            load = (rates.run_load_per_s + (
                rates.full_dash_load_per_s - rates.run_load_per_s
            ) * frame.applied_dash_power ** rates.dash_load_curve)
            recovery_rate = rates.dash_recovery_per_s
            nominal_speed = rates.run_speed_m_s * (
                1 + (rates.max_dash_multiplier - 1) * frame.applied_dash_power
            )
            m0_extra = rates.additional_dash_m0_per_s * (
                frame.applied_dash_power * WORLD_TICK_SECONDS
            )
    else:
        if frame.applied_dash_power != 0 or frame.available_extra_m0_energy is not None:
            raise FatigueRejected("non-DASH cannot claim DASH energy or output")
        load, recovery_rate, nominal_speed = {
            "WAIT": (0.0, rates.wait_recovery_per_s, 0.0),
            "WALK": (rates.walk_load_per_s, rates.walk_recovery_per_s,
                     rates.walk_speed_m_s),
            "JOG": (rates.jog_load_per_s, rates.jog_recovery_per_s,
                    rates.jog_speed_m_s),
            "RUN": (rates.run_load_per_s, rates.run_recovery_per_s,
                    rates.run_speed_m_s),
        }[frame.gait]
        m0_extra = 0.0
    # Analytic solution to one tick of dF/dt = load - k F. This avoids
    # integration-step dependence and counts recovery even during DASH.
    decay = -math.expm1(-recovery_rate * WORLD_TICK_SECONDS)
    recovered = state.fatigue * decay
    added = profile.capacity * load / recovery_rate * decay
    new_fatigue = min(profile.capacity, max(0.0, state.fatigue - recovered + added))
    added = new_fatigue - state.fatigue + recovered  # clipped actual increment
    if not all(math.isfinite(x) for x in (new_fatigue, added, m0_extra)):
        raise FatigueRejected("nonfinite gait transition")
    after = FatigueState(state.session_id, state.profile_sha256,
                         frame.world_tick, new_fatigue)
    return GaitTransitionDev(
        before=state, after=after, frame=frame,
        accumulated=max(0.0, added), recovered=recovered,
        added_m0_charge=m0_extra,
        nominal_forward_speed_m_s=nominal_speed,
        directional_speed_cap_m_s=nominal_speed,
        exhausted=after.fatigue >= profile.capacity - 1e-10,
    )
