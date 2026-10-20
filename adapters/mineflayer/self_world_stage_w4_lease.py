"""DEV-only, owner-local read lease. Never installed by S49/R/V defaults.

A receive CALL issues a one-use coroutine capability. Its issuer is checked
before any await; wait_for may execute that exact coroutine in a child Task.
Inherited context and arbitrary descendants carry no receiving authority.
This is cooperative Python I/O exclusion, not external identity attestation.
"""
from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass

from adapters.mineflayer.process_session import MineflayerProcessEnded, MineflayerProcessSession
from adapters.mineflayer.python_protocol import (
    MineflayerAdapterErrorMessage,
    MineflayerCommandError,
    MineflayerConnectionEnd,
    MineflayerEffectResult,
    MineflayerObservation,
)
from adapters.mineflayer.self_world_stage_w4_preflight import W4PreworldBlocked
from relay_self.action import ActionState
from relay_self.action_supervision import ActionSupervisor


@dataclass(frozen=True, slots=True)
class ReadOperation:
    session: object
    epoch: int
    phase: str
    binding: str


@dataclass(frozen=True, slots=True)
class ReadAudit:
    event: str
    epoch: int
    phase: str
    binding: str
    issuer: str
    reader: str
    seq: int | None = None
    detail: str = ""
    session_id: str | None = None


class _CompleteLineDecoder:
    def __init__(self, original):
        self.original = original

    def decode(self, text):
        if not text.endswith("\n"):
            raise W4PreworldBlocked("partial JSONL frame")
        return self.original.decode(text)


class W4DevLeasedSession(MineflayerProcessSession):
    """Genuine process-session subtype; reuses original receive and decoder.

    No background Task, task factory, ContextVar or second stream consumer.
    The constructing Task is the sole owner controller. A delegated HOST
    Task can explicitly enter ACTION_READ using the same local owner token.
    Tokens/operations are instance-local capabilities, never live S49 proof.
    """

    _NEXT = {
        "STARTUP": {"PREWORLD"}, "PREWORLD": {"WORLD_WINDOW"},
        "WORLD_WINDOW": {"HOST"}, "HOST": {"ACTION_READ", "QUIESCE"},
        "ACTION_READ": {"HOST"}, "QUIESCE": {"SHUTDOWN"},
        "SHUTDOWN": {"CLOSED"},
    }

    def __init__(self, process, *, raw_capture_root=None):
        super().__init__(process, raw_capture_root=raw_capture_root)
        self._decoder = _CompleteLineDecoder(self._decoder)
        self._controller = asyncio.current_task()
        if self._controller is None:
            raise W4PreworldBlocked("construct inside owner Task")
        self._actor = self._controller
        self._owner = object()
        self._identity = object()
        self._operation = ReadOperation(self._identity, 1, "STARTUP", "startup")
        self._pending = None
        self._active = False
        self._delegated = 0
        self._handoff_pending = None
        self._blocked = False
        self._probe = None
        self._seen_requests = set()
        self._bridge = None
        self._ledger = None
        self._marker = False
        self._spawn_seen = False
        self._shutdown_completed = False
        self._supervisor = None
        self._audit: list[ReadAudit] = []
        self._tasks = {}
        self._sid = None
        self._record("OPEN")

    @property
    def phase(self):
        return "BLOCKED" if self._blocked else self._operation.phase

    @property
    def audit(self):
        return tuple(self._audit)

    def _record(self, event, *, issuer=None, seq=None, detail=""):
        op = self._operation
        task = asyncio.current_task()
        def task_ref(value):
            if value not in self._tasks:
                self._tasks[value] = str(len(self._tasks) + 1)
            return self._tasks[value]
        self._audit.append(ReadAudit(event, op.epoch, op.phase, op.binding,
                                     task_ref(issuer or task), task_ref(task), seq, detail,
                                     self._sid))

    def _deny(self, reason):
        self._blocked = True
        self._record("DENY", detail=reason)
        raise W4PreworldBlocked(reason)

    def owner_token(self):
        if asyncio.current_task() is not self._controller or self._blocked:
            self._deny("owner token unavailable to foreign Task")
        return self._owner

    def _check(self, owner):
        if (self._blocked or self._handoff_pending is not None
                or self.phase == "CLOSED" or owner is not self._owner
                or asyncio.current_task() is not self._actor):
            self._deny("foreign/replayed owner or revoked operation")

    def advance(self, *, owner, phase, binding, supervisor=None):
        self._check(owner)
        if (self._pending is not None or self._active
                or phase not in self._NEXT.get(self.phase, set())
                or (phase == "PREWORLD" and not self._spawn_seen)
                or (phase == "CLOSED" and not self._shutdown_completed)
                or (phase == "WORLD_WINDOW" and self._ledger is None)
                or (self.phase == "WORLD_WINDOW" and phase == "HOST" and not self._marker)
                or not isinstance(binding, str) or not binding
                or (self._delegated and phase in {"QUIESCE", "SHUTDOWN", "CLOSED"})
                or (supervisor is not None and (
                    phase != "ACTION_READ" or not isinstance(supervisor, ActionSupervisor)))):
            self._deny("illegal phase/unfinished receive/delegation")
        self._record("REVOKE")
        self._operation = ReadOperation(self._identity, self._operation.epoch + 1, phase, binding)
        self._probe = None
        self._supervisor = supervisor
        self._record("OPEN")
        return self._operation

    def bind_probe(self, *, owner, request_id):
        self._check(owner)
        if (self._pending is not None or self.phase not in {"PREWORLD", "HOST"}
                or not isinstance(request_id, str) or not request_id or self._probe is not None
                or request_id in self._seen_requests):
            self._deny("probe requires idle current operation and fresh request")
        self._probe = request_id
        self._seen_requests.add(request_id)
        self._record("PROBE_BIND", detail=request_id)

    async def capture_preworld(self, *, owner, request_id, slot, token):
        from adapters.mineflayer.self_world_stage_w4_prehost import W4PrehostOwnerBridge

        self._check(owner)
        if self.phase != "PREWORLD" or self._bridge is not None:
            self._deny("preworld capture out of order/replayed")
        self.bind_probe(owner=owner, request_id=request_id)
        self._bridge = W4PrehostOwnerBridge(
            session=self, session_id=self.started.session_id, owner=owner,
        )
        try:
            return await self._bridge.capture(
                owner=owner, request_id=request_id, slot=slot, token=token,
            )
        except BaseException:
            self._blocked = True
            self._record("ABORT", detail="preworld capture")
            raise

    def take_preworld_ledger(self, *, owner):
        self._check(owner)
        if self.phase != "PREWORLD" or self._bridge is None or self._ledger is not None:
            self._deny("preworld ledger missing/replayed")
        try:
            self._ledger = self._bridge.take_pre_world_ledger(owner=owner)
        except BaseException:
            self._blocked = True
            raise
        self._record("LEDGER_TRANSFER")
        return self._ledger

    def world_marker(self, *, owner, marker):
        self._check(owner)
        if self.phase != "WORLD_WINDOW" or self._marker or self._bridge is None:
            self._deny("world marker out of order")
        try:
            self._bridge._handoff.observe_existing_collector_marker(marker, owner=owner)
        except BaseException:
            self._blocked = True
            raise
        self._marker = True
        self._record("WORLD_HANDOFF")

    def delegate(self, *, owner, operation, invoke):
        """One explicit HOST coroutine, passed directly to original wait_for.

        invoke is a factory so rejected delegation creates no orphan coroutine.
        A foreign wrapper Task awaiting this capability is rejected before IO.
        """
        self._check(owner)
        if (operation is not self._operation or self.phase not in {"HOST", "SHUTDOWN"}
                or self._pending is not None):
            self._deny("stale/foreign/reentrant delegation")
        origin = asyncio.current_task()
        ticket = object()
        self._handoff_pending = ticket
        self._delegated += 1
        self._record("DELEGATE")

        async def delegated():
            task = asyncio.current_task()
            if (self._blocked or operation is not self._operation
                    or self._handoff_pending is not ticket
                    or (task is not origin and task.get_coro() is not capability)):
                self._deny("unauthorized delegation target")
            self._handoff_pending = None
            self._actor = task
            try:
                result = await invoke()
                if self._blocked or self._pending is not None:
                    self._deny("delegated operation incomplete/blocked")
                return result
            except BaseException:
                self._blocked = True
                self._record("ABORT")
                raise
            finally:
                self._actor = origin
                self._delegated -= 1
                # No child authority survives the host completion.
                self._record("DELEGATE_REVOKE")

        capability = delegated()
        return capability

    def receive(self):
        """Issue only from the current actor; reserve before scheduling a read."""
        issuer = asyncio.current_task()
        if (self._blocked or self._handoff_pending is not None or issuer is not self._actor
                or self.phase not in {"STARTUP", "PREWORLD", "HOST", "ACTION_READ", "SHUTDOWN"}
                or self._pending is not None or self._active
                or (self.process_returncode is not None and self.phase != "SHUTDOWN")):
            self._deny("unauthorized or competing receive")
        op = self._operation
        ticket = object()
        self._pending = ticket
        self._record("ISSUE", issuer=issuer)

        async def read():
            task = asyncio.current_task()
            if (self._blocked or op is not self._operation or self._pending is not ticket
                    or (task is not issuer and task.get_coro() is not capability)):
                self._deny("stale epoch or unauthorized read target")
            if task.cancelling():
                self._deny("cancelled reader cannot resume")
            self._active = True
            self._record("READ", issuer=issuer)
            try:
                frame = await super(W4DevLeasedSession, self).receive()
                if self._sid is None:
                    self._sid = frame.session_id
                elif frame.session_id != self._sid:
                    self._deny("session ID mismatch")
                self._record("DECODED", issuer=issuer, seq=frame.seq)
                if isinstance(frame, MineflayerObservation) and frame.kind == "spawn":
                    self._spawn_seen = True
                if self._blocked or op is not self._operation or task.cancelling():
                    self._deny("revoked/cancelled in-flight read")
                if isinstance(frame, (MineflayerAdapterErrorMessage, MineflayerCommandError)) or (
                    isinstance(frame, MineflayerConnectionEnd) and self.phase != "SHUTDOWN"
                ):
                    self._deny("terminal native frame")
                if isinstance(frame, MineflayerEffectResult):
                    expected = self._operation.binding
                    if self.phase != "ACTION_READ" or frame.action_id not in {
                        expected, expected + "-s15-clear",
                    }:
                        self._deny("foreign action readback")
                if isinstance(frame, MineflayerObservation) and frame.kind == "probe":
                    if self.phase != "ACTION_READ" and (
                        self._probe is None or frame.request_id != self._probe
                    ):
                        self._deny("stale/foreign probe request")
                    if self.phase == "ACTION_READ" and frame.request_id is not None:
                        self._deny("foreign S16 legacy probe")
                    self._probe = None
                self._record("DELIVER", issuer=issuer, seq=frame.seq)
                return frame
            except MineflayerProcessEnded:
                if self.phase == "SHUTDOWN" and self.process_returncode in {None, 0}:
                    self._record("EOF")
                else:
                    self._blocked = True
                    self._record("ABORT", detail="unexpected EOF/exit")
                raise
            except BaseException:
                self._blocked = True
                self._record("ABORT")
                raise
            finally:
                self._active = False
                self._pending = None
                self._record("READ_REVOKE", issuer=issuer)

        capability = read()
        return capability

    async def _send(self, line):
        self._check(self._owner)
        payload = json.loads(line)
        command = payload.get("effect") if payload.get("type") == "effect" else payload.get("type")
        if command == "observe":
            if self.phase not in {"PREWORLD", "HOST", "ACTION_READ"} or (
                (self.phase != "ACTION_READ" and payload.get("request_id") != self._probe)
                or (self.phase == "ACTION_READ" and payload.get("request_id") is not None)
            ):
                self._deny("unbound probe send")
        elif command == "shutdown":
            if self.phase != "SHUTDOWN":
                self._deny("shutdown outside quiesced operation")
        elif command in {"set_control", "clear_controls"}:
            if self.phase != "ACTION_READ" or self._supervisor is None:
                self._deny("no original issued Action authority")
            try:
                issued = self._supervisor.get(self._operation.binding)
            except ValueError:
                self._deny("original supervisor has no issued action")
            expected = issued.action_id + ("-s15-clear" if command == "clear_controls" else "")
            if (issued.state is not ActionState.ISSUED or not issued.is_current_snapshot
                    or payload.get("action_id") != expected
                    or (command == "set_control" and (
                        payload.get("control") != "back" or payload.get("state") is not True))):
                self._deny("command not bound to current original issued Action")
        else:
            self._deny("lease grants no World command authority")
        try:
            await super()._send(line)
        except BaseException:
            self._blocked = True
            self._record("ABORT", detail="send failure")
            raise

    async def terminate(self):
        self._blocked = True
        self._record("ABORT", detail="process termination")
        return await super().terminate()

    async def shutdown(self, *, timeout_s=5.0):
        self._check(self._owner)
        if self.phase != "SHUTDOWN" or self._pending is not None or self._delegated:
            self._deny("shutdown before quiescence")
        try:
            if self._raw_capture is None:
                rc = await super().shutdown(timeout_s=timeout_s)
            else:
                # DEV-only explicit drain delegation. Base capture shutdown's
                # private until_eof coroutine has no delegation seam.
                from adapters.mineflayer.python_protocol import encode_shutdown

                if self.process_returncode is None:
                    await self._send(encode_shutdown())

                async def until_eof():
                    while True:
                        try:
                            await self.receive()
                        except MineflayerProcessEnded:
                            return

                await asyncio.wait_for(self.delegate(
                    owner=self._owner, operation=self._operation, invoke=until_eof,
                ), timeout=timeout_s)
                rc = await asyncio.wait_for(self._process.wait(), timeout=timeout_s)
                self._seal_raw_capture(exit_code=rc, reason="clean_shutdown")
            if rc != 0:
                self._deny("abnormal Node exit")
            self._shutdown_completed = True
            self.advance(owner=self._owner, phase="CLOSED", binding="closed")
            return rc
        except BaseException:
            self._blocked = True
            self._record("ABORT", detail="shutdown")
            await self.terminate()
            raise


class W4DevNativeObservationPort:
    """Explicit child delegation around the UNMODIFIED S49 frame filter.

    NormalWorldL0 wraps this receive in wait_for. Only this exact filter
    coroutine is delegated; the actual S16 session remains the true subtype.
    """

    def __init__(self, session: W4DevLeasedSession, *, owner: object):
        from adapters.mineflayer.s49_normal_session_real_ci import NativeObservationOnly

        self.session = session
        self.owner = owner
        self.original = NativeObservationOnly(session)
        self.started = self.original.started

    def receive(self):
        return self.session.delegate(
            owner=self.owner, operation=self.session._operation,
            invoke=self.original.receive,
        )
