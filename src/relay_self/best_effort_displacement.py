"""S60-A event-loop-local logical displacement, without backend stop claims.

Adapters must provide nonblocking start/cancel callbacks and a Future whose
successful result denotes naturally observed completion of that provider attempt.
Client-only cancellation/errors cannot release this lease. No live adapter here.
"""
from __future__ import annotations

import asyncio
import math
from collections import deque
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from relay_self.concurrent_cognition import UrgentL0Receipt
from relay_self.interruption_fence import (
    CognitionContext,
    InterruptRejected,
    L2InterruptionFence,
    L2WorkTicket,
)
from relay_self.provenance import Provenance


class DisplacementRejected(ValueError):
    """Foreign admission or unsupported runtime assertion."""


@dataclass(frozen=True, slots=True)
class ModelRequest:
    work_id: str
    generation: int
    context: CognitionContext
    level: str
    priority: int
    deadline: float
    wait_budget: float
    provenance: Provenance


@dataclass(frozen=True, slots=True)
class RuntimeReceipt:
    event: str
    generation: int


@dataclass(frozen=True, slots=True)
class CognitiveResult:
    """Transient current output, never Action or Learning authorization."""
    request: ModelRequest
    value: Any


@dataclass(slots=True)
class _Lease:
    request: ModelRequest
    fence: L2InterruptionFence
    ticket: L2WorkTicket
    future: asyncio.Future | None = None
    failure_observed: bool = False


class BestEffortDisplacement:
    """One active lease, one pending candidate; caller drives tick, no workers.

    All calls belong to one foreground event loop. A callback may not reenter
    model coordination. L0 callback owns its existing Action authority elsewhere.
    No idle assertion API exists: unknown/false idle cannot release an active lease.
    """

    def __init__(
        self, context: CognitionContext, admission_source: str,
        start: Callable[[ModelRequest], asyncio.Future],
        cancel: Callable[[ModelRequest], None], clock: Callable[[], float],
    ) -> None:
        if (not isinstance(context, CognitionContext)
            or not isinstance(admission_source, str) or not admission_source.strip()
            or not all(callable(x) for x in (start, cancel, clock))):
            raise DisplacementRejected("typed context/source and callbacks required")
        self._loop = asyncio.get_running_loop()
        self._identity = uuid4().hex
        self._last_future: asyncio.Future | None = None
        self.context = context
        self._source = admission_source
        self._start = start
        self._cancel = cancel
        self._clock = clock
        self._last_time = -math.inf
        self._generation = 0
        self._issued: ModelRequest | None = None
        self._active: _Lease | None = None
        self._pending: ModelRequest | None = None
        self._pending_until = 0.0
        self._receipts: deque[RuntimeReceipt] = deque(maxlen=64)
        self._in_callback = False

    def _now(self) -> float:
        if asyncio.get_running_loop() is not self._loop:
            raise DisplacementRejected("one foreground event loop required")
        if self._in_callback:
            raise DisplacementRejected("provider callback cannot reenter coordination")
        now = self._clock()
        if (type(now) not in (int, float) or not math.isfinite(now)
            or now < self._last_time):
            raise DisplacementRejected("finite monotonic clock required")
        self._last_time = now
        return now

    def _record(self, event: str, request: ModelRequest | None = None) -> None:
        self._receipts.append(RuntimeReceipt(event, request.generation if request else 0))

    @property
    def receipts(self) -> tuple[RuntimeReceipt, ...]:
        return tuple(self._receipts)

    @property
    def active(self) -> ModelRequest | None:
        return self._active.request if self._active else None

    @property
    def pending(self) -> ModelRequest | None:
        return self._pending

    def admit(
        self, context: CognitionContext, level: str, priority: int,
        deadline: float, wait_budget: float, provenance: Provenance,
    ) -> ModelRequest:
        now = self._now()
        if (context != self.context or not isinstance(context, CognitionContext)
            or level not in ("L1", "L2") or type(priority) is not int or priority < 0
            or any(type(x) not in (int, float) or not math.isfinite(x)
                   for x in (deadline, wait_budget))
            or deadline <= now or wait_budget <= 0
            or not isinstance(provenance, Provenance) or provenance.source != self._source):
            raise DisplacementRejected("current source-scoped bounded admission required")
        self._generation += 1
        request = ModelRequest(
            f"s60-{self._identity}-{self._generation}", self._generation, context, level,
            priority, deadline, wait_budget, provenance,
        )
        # Only the latest owner-issued admission can be consumed; no replay set.
        self._issued = request
        return request

    def submit(self, request: ModelRequest) -> None:
        now = self._now()
        if request is not self._issued or request is None:
            raise DisplacementRejected("forged, superseded or consumed admission")
        self._issued = None
        if request.context != self.context or request.deadline <= now:
            self._record("MODEL_SKIPPED", request)
            return
        self._expire(now)
        if self._active is None:
            self._begin(request)
            return
        incumbent = self._pending or self._active.request
        if request.priority < incumbent.priority:
            self._record("MODEL_SKIPPED", request)
            return
        if self._pending:
            self._record("PENDING_REPLACED", self._pending)
        self._pending = request
        self._pending_until = min(request.deadline, now + request.wait_budget)
        self._displace()
        self._record("BACKEND_BUSY", request)

    def _begin(self, request: ModelRequest) -> None:
        fence = L2InterruptionFence()
        ticket = fence.start(request.work_id, request.context)
        lease = _Lease(request, fence, ticket)
        self._active = lease
        self._in_callback = True
        # Recorded only at the actual callable invocation, not queue admission.
        self._record("NEW_REQUEST_STARTED", request)
        try:
            future = self._start(request)
            if not isinstance(future, asyncio.Future):
                raise DisplacementRejected("provider must return its completion Future")
            if future is self._last_future or future.get_loop() is not self._loop:
                raise DisplacementRejected("foreign or reused provider Future")
            self._last_future = future
            lease.future = future
        except (Exception, asyncio.CancelledError):
            lease.failure_observed = True
            self._record("PROVIDER_UNCONFIRMED", request)
        finally:
            self._in_callback = False

    def _displace(self) -> None:
        lease = self._active
        if lease is None or lease.fence.stage.value != "RUNNING":
            return
        # Atomic logical fence FIRST, including if cancel raises or completes.
        lease.fence.request_interrupt(lease.ticket)
        self._record("DISPLACED", lease.request)
        self._record("HOST_CANCEL_REQUESTED", lease.request)
        self._in_callback = True
        try:
            self._cancel(lease.request)
        except (Exception, asyncio.CancelledError):
            self._record("HOST_CANCEL_FAILED", lease.request)
        else:
            self._record("HOST_CANCEL_UNCONFIRMED", lease.request)
        finally:
            self._in_callback = False

    def observe(self, context: CognitionContext) -> None:
        self._now()
        if not isinstance(context, CognitionContext):
            raise DisplacementRejected("typed context required")
        old = self.context
        if (context.session_id == old.session_id and any(
            new < previous for new, previous in zip(
                (context.world_seq, context.intent_revision, context.retained_revision),
                (old.world_seq, old.intent_revision, old.retained_revision), strict=True,
            )
        )):
            raise DisplacementRejected("causal revision regressed")
        if context == old:
            return
        self.context = context
        self._issued = None
        if self._pending:
            self._record("STALE_REJECTED", self._pending)
            self._pending = None
        if self._active:
            self._active.fence.observe(context)
            self._displace()

    def _expire(self, now: float) -> None:
        if self._pending and now >= self._pending_until:
            self._record("PENDING_EXPIRED", self._pending)
            self._record("CANCEL_UNCONFIRMED_BACKEND_BUSY", self._pending)
            self._record("MODEL_SKIPPED", self._pending)
            self._pending = None

    def tick(self) -> CognitiveResult | None:
        """Service completion/expiry once. Never await backend or retry errors."""
        now = self._now()
        self._expire(now)
        lease = self._active
        if lease is None:
            return None
        if now >= lease.request.deadline:
            self._displace()
        if lease.future is None or not lease.future.done():
            return None
        future = lease.future
        if future.cancelled():
            if not lease.failure_observed:
                self._record("HOST_TASK_CANCELLED_BACKEND_UNCONFIRMED", lease.request)
            lease.failure_observed = True
            return None
        error = future.exception()  # consume exceptions: no orphan warning
        if error is not None:
            if not lease.failure_observed:
                self._record("PROVIDER_UNCONFIRMED", lease.request)
            lease.failure_observed = True
            return None
        value = future.result()
        self._record("BACKEND_COMPLETION_OBSERVED", lease.request)
        result = None
        try:
            if now >= lease.request.deadline:
                self._displace()
            lease.fence.accept_l2_result(lease.ticket, self.context)
        except InterruptRejected:
            self._record("STALE_REJECTED", lease.request)
        else:
            result = CognitiveResult(lease.request, value)
        # This releases only our naturally completed provider lease. Never call
        # S48 retire_interrupted, forge its ACK, or claim independent slot idle.
        self._active = None
        if self._pending:
            pending, self._pending = self._pending, None
            self._begin(pending)
        return result

    async def run_l0(self, callback: Callable[[], Awaitable[Any]]) -> Any:
        """Independent path, even with busy/failed/no model. UNKNOWN stays UNKNOWN."""
        if not callable(callback):
            raise DisplacementRejected("L0 callback required")
        value = await callback()
        self._record("L0_COMPLETED")
        return value

    async def urgent_l0(
        self, context: CognitionContext, callback: Callable[[], Awaitable[None]],
    ) -> UrgentL0Receipt:
        self.observe(context)
        request = self.active
        self._displace()
        await self.run_l0(callback)
        return UrgentL0Receipt(
            request.work_id if request else "", context.world_seq, True, False, False,
        )
