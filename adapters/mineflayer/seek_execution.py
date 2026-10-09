"""S50 bounded target-native SEEK step, gated by exact ISSUED Action owner.

This is a physical steering *step*, not pathfinding or guaranteed arrival.
Caller must separately authorize and close the supervised Action; no retries
after an uncertain effect or lost Node source.
"""
from __future__ import annotations

import asyncio
import math
from dataclasses import dataclass
from enum import Enum

from adapters.mineflayer.process_session import MineflayerProcessSession
from adapters.mineflayer.python_protocol import (
    MineflayerEffectResult,
    MineflayerObservation,
)
from relay_self.action import ActionLifecycle, ActionState
from relay_self.action_supervision import ActionSupervisor
from relay_self.seek_waypoint import SeekStatus, SeekStep


class SeekExecutionRejected(ValueError):
    """No live owner/source or uncertain native effect lineage."""


class SeekConsequenceKind(str, Enum):
    PROGRESSED = "PROGRESSED"
    ARRIVED = "ARRIVED"
    BLOCKED = "BLOCKED"


@dataclass(frozen=True, slots=True)
class SeekConsequence:
    action_id: str
    session_id: str
    before_seq: int
    after_seq: int
    progress_m: float
    remaining_m: float
    kind: SeekConsequenceKind
    look_seq: int
    forward_seq: int
    clear_seq: int


async def _effect(session, action_id: str, effect: str):
    for _ in range(100):
        frame = await asyncio.wait_for(session.receive(), timeout=8)
        if isinstance(frame, MineflayerEffectResult):
            if frame.action_id == action_id and frame.effect == effect:
                if frame.result != "applied":
                    raise SeekExecutionRejected(f"{effect} rejected: {frame.error}")
                return frame
        elif not isinstance(frame, MineflayerObservation):
            raise SeekExecutionRejected("native connection ended during SEEK")
    raise SeekExecutionRejected("native effect missing in bounded stream")


async def _probe(session, request_id: str):
    for _ in range(100):
        frame = await asyncio.wait_for(session.receive(), timeout=8)
        if isinstance(frame, MineflayerObservation):
            if frame.kind == "probe":
                if frame.request_id != request_id:
                    raise SeekExecutionRejected("uncorrelated SEEK probe")
                return frame
        else:
            raise SeekExecutionRejected("missing stable World evidence")
    raise SeekExecutionRejected("native probe missing in bounded stream")


async def execute_seek_step(
    session: MineflayerProcessSession,
    supervisor: ActionSupervisor,
    issued: ActionLifecycle,
    step: SeekStep,
) -> SeekConsequence:
    if (
        not isinstance(session, MineflayerProcessSession)
        or not isinstance(supervisor, ActionSupervisor)
        or not isinstance(issued, ActionLifecycle)
        or not isinstance(step, SeekStep)
        or issued.state is not ActionState.ISSUED
        or not issued.is_current_snapshot
        or supervisor.get(issued.action_id) is not issued
        or supervisor.open_actions != (issued,)
        or session.started.session_id != step.session_id
        or session.process_returncode is not None
        or step.status is not SeekStatus.STEER
        or step.yaw is None
        or not math.isfinite(step.yaw)
        or not 0 < step.step_distance_m <= 2
    ):
        raise SeekExecutionRejected("current issued action and steer-only step required")
    # Issued, source-scoped action ID is unique; child-effect IDs are not
    # independent action authorization.
    look_id, clear_id = issued.action_id + "-look", issued.action_id + "-clear"
    await session.send_look(look_id, yaw=step.yaw, pitch=0)
    looked = await _effect(session, look_id, "look")
    await session.send_set_control(issued.action_id, control="forward", state=True)
    forward = await _effect(session, issued.action_id, "set_control")
    await asyncio.sleep(min(0.40, max(0.08, step.step_distance_m * 0.30)))
    await session.send_clear_controls(clear_id)
    clear = await _effect(session, clear_id, "clear_controls")
    request_id = issued.action_id + "-seek-after"
    await session.send_observe(request_id)
    after = await _probe(session, request_id)
    if (
        looked.session_id != step.session_id
        or forward.session_id != step.session_id
        or clear.session_id != step.session_id
        or after.session_id != step.session_id
        or not step.probe_seq < looked.seq < forward.seq < clear.seq < after.seq
    ):
        raise SeekExecutionRejected("real SEEK effect receipt chronology invalid")
    p = after.snapshot.position
    remaining = math.hypot(step.target.x - p.x, step.target.z - p.z)
    progress = step.distance_horizontal_m - remaining
    kind = (
        SeekConsequenceKind.ARRIVED if remaining <= 0.7
        else SeekConsequenceKind.PROGRESSED if progress >= 0.05
        else SeekConsequenceKind.BLOCKED
    )
    return SeekConsequence(
        issued.action_id, step.session_id, step.probe_seq, after.seq,
        progress, remaining, kind, looked.seq, forward.seq, clear.seq,
    )
