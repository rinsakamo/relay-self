"""W4-PREHOST: loss-accounted original-session preworld probe bridge (DEV).

This is not a runnable W4/NH1 physical scenario. It only uses a session
object already owned by its caller and explicitly cannot create a new reader,
process, Minecraft server, World command writer, Action or S10 issuer.

No preworld unsolicited frame is silently discarded. Such frames are returned
as preworld evidence, NEVER recast as post-placement L0 stimuli.
"""
from __future__ import annotations

import asyncio
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
            if (
                not isinstance(frame, (MineflayerObservation, MineflayerEntityHurt))
                or frame.session_id != self._sid
                or frame.seq <= self._last_seq
            ):
                self._block("unrecognized/replayed/foreign preworld frame")
            self._last_seq = frame.seq
            if self._first_seq is None:
                self._first_seq = frame.seq
            if isinstance(frame, MineflayerObservation) and frame.kind == "probe":
                if frame.request_id != request_id:
                    self._block("wrong original preworld probe correlation")
                self._source = frame
                return frame
            if isinstance(frame, MineflayerObservation):
                if frame.kind != "entities":
                    self._block("unexpected prehost observation kind")
                if any(e.name == "zombie" for e in frame.snapshot.nearby_entities):
                    self._block("preworld hostile entity makes NH1 scenario ambiguous")
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
        )

    def abandon(self, *, owner: object) -> None:
        if owner is not self._owner:
            self._block("foreign owner attempted prehost abort")
        self._state = "BLOCKED"
