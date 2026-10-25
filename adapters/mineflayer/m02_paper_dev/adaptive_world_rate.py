"""#150 T0: offline adaptive Paper rate proposal, NOT a tick-rate actuator.

This module neither authenticates Paper telemetry nor controls Minecraft.
The caller must obtain native tick and L0 evidence via the existing owner;
synthetic test fixtures never constitute physical or R qualification.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum


class RateAction(str, Enum):
    HOLD = "HOLD"
    RAISE = "RAISE"
    LOWER = "LOWER"
    FALLBACK = "FALLBACK"


@dataclass(frozen=True, slots=True)
class RatePolicy:
    min_tps: int = 2
    normal_tps: int = 20
    experimental_cap_tps: int = 400
    raise_after_windows: int = 3
    min_effective_ratio: float = 0.90

    def __post_init__(self) -> None:
        if any(type(x) is not int for x in (
            self.min_tps, self.normal_tps, self.experimental_cap_tps,
            self.raise_after_windows,
        )):
            raise ValueError("rate limits and windows must be integers")
        if not (1 <= self.min_tps <= self.normal_tps <= self.experimental_cap_tps):
            raise ValueError("invalid bounded TPS range")
        if self.raise_after_windows < 2 or self.raise_after_windows > 128:
            raise ValueError("invalid stable-window threshold")
        if not (math.isfinite(self.min_effective_ratio)
                and 0.5 < self.min_effective_ratio < 1.0):
            raise ValueError("invalid effective-rate threshold")


@dataclass(frozen=True, slots=True)
class RateState:
    requested_tps: int = 20
    good_windows: int = 0
    last_server_tick: int | None = None
    world_id: str | None = None
    session_id: str | None = None


@dataclass(frozen=True, slots=True)
class TickWindow:
    """One consecutive native interval, first..last inclusive.

    wall_elapsed_ns measures start-of-first to end-of-last interval.
    Each actual Paper tick and its L0 check must be separately recorded;
    merely providing a matching count is insufficient.
    """

    world_id: str
    session_id: str
    first_server_tick: int
    last_server_tick: int
    paper_ticks: tuple[int, ...]
    l0_checked_ticks: tuple[int, ...]
    wall_elapsed_ns: int
    action_active: bool = False
    tick_motor_verified: bool = False
    action_rate_authorized: bool = False
    danger: bool = False
    missed_control_deadline: bool = False
    cognition_pending: bool = False


@dataclass(frozen=True, slots=True)
class RateProposal:
    action: RateAction
    state: RateState
    reason: str
    effective_tps: float | None
    stop_required: bool = False


def simulated_seconds(world_tick_delta: int) -> float:
    """Reference World duration; independent of requested/actual wall TPS."""
    if type(world_tick_delta) is not int or world_tick_delta < 0:
        raise ValueError("world_tick_delta must be a nonnegative integer")
    return world_tick_delta / 20.0


def _valid_window(window: TickWindow, state: RateState) -> bool:
    if not isinstance(window, TickWindow):
        return False
    if not all(isinstance(x, str) and x.strip() for x in
               (window.world_id, window.session_id)):
        return False
    if any(type(x) is not bool for x in (
        window.action_active, window.tick_motor_verified,
        window.action_rate_authorized, window.danger,
        window.missed_control_deadline, window.cognition_pending,
    )):
        return False
    if (type(window.first_server_tick) is not int
        or type(window.last_server_tick) is not int
        or not 0 <= window.first_server_tick <= window.last_server_tick
        or window.last_server_tick - window.first_server_tick >= 128
        or type(window.wall_elapsed_ns) is not int
        or window.wall_elapsed_ns <= 0):
        return False
    expected = tuple(range(window.first_server_tick, window.last_server_tick + 1))
    if window.paper_ticks != expected or window.l0_checked_ticks != expected:
        return False
    if state.last_server_tick is not None:
        if window.first_server_tick != state.last_server_tick + 1:
            return False
        if window.world_id != state.world_id or window.session_id != state.session_id:
            return False
    return True


def propose_world_rate(
    state: RateState,
    window: TickWindow,
    *,
    policy: RatePolicy = RatePolicy(),
) -> RateProposal:
    """Propose only; does not set TPS, issue STOP, or grant action authority.

    Safety overrides throughput. No time-skip or unobserved L0 tick is
    counted as success. This offline rule depends on upstream genuine source
    observation and cannot itself attest native Paper provenance.
    """
    if (not isinstance(state, RateState)
        or type(state.requested_tps) is not int
        or not policy.min_tps <= state.requested_tps <= policy.experimental_cap_tps
        or type(state.good_windows) is not int or state.good_windows < 0
        or not _valid_window(window, state)):
        return RateProposal(
            RateAction.FALLBACK, RateState(policy.normal_tps),
            "INVALID_OR_INCOMPLETE_TICK_OR_L0_LINEAGE", None, True,
        )

    effective = len(window.paper_ticks) * 1_000_000_000 / window.wall_elapsed_ns
    next_cursor = dict(
        last_server_tick=window.last_server_tick,
        world_id=window.world_id,
        session_id=window.session_id,
    )

    def proposal(action: RateAction, requested: int, good: int,
                 reason: str, *, stop: bool = False) -> RateProposal:
        return RateProposal(action, RateState(requested, good, **next_cursor),
                            reason, effective, stop)

    if window.danger or window.missed_control_deadline:
        return proposal(RateAction.FALLBACK, policy.normal_tps, 0,
                        "DANGER_OR_CONTROL_DEADLINE", stop=True)

    # Minecraft player physics/Mineflayer input rate cannot be assumed to
    # accelerate with server TPS. No arbitrary rate during live physical
    # actions unless an independently tested motor + owner approval exists.
    if window.action_active and not (
        window.tick_motor_verified and window.action_rate_authorized
    ):
        if state.requested_tps != policy.normal_tps:
            return proposal(RateAction.FALLBACK, policy.normal_tps, 0,
                            "UNQUALIFIED_ACTIVE_MOTOR", stop=True)
        if effective < policy.normal_tps * policy.min_effective_ratio:
            return proposal(RateAction.FALLBACK, policy.normal_tps, 0,
                            "ACTIVE_MOTOR_CANNOT_KEEP_UP", stop=True)
        return proposal(RateAction.HOLD, policy.normal_tps, 0,
                        "ACTIVE_MOTOR_NORMAL_TPS_ONLY")

    if effective < state.requested_tps * policy.min_effective_ratio:
        reduced = max(policy.min_tps, state.requested_tps // 2)
        return proposal(RateAction.LOWER if reduced < state.requested_tps else RateAction.HOLD,
                        reduced, 0, "ACTUAL_TPS_BELOW_REQUEST")

    if window.cognition_pending:
        slower = max(policy.min_tps, state.requested_tps // 2)
        return proposal(RateAction.LOWER if slower < state.requested_tps else RateAction.HOLD,
                        slower, 0, "BOUNDED_COGNITION_NEEDS_WALL_TIME")

    if state.good_windows + 1 < policy.raise_after_windows:
        return proposal(RateAction.HOLD, state.requested_tps,
                        state.good_windows + 1, "STABILITY_WINDOW")
    higher = min(policy.experimental_cap_tps,
                 max(state.requested_tps + 1, (state.requested_tps * 5 + 3) // 4))
    return proposal(RateAction.RAISE if higher > state.requested_tps else RateAction.HOLD,
                    higher, 0, "STABLE_RATE_PROBE" if higher > state.requested_tps else "AT_CAP")
