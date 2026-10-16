"""P1-B evaluator-only admission seam for existing S/R action and World owners.

This module neither authorizes an S Action nor authenticates a World source.
S/R must separately validate original S action lifecycle, ordered native World
source, full-tick physical WAIT evidence, and actual displacement before constructing
SourceBoundTick. An identifier here is a correlation key, not authentication.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal

from experiments.fatigue_p1 import (
    FatigueFrame,
    FatigueObservation,
    FatigueProfile,
    FatigueRejected,
    FatigueSensor,
    FatigueState,
    FatigueTransition,
    advance,
    capability,
    observe,
)

Activity = Literal["WAIT", "MOVE", "FIGHT"]


class P1BoundaryRejected(FatigueRejected):
    """A proposed activity or correlated source shape cannot be admitted."""


def _positive(x: object) -> bool:
    return type(x) in (int, float) and math.isfinite(x) and x > 0


def _nonnegative(x: object) -> bool:
    return type(x) in (int, float) and math.isfinite(x) and x >= 0


def _key(x: object) -> bool:
    return isinstance(x, str) and bool(x.strip())


@dataclass(frozen=True)
class SActivityRequest:
    """Request only, not S's granted Action lifecycle or physical effect.

    WAIT is a verified physically inactive Body state, not a REST intent.
    The candidate request alone is never proof of WAIT. MOVE/FIGHT refer to
    existing S-proposed Actions with independent authorization and outcome.
    """

    session_id: str
    world_tick_before: int
    activity: Activity
    requested_blocks: float = 0.0
    action_ref: str | None = None


@dataclass(frozen=True)
class BodyPreflight:
    """Evaluator-private cap for an existing action gate; NEVER a grant."""

    request: SActivityRequest
    profile_sha256: str
    admitted_world_tick: int
    allowed_blocks: float
    constrained: bool


@dataclass(frozen=True)
class SourceBoundTick:
    """Correlated descriptor accepted only after external S/R verification.

    S/R must source-authenticate the World source and original full-tick
    inactivity witness on WAIT. Neither field is a cryptographic proof by its mere existence.
    An S50 MOVE action can span multiple World ticks: action_effect_ref is
    the tick-local observed progress, while action_outcome_ref is optional
    and must only be supplied at the genuine S terminal Action OUTCOME.
    `observed_blocks` denotes actual World path distance, not requested step
    or Paper's number of native WALK exhaustion callbacks.
    """

    session_id: str
    world_tick: int
    activity: Activity
    world_source_ref: str
    observed_blocks: float = 0.0
    blocked: bool = False
    observed_fight_events: int = 0
    action_ref: str | None = None
    action_effect_ref: str | None = None
    action_outcome_ref: str | None = None
    wait_interval_ref: str | None = None


@dataclass(frozen=True)
class P1ReconciledTick:
    """Evaluator-private; not an input to L0/L1/L2 or a World proof."""

    preflight: BodyPreflight
    source: SourceBoundTick
    transition: FatigueTransition


def preflight(
    profile: FatigueProfile, state: FatigueState, request: SActivityRequest,
) -> BodyPreflight:
    """Constrain prospective body ability *before* S authorization/issuance.

    A proposed full block at high fatigue may become a shorter candidate;
    the S/S50 owner must apply the returned cap. A cap is NOT a permit or
    reliable proof of physical enforcement in Minecraft.
    """
    cap = capability(profile, state)  # also checks state/profile
    if (not isinstance(request, SActivityRequest)
            or request.session_id != state.session_id
            or type(request.world_tick_before) is not int
            or request.world_tick_before != state.world_tick
            or request.activity not in ("WAIT", "MOVE", "FIGHT")
            or not _nonnegative(request.requested_blocks)):
        raise P1BoundaryRejected("wrong session, World time, activity or requested distance")
    if request.activity == "MOVE":
        if (not _positive(request.requested_blocks)
                or request.requested_blocks > profile.nominal_move_limit_blocks
                or not _key(request.action_ref)
):
            raise P1BoundaryRejected("MOVE needs bounded requested distance and S Action ref")
        allowed = min(request.requested_blocks, cap.max_move_blocks_per_world_tick)
        constrained = allowed < request.requested_blocks
    elif request.activity == "FIGHT":
        if (request.requested_blocks != 0 or not _key(request.action_ref)
):
            raise P1BoundaryRejected("FIGHT requires a proposed S Action, not distance")
        if not cap.fight_mechanically_possible:
            raise P1BoundaryRejected("FIGHT mechanically unavailable at current fatigue")
        allowed, constrained = 0.0, False
    else:
        if request.requested_blocks != 0 or request.action_ref is not None:
            raise P1BoundaryRejected("WAIT cannot smuggle a proposed action")
        allowed, constrained = 0.0, False
    return BodyPreflight(request, profile.sha256, state.world_tick + 1, allowed,
                         constrained)


def reconcile(
    profile: FatigueProfile, state: FatigueState,
    prepared: BodyPreflight, source: SourceBoundTick,
    *, movement_tolerance_blocks: float = 0.0,
) -> P1ReconciledTick:
    """Strict offline correlation, *not* admission of source authenticity.

    A movement overrun fails closed instead of silently clipping physical
    distance or rewriting S50 Action evidence. S/R must preserve that original
    effect and diagnose it outside P1. The optional tolerance is an explicitly
    configured bounded (at most 0.05 block) measurement allowance, OFF by
    default. Re-evaluate a new tick with the same in-flight S Action ref, but
    only S/R may prove lifecycle state/observed movement per tick.
    """
    capability(profile, state)
    if (not isinstance(prepared, BodyPreflight)
            or not isinstance(source, SourceBoundTick)
            or not _nonnegative(movement_tolerance_blocks)
            or movement_tolerance_blocks > 0.05):
        raise P1BoundaryRejected("invalid preflight/source/tolerance")
    proposal = prepared.request
    if (prepared.profile_sha256 != profile.sha256
            or prepared.admitted_world_tick != state.world_tick + 1
            or source.session_id != state.session_id
            or source.world_tick != prepared.admitted_world_tick
            or source.activity != proposal.activity
            or not _key(source.world_source_ref)
            or not _nonnegative(source.observed_blocks)
            or type(source.blocked) is not bool
            or type(source.observed_fight_events) is not int
            or not 0 <= source.observed_fight_events <= 1):
        raise P1BoundaryRejected("uncorrelated source tick or bad World evidence shape")
    # Recompute so a caller-supplied forged/stale cap cannot relax the limit.
    if prepared != preflight(profile, state, proposal):
        raise P1BoundaryRejected("preflight was forged or changed")
    if source.activity in ("MOVE", "FIGHT"):
        if (source.action_ref != proposal.action_ref
                or not _key(source.action_effect_ref)
                or (source.action_outcome_ref is not None
                    and not _key(source.action_outcome_ref))
                or source.wait_interval_ref is not None):
            raise P1BoundaryRejected("S Action and outcome must be source-correlated")
        if source.activity == "MOVE" and (
            source.observed_blocks > prepared.allowed_blocks + movement_tolerance_blocks
            or source.observed_fight_events != 0
        ):
            raise P1BoundaryRejected("MOVE exceeded physical capability or mixed combat")
        if source.activity == "FIGHT" and (source.observed_blocks != 0 or source.blocked):
            raise P1BoundaryRejected("FIGHT cannot smuggle displacement/blockage")
    else:
        if (source.action_ref is not None or source.action_effect_ref is not None
                or source.action_outcome_ref is not None or source.observed_blocks != 0
                or source.observed_fight_events != 0
                or source.blocked):
            raise P1BoundaryRejected("idle tick cannot fabricate an issued action/effect")
        if not _key(source.wait_interval_ref):
            raise P1BoundaryRejected("WAIT requires genuine full-tick inactivity witness")
    frame = FatigueFrame(
        source.session_id, source.world_tick, source.activity,
        source.observed_blocks, source.blocked, source.observed_fight_events,
    )
    return P1ReconciledTick(prepared, source, advance(profile, state, frame))


def sensed_for_self(
    profile: FatigueProfile, state: FatigueState, sensor: FatigueSensor,
) -> FatigueObservation:
    """Only public sensor projection; do not expose capability or true state."""
    return observe(profile, state, sensor)