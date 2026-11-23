"""#860 Stage21: shared single-slot llama.cpp GPU-work ownership, per Self.

The external model process remains resident. A timed-out HTTP client or a
cancelled Python coroutine is NOT backend cancellation. Only the natural
provider call returning *and* a fresh n_parallel=1 /slots idle readback can
terminate an admitted inference in this bounded exclusive lane. One
unresponsive backend HOLDS GPU admission, not the physical World or peers'
CPU cognition. Operator must prevent any bypass clients to this endpoint.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import threading
import urllib.error
import urllib.request
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import asdict, dataclass
from urllib.parse import urlsplit

from adapters.llama_cpp.relay_engine import LlamaCppRelayProvider
from relay_self.persistent_cognition import Memory
from relay_self.relay_engine import (
    BoundedChoiceRequest,
    CognitionMode,
    OpenCognitionRequest,
    ProviderDecision,
    ProviderExpression,
)
from relay_self.resident_cognitive_work_owner_dev import (
    ResidentCognitiveWorkOwner,
)


class ResidentGpuLaneError(RuntimeError):
    """Inference not owned, backend possibly active, or stale Self epoch."""


@dataclass(frozen=True, slots=True)
class LlamaSlotIdleReceipt:
    backend_ref: str
    slot_id: int
    n_slots: int
    is_processing: bool
    source_ref: str
    request_issue_authorized: bool = False


@dataclass(frozen=True, slots=True)
class ResidentInferenceTicket:
    self_id: str
    work_ref: str
    request_id: str
    mode: CognitionMode
    self_epoch: int
    native_session_id: str
    world_epoch: int
    backend_ref: str
    action_issue_authorized: bool = False
    # Immutable deny-only job purpose; never grants model or Action authority.
    purpose: str = "general"


@dataclass(frozen=True, slots=True)
class ResidentInferenceRetirement:
    self_id: str
    native_session_id: str
    world_epoch: int
    self_epoch: int
    submitted_refs: tuple[str, ...]
    actually_completed_refs: tuple[str, ...]
    queued_cancelled_refs: tuple[str, ...]
    backend_idle_checked: bool
    vram_released: bool = False
    llm_model_unloaded: bool = False
    physical_action_authorized: bool = False


@dataclass(slots=True)
class _Job:
    ticket: ResidentInferenceTicket
    request: BoundedChoiceRequest | OpenCognitionRequest
    request_sha256: str
    future: Future[ProviderDecision | ProviderExpression] | None = None
    terminal_slot_idle: bool = False
    result_adopted: bool = False
    question_adoption_state: str = "unused"
    question_adoption_binding: tuple | None = None


def _request_sha256(
    request: BoundedChoiceRequest | OpenCognitionRequest, mode: CognitionMode,
) -> str:
    """Bind every request field, its concrete type and the submitted mode."""
    payload = {"type": type(request).__name__, "mode": mode.value,
               "request": asdict(request)}
    return hashlib.sha256(json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")).hexdigest()


def _require_local_url(endpoint: str) -> tuple[str, int]:
    parsed = urlsplit(endpoint)
    if (
        parsed.scheme != "http"
        or parsed.hostname not in ("127.0.0.1", "localhost")
        or parsed.username is not None or parsed.password is not None
        or not parsed.port or parsed.query or parsed.fragment
    ):
        raise ResidentGpuLaneError(
            "owned inference must use explicit loopback http host:port"
        )
    return parsed.hostname, parsed.port


class LlamaCppSingleSlotWitness:
    """Inspect an exclusive local llama-server /slots (not VRAM residency).

    The endpoint's process owner and exclusivity are operator requirements.
    A busy slot, 2+ slots, malformed response or failed HTTP probe is HOLD.
    """

    def __init__(self, *, provider: LlamaCppRelayProvider,
                 backend_ref: str, timeout_s: float = 2.0) -> None:
        if not isinstance(provider, LlamaCppRelayProvider):
            raise ResidentGpuLaneError("actual llama.cpp provider required")
        if (
            type(backend_ref) is not str or not backend_ref.strip()
            or type(timeout_s) not in (int, float) or not 0 < timeout_s <= 10
        ):
            raise ResidentGpuLaneError("bounded backend witness identity required")
        host, port = _require_local_url(provider.endpoint)
        if provider.systemone_endpoint is not None:
            other_host, other_port = _require_local_url(provider.systemone_endpoint)
            if (host, port) != (other_host, other_port):
                raise ResidentGpuLaneError(
                    "L1 and L2 on different backends require separate owners"
                )
        self.backend_ref = backend_ref
        self.endpoint = f"http://{host}:{port}/slots"
        self.timeout_s = float(timeout_s)

    def require_idle(self) -> LlamaSlotIdleReceipt:
        request = urllib.request.Request(
            self.endpoint, method="GET",
            headers={"Accept": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_s) as response:
                if response.status != 200:
                    raise ResidentGpuLaneError("llama slot readback is not HTTP 200")
                raw = response.read(1024 * 1024)
            obj = json.loads(raw)
        except (OSError, ValueError, urllib.error.URLError) as exc:
            raise ResidentGpuLaneError(
                "backend slot owner unavailable or malformed"
            ) from exc
        if (
            type(obj) is not list or len(obj) != 1
            or type(obj[0]) is not dict or type(obj[0].get("id")) is not int
            or obj[0]["id"] != 0
            or type(obj[0].get("is_processing")) is not bool
            or obj[0]["is_processing"] is not False
        ):
            raise ResidentGpuLaneError(
                "exclusive backend n_parallel=1 idle slot unverified"
            )
        return LlamaSlotIdleReceipt(
            self.backend_ref, 0, 1, False,
            f"{self.backend_ref}:GET /slots:id=0:idle",
        )


class ResidentLlamaInferenceLane:
    """One serialized provider call at a time, with backend-side idle check.

    The actual provider thread is not canceled when Self logs off; it stays
    owned until finished and /slots confirms idle. If a timeout leaves llama
    working, only that Self is quarantined but the one shared GPU lane stays
    unavailable to other Self, whereas their CPU/World Actions continue.
    """

    def __init__(
        self, *, provider: LlamaCppRelayProvider,
        cognitive_work: ResidentCognitiveWorkOwner,
        witness: LlamaCppSingleSlotWitness,
    ) -> None:
        if (
            not isinstance(provider, LlamaCppRelayProvider)
            or not isinstance(cognitive_work, ResidentCognitiveWorkOwner)
            or not isinstance(witness, LlamaCppSingleSlotWitness)
            or _require_local_url(provider.endpoint)
            != _require_local_url(witness.endpoint)
        ):
            raise ResidentGpuLaneError("one original cognitive owner and local backend")
        self.provider = provider
        self.cognitive_work = cognitive_work
        self.witness = witness
        self.backend_ref = witness.backend_ref
        self._lock = threading.RLock()
        self._pool = ThreadPoolExecutor(
            max_workers=1, thread_name_prefix="relay-self-shared-llama",
        )
        self._jobs: dict[tuple[str, str], _Job] = {}
        self._fenced: set[str] = set()
        self._retired: dict[str, ResidentInferenceRetirement] = {}
        self._uncertain = False

    @property
    def uncertain(self) -> bool:
        with self._lock:
            return self._uncertain

    def bind_login(self, self_id: str) -> None:
        with self.cognitive_work.lock, self._lock:
            # The original cognition owner MUST have a current verified
            # native session; no stale work from the prior login may exist.
            self.cognitive_work.current_scope(self_id)
            if any(
                sid == self_id and job.future is not None
                and not job.future.done()
                for (sid, _), job in self._jobs.items()
            ):
                raise ResidentGpuLaneError("old backend task not retired")
            if self._uncertain:
                raise ResidentGpuLaneError("backend generation remains uncertain")
            self._fenced.discard(self_id)
            self._retired.pop(self_id, None)

    def submit(
        self, self_id: str, *, work_ref: str,
        request: BoundedChoiceRequest | OpenCognitionRequest,
        mode: CognitionMode,
        purpose: str = "general",
    ) -> ResidentInferenceTicket:
        if (
            type(work_ref) is not str or not work_ref.strip()
            or not isinstance(mode, CognitionMode)
            or not isinstance(request, (BoundedChoiceRequest, OpenCognitionRequest))
            or (mode is CognitionMode.OPEN) != isinstance(request, OpenCognitionRequest)
            or type(purpose) is not str
            or purpose not in ("general", "original_rejoin_question")
            or (purpose == "original_rejoin_question" and mode is not CognitionMode.BOUNDED)
        ):
            raise ResidentGpuLaneError("typed L1/L2 request, purpose and work reference required")
        with self.cognitive_work.lock, self._lock:
            scope = self.cognitive_work.current_scope(self_id)
            if self_id in self._fenced or self._uncertain:
                raise ResidentGpuLaneError("Self or GPU lane is fenced")
            key = (self_id, work_ref)
            if key in self._jobs:
                raise ResidentGpuLaneError("duplicate work reference; never replay")
            ticket = ResidentInferenceTicket(
                self_id, work_ref, request.request_id, mode,
                scope[0], scope[1], scope[2], self.backend_ref,
                purpose=purpose,
            )
            job = _Job(ticket, request, _request_sha256(request, mode))
            self._jobs[key] = job
            try:
                job.future = self._pool.submit(self._execute, key, request)
            except BaseException:
                del self._jobs[key]
                raise
            return ticket

    def _execute(
        self, key: tuple[str, str],
        request: BoundedChoiceRequest | OpenCognitionRequest,
    ) -> ProviderDecision | ProviderExpression:
        job = self._jobs[key]
        try:
            with self._lock:
                if self._uncertain:
                    raise ResidentGpuLaneError("prior backend slot not retired")
            # Owned singleton backend, first show no external holder.
            self.witness.require_idle()
            try:
                answer = self.provider(request, mode=job.ticket.mode)
            except BaseException:
                # Even after provider timeout, the backend may still
                # generate tokens. A new idle probe is REQUIRED.
                self.witness.require_idle()
                with self._lock:
                    job.terminal_slot_idle = True
                raise
            self.witness.require_idle()
            with self._lock:
                job.terminal_slot_idle = True
            return answer
        except BaseException:
            with self._lock:
                if not job.terminal_slot_idle:
                    self._uncertain = True
            raise

    async def await_result(
        self, ticket: ResidentInferenceTicket, *, timeout_s: float = 60.0,
    ) -> ProviderDecision | ProviderExpression:
        """Wait for true thread completion without disconnecting the model."""
        if type(timeout_s) not in (int, float) or not 0 < timeout_s <= 120:
            raise ResidentGpuLaneError("bounded result wait required")
        with self.cognitive_work.lock, self._lock:
            job = self._require_current_job(ticket)
            if job.future is None:
                raise ResidentGpuLaneError("inference not actually submitted")
            future = job.future
        try:
            await asyncio.wait_for(
                asyncio.shield(asyncio.wrap_future(future)),
                timeout=float(timeout_s),
            )
        except TimeoutError as exc:
            raise ResidentGpuLaneError(
                "result wait elapsed; backend may still be generating"
            ) from exc
        return self.result(ticket)

    def result(
        self, ticket: ResidentInferenceTicket,
    ) -> ProviderDecision | ProviderExpression:
        with self.cognitive_work.lock, self._lock:
            job = self._require_current_job(ticket)
            if job.future is None or not job.future.done() or not job.terminal_slot_idle:
                raise ResidentGpuLaneError("backend execution not verifiably terminal")
            self._require_current_scope(ticket)
            if self._uncertain:
                raise ResidentGpuLaneError("shared GPU backend uncertain")
            return job.future.result()

    def adopt_memory(
        self, ticket: ResidentInferenceTicket, memory: Memory,
    ) -> None:
        with self.cognitive_work.lock, self._lock:
            job = self._require_current_job(ticket)
            if (
                # The original Question issuer marks this immutable purpose
                # atomically at submit. ADOPT/HOLD/DECLINE/UNRESOLVED can
                # never be reinterpreted as a generic Memory result.
                job.ticket.purpose != "general"
                or job.question_adoption_state != "unused"
                or job.question_adoption_binding is not None
                or job.result_adopted or job.future is None
                or not job.future.done() or not job.terminal_slot_idle
                or job.future.cancelled() or self._uncertain
            ):
                raise ResidentGpuLaneError("inference result not adoptable")
            self._require_current_scope(ticket)
            # Failed model calls cannot become synthetic memories.
            job.future.result()
            self.cognitive_work.owners[ticket.self_id].retain_memory(memory)
            job.result_adopted = True

    def verify_submitted_bounded_request(
        self, ticket: ResidentInferenceTicket, expected: BoundedChoiceRequest,
    ) -> ProviderDecision:
        """Read the completed job's result only if its actual request matches.

        This association does not authorize adoption or any state change.
        """
        with self.cognitive_work.lock, self._lock:
            result = self.result(ticket)
            job = self._require_current_job(ticket)
            if (
                ticket.mode is not CognitionMode.BOUNDED
                or ticket.backend_ref != self.backend_ref
                or type(expected) is not BoundedChoiceRequest
                or type(job.request) is not BoundedChoiceRequest
                or ticket.request_id != job.request.request_id
                or job.request != expected
                or job.request_sha256 != _request_sha256(expected, ticket.mode)
                or job.request_sha256 != _request_sha256(job.request, ticket.mode)
                or not isinstance(result, ProviderDecision)
            ):
                raise ResidentGpuLaneError("submitted bounded request mismatch")
            return result

    def fence_self(self, self_id: str) -> None:
        """Sync per Self; does not cancel the backend generation thread."""
        with self._lock:
            self._fenced.add(self_id)
            for (sid, _), job in self._jobs.items():
                if sid == self_id and job.future is not None:
                    job.future.cancel()  # only queued jobs can actually cancel

    async def retire_self(
        self, self_id: str, *, timeout_s: float = 5.0,
    ) -> ResidentInferenceRetirement:
        if (
            type(timeout_s) not in (int, float) or not 0 < timeout_s <= 60
        ):
            raise ResidentGpuLaneError("bounded inference retirement deadline required")
        with self.cognitive_work.lock, self._lock:
            if self_id not in self._fenced:
                raise ResidentGpuLaneError("GPU admission must be fenced first")
            relevant = {
                ref: j for (sid, ref), j in self._jobs.items()
                if sid == self_id
            }
            token = self.cognitive_work.quarantined_scope(self_id)
            futures = [j.future for j in relevant.values() if j.future is not None]
        if futures:
            wrapped = [asyncio.wrap_future(f) for f in futures]
            done, pending = await asyncio.wait(wrapped, timeout=float(timeout_s))
            if pending:
                # No async wrapper cancellation: provider thread continues and
                # its source proof cannot be inferred from HTTP client closure.
                raise ResidentGpuLaneError(
                    "llama backend request still active; individual Self HOLD"
                )
            assert all(f.done() for f in done)
        with self.cognitive_work.lock, self._lock:
            if (
                self._uncertain
                or token != self.cognitive_work.quarantined_scope(self_id)
                or any(
                    j.future is None or not j.future.done()
                    or (not j.future.cancelled() and not j.terminal_slot_idle)
                    for j in relevant.values()
                )
            ):
                raise ResidentGpuLaneError("individual backend not qualified idle")
            result = ResidentInferenceRetirement(
                self_id, token[1], token[2], token[0],
                tuple(sorted(relevant)),
                tuple(sorted(ref for ref, j in relevant.items()
                             if j.future is not None and not j.future.cancelled())),
                tuple(sorted(ref for ref, j in relevant.items()
                             if j.future is not None and j.future.cancelled())),
                # If only queued B tasks were cancelled while A executes,
                # B is retired but the SHARED slot is not idle. No global
                # idle claim is allowed until require_world_idle().
                any(j.terminal_slot_idle for j in relevant.values()),
            )
            self._retired[self_id] = result
            return result

    def retired_clean(self, self_id: str) -> bool:
        with self._lock:
            return (
                not self._uncertain and self_id in self._retired
                and self_id in self._fenced
                and all(
                    j.future is not None and j.future.done()
                    and (j.future.cancelled() or j.terminal_slot_idle)
                    for (sid, _), j in self._jobs.items() if sid == self_id
                )
            )

    def verified_retirement(self, self_id: str) -> ResidentInferenceRetirement:
        """Exact actor source proof, not global GPU or VRAM release."""
        with self._lock:
            if not self.retired_clean(self_id):
                raise ResidentGpuLaneError("Self inference retirement not qualified")
            return self._retired[self_id]

    def require_world_idle(self) -> LlamaSlotIdleReceipt:
        with self._lock:
            if self._uncertain or any(
                j.future is not None and not j.future.done()
                for j in self._jobs.values()
            ):
                raise ResidentGpuLaneError("outstanding llama work at World stop")
        return self.witness.require_idle()

    def _require_current_job(self, ticket: ResidentInferenceTicket) -> _Job:
        if not isinstance(ticket, ResidentInferenceTicket):
            raise ResidentGpuLaneError("typed inference ticket required")
        try:
            job = self._jobs[(ticket.self_id, ticket.work_ref)]
        except (KeyError, TypeError) as exc:
            raise ResidentGpuLaneError("unregistered inference work ticket") from exc
        if job.ticket != ticket:
            raise ResidentGpuLaneError("foreign Self/native/epoch inference ticket")
        return job

    def _require_current_scope(self, ticket: ResidentInferenceTicket) -> None:
        if (
            ticket.self_id in self._fenced
            or self.cognitive_work.current_scope(ticket.self_id)
            != (ticket.self_epoch, ticket.native_session_id, ticket.world_epoch)
        ):
            raise ResidentGpuLaneError("late inference result from prior Self epoch")
