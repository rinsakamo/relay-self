"""W4-PREHOST: loss-accounted original-session preworld probe bridge (DEV).

This is not a runnable W4/NH1 physical scenario. It only uses a session
object already owned by its caller and explicitly cannot create a new reader,
process, Minecraft server, World command writer, Action or S10 issuer.

No preworld unsolicited frame is silently discarded. Such frames are returned
as preworld evidence, NEVER recast as post-placement L0 stimuli.
"""
from __future__ import annotations

import asyncio
from contextvars import ContextVar
from dataclasses import dataclass

from adapters.mineflayer.python_protocol import (
    MineflayerEntityHurt,
    MineflayerObservation,
)
from adapters.mineflayer.self_world_stage_w4_preflight import W4PreworldBlocked
from adapters.mineflayer.self_world_stage_w4_preprobe import (
    W4OwnerPreworldProbePort,
    W4PreworldPortReceipt,
)

_MAX_PREWORLD_FRAMES = 32


@dataclass(frozen=True, slots=True)
class W4PrehostLedger:
    """Complete bounded records consumed BEFORE the World-staging barrier."""

    session_id: str
    probe_reference: str
    buffered_frames: tuple[MineflayerObservation | MineflayerEntityHurt, ...]
    first_seq: int
    last_seq: int
    captured_frames: tuple[MineflayerObservation | MineflayerEntityHurt, ...]
    delivery_scope: str = "PREWORLD_EVIDENCE_ONLY_NOT_L0_STIMULUS"
    original_reader_lease_attested: bool = False
    external_source_qualified: bool = False
    physical_run_permitted: bool = False


class W4PrehostOwnerBridge:
    """One-shot delegated receive under a caller-held original S49 session.

    A running original host loop or staging task is incompatible with this
    interface. The absence of those tasks cannot be independently attested
    from the boolean inputs, so caller-originated metadata NEVER qualifies
    a live source. The bridge never provides session.send_* Action access.
    """

    def __init__(self, *, session, session_id: str, owner: object) -> None:
        if (
            type(owner) is not object
            or type(session_id) is not str or not session_id
            or session is None
            or not callable(getattr(session, "send_observe", None))
            or not callable(getattr(session, "receive", None))
        ):
            raise W4PreworldBlocked("original owner/session receive path required")
        self._session = session
        self._owner = owner
        self._sid = session_id
        self._state = "IDLE"
        self._buffer: list[MineflayerObservation | MineflayerEntityHurt] = []
        self._owner_task: asyncio.Task | None = None
        self._first_seq: int | None = None
        self._last_seq = -1
        self._source: MineflayerObservation | None = None
        self._ledger_delivered = False
        self._audit = []

    @property
    def state(self) -> str:
        return self._state

    def _block(self, reason: str) -> None:
        self._state = "BLOCKED"
        raise W4PreworldBlocked(reason)

    async def _receive_correlated(self, request_id: str) -> MineflayerObservation:
        if self._state != "CAPTURING" or asyncio.current_task() is not self._owner_task:
            self._block("foreign concurrent reader task in prehost session")
        await self._session.send_observe(request_id)
        for _ in range(_MAX_PREWORLD_FRAMES):
            frame = await asyncio.wait_for(self._session.receive(), timeout=2.0)
            self._audit.append(frame)
            if (
                not isinstance(frame, (MineflayerObservation, MineflayerEntityHurt))
                or frame.session_id != self._sid
                or frame.seq <= self._last_seq
                or (self._last_seq >= 0 and frame.seq != self._last_seq + 1)
            ):
                self._block("unrecognized/replayed/foreign preworld frame")
            self._last_seq = frame.seq
            if self._first_seq is None:
                self._first_seq = frame.seq
            if isinstance(frame, MineflayerObservation) and any(
                e.name == "zombie" for e in frame.snapshot.nearby_entities
            ):
                self._block("preworld hostile entity makes NH1 scenario ambiguous")
            if isinstance(frame, MineflayerObservation) and frame.kind == "probe":
                if frame.request_id != request_id:
                    self._block("wrong original preworld probe correlation")
                self._source = frame
                return frame
            if isinstance(frame, MineflayerObservation):
                if frame.kind != "entities":
                    self._block("unexpected prehost observation kind")
            self._buffer.append(frame)
        self._block("original preworld probe frame bound exhausted")

    async def capture(
        self, *, owner: object, request_id: str, slot: int, token: str,
        host_loop_started: bool = False, stage_world_started: bool = False,
    ) -> W4PreworldPortReceipt:
        task = asyncio.current_task()
        if (
            owner is not self._owner or task is None or self._state != "IDLE"
            or host_loop_started is not False
            or stage_world_started is not False
        ):
            self._block("prehost ownership/phase not admitted")
        self._state = "CAPTURING"
        self._owner_task = task
        port = W4OwnerPreworldProbePort(
            session_id=self._sid, owner=self._owner,
            native_probe=self._receive_correlated,
        )
        self._handoff = port.handoff
        try:
            receipt = await port.capture_pre_world(
                owner=owner, request_id=request_id, slot=slot, token=token,
                host_loop_started=host_loop_started,
                stage_world_started=stage_world_started,
            )
        except BaseException:
            self._state = "BLOCKED"
            raise
        self._state = "AWAIT_PREWORLD_LEDGER"
        return receipt

    def take_pre_world_ledger(self, *, owner: object) -> W4PrehostLedger:
        """One-shot transfer of PRE-world frames before host/World may start.

        The original owner must independently seal/store this evidence;
        no zombie-free preworld frame is replayed as a *later* L0 stimulus.
        """
        if (
            owner is not self._owner
            or asyncio.current_task() is not self._owner_task
            or self._state != "AWAIT_PREWORLD_LEDGER"
            or self._ledger_delivered
            or self._source is None
            or self._first_seq is None
        ):
            self._block("preworld frame ledger transfer missing/duplicated")
        self._ledger_delivered = True
        self._state = "HANDED_OFF"
        return W4PrehostLedger(
            session_id=self._sid,
            probe_reference=self._source.provenance.reference,
            buffered_frames=tuple(self._buffer),
            first_seq=self._first_seq, last_seq=self._last_seq,
            captured_frames=tuple(self._audit),
        )

    def abandon(self, *, owner: object) -> None:
        if owner is not self._owner:
            self._block("foreign owner attempted prehost abort")
        self._state = "BLOCKED"


class W4OfflineS49Owner:
    """Runner-independent DEV seam with real decoder and original S49 filter.

    Construction accepts JSONL bytes only. No live process/session/server can
    be injected. The sole process-session reader is guarded across prehost and
    host phases. This establishes local exclusion, not live S49 qualification.
    """

    def __init__(self, lines: tuple[bytes, ...], *, owner: object) -> None:
        from types import SimpleNamespace

        from adapters.mineflayer.process_session import MineflayerProcessSession

        if type(lines) is not tuple or any(type(x) is not bytes for x in lines):
            raise W4PreworldBlocked("offline JSONL fixture required")
        if type(owner) is not object:
            raise W4PreworldBlocked("explicit offline owner required")
        self._owner = owner
        self._reader_scope = ContextVar("w4_offline_reader", default=False)
        self._task = None
        self._busy = False
        self.phase = "NEW"
        self.audit = []
        self.host_deliveries = []
        self.commands = []
        from collections import deque

        pending = deque(lines)
        self.raw_audit: list[bytes] = []

        class FixtureStdout:
            async def readline(inner):
                # Cooperative transport boundary permits real contention tests.
                await asyncio.sleep(0)
                raw = pending.popleft() if pending else b""
                self.raw_audit.append(raw)
                return raw

        stream = FixtureStdout()

        class Sink:
            def write(inner, data):
                # Only probe writes exist in this seam; no Action port.
                self.commands.append(data)

            async def drain(inner):
                return None

        self._session = MineflayerProcessSession(SimpleNamespace(
            stdin=Sink(), stdout=stream, returncode=None,
        ))
        self._bridge = None
        self._native = None

    @property
    def started(self):
        return self._session.started

    def _deny(self, reason):
        self.phase = "BLOCKED"
        raise W4PreworldBlocked(reason)

    def _check(self, owner, phase):
        if (owner is not self._owner or self.phase != phase
                or asyncio.current_task() is not self._task or self._busy):
            self._deny("offline original-owner phase/task/reader conflict")

    async def receive(self):
        if (not self._reader_scope.get() or self._busy
                or self.phase not in {"STARTUP", "PREHOST", "HOST"}):
            self._deny("competing reader or closed reader lease")
        self._busy = True
        try:
            frame = await self._session.receive()
            if self.phase == "BLOCKED":
                self._deny("reader lease revoked while receive was in flight")
            self.audit.append((self.phase, frame))
            return frame
        except BaseException:
            self.phase = "BLOCKED"
            raise
        finally:
            self._busy = False

    async def send_observe(self, request_id):
        if not self._reader_scope.get() or self.phase not in {"PREHOST", "HOST"}:
            self._deny("probe outside admitted reader lease")
        await self._session.send_observe(request_id)

    async def start(self, *, owner):
        from adapters.mineflayer.python_protocol import MineflayerAdapterStarted
        from adapters.mineflayer.s31a_real_server_ci import _await_spawn

        if owner is not self._owner or self.phase != "NEW":
            self._deny("startup owner/reuse rejected")
        self._task = asyncio.current_task()
        self.phase = "STARTUP"
        scope = self._reader_scope.set(True)
        try:
            first = await self.receive()
            if not isinstance(first, MineflayerAdapterStarted):
                self._deny("adapter startup missing")
            self._session._started = first
            # Same spawn waiter as _new_session; all consumed frames audited.
            await _await_spawn(self)
            if any(isinstance(frame, MineflayerObservation) and any(
                e.name == "zombie" for e in frame.snapshot.nearby_entities
            ) for _, frame in self.audit):
                self._deny("preworld startup hostile entity is not admitted")
            self._bridge = W4PrehostOwnerBridge(
                session=self, session_id=first.session_id, owner=owner,
            )
            self.phase = "READY"
        except BaseException:
            self.phase = "BLOCKED"
            raise
        finally:
            self._reader_scope.reset(scope)

    async def preworld(self, *, owner, request_id, slot, token):
        self._check(owner, "READY")
        self.phase = "PREHOST"
        scope = self._reader_scope.set(True)
        try:
            receipt = await self._bridge.capture(
                owner=owner, request_id=request_id, slot=slot, token=token,
            )
            ledger = self._bridge.take_pre_world_ledger(owner=owner)
            self.phase = "LEDGER_TRANSFERRED"
            return receipt, ledger
        except BaseException:
            self.phase = "BLOCKED"
            raise
        finally:
            self._reader_scope.reset(scope)

    def begin_staging(self, *, owner):
        self._check(owner, "LEDGER_TRANSFERRED")
        self.phase = "STAGING"

    def handoff_host(self, *, owner, marker):
        from adapters.mineflayer.s49_normal_session_real_ci import NativeObservationOnly

        self._check(owner, "STAGING")
        try:
            self._bridge._handoff.observe_existing_collector_marker(marker, owner=owner)
        except BaseException:
            self.phase = "BLOCKED"
            raise
        self._native = NativeObservationOnly(self)
        self.phase = "HOST"

    async def host_receive(self, *, owner):
        self._check(owner, "HOST")
        scope = self._reader_scope.set(True)
        try:
            frame = await self._native.receive()
            self.host_deliveries.append(frame)
            return frame
        except BaseException:
            self.phase = "BLOCKED"
            raise
        finally:
            self._reader_scope.reset(scope)

    async def host_probe(self, *, owner, request_id):
        from adapters.mineflayer.s31a_real_server_ci import _correlated_observe

        self._check(owner, "HOST")
        scope = self._reader_scope.set(True)
        try:
            # Original reprobe implementation; interleaved frames remain in audit.
            return await _correlated_observe(self, request_id)
        except BaseException:
            self.phase = "BLOCKED"
            raise
        finally:
            self._reader_scope.reset(scope)

    def close(self, *, owner):
        if owner is not self._owner or self._busy:
            self._deny("cannot close foreign/active reader")
        self.phase = "CLOSED"

    async def run_host(self, host, *, owner, request_id, max_frames=1):
        """Run the unchanged original L0 loop with NO Action authorization."""
        from adapters.mineflayer.normal_action import NormalWorldL0
        from adapters.mineflayer.s31a_real_server_ci import _correlated_observe

        self._check(owner, "HOST")
        if type(host) is not NormalWorldL0:
            self._deny("original S49 L0 required")
        seam = self

        class HostPort:
            started = seam.started

            async def receive(inner):
                frame = await seam._native.receive()
                seam.host_deliveries.append(frame)
                return frame

        async def probe(_frame):
            return await _correlated_observe(self, request_id)

        async def no_action(_step):
            self._deny("offline seam cannot execute Action")

        scope = self._reader_scope.set(True)
        try:
            return await host.run_session(
                HostPort(), probe=probe, grant=lambda *_: None,
                on_action_request=no_action, max_frames=max_frames,
            )
        except BaseException:
            self.phase = "BLOCKED"
            raise
        finally:
            self._reader_scope.reset(scope)


def join_w4_prehost_s16_offline(before, closed, **window_options):
    """Require closure-native target continuity before unchanged W4/S16 readback.

    Stage S can legitimately return HOLD for missing target geometry. Such a
    HOLD cannot qualify a prehost placement/closure identity join.
    """
    from adapters.mineflayer.normal_action import NormalActionClosedReadback
    from adapters.mineflayer.self_world_stage_w4_window import join_w4_window_and_s16_offline

    if type(closed) is not NormalActionClosedReadback:
        raise W4PreworldBlocked("original S16 closure required")
    frames = (closed.original_probe, closed.consequence.before_observation,
              closed.consequence.after_observation)
    targets = [tuple(e.entity_id for e in frame.snapshot.nearby_entities if e.name == "zombie")
               for frame in frames]
    if (len(targets[0]) != 1 or any(ids != targets[0] for ids in targets[1:])
            or any(frame.session_id != before.session_id for frame in frames)):
        raise W4PreworldBlocked("original S16 native target identity is not continuous")
    return join_w4_window_and_s16_offline(before, closed, **window_options)
