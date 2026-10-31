"""S28: explicit serialized Mineflayer observe/receive seam after an Action outcome.

No wire request ID exists in the frozen adapter protocol. A caller-exclusive
session cursor bounds one receive roundtrip; seq and session checks are
structural and do not prove physical origin or request-response causality.
"""
from __future__ import annotations

import asyncio
import math
from dataclasses import dataclass
from typing import Protocol

from adapters.mineflayer.execution import WorldConsequence, WorldConsequenceStatus
from adapters.mineflayer.python_protocol import (
    MineflayerAdapterStarted,
    MineflayerMessage,
    MineflayerObservation,
)
from relay_self.action import ActionLifecycle, ActionState
from relay_self.action_supervision import ActionSupervisor
from relay_self.provenance import Provenance
from relay_self.source_native_world import (
    SourceNativeThreatReceipt,
    project_source_native_threat,
)


class InvalidExplicitProbe(ValueError):
    """Explicit probe session, transport stream or caller authority invalid."""


class ExplicitProbeSession(Protocol):
    @property
    def started(self) -> MineflayerAdapterStarted: ...

    async def send_observe(self) -> None: ...

    async def receive(self) -> MineflayerMessage: ...


@dataclass(frozen=True, slots=True)
class ExplicitProbeAuthority:
    """Caller grant for one post-outcome observation, not Action issuance."""

    authority_id: str
    session_id: str
    parent_action_id: str
    target_entity_id: int
    target_name: str
    granted: bool
    provenance: Provenance

    def __post_init__(self) -> None:
        for key in ("authority_id", "session_id", "parent_action_id"):
            value = getattr(self, key)
            if not isinstance(value, str) or not value or value.strip() != value:
                raise InvalidExplicitProbe(f"{key} invalid")
        if not isinstance(self.target_entity_id, int) or isinstance(self.target_entity_id, bool):
            raise InvalidExplicitProbe("target_entity_id invalid")
        if self.target_entity_id < 0 or self.target_name != "zombie":
            raise InvalidExplicitProbe("target must be exact zombie registry entity")
        if type(self.granted) is not bool or not isinstance(self.provenance, Provenance):
            raise InvalidExplicitProbe("grant/provenance invalid")


@dataclass(slots=True)
class ExclusiveProbeCursor:
    """Caller-owned one-shot consumed token, not persistent/global replay storage."""

    session_id: str
    next_seq: int
    consumed: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.session_id, str) or not self.session_id:
            raise InvalidExplicitProbe("cursor session is missing")
        if not isinstance(self.next_seq, int) or isinstance(self.next_seq, bool) or self.next_seq < 1:
            raise InvalidExplicitProbe("cursor next_seq must be positive")
        if type(self.consumed) is not bool:
            raise InvalidExplicitProbe("cursor consumed must be bool")


@dataclass(frozen=True, slots=True)
class ExplicitProbeRoundtrip:
    authority_id: str
    request_cursor_seq: int
    received_count: int
    probe_seq: int
    inspected_at_ns: int
    source_receipt: SourceNativeThreatReceipt


async def request_explicit_post_action_probe(
    adapter: ExplicitProbeSession,
    cursor: ExclusiveProbeCursor,
    authority: ExplicitProbeAuthority,
    supervisor: ActionSupervisor,
    action: ActionLifecycle,
    consequence: WorldConsequence,
    *,
    observed_at_ns: int,
    inspected_at_ns: int,
    max_age_ns: int,
    timeout_s: float = 0.25,
    max_frames: int = 4,
) -> ExplicitProbeRoundtrip:
    """Send one observe and read a bounded contiguous typed adapter stream.

    Cursor is irreversibly consumed *before* sending to fail closed on errors
    or cancellation. No Action authority, cognition, timer or retry is added.
    """
    if not isinstance(cursor, ExclusiveProbeCursor) or cursor.consumed:
        raise InvalidExplicitProbe("fresh caller-owned one-shot cursor required")
    if not isinstance(authority, ExplicitProbeAuthority) or not authority.granted:
        raise InvalidExplicitProbe("explicit granted observation authority required")
    if not isinstance(supervisor, ActionSupervisor):
        raise InvalidExplicitProbe("requires existing supervisor")
    if not isinstance(action, ActionLifecycle) or not action.is_current_snapshot:
        raise InvalidExplicitProbe("requires current terminal Action")
    if action.state is not ActionState.OUTCOME:
        raise InvalidExplicitProbe("source Action must be OUTCOME")
    try:
        current = supervisor.get(action.action_id)
    except ValueError as exc:
        raise InvalidExplicitProbe("Action is not supervised") from exc
    if current is not action:
        raise InvalidExplicitProbe("Action ownership mismatch")
    if not isinstance(consequence, WorldConsequence):
        raise InvalidExplicitProbe("requires typed WorldConsequence")
    after = consequence.after_observation
    if (
        consequence.status is not WorldConsequenceStatus.EXECUTED
        or consequence.action_id != action.action_id
        or action.events[-1].provenance != consequence.provenance
        or not isinstance(after, MineflayerObservation)
        or after.kind != "probe"
        or after.session_id != consequence.session_id
    ):
        raise InvalidExplicitProbe("invalid parent WorldConsequence ancestry")
    started = getattr(adapter, "started", None)
    if not isinstance(started, MineflayerAdapterStarted) or started.seq != 0:
        raise InvalidExplicitProbe("exact adapter_started missing")
    if (
        authority.parent_action_id != action.action_id
        or authority.session_id != consequence.session_id
        or started.session_id != consequence.session_id
        or cursor.session_id != consequence.session_id
        or cursor.next_seq != after.seq + 1
    ):
        raise InvalidExplicitProbe("wrong session, source Action or sequence cursor")
    if any(
        not isinstance(v, int) or isinstance(v, bool) or v < 0
        for v in (observed_at_ns, inspected_at_ns, max_age_ns)
    ):
        raise InvalidExplicitProbe("invalid caller observation clock")
    if (
        observed_at_ns <= action.events[-1].at_ns
        or inspected_at_ns < observed_at_ns
        or max_age_ns == 0
        or inspected_at_ns - observed_at_ns > max_age_ns
        or supervisor.last_at_ns is None
        or inspected_at_ns < supervisor.last_at_ns
    ):
        raise InvalidExplicitProbe("stale or inconsistent caller clock")
    if (
        not isinstance(timeout_s, (float, int))
        or isinstance(timeout_s, bool)
        or not math.isfinite(timeout_s)
        or timeout_s <= 0
    ):
        raise InvalidExplicitProbe("invalid timeout")
    if not isinstance(max_frames, int) or isinstance(max_frames, bool) or not 1 <= max_frames <= 16:
        raise InvalidExplicitProbe("max_frames outside bounded range")
    if not callable(getattr(adapter, "send_observe", None)) or not callable(
        getattr(adapter, "receive", None)
    ):
        raise InvalidExplicitProbe("adapter observation methods missing")

    first_seq = cursor.next_seq
    cursor.consumed = True
    # A single bounded receive deadline covers the whole roundtrip.
    async def _roundtrip() -> ExplicitProbeRoundtrip:
        await adapter.send_observe()
        expected_seq = first_seq
        for count in range(1, max_frames + 1):
            message = await adapter.receive()
            if not isinstance(message, MineflayerMessage):
                raise InvalidExplicitProbe("adapter returned untyped frame")
            if message.session_id != cursor.session_id or message.seq != expected_seq:
                raise InvalidExplicitProbe("cross-session, missing, stale or replayed frame")
            expected_seq += 1
            if not isinstance(message, MineflayerObservation):
                raise InvalidExplicitProbe("unexpected non-observation frame in exclusive probe")
            if message.kind != "probe":
                # Existing adapter can emit move/entities before explicit probe.
                continue
            receipt = project_source_native_threat(
                supervisor, action, consequence, message,
                target_entity_id=authority.target_entity_id,
                target_name=authority.target_name,
                observed_at_ns=observed_at_ns,
                inspected_at_ns=inspected_at_ns,
                max_age_ns=max_age_ns,
            )
            return ExplicitProbeRoundtrip(
                authority_id=authority.authority_id,
                request_cursor_seq=first_seq,
                received_count=count,
                probe_seq=message.seq,
                inspected_at_ns=inspected_at_ns,
                source_receipt=receipt,
            )
        raise InvalidExplicitProbe("probe absent within bounded number of frames")

    try:
        return await asyncio.wait_for(_roundtrip(), timeout=float(timeout_s))
    except asyncio.TimeoutError as exc:
        raise InvalidExplicitProbe("bounded probe timed out") from exc
