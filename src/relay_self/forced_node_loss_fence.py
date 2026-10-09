"""S38 forced Mineflayer child loss: cognition quarantine and new-source recovery.

A bounded, process-local owner for S37 host session generations.
- Observed unexpected child EOF + nonzero process death quarantines all work.
- No old ticket or new cognition is accepted while quarantined.
- A supervisor may explicitly open one PROBATION successor generation.
- ONLY a genuine new-session native entities event, distinct correlated probe,
  exact S35 independently granted ticket and one S37 cognitive callback can
  restore ACTIVE.
- The fence imports no Action/Skill/physical control APIs and never reconnects
  on its own. Unexpected disconnect isn't falsely called clean shutdown.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Awaitable, Callable, TypeVar

from adapters.mineflayer.process_session import (
    MineflayerProcessEnded,
    MineflayerProcessSession,
)
from adapters.mineflayer.python_protocol import MineflayerObservation
from relay_self.bounded_native_host_loop import (
    BoundedNativeHostLoop,
    HostCognitionEvent,
    HostLoopBudget,
)
from relay_self.native_event_cognition import (
    AdmittedNativeCognitionTicket,
    EventCognitionTriggerGrant,
    NativeEventCognitionCandidate,
)

T = TypeVar("T")


class WorldLossBoundaryError(RuntimeError):
    """Unobserved process death, old source or premature cognitive reentry."""


class WorldLossState(str, Enum):
    NEW = "new"
    ACTIVE = "active"
    QUARANTINED = "quarantined"
    PROBATION = "probation"
    CLOSED = "closed"


@dataclass(frozen=True, slots=True)
class ObservedBridgeFailure:
    session_id: str
    process_returncode: int
    transport_error: str
    old_epochs: int
    expired_pending: int


class ForcedNodeLossFence:
    """Serial caller-owned explicit forced-loss + successor revalidation.

    This is no durable crash-resume or autonomous reconnection algorithm.
    The caller MUST witness the actual MineflayerProcessEnded and nonzero
    operating-system exit, then explicitly begin a NEW Node source generation.
    The readmission gate invokes original S37/S36 source correlation; it
    never promotes an old ticket based on its previously admitted status.
    """

    def __init__(self, budget: HostLoopBudget | None = None) -> None:
        self._host = BoundedNativeHostLoop(budget or HostLoopBudget(
            max_sessions=2, max_epochs_per_session=2,
            max_total_epochs=2, max_frames_per_event=100,
            receive_timeout_s=20,
        ))
        self._state = WorldLossState.NEW
        self._fault: ObservedBridgeFailure | None = None

    @property
    def state(self) -> WorldLossState:
        return self._state

    @property
    def host(self) -> BoundedNativeHostLoop:
        """Read-only *convention*; not a capability-security boundary."""
        return self._host

    @property
    def fault(self) -> ObservedBridgeFailure | None:
        return self._fault

    def begin_initial(self, session_id: str) -> None:
        if self._state is not WorldLossState.NEW:
            raise WorldLossBoundaryError("initial session only once")
        self._host.begin_session(session_id)
        self._state = WorldLossState.ACTIVE

    def require_active_ticket(self, ticket: AdmittedNativeCognitionTicket) -> None:
        if self._state is not WorldLossState.ACTIVE:
            raise WorldLossBoundaryError("cognition ticket requires ACTIVE source")
        self._host.require_current_ticket(ticket)

    async def run_active(
        self,
        session: MineflayerProcessSession,
        *,
        probe: Callable[[NativeEventCognitionCandidate], Awaitable[MineflayerObservation]],
        grant: Callable[[NativeEventCognitionCandidate], EventCognitionTriggerGrant],
        cognition: Callable[[AdmittedNativeCognitionTicket], T],
    ) -> HostCognitionEvent:
        if self._state is not WorldLossState.ACTIVE:
            raise WorldLossBoundaryError("cannot cognize while source quarantined")
        def active_cognition(ticket: AdmittedNativeCognitionTicket) -> T:
            self.require_active_ticket(ticket)
            return cognition(ticket)
        return await self._host.wait_for_event_cognition(
            session, probe=probe, grant=grant, cognition=active_cognition,
        )

    def observe_forced_failure(
        self,
        session_id: str,
        *,
        transport_error: MineflayerProcessEnded,
        process_returncode: int,
    ) -> ObservedBridgeFailure:
        if (
            self._state is not WorldLossState.ACTIVE
            or self._host.active_session_id != session_id
            or not isinstance(transport_error, MineflayerProcessEnded)
            or type(process_returncode) is not int
            or process_returncode == 0
        ):
            raise WorldLossBoundaryError(
                "quarantine requires actual failed active session and nonzero exit"
            )
        previous = self._host.total_epochs
        before_pending = self._host.pending_count
        self._host.end_session(session_id)
        self._state = WorldLossState.QUARANTINED
        self._fault = ObservedBridgeFailure(
            session_id=session_id,
            process_returncode=process_returncode,
            transport_error=type(transport_error).__name__,
            old_epochs=previous,
            expired_pending=before_pending,
        )
        return self._fault

    def begin_successor(self, session_id: str) -> None:
        if self._state is not WorldLossState.QUARANTINED:
            raise WorldLossBoundaryError("not quarantined after real process fault")
        if self._fault is None or session_id == self._fault.session_id:
            raise WorldLossBoundaryError("new distinct native session required")
        self._host.begin_session(session_id)
        self._state = WorldLossState.PROBATION

    async def revalidate_successor(
        self,
        session: MineflayerProcessSession,
        *,
        probe: Callable[[NativeEventCognitionCandidate], Awaitable[MineflayerObservation]],
        grant: Callable[[NativeEventCognitionCandidate], EventCognitionTriggerGrant],
        cognition: Callable[[AdmittedNativeCognitionTicket], T],
    ) -> HostCognitionEvent:
        if (
            self._state is not WorldLossState.PROBATION
            or self._fault is None
            or session.started.session_id == self._fault.session_id
            or self._host.active_session_id != session.started.session_id
        ):
            raise WorldLossBoundaryError("no independently opened recovery session")
        # The only sanctioned cognitive callback in PROBATION MUST itself
        # contain a new original-world entity event and later correlated
        # observation, enforced by the frozen S37/S36/S35 stack.
        def source_checked_cognition(ticket: AdmittedNativeCognitionTicket) -> T:
            if (
                self._state is not WorldLossState.PROBATION
                or ticket.candidate.session_id == self._fault.session_id
                or ticket.correlated_probe.session_id != session.started.session_id
            ):
                raise WorldLossBoundaryError("foreign/old cognition proof during probation")
            self._host.require_current_ticket(ticket)
            return cognition(ticket)
        result = await self._host.wait_for_event_cognition(
            session, probe=probe, grant=grant, cognition=source_checked_cognition,
        )
        if (
            result.session_id == self._fault.session_id
            or result.event_seq >= result.probe_seq
            or result.ticket.candidate.session_id != result.session_id
        ):
            raise WorldLossBoundaryError("successor lacks fresh correlated source")
        self._state = WorldLossState.ACTIVE
        return result

    def close_successor(self, session_id: str) -> None:
        if (
            self._state is not WorldLossState.ACTIVE
            or self._fault is None
            or session_id == self._fault.session_id
        ):
            raise WorldLossBoundaryError("successor never revalidated")
        self._host.end_session(session_id)
        self._state = WorldLossState.CLOSED
