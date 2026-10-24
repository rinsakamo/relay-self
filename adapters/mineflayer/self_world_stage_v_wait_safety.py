"""Stage V: preregistered observable near-WAIT consequences, NEVER live permit.

World health, hurt/death events and server-clock exposure must be inspected
together. A no-harm observation is NOT a prospective survival benefit or
permission to WAIT in the dangerous World.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum

from adapters.mineflayer.python_protocol import (
    MineflayerEntityHurt,
    MineflayerNativeClockPacket,
    MineflayerObservation,
)


class StageVWaitRejected(ValueError):
    """Unqualified or internally contradictory native wait evidence."""


class StageVWaitResult(str, Enum):
    HARM_OBSERVED = "harm_observed"
    NO_HARM_WINDOW_CANDIDATE = "no_harm_window_candidate"
    UNDETERMINED = "undetermined"


@dataclass(frozen=True, slots=True)
class StageVWaitRule:
    """Candidate prospectively fixed screening thresholds, not fitness claims."""

    name: str = "stage-v-near-zombie-wait-screen-v0"
    exposure_ticks: int = 20
    near_radius_m: float = 2.5
    stationary_tolerance_m: float = 0.01

    def __post_init__(self) -> None:
        if (
            self.name != "stage-v-near-zombie-wait-screen-v0"
            or type(self.exposure_ticks) is not int or self.exposure_ticks != 20
            or type(self.near_radius_m) is not float or self.near_radius_m != 2.5
            or type(self.stationary_tolerance_m) is not float
            or self.stationary_tolerance_m != 0.01
        ):
            raise StageVWaitRejected("WAIT screening rule must be immutable")


@dataclass(frozen=True, slots=True)
class StageVWaitAssessment:
    status: StageVWaitResult
    reason: str
    session_id: str
    health_before: float
    health_after: float
    world_age_tick_delta: int | None
    hurt_events: int
    near_zombie_id: int | None
    stream_continuity_independently_attested: bool = False
    signed_world_source_attested: bool = False
    safe_to_wait_near_zombie: bool = False
    physical_wait_permitted: bool = False
    survival_gain_proven: bool = False
    science_qualified: bool = False


def _target_id(observation: MineflayerObservation, rule: StageVWaitRule) -> int | None:
    c = observation.snapshot.nearby_entities_coverage
    if c.truncated or c.candidate_count != len(observation.snapshot.nearby_entities):
        raise StageVWaitRejected("complete original Mineflayer registry required")
    p = observation.snapshot.position
    zombies = [e for e in observation.snapshot.nearby_entities if e.name == "zombie"]
    if len(zombies) != 1:
        return None
    z = zombies[0]
    actual = math.dist(
        (p.x, p.y, p.z), (z.position.x, z.position.y, z.position.z),
    )
    if not math.isclose(actual, z.distance, rel_tol=0, abs_tol=1e-6):
        raise StageVWaitRejected("World target geometry spoofed")
    return z.entity_id if actual < rule.near_radius_m else None


def screen_near_wait_observation(
    *, before: MineflayerObservation, after: MineflayerObservation,
    start_clock: MineflayerNativeClockPacket,
    end_clock: MineflayerNativeClockPacket,
    hurt_events: tuple[MineflayerEntityHurt, ...],
    death_events: tuple[MineflayerObservation, ...],
    bot_entity_id: int,
    rule: StageVWaitRule,
) -> StageVWaitAssessment:
    """Evaluate an already-observed window. Never create or grant WAIT.

    The native-clock packet is not an authoritative command-effect duration.
    Stream continuity is not independently attestable from only these inputs;
    even an apparent zero-harm window remains strictly unqualified.
    """
    if (
        not isinstance(rule, StageVWaitRule)
        or not isinstance(before, MineflayerObservation)
        or not isinstance(after, MineflayerObservation)
        or not isinstance(start_clock, MineflayerNativeClockPacket)
        or not isinstance(end_clock, MineflayerNativeClockPacket)
        or not isinstance(hurt_events, tuple)
        or not all(isinstance(h, MineflayerEntityHurt) for h in hurt_events)
        or not isinstance(death_events, tuple)
        or not all(isinstance(d, MineflayerObservation) for d in death_events)
        or type(bot_entity_id) is not int or bot_entity_id < 0
        or before.kind != "probe" or after.kind != "probe"
        or before.session_id != after.session_id
        or before.session_id != start_clock.session_id
        or before.session_id != end_clock.session_id
        or not (start_clock.seq <= before.seq < after.seq <= end_clock.seq)
        or not all(
            e.session_id == before.session_id and before.seq < e.seq <= after.seq
            for e in (*hurt_events, *death_events)
        )
        or not all(d.kind == "death" for d in death_events)
    ):
        raise StageVWaitRejected("same native World exposure window required")
    first_tick, last_tick = int(start_clock.world_age_ticks), int(end_clock.world_age_ticks)
    if last_tick < first_tick:
        raise StageVWaitRejected("World clock decreased across exposure")
    elapsed = last_tick - first_tick
    before_health, after_health = before.snapshot.health, after.snapshot.health
    first_zombie = _target_id(before, rule)
    last_zombie = _target_id(after, rule)
    attacks = sum(1 for e in hurt_events if e.entity_id == bot_entity_id)
    if death_events or before_health > after_health or attacks or after_health == 0:
        return StageVWaitAssessment(
            StageVWaitResult.HARM_OBSERVED,
            "health_loss_hurt_or_death", before.session_id,
            before_health, after_health, elapsed, attacks, first_zombie,
        )
    p, q = before.snapshot.position, after.snapshot.position
    drift = math.dist((p.x, p.y, p.z), (q.x, q.y, q.z))
    if (
        first_zombie is None or last_zombie != first_zombie
        or elapsed < rule.exposure_ticks
        or drift > rule.stationary_tolerance_m
        or after_health != before_health
    ):
        return StageVWaitAssessment(
            StageVWaitResult.UNDETERMINED,
            "insufficient_exposure_source_or_stationarity", before.session_id,
            before_health, after_health, elapsed, attacks, first_zombie,
        )
    return StageVWaitAssessment(
        StageVWaitResult.NO_HARM_WINDOW_CANDIDATE,
        "bounded_native_no_harm_candidate_only", before.session_id,
        before_health, after_health, elapsed, attacks, first_zombie,
    )
