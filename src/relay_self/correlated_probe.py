"""S29: protocol-level correlated explicit Mineflayer probe roundtrip.

Unlike S28's sequence-only observation, a correlated probe MUST echo the
exact bounded request_id that the caller submitted. This is protocol-level
matching, NOT proof of server provenance, event causality, or process identity.
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
    encode_observe,
)
from relay_self.action import ActionLifecycle, ActionState
from relay_self.action_supervision import ActionSupervisor
from relay_self.explicit_probe import ExclusiveProbeCursor, ExplicitProbeAuthority
from relay_self.source_native_world import (
    SourceNativeThreatReceipt,
    project_source_native_threat,
)


class InvalidCorrelatedProbe(ValueError):
    """Wrong request ID, Action lineage, stream cursor or limited caller scope."""


class CorrelatedProbeSession(Protocol):
    @property
    def started(self) -> MineflayerAdapterStarted: ...

    async def send_observe(self, request_id: str | None = None) -> None: ...

    async def receive(self) -> MineflayerMessage: ...


@dataclass(frozen=True, slots=True)
class CorrelatedProbeGrant:
    """Caller-selected ID bound to a separate, explicit observation authority."""

    authority: ExplicitProbeAuthority
    request_id: str

    def __post_init__(self) -> None:
        if not isinstance(self.authority, ExplicitProbeAuthority):
            raise InvalidCorrelatedProbe("requires existing typed probe authority")
        try:
            encode_observe(self.request_id)
        except ValueError as exc:
            raise InvalidCorrelatedProbe("invalid protocol request ID") from exc


@dataclass(frozen=True, slots=True)
class CorrelatedProbeReceipt:
    authority_id: str
    request_id: str
    acknowledged_request_id: str
    request_cursor_seq: int
    probe_seq: int
    received_count: int
    next_cursor_seq: int
    inspected_at_ns: int
    source_receipt: SourceNativeThreatReceipt


async def request_correlated_post_action_probe(
    adapter: CorrelatedProbeSession,
    cursor: ExclusiveProbeCursor,
    grant: CorrelatedProbeGrant,
    supervisor: ActionSupervisor,
    action: ActionLifecycle,
    consequence: WorldConsequence,
    *,
    observed_at_ns: int,
    inspected_at_ns: int,
    max_age_ns: int,
    timeout_s: float = 0.25,
    max_frames: int = 4,
    previous_receipt: CorrelatedProbeReceipt | None = None,
) -> CorrelatedProbeReceipt:
    """Send exactly one correlated observe and require its echoed request_id.

    The one-shot cursor is consumed before I/O. Assumes sole-reader access to
    this session; does not install a global transport lock or retry.
    """
    if not isinstance(cursor, ExclusiveProbeCursor) or cursor.consumed:
        raise InvalidCorrelatedProbe("fresh one-shot cursor required")
    if not isinstance(grant, CorrelatedProbeGrant) or not grant.authority.granted:
        raise InvalidCorrelatedProbe("explicit granted caller request needed")
    if not isinstance(supervisor, ActionSupervisor):
        raise InvalidCorrelatedProbe("requires ActionSupervisor")
    if not isinstance(action, ActionLifecycle) or not action.is_current_snapshot:
        raise InvalidCorrelatedProbe("current Action snapshot required")
    if action.state is not ActionState.OUTCOME:
        raise InvalidCorrelatedProbe("terminal Action OUTCOME required")
    try:
        current = supervisor.get(action.action_id)
    except ValueError as exc:
        raise InvalidCorrelatedProbe("Action not supervised") from exc
    if current is not action:
        raise InvalidCorrelatedProbe("Action snapshot is stale")
    if not isinstance(consequence, WorldConsequence):
        raise InvalidCorrelatedProbe("typed WorldConsequence required")
    parent = consequence.after_observation
    if (
        consequence.status is not WorldConsequenceStatus.EXECUTED
        or consequence.action_id != action.action_id
        or consequence.provenance != action.events[-1].provenance
        or not isinstance(parent, MineflayerObservation)
        or parent.kind != "probe"
        or parent.session_id != consequence.session_id
    ):
        raise InvalidCorrelatedProbe("source Action / WorldConsequence lineage invalid")
    started = getattr(adapter, "started", None)
    if not isinstance(started, MineflayerAdapterStarted) or started.seq != 0:
        raise InvalidCorrelatedProbe("adapter_started invalid")
    a = grant.authority
    if previous_receipt is not None:
        if (
            not isinstance(previous_receipt, CorrelatedProbeReceipt)
            or previous_receipt.source_receipt.source.session_id != consequence.session_id
            or previous_receipt.source_receipt.source.request_id
            != previous_receipt.request_id
            or previous_receipt.request_id == grant.request_id
        ):
            raise InvalidCorrelatedProbe("invalid previous correlated probe receipt")
        expected_cursor = previous_receipt.next_cursor_seq
    else:
        expected_cursor = parent.seq + 1
    if (
        a.parent_action_id != action.action_id
        or a.session_id != consequence.session_id
        or started.session_id != consequence.session_id
        or cursor.session_id != consequence.session_id
        or cursor.next_seq != expected_cursor
    ):
        raise InvalidCorrelatedProbe("wrong caller/adapter session or sequence")
    if any(
        not isinstance(x, int) or isinstance(x, bool) or x < 0
        for x in (observed_at_ns, inspected_at_ns, max_age_ns)
    ):
        raise InvalidCorrelatedProbe("caller clock invalid")
    if (
        observed_at_ns <= action.events[-1].at_ns
        or inspected_at_ns < observed_at_ns
        or max_age_ns == 0
        or inspected_at_ns - observed_at_ns > max_age_ns
        or supervisor.last_at_ns is None
        or inspected_at_ns < supervisor.last_at_ns
    ):
        raise InvalidCorrelatedProbe("stale or reversed observation clock")
    if (
        not isinstance(timeout_s, (int, float))
        or isinstance(timeout_s, bool)
        or not math.isfinite(timeout_s)
        or timeout_s <= 0
    ):
        raise InvalidCorrelatedProbe("timeout_s invalid")
    if not isinstance(max_frames, int) or isinstance(max_frames, bool) or not 1 <= max_frames <= 16:
        raise InvalidCorrelatedProbe("max_frames invalid")
    if not callable(getattr(adapter, "send_observe", None)) or not callable(
        getattr(adapter, "receive", None)
    ):
        raise InvalidCorrelatedProbe("adapter missing observation transport")

    sequence = cursor.next_seq
    cursor.consumed = True

    async def _roundtrip() -> CorrelatedProbeReceipt:
        await adapter.send_observe(grant.request_id)
        expected_seq = sequence
        for count in range(1, max_frames + 1):
            message = await adapter.receive()
            if not isinstance(message, MineflayerMessage):
                raise InvalidCorrelatedProbe("untyped adapter response")
            if message.session_id != cursor.session_id or message.seq != expected_seq:
                raise InvalidCorrelatedProbe("session/seq mismatch or replay")
            expected_seq += 1
            if not isinstance(message, MineflayerObservation):
                raise InvalidCorrelatedProbe("non-observation event in exclusive probe")
            if message.kind != "probe":
                continue
            if message.request_id != grant.request_id:
                raise InvalidCorrelatedProbe(
                    "wrong, missing or stale echoed request_id"
                )
            source = project_source_native_threat(
                supervisor, action, consequence, message,
                target_entity_id=a.target_entity_id,
                target_name=a.target_name,
                observed_at_ns=observed_at_ns,
                inspected_at_ns=inspected_at_ns,
                max_age_ns=max_age_ns,
            )
            return CorrelatedProbeReceipt(
                authority_id=a.authority_id,
                request_id=grant.request_id,
                acknowledged_request_id=message.request_id,
                request_cursor_seq=sequence,
                probe_seq=message.seq,
                received_count=count,
                next_cursor_seq=expected_seq,
                inspected_at_ns=inspected_at_ns,
                source_receipt=source,
            )
        raise InvalidCorrelatedProbe("correlated probe absent within frame budget")

    try:
        return await asyncio.wait_for(_roundtrip(), timeout=float(timeout_s))
    except TimeoutError as exc:
        raise InvalidCorrelatedProbe("correlated probe timeout") from exc
