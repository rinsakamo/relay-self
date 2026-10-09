"""S37 bounded multi-event Mineflayer host loop with explicit reconnect.

Host receives native frames and calls S36 event scheduler. NO Action/effect
interfaces, background daemon, durable ledger or independent authority.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Awaitable, Callable, TypeVar

from adapters.mineflayer.process_session import MineflayerProcessSession
from adapters.mineflayer.python_protocol import (
    MineflayerAdapterErrorMessage,
    MineflayerConnectionEnd,
    MineflayerObservation,
)
from relay_self.bounded_event_scheduler import (
    BoundedEventCognitionScheduler,
    EventSchedulerBudget,
)
from relay_self.native_event_cognition import (
    AdmittedNativeCognitionTicket,
    EventCognitionTriggerGrant,
    NativeEventCognitionCandidate,
    native_entity_event_to_cognition_candidate,
)

T = TypeVar("T")


class HostLoopBoundaryError(RuntimeError):
    """Reject foreign/retired sessions, tickets or unexpected disconnection."""


class HostLoopResourceError(RuntimeError):
    """Bounded session/event/cognition budget exceeded; not a PASS."""


@dataclass(frozen=True, slots=True)
class HostLoopBudget:
    max_sessions: int = 2
    max_epochs_per_session: int = 2
    max_total_epochs: int = 3
    max_frames_per_event: int = 100
    receive_timeout_s: float = 30.0

    def __post_init__(self) -> None:
        for name in (
            "max_sessions", "max_epochs_per_session",
            "max_total_epochs", "max_frames_per_event",
        ):
            value = getattr(self, name)
            if type(value) is not int or not 1 <= value <= 1000:
                raise HostLoopResourceError(f"{name}: positive bounded int required")
        if (
            isinstance(self.receive_timeout_s, bool)
            or not isinstance(self.receive_timeout_s, (float, int))
            or not 0 < self.receive_timeout_s <= 120
        ):
            raise HostLoopResourceError("receive_timeout_s not in (0,120]")


@dataclass(frozen=True, slots=True)
class HostCognitionEvent:
    session_id: str
    entity_id: int
    event_seq: int
    event_provenance: str
    probe_request_id: str
    probe_seq: int
    ticket: AdmittedNativeCognitionTicket
    cognition: object


class BoundedNativeHostLoop:
    """Serial in-process epoch/event owner; outside caller owns lifecycle.

    Previous S36 scheduler and ledger are discarded on end_session.
    Reconnect is *explicit*, not an automatic network fault recovery.
    """

    def __init__(self, budget: HostLoopBudget | None = None) -> None:
        self.budget = budget or HostLoopBudget()
        self._active_session_id: str | None = None
        self._scheduler: BoundedEventCognitionScheduler | None = None
        self._history: set[str] = set()
        self._seen_entities: set[int] = set()
        self._session_epochs = 0
        self.total_epochs = 0
        self.total_sessions = 0
        self.expired_pending = 0
        self.rejected_replays = 0

    @property
    def active_session_id(self) -> str | None:
        return self._active_session_id

    @property
    def pending_count(self) -> int:
        return 0 if self._scheduler is None else self._scheduler.pending_count

    def begin_session(self, session_id: str) -> None:
        if self._active_session_id is not None:
            raise HostLoopBoundaryError("end old native session before reconnect")
        if not isinstance(session_id, str) or not session_id or session_id in self._history:
            raise HostLoopBoundaryError("missing or reused source session ID")
        if self.total_sessions >= self.budget.max_sessions:
            raise HostLoopResourceError("max_sessions exhausted")
        self._active_session_id = session_id
        self._history.add(session_id)
        self.total_sessions += 1
        self._session_epochs = 0
        self._seen_entities = set()
        self._scheduler = BoundedEventCognitionScheduler(
            EventSchedulerBudget(
                max_pending=4, max_epochs_per_batch=1,
                max_total_cognition=self.budget.max_epochs_per_session,
                max_event_age_seq=16, max_urgent_burst=2,
                per_probe_timeout_s=10,
            ),
        )

    def end_session(self, session_id: str) -> None:
        if session_id != self._active_session_id or self._scheduler is None:
            raise HostLoopBoundaryError("cannot close another session")
        self.expired_pending += self._scheduler.pending_count
        self._scheduler = None
        self._seen_entities.clear()
        self._active_session_id = None
        self._session_epochs = 0

    def require_current_ticket(self, ticket: AdmittedNativeCognitionTicket) -> None:
        if (
            not isinstance(ticket, AdmittedNativeCognitionTicket)
            or self._active_session_id is None
            or ticket.candidate.session_id != self._active_session_id
            or ticket.correlated_probe.session_id != self._active_session_id
        ):
            raise HostLoopBoundaryError("retired native ticket across reconnect")

    async def wait_for_event_cognition(
        self,
        session: MineflayerProcessSession,
        *,
        probe: Callable[[NativeEventCognitionCandidate], Awaitable[MineflayerObservation]],
        grant: Callable[[NativeEventCognitionCandidate], EventCognitionTriggerGrant],
        cognition: Callable[[AdmittedNativeCognitionTicket], T],
    ) -> HostCognitionEvent:
        """Bounded event-consuming host callback; no explicit cognition call.

        This loop serially owns Node stdout. Probe callback temporarily reads
        response while this loop is suspended. Caller never authorizes Action.
        """
        active = self._active_session_id
        scheduler = self._scheduler
        if active is None or scheduler is None or session.started.session_id != active:
            raise HostLoopBoundaryError("process does not match current host session")
        if (
            self.total_epochs >= self.budget.max_total_epochs
            or self._session_epochs >= self.budget.max_epochs_per_session
        ):
            raise HostLoopResourceError("cognitive epoch quota exceeded")
        for _ in range(self.budget.max_frames_per_event):
            try:
                frame = await asyncio.wait_for(
                    session.receive(), timeout=self.budget.receive_timeout_s,
                )
            except TimeoutError as exc:
                raise HostLoopResourceError("native receive timeout") from exc
            if isinstance(frame, (MineflayerConnectionEnd, MineflayerAdapterErrorMessage)):
                raise HostLoopBoundaryError("unexpected real Node/World disconnect")
            if not isinstance(frame, MineflayerObservation):
                continue
            if frame.session_id != active:
                raise HostLoopBoundaryError("foreign or retired world source frame")
            if frame.kind != "entities":
                continue
            candidate = native_entity_event_to_cognition_candidate(frame)
            if candidate is None:
                scheduler.ingest_native(frame)
                continue
            if candidate.target_entity_id in self._seen_entities:
                self.rejected_replays += 1
                scheduler.ingest_native(frame)
                continue
            _, batch = await scheduler.on_native_event(
                frame, probe=probe, grant=grant, cognition=cognition,
            )
            if len(batch.outcomes) != 1 or batch.work_attempted != 1:
                raise HostLoopBoundaryError("event did not produce one admitted cognition")
            outcome = batch.outcomes[0]
            self.require_current_ticket(outcome.ticket)
            if outcome.ticket.candidate.target_entity_id != candidate.target_entity_id:
                raise HostLoopBoundaryError("new evidence changed entity identity")
            self._seen_entities.add(candidate.target_entity_id)
            self._session_epochs += 1
            self.total_epochs += 1
            return HostCognitionEvent(
                session_id=active, entity_id=candidate.target_entity_id,
                event_seq=frame.seq,
                event_provenance=frame.provenance.reference,
                probe_request_id=outcome.ticket.probe_request_id,
                probe_seq=outcome.ticket.correlated_probe.seq,
                ticket=outcome.ticket, cognition=outcome.cognition_result,
            )
        raise HostLoopResourceError("native frame budget exhausted")
