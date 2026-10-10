"""E11 bounded sequential native avatar handoff; no server/bridge launcher.

This transport seam owns no World, Action, or authorization. Its explicitly
injected close and launch callbacks are used only after the E10 policy has
selected MOVE_AWAY and a separate Action4 owner has AUTHORIZED that Action.
A matching username and spawn is a provisional continuity check, never a
physical source attestation. Original raw bytes belong to the caller's
separately captured transport and server evidence.
"""
from __future__ import annotations

import asyncio
import math
from dataclasses import dataclass
from typing import Awaitable, Callable

from adapters.mineflayer.python_protocol import (
    MineflayerAdapterStarted,
    MineflayerConnectionEnd,
    MineflayerObservation,
    MineflayerShutdownAck,
)


class E11HandoffRejected(ValueError):
    """A fresh, sequential native client could not be safely established."""


@dataclass(frozen=True, slots=True)
class SourceShutdown:
    session_id: str
    shutdown_ack: MineflayerShutdownAck
    connection_end: MineflayerConnectionEnd | None
    exit_code: int


@dataclass(frozen=True, slots=True)
class HandoffReceipt:
    source_session_id: str
    action_session_id: str
    source_shutdown_seq: int
    action_spawn_seq: int
    position_delta_m: float
    health_before: float
    health_after: float
    same_declared_avatar: bool
    physically_authenticated: bool = False


class BufferedActionSession:
    """Expose the original unaltered seq1 spawn *once*, then live native source.

    E10's execution reader begins at seq1. Consuming spawn for the handoff
    must not silently drop it, synthesize a replacement or renumber frames.
    """

    def __init__(self, adapter: object, spawn: MineflayerObservation):
        self._adapter = adapter
        self._first = spawn
        self.started = adapter.started

    async def receive(self):
        if self._first is not None:
            frame, self._first = self._first, None
            return frame
        return await self._adapter.receive()

    async def send_observe(self, request_id=None):
        return await self._adapter.send_observe(request_id)

    async def send_set_control(self, action_id, *, control, state):
        return await self._adapter.send_set_control(
            action_id, control=control, state=state,
        )

    async def send_clear_controls(self, action_id):
        return await self._adapter.send_clear_controls(action_id)


class SequentialActionHandoff:
    """Consume one parent connection, then acquire at most one Action4 client.

    The close callback must drain original native shutdown ACK and optional
    connection_end, verify owned process exit0 and preserve full raw stdout.
    The launch callback must create a new source-captured production session;
    it is never called unless the close receipt independently qualifies.
    """

    def __init__(
        self,
        *,
        close_source: Callable[[object], Awaitable[SourceShutdown]],
        launch_action4: Callable[[], Awaitable[object]],
        timeout_s: float = 15.0,
        position_tolerance_m: float = 0.01,
    ) -> None:
        if (type(timeout_s) not in (int, float)
                or not math.isfinite(timeout_s) or not 0 < timeout_s <= 120):
            raise E11HandoffRejected("positive bounded handoff timeout required")
        if (type(position_tolerance_m) not in (int, float)
                or not math.isfinite(position_tolerance_m)
                or not 0 <= position_tolerance_m <= 0.05):
            raise E11HandoffRejected("bounded position tolerance required")
        if not callable(close_source) or not callable(launch_action4):
            raise E11HandoffRejected("two exact operator-owned callbacks required")
        self._close_source = close_source
        self._launch_action4 = launch_action4
        self._timeout_s = timeout_s
        self._tolerance_m = position_tolerance_m
        self._consumed = False
        self.receipt: HandoffReceipt | None = None
        self.shutdown: SourceShutdown | None = None
        self.acquired: BufferedActionSession | None = None

    async def acquire_after_policy(self, source, decision) -> BufferedActionSession:
        # Mark before any awaited I/O. Never retry after partial failure.
        if self._consumed:
            raise E11HandoffRejected("consumed handoff cannot be replayed")
        self._consumed = True
        if (decision.selected != "MOVE_AWAY"
                or decision.receipt is None
                or decision.observation_count != 1
                or len(source.frames) < 1):
            raise E11HandoffRejected("authorized MOVE_AWAY with qualified policy source required")
        last = source.frames[-1]
        if (not isinstance(last, MineflayerObservation)
                or last.kind != "probe"
                or last.request_id != decision.receipt.request_id
                or last.seq != decision.receipt.probe_seq
                or last.session_id != source.session_id
                or source.started.session_id != source.session_id):
            raise E11HandoffRejected("actual native final policy probe is missing")
        try:
            done = await asyncio.wait_for(
                self._close_source(source.adapter), timeout=self._timeout_s,
            )
        except (OSError, TimeoutError, asyncio.TimeoutError) as exc:
            raise E11HandoffRejected("source client did not close cleanly") from exc
        if (not isinstance(done, SourceShutdown)
                or done.session_id != source.session_id
                or type(done.exit_code) is not int or done.exit_code != 0
                or not isinstance(done.shutdown_ack, MineflayerShutdownAck)
                or done.shutdown_ack.session_id != source.session_id
                or done.shutdown_ack.seq <= last.seq):
            raise E11HandoffRejected("missing native ACK / zero-exit source close")
        if done.connection_end is not None and (
                not isinstance(done.connection_end, MineflayerConnectionEnd)
                or done.connection_end.session_id != source.session_id
                or done.connection_end.seq != done.shutdown_ack.seq + 1):
            raise E11HandoffRejected("unqualified native post-ACK close sequence")
        self.shutdown = done
        # The original source has definitely ended before this callback begins.
        try:
            fresh = await asyncio.wait_for(
                self._launch_action4(), timeout=self._timeout_s,
            )
        except (OSError, TimeoutError, asyncio.TimeoutError) as exc:
            raise E11HandoffRejected("new native client failed to launch") from exc
        try:
            started = getattr(fresh, "started", None)
            if (not isinstance(started, MineflayerAdapterStarted)
                    or started.seq != 0
                    or started.session_id == source.session_id
                    or started.config != source.started.config
                    or started.mineflayer_version != source.started.mineflayer_version):
                raise E11HandoffRejected("distinct source / exact config and avatar required")
            spawn = await asyncio.wait_for(
                fresh.receive(), timeout=self._timeout_s,
            )
            if (not isinstance(spawn, MineflayerObservation)
                    or spawn.kind != "spawn"
                    or spawn.seq != 1
                    or spawn.session_id != started.session_id
                    or spawn.request_id is not None):
                raise E11HandoffRejected("new native seq1 original spawn required")
            a, b = last.snapshot.position, spawn.snapshot.position
            delta = math.dist((a.x, a.y, a.z), (b.x, b.y, b.z))
            if not math.isfinite(delta) or delta > self._tolerance_m:
                raise E11HandoffRejected("new avatar spawn differs from last policy position")
            self.receipt = HandoffReceipt(
                source_session_id=source.session_id,
                action_session_id=started.session_id,
                source_shutdown_seq=done.shutdown_ack.seq,
                action_spawn_seq=spawn.seq,
                position_delta_m=delta,
                health_before=last.snapshot.health,
                health_after=spawn.snapshot.health,
                same_declared_avatar=True,
            )
            self.acquired = BufferedActionSession(fresh, spawn)
            return self.acquired
        except BaseException:
            # Never leave an unqualified second owned client running.
            cleanup = getattr(fresh, "terminate", None)
            if callable(cleanup):
                try:
                    await asyncio.wait_for(cleanup(), timeout=self._timeout_s)
                except (OSError, TimeoutError, asyncio.TimeoutError):
                    pass
            raise
