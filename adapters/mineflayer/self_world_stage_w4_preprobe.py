"""W4-PREPROBE: single-shot preworld observer port for sole S49 owner.

Proposed DEV interface. There is NO process launch, Minecraft server/World
write, Node stdout read, second stream consumer, Action issuance, or S10 grant.
An *injected original-owner coroutine* is the only way to obtain the frame.
Callers must separately prove that the callback actually belongs to the
sole original reader and that S49 host.run_session has not begun.
"""
from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from adapters.mineflayer.python_protocol import MineflayerObservation
from adapters.mineflayer.self_world_stage_w4_owner_contract import (
    W4OwnerHandoffGate,
)
from adapters.mineflayer.self_world_stage_w4_preflight import (
    W4PreworldBlocked,
)
from adapters.mineflayer.self_world_stage_w4_window import W4PlacementCommands

OwnerReadProbe = Callable[[str], Awaitable[MineflayerObservation]]


@dataclass(frozen=True, slots=True)
class W4PreworldPortReceipt:
    """Typed observation handed to W4-OWNER; no privileged run admission."""

    schema: str
    session_id: str
    request_id: str
    observation_seq: int
    observation_source: str
    slot: int
    candidate_commands: W4PlacementCommands
    owner_attested: bool = False
    reader_exclusivity_attested: bool = False
    host_loop_not_started_attested: bool = False
    stage_world_not_started_attested: bool = False
    external_custody_qualified: bool = False
    physical_run_permitted: bool = False
    s10_permission: bool = False


class W4OwnerPreworldProbePort:
    """One bounded preworld probe through a callback supplied by *one* owner.

    This port never calls session.receive() or constructs a new adapter.
    The caller owns the original native stream. This code can validate the
    handoff but CANNOT prove ownership solely from a token/callback label.
    """

    def __init__(
        self, *, session_id: str, owner: object, native_probe: OwnerReadProbe,
        minimum_seq: int = 0,
    ) -> None:
        if (
            type(session_id) is not str or not session_id
            or type(owner) is not object
            or not callable(native_probe)
            or type(minimum_seq) is not int or minimum_seq < 0
        ):
            raise W4PreworldBlocked("explicit in-process original owner required")
        self._session = session_id
        self._owner = owner
        self._probe = native_probe
        self._minimum_seq = minimum_seq
        self._phase = "IDLE"
        self._caller_task: asyncio.Task | None = None
        self._handoff = W4OwnerHandoffGate(session_id=session_id, native_owner=owner)

    @property
    def phase(self) -> str:
        return self._phase

    @property
    def handoff(self) -> W4OwnerHandoffGate:
        """Readonly source of offline handoff state; never a real-world grant."""
        return self._handoff

    def _fail(self, why: str) -> None:
        self._phase = "BLOCKED"
        # The handoff has the same terminal state after a rejected pre-probe.
        self._handoff.abort(owner=self._owner)
        raise W4PreworldBlocked(why)

    async def capture_pre_world(
        self, *, owner: object, request_id: str, slot: int, token: str,
        host_loop_started: bool = False, stage_world_started: bool = False,
    ) -> W4PreworldPortReceipt:
        """Read one source-bound probe before staging, from the owner task.

        Both *_started inputs are local caller assertions, NOT attestations.
        They may veto admission but never produce a physical grant.
        """
        task = asyncio.current_task()
        if (
            owner is not self._owner or task is None
            or self._phase != "IDLE"
            or host_loop_started is not False
            or stage_world_started is not False
            or type(request_id) is not str or not request_id
            or type(slot) is not int or slot not in (1, 2)
            or type(token) is not str or not token
        ):
            self._fail("original S49 preworld probe owner/admission rejected")
        self._phase = "PROBE_IN_FLIGHT"
        self._caller_task = task
        try:
            reading = await self._probe(request_id)
            if (
                asyncio.current_task() is not self._caller_task
                or type(reading) is not MineflayerObservation
                or reading.session_id != self._session
                or reading.kind != "probe"
                or reading.request_id != request_id
                or reading.seq < self._minimum_seq
            ):
                self._fail("original native preworld correlated probe mismatch")
            commands = self._handoff.before_world(
                reading, owner=self._owner,
                request_id=request_id, slot=slot, token=token,
                origin="s49_original_owner_pre_world",
            )
        except BaseException:
            self._phase = "BLOCKED"
            self._handoff.abort(owner=self._owner)
            raise
        self._phase = "PREWORLD_SOURCE_CAPTURED"
        return W4PreworldPortReceipt(
            "W4_ORIGINAL_OWNER_PREWORLD_PROBE_DEV_V0",
            self._session, request_id, reading.seq,
            reading.provenance.reference, slot, commands,
        )

    def abandon(self, *, owner: object) -> None:
        if owner is not self._owner:
            self._fail("foreign original-owner cancellation")
        self._phase = "BLOCKED"
        self._handoff.abort(owner=self._owner)
