"""Read-only P1 owner-tick sensor export for eventual SelfBody consumers.

P1/S/R still separately authenticate original World source, WAIT inactivity,
S50 movement and Action outcomes. This pure check does not do any of those.
"""
from __future__ import annotations

from dataclasses import dataclass

from experiments.fatigue_p1 import (
    FatigueProfile,
    FatigueSensor,
    FatigueState,
)
from experiments.fatigue_p1_boundary import (
    P1BoundaryRejected,
    P1ReconciledTick,
    reconcile,
    sensed_for_self,
)


@dataclass(frozen=True, slots=True)
class P1SelfBodyReadout:
    """Producer-local evidence pointer plus *quantized* sensor value."""

    session_id: str
    profile_sha256: str
    world_tick: int
    activity: str
    world_source_ref: str
    wait_interval_ref: str | None
    sensor_reading: float
    source_scope: str = "P1_PRODUCER_LOCAL_NOT_WORLD_ATTESTED"


def export_p1_sensed_tick(
    profile: FatigueProfile,
    before: FatigueState,
    tick: P1ReconciledTick,
    sensor: FatigueSensor,
) -> P1SelfBodyReadout:
    """Recheck original P1 physics; do not expose true fatigue or capacity.

    Only zero-tolerance SourceBoundTick is exported. A caller-supplied source
    string is NOT independent authentication of a full idle World tick.
    """
    if (
        not isinstance(profile, FatigueProfile)
        or not isinstance(before, FatigueState)
        or not isinstance(tick, P1ReconciledTick)
        or not isinstance(sensor, FatigueSensor)
    ):
        raise P1BoundaryRejected("typed P1 owner state/reconcile/sensor required")
    if tick.transition.before != before:
        raise P1BoundaryRejected("foreign, stale or overwritten P1 before-state")
    if tick.preflight.profile_sha256 != profile.sha256:
        raise P1BoundaryRejected("foreign P1 profile")
    # The product readout must not accept forged before/after state, caps,
    # transition or an overrun credited through unrecorded tolerance.
    checked = reconcile(profile, before, tick.preflight, tick.source)
    if checked != tick:
        raise P1BoundaryRejected("forged P1 reconciled transition")
    reading = sensed_for_self(profile, tick.transition.after, sensor)
    if reading.world_tick != tick.source.world_tick:
        raise P1BoundaryRejected("P1 sensor not from next owner World tick")
    return P1SelfBodyReadout(
        session_id=tick.source.session_id,
        profile_sha256=profile.sha256,
        world_tick=reading.world_tick,
        activity=tick.source.activity,
        world_source_ref=tick.source.world_source_ref,
        wait_interval_ref=tick.source.wait_interval_ref,
        sensor_reading=reading.reading,
    )
