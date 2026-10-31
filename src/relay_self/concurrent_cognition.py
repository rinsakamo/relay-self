"""S53 concurrent L0 dispatch while one L2 generation remains outstanding.

One async host event reader owns World IO externally; this component never
reads native stdout or authorizes Action. Cancellation requested != backend
stopped != measured GPU release, and interrupted model output is discarded.
"""
from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import TypeVar

from relay_self.interruption_fence import (
    CognitionContext,
    InterruptEvidence,
    InterruptRejected,
    L2InterruptionFence,
    L2WorkTicket,
)

T = TypeVar("T")


class ConcurrentCognitionRejected(ValueError):
    """Cannot claim completed or preempted L2 without matching evidence."""


@dataclass(frozen=True, slots=True)
class UrgentL0Receipt:
    l2_work_id: str
    world_seq: int
    l0_completed: bool
    backend_stopped: bool
    gpu_released: bool


class ConcurrentL0L2:
    """Foreground host-local controller with one outstanding provider request."""

    def __init__(self) -> None:
        self.fence = L2InterruptionFence()
        self._task: asyncio.Task | None = None
        self._ticket: L2WorkTicket | None = None

    def begin_l2(
        self, work_id: str, context: CognitionContext,
        provider: Callable[[], T],
    ) -> L2WorkTicket:
        if self._task is not None or not callable(provider):
            raise ConcurrentCognitionRejected("one outstanding typed provider only")
        ticket = self.fence.start(work_id, context)
        self._ticket = ticket
        # Run blocking RelayEngine/HTTP provider off the L0 event loop. This
        # thread continues unless actual backend gives a separate stop ACK.
        self._task = asyncio.create_task(asyncio.to_thread(provider))
        return ticket

    async def urgent_l0(
        self, current: CognitionContext,
        handle_l0: Callable[[], Awaitable[None]],
    ) -> UrgentL0Receipt:
        ticket = self._ticket
        if (
            ticket is None or self._task is None
            or not isinstance(current, CognitionContext)
            or not callable(handle_l0)
        ):
            raise ConcurrentCognitionRejected("no outstanding source-scoped L2")
        self.fence.observe(current)
        self.fence.request_interrupt(ticket)
        # Do not await the L2 backend or confuse a local task cancel with
        # GPU memory being returned. Actual L0 Action authority is elsewhere.
        await handle_l0()
        return UrgentL0Receipt(
            ticket.work_id, current.world_seq, True, False, False,
        )

    def acknowledge_backend_stop(
        self, evidence: InterruptEvidence,
    ) -> None:
        if self._ticket is None:
            raise ConcurrentCognitionRejected("no L2 to acknowledge")
        self.fence.backend_stop_ack(self._ticket, evidence)

    def acknowledge_release(self, evidence: InterruptEvidence) -> None:
        if self._ticket is None:
            raise ConcurrentCognitionRejected("no L2 to release")
        self.fence.evidence_of_release(self._ticket, evidence)

    async def collect_l2(self, current: CognitionContext) -> T | None:
        if self._task is None or self._ticket is None:
            raise ConcurrentCognitionRejected("no active L2 generation")
        task, ticket = self._task, self._ticket
        result = await task
        try:
            self.fence.accept_l2_result(ticket, current)
        except InterruptRejected:
            # A cancelled/interrupted result, even if it happened to finish,
            # can never be committed as new evidence/Action. A backend
            # stopped acknowledgement is needed before another L2 starts.
            if self.fence.ack is not None:
                self.fence.retire_interrupted(ticket)
                self._ticket = None
                self._task = None
            return None
        self._task = None
        self._ticket = None
        return result

    def retire_after_stop(self) -> None:
        """Clear host bookkeeping only after an independent backend stop ACK.

        Caller evidence is mandatory; task completion or local cancellation
        alone does NOT mean that a model runner has stopped or VRAM is free.
        """
        if (
            self._task is None or self._ticket is None
            or not self._task.done() or self.fence.ack is None
        ):
            raise ConcurrentCognitionRejected(
                "cannot retire L2 without completed task and backend stop ACK"
            )
        self.fence.retire_interrupted(self._ticket)
        self._task = None
        self._ticket = None

    @property
    def pending_backend_stop(self) -> bool:
        return self._ticket is not None and self.fence.ack is None
