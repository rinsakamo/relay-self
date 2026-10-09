"""S45 bounded Mineflayer-local SEEK geometry, not a motor command.

This computes one prospective target-local steering proposal from a real native
body position; it cannot authorize or issue motion and cannot claim traversable
terrain. A downstream Action gate remains mandatory.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum

from adapters.mineflayer.python_protocol import (
    MineflayerObservation,
    MineflayerPosition,
    mineflayer_yaw_to_target,
)
from relay_self.provenance import Provenance


class SeekRejected(ValueError):
    """Reject forged, stale, unreachable-by-local-step or ambiguous positions."""


class SeekStatus(str, Enum):
    ARRIVED = "ARRIVED"
    STEER = "STEER"
    NEEDS_ROUTE = "NEEDS_ROUTE"


@dataclass(frozen=True, slots=True)
class SeekWaypoint:
    goal_id: str
    target: MineflayerPosition
    tolerance_m: float = 0.7
    max_step_m: float = 1.0

    def __post_init__(self) -> None:
        if (
            not isinstance(self.goal_id, str) or not self.goal_id
            or not isinstance(self.target, MineflayerPosition)
            or any(
                type(v) not in (int, float) or not math.isfinite(v)
                for v in (self.tolerance_m, self.max_step_m)
            )
            or not 0.1 <= self.tolerance_m <= 4.0
            or not 0.1 <= self.max_step_m <= 2.0
        ):
            raise SeekRejected("bounded waypoint geometry required")


@dataclass(frozen=True, slots=True)
class SeekStep:
    goal_id: str
    session_id: str
    probe_seq: int
    status: SeekStatus
    current: MineflayerPosition
    target: MineflayerPosition
    distance_horizontal_m: float
    yaw: float | None
    step_distance_m: float
    provenance: Provenance


class SeekCursor:
    """A caller-owned per-session source cursor; no persistent route/planner."""

    def __init__(self, session_id: str) -> None:
        if not isinstance(session_id, str) or not session_id:
            raise SeekRejected("session ID required")
        self.session_id = session_id
        self._last_seq = -1

    def plan(self, probe: MineflayerObservation, waypoint: SeekWaypoint) -> SeekStep:
        if (
            not isinstance(probe, MineflayerObservation)
            or probe.kind != "probe" or not probe.request_id
            or probe.session_id != self.session_id
            or probe.seq <= self._last_seq
            or probe.provenance.source != "mineflayer"
            or not isinstance(waypoint, SeekWaypoint)
        ):
            raise SeekRejected("fresh correlated target-native World position required")
        current = probe.snapshot.position
        target = waypoint.target
        horizontal = math.hypot(target.x - current.x, target.z - current.z)
        vertical = abs(target.y - current.y)
        if horizontal <= waypoint.tolerance_m and vertical <= 1:
            status, yaw, distance = SeekStatus.ARRIVED, None, 0.0
        elif vertical > 1:
            # A height gap is not evidence that simply walking is safe.
            status, yaw, distance = SeekStatus.NEEDS_ROUTE, None, 0.0
        else:
            status = SeekStatus.STEER
            yaw = mineflayer_yaw_to_target(current, target)
            distance = min(horizontal - waypoint.tolerance_m, waypoint.max_step_m)
            if not math.isfinite(yaw) or distance <= 0:
                raise SeekRejected("invalid local steering solution")
        self._last_seq = probe.seq
        return SeekStep(
            goal_id=waypoint.goal_id, session_id=self.session_id, probe_seq=probe.seq,
            status=status, current=current, target=target,
            distance_horizontal_m=horizontal, yaw=yaw,
            step_distance_m=distance, provenance=probe.provenance,
        )
