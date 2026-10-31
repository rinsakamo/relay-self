"""S48 cheap urgent-L0 coexistence and stale-L2 result invalidation.

A host task cancellation is not a provider/backend stop, and a backend stop
is not proof of GPU slot/VRAM release. This guard owns only one transient L2
work ticket, not a global scheduler, a new Self owner or Action authority.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from relay_self.provenance import Provenance


class InterruptRejected(ValueError):
    """Old/foreign task, stale World context or unsupported release assertion."""


class InterruptStage(str, Enum):
    RUNNING = "RUNNING"
    REQUESTED = "REQUESTED"
    HOST_CANCELLED = "HOST_CANCELLED"
    BACKEND_STOP_ACK = "BACKEND_STOP_ACK"
    RESOURCE_RELEASE_EVIDENCED = "RESOURCE_RELEASE_EVIDENCED"


@dataclass(frozen=True, slots=True)
class CognitionContext:
    session_id: str
    world_seq: int
    intent_revision: int
    retained_revision: int

    def __post_init__(self) -> None:
        if (
            not isinstance(self.session_id, str) or not self.session_id
            or any(type(x) is not int or x < 0 for x in (
                self.world_seq, self.intent_revision, self.retained_revision,
            ))
        ):
            raise InterruptRejected("exact session and causal revisions required")


@dataclass(frozen=True, slots=True)
class L2WorkTicket:
    work_id: str
    generation: int
    context: CognitionContext


@dataclass(frozen=True, slots=True)
class InterruptEvidence:
    work_id: str
    stage: InterruptStage
    provenance: Provenance

    def __post_init__(self) -> None:
        if (
            not isinstance(self.work_id, str) or not self.work_id
            or not isinstance(self.stage, InterruptStage)
            or not isinstance(self.provenance, Provenance)
            or self.provenance.source == "mineflayer"
        ):
            raise InterruptRejected("independent non-World runtime evidence required")


class L2InterruptionFence:
    """Owner-local one-task control; all Action decisions remain outside."""

    def __init__(self) -> None:
        self.ticket: L2WorkTicket | None = None
        self.stage: InterruptStage | None = None
        self.generation = 0
        self.latest_context: CognitionContext | None = None
        self.ack: InterruptEvidence | None = None
        self.release: InterruptEvidence | None = None

    def start(self, work_id: str, context: CognitionContext) -> L2WorkTicket:
        if (
            self.ticket is not None or not isinstance(work_id, str) or not work_id
            or not isinstance(context, CognitionContext)
        ):
            raise InterruptRejected("one fully identified outstanding L2 task only")
        self.generation += 1
        self.ticket = L2WorkTicket(work_id, self.generation, context)
        self.latest_context = context
        self.stage = InterruptStage.RUNNING
        self.ack = None
        self.release = None
        return self.ticket

    def observe(self, current: CognitionContext) -> None:
        if not isinstance(current, CognitionContext):
            raise InterruptRejected("typed new context required")
        if (
            self.latest_context is not None
            and current.session_id == self.latest_context.session_id
            and current.world_seq < self.latest_context.world_seq
        ):
            raise InterruptRejected("World sequence regressed")
        self.latest_context = current

    def _require(self, ticket: L2WorkTicket) -> None:
        if not isinstance(ticket, L2WorkTicket) or ticket is not self.ticket:
            raise InterruptRejected("foreign, duplicated or retired L2 ticket")

    def request_interrupt(self, ticket: L2WorkTicket) -> None:
        self._require(ticket)
        if self.stage is not InterruptStage.RUNNING:
            raise InterruptRejected("interrupt already requested")
        self.stage = InterruptStage.REQUESTED

    def host_cancelled(self, ticket: L2WorkTicket) -> None:
        self._require(ticket)
        if self.stage is not InterruptStage.REQUESTED:
            raise InterruptRejected("cannot assert host cancel without request")
        self.stage = InterruptStage.HOST_CANCELLED

    def backend_stop_ack(
        self, ticket: L2WorkTicket, evidence: InterruptEvidence,
    ) -> None:
        self._require(ticket)
        if (
            self.stage not in (InterruptStage.REQUESTED, InterruptStage.HOST_CANCELLED)
            or not isinstance(evidence, InterruptEvidence)
            or evidence.work_id != ticket.work_id
            or evidence.stage is not InterruptStage.BACKEND_STOP_ACK
        ):
            raise InterruptRejected("independent backend acknowledgement absent")
        self.ack = evidence
        self.stage = InterruptStage.BACKEND_STOP_ACK

    def evidence_of_release(
        self, ticket: L2WorkTicket, evidence: InterruptEvidence,
    ) -> None:
        self._require(ticket)
        if (
            self.stage is not InterruptStage.BACKEND_STOP_ACK
            or not isinstance(evidence, InterruptEvidence)
            or evidence.work_id != ticket.work_id
            or evidence.stage is not InterruptStage.RESOURCE_RELEASE_EVIDENCED
            or self.ack is None or evidence.provenance == self.ack.provenance
        ):
            raise InterruptRejected("separate resource release evidence required")
        self.release = evidence
        self.stage = InterruptStage.RESOURCE_RELEASE_EVIDENCED

    def accept_l2_result(
        self, ticket: L2WorkTicket, current: CognitionContext,
    ) -> None:
        """Transient result is current, not permission to commit or issue Action."""
        self._require(ticket)
        if (
            self.stage is not InterruptStage.RUNNING
            or not isinstance(current, CognitionContext)
            or self.latest_context != current
            or ticket.context != current
        ):
            raise InterruptRejected("interrupted or stale L2 result denied")
        self.ticket = None
        self.stage = None

    def retire_interrupted(self, ticket: L2WorkTicket) -> None:
        """Retire only after provider stop receipt; host cancellation is insufficient."""
        self._require(ticket)
        if self.stage not in (
            InterruptStage.BACKEND_STOP_ACK,
            InterruptStage.RESOURCE_RELEASE_EVIDENCED,
        ):
            raise InterruptRejected("backend may still be running")
        self.ticket = None
        self.stage = None
