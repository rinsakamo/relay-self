"""S36 bounded, in-memory, event-driven cognition-only scheduler.

The bridge's unsolicited Mineflayer entity event can enqueue work without a
human calling a cognition step. The event consumer invokes on_native_event(),
which admits at most configured units of work using separate injected
probe, trigger-grant and cognition seams. No Action/Skill/issue APIs are
imported or exposed. No global/durable replay or wall-clock authority.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from enum import Enum
from typing import Awaitable, Callable, TypeVar

from adapters.mineflayer.python_protocol import MineflayerObservation
from relay_self.native_event_cognition import (
    AdmittedNativeCognitionTicket,
    EventCognitionLedger,
    EventCognitionTriggerGrant,
    NativeEventCognitionCandidate,
    native_entity_event_to_cognition_candidate,
)

T = TypeVar("T")


class SchedulerGateError(ValueError):
    """An event queue gate rejected source ordering or bounded capacity."""


class SchedulerResourceExhausted(RuntimeError):
    """A bounded external seam timed out; do not claim cognition ran."""


class EventQueueDisposition(str, Enum):
    ENQUEUED = "enqueued"
    COALESCED = "coalesced"
    IGNORED = "ignored"
    INVALIDATED = "invalidated"
    STALE = "stale"
    FULL = "full"


@dataclass(frozen=True, slots=True)
class EventSchedulerBudget:
    max_pending: int = 4
    max_epochs_per_batch: int = 2
    max_event_age_seq: int = 16
    max_urgent_burst: int = 2
    per_probe_timeout_s: float = 10.0

    def __post_init__(self) -> None:
        for field in (
            "max_pending", "max_epochs_per_batch", "max_event_age_seq",
            "max_urgent_burst",
        ):
            value = getattr(self, field)
            if type(value) is not int or value < 1 or value > 1024:
                raise SchedulerGateError(f"{field} requires a bounded positive integer")
        if (
            isinstance(self.per_probe_timeout_s, bool)
            or not isinstance(self.per_probe_timeout_s, (float, int))
            or not 0 < self.per_probe_timeout_s <= 60
        ):
            raise SchedulerGateError("per_probe_timeout_s must be in (0,60]")


@dataclass(frozen=True, slots=True)
class _PendingEvent:
    candidate: NativeEventCognitionCandidate
    order: int


@dataclass(frozen=True, slots=True)
class SchedulerOutcome:
    event_id: str
    ticket: AdmittedNativeCognitionTicket
    cognition_result: object


@dataclass(frozen=True, slots=True)
class SchedulerBatch:
    outcomes: tuple[SchedulerOutcome, ...]
    work_attempted: int
    remaining_pending: int
    dropped_stale: int


class BoundedEventCognitionScheduler:
    """Serial caller-owned event-loop scheduler with independent cognition grant.

    Priority: near (distance <=2.5m) over farther, within each band FIFO.
    Fairness: after max_urgent_burst urgent attempts, a waiting nonurgent
    item is selected before more urgent work. Each batch attempts no more
    than max_epochs_per_batch; no burst drains unboundedly.

    The host must call on_native_event for each native event, and must
    supply independently authorized grant/probe/cognition callbacks.
    The scheduler NEVER fabricates its own authority or runs Action code.
    """

    def __init__(self, budget: EventSchedulerBudget | None = None) -> None:
        self.budget = budget or EventSchedulerBudget()
        self.ledger = EventCognitionLedger()
        self._pending: list[_PendingEvent] = []
        self._last_entity_seq: dict[str, int] = {}
        self._next_order = 0
        self._urgent_run = 0
        self.total_cognition = 0
        self.total_coalesced = 0
        self.total_invalidated = 0
        self.total_stale_dropped = 0
        self.total_full = 0

    @property
    def pending_count(self) -> int:
        return len(self._pending)

    def ingest_native(self, event: MineflayerObservation) -> EventQueueDisposition:
        if not isinstance(event, MineflayerObservation):
            raise SchedulerGateError("only typed Mineflayer observation may enter queue")
        if event.kind != "entities":
            return EventQueueDisposition.IGNORED
        last = self._last_entity_seq.get(event.session_id, -1)
        if event.seq <= last:
            return EventQueueDisposition.STALE
        # Advance the native session's event cursor, including disappearances.
        self._last_entity_seq[event.session_id] = event.seq
        candidate = native_entity_event_to_cognition_candidate(event)
        if candidate is None:
            before = len(self._pending)
            self._pending = [
                p for p in self._pending
                if p.candidate.session_id != event.session_id
            ]
            removed = before - len(self._pending)
            self.total_invalidated += removed
            return (EventQueueDisposition.INVALIDATED if removed
                    else EventQueueDisposition.IGNORED)
        for i, pending in enumerate(self._pending):
            old = pending.candidate
            if (
                old.session_id == candidate.session_id
                and old.target_entity_id == candidate.target_entity_id
            ):
                # Newer exact native evidence supersedes stale pending intent.
                self._pending[i] = _PendingEvent(candidate, pending.order)
                self.total_coalesced += 1
                return EventQueueDisposition.COALESCED
        if len(self._pending) >= self.budget.max_pending:
            self.total_full += 1
            return EventQueueDisposition.FULL
        self._pending.append(_PendingEvent(candidate, self._next_order))
        self._next_order += 1
        return EventQueueDisposition.ENQUEUED

    def _pop_next(self) -> _PendingEvent:
        # Expiration is checked before selection; here only valid candidates.
        urgent = [x for x in self._pending if x.candidate.distance_m <= 2.5]
        normal = [x for x in self._pending if x.candidate.distance_m > 2.5]
        if normal and (not urgent or self._urgent_run >= self.budget.max_urgent_burst):
            chosen = min(normal, key=lambda x: x.order)
            self._urgent_run = 0
        elif urgent:
            chosen = min(urgent, key=lambda x: x.order)
            self._urgent_run += 1
        else:
            chosen = min(normal, key=lambda x: x.order)
            self._urgent_run = 0
        self._pending.remove(chosen)
        return chosen

    def _drop_stale(self) -> int:
        fresh: list[_PendingEvent] = []
        dropped = 0
        for pending in self._pending:
            candidate = pending.candidate
            latest = self._last_entity_seq.get(candidate.session_id, -1)
            if latest - candidate.event_seq > self.budget.max_event_age_seq:
                dropped += 1
            else:
                fresh.append(pending)
        self._pending = fresh
        self.total_stale_dropped += dropped
        return dropped

    async def drain_batch(
        self,
        *,
        probe: Callable[[NativeEventCognitionCandidate], Awaitable[MineflayerObservation]],
        grant: Callable[[NativeEventCognitionCandidate], EventCognitionTriggerGrant],
        cognition: Callable[[AdmittedNativeCognitionTicket], T],
    ) -> SchedulerBatch:
        """Automatically dispatch bounded ready cognition; no automatic Action.

        A probe timeout/error, malformed grant or cognitive exception raises
        and is NOT silently converted to PASS or retried. The queue's popped
        item does not run again without a new native event. Output is caller-
        auditable and bounded by max_epochs_per_batch.
        """
        dropped = self._drop_stale()
        outcomes: list[SchedulerOutcome] = []
        attempts = 0
        while self._pending and attempts < self.budget.max_epochs_per_batch:
            item = self._pop_next()
            attempts += 1
            try:
                observed = await asyncio.wait_for(
                    probe(item.candidate),
                    timeout=self.budget.per_probe_timeout_s,
                )
            except TimeoutError as exc:
                raise SchedulerResourceExhausted("native re-probe exceeded budget") from exc
            authority = grant(item.candidate)
            ticket = self.ledger.admit(
                item.candidate,
                observed,
                authority,
                request_id=observed.request_id or "",
            )
            result = cognition(ticket)
            outcomes.append(SchedulerOutcome(item.candidate.candidate_id, ticket, result))
            self.total_cognition += 1
        return SchedulerBatch(tuple(outcomes), attempts, len(self._pending), dropped)

    async def on_native_event(
        self,
        event: MineflayerObservation,
        *,
        probe: Callable[[NativeEventCognitionCandidate], Awaitable[MineflayerObservation]],
        grant: Callable[[NativeEventCognitionCandidate], EventCognitionTriggerGrant],
        cognition: Callable[[AdmittedNativeCognitionTicket], T],
    ) -> tuple[EventQueueDisposition, SchedulerBatch]:
        """One native input automatically runs an admitted bounded cognition batch.

        This is an event-loop callback entrypoint, not caller-driven explicit
        cognition invocation. No background threads or unbounded retries.
        """
        disposition = self.ingest_native(event)
        if disposition in (EventQueueDisposition.STALE, EventQueueDisposition.FULL):
            return disposition, SchedulerBatch((), 0, self.pending_count, 0)
        batch = await self.drain_batch(probe=probe, grant=grant, cognition=cognition)
        return disposition, batch
