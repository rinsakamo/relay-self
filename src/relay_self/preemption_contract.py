"""CPU/GPU preemption v0.1: pure owner-facing proof sequence (Issue #837).

This validates *records supplied by existing owners*; it neither stops llama.cpp
nor measures GPU occupancy, authenticates receipts, grants a GPU lease, or runs L1.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum

from relay_self.cognitive_profile_contract import (
    GPUState,
    ProfileRoute,
)
from relay_self.common_io import (
    CognitionResultReceipt,
    CognitiveTask,
    PreemptionEvent,
    PreemptionPhase,
    PreemptionTrace,
    Profile,
    ProfileDecision,
    ScopeRef,
    TaskRequirement,
    result_is_current,
)
from relay_self.provenance import Provenance


class PreemptionContractError(ValueError):
    """An out-of-order, stale, foreign or incomplete preemption witness."""


@dataclass(frozen=True, slots=True)
class L2ComputeLease:
    """Existing resource owner's lease identity, not permission created here."""

    scope: ScopeRef
    task_ref: str
    generation: int
    lease_ref: str
    backend_instance_ref: str
    gpu_ref: str
    resource_owner_ref: str
    resource_revision: int
    granted_at_ns: int
    provenance: Provenance

    def __post_init__(self) -> None:
        if not isinstance(self.scope, ScopeRef):
            raise PreemptionContractError("L2 lease requires valid scope")
        for name in ("task_ref", "lease_ref", "backend_instance_ref", "gpu_ref",
                     "resource_owner_ref"):
            _text(name, getattr(self, name))
        for name in ("generation", "resource_revision", "granted_at_ns"):
            _nonnegative(name, getattr(self, name))
        _prov("lease provenance", self.provenance)


@dataclass(frozen=True, slots=True)
class OutputFenceReceipt:
    lease_ref: str
    task_ref: str
    generation: int
    result_owner_ref: str
    at_ns: int
    verification_ref: str
    provenance: Provenance
    rejected_generation: bool

    def __post_init__(self) -> None:
        for name in ("lease_ref", "task_ref", "result_owner_ref",
                     "verification_ref"):
            _text(name, getattr(self, name))
        _nonnegative("generation", self.generation)
        _nonnegative("at_ns", self.at_ns)
        _prov("fence provenance", self.provenance)
        _bool("rejected_generation", self.rejected_generation)


@dataclass(frozen=True, slots=True)
class BackendStopReceipt:
    lease_ref: str
    task_ref: str
    generation: int
    backend_instance_ref: str
    at_ns: int
    verification_ref: str
    provenance: Provenance
    stopped_confirmed: bool
    active_request_count: int
    transport_cancelled: bool = False

    def __post_init__(self) -> None:
        for name in ("lease_ref", "task_ref", "backend_instance_ref",
                     "verification_ref"):
            _text(name, getattr(self, name))
        for name in ("generation", "at_ns", "active_request_count"):
            _nonnegative(name, getattr(self, name))
        _prov("backend provenance", self.provenance)
        _bool("stopped_confirmed", self.stopped_confirmed)
        _bool("transport_cancelled", self.transport_cancelled)


@dataclass(frozen=True, slots=True)
class ResourceReleaseReceipt:
    """Observed compute-slot+VRAM state, supplied by existing GPU resource owner."""

    scope: ScopeRef
    released_lease_ref: str
    gpu_ref: str
    resource_owner_ref: str
    resource_revision: int
    at_ns: int
    expires_at_ns: int
    verification_ref: str
    provenance: Provenance
    gpu_state: GPUState
    released_lease_active: bool
    available_vram_mib: int

    def __post_init__(self) -> None:
        if not isinstance(self.scope, ScopeRef):
            raise PreemptionContractError("release scope must be ScopeRef")
        for name in ("released_lease_ref", "gpu_ref", "resource_owner_ref",
                     "verification_ref"):
            _text(name, getattr(self, name))
        for name in ("resource_revision", "at_ns", "expires_at_ns",
                     "available_vram_mib"):
            _nonnegative(name, getattr(self, name))
        if self.expires_at_ns <= self.at_ns:
            raise PreemptionContractError("release readout already expired")
        if not isinstance(self.gpu_state, GPUState):
            raise PreemptionContractError("release requires typed GPU state")
        _bool("released_lease_active", self.released_lease_active)
        _prov("release provenance", self.provenance)


@dataclass(frozen=True, slots=True)
class L1ComputeGrantReceipt:
    """New lease issued by existing resource owner (not minted by this module)."""

    scope: ScopeRef
    task_ref: str
    generation: int
    new_lease_ref: str
    resource_owner_ref: str
    resource_revision: int
    at_ns: int
    verification_ref: str
    provenance: Provenance
    grant_confirmed: bool

    def __post_init__(self) -> None:
        if not isinstance(self.scope, ScopeRef):
            raise PreemptionContractError("grant scope must be ScopeRef")
        for name in ("task_ref", "new_lease_ref", "resource_owner_ref",
                     "verification_ref"):
            _text(name, getattr(self, name))
        for name in ("generation", "resource_revision", "at_ns"):
            _nonnegative(name, getattr(self, name))
        _prov("grant provenance", self.provenance)
        _bool("grant_confirmed", self.grant_confirmed)


class PendingReason(str, Enum):
    STOP_TIMEOUT = "STOP_TIMEOUT"
    RELEASE_UNVERIFIED = "RELEASE_UNVERIFIED"
    OWNER_UNAVAILABLE = "OWNER_UNAVAILABLE"
    L1_DEADLINE_EXPIRED = "L1_DEADLINE_EXPIRED"


@dataclass(frozen=True, slots=True)
class PreemptionPending:
    """Trace-only blocker; never unfences old L2, unblocks L1 or retries."""

    reason: PendingReason
    at_ns: int
    provenance: Provenance

    def __post_init__(self) -> None:
        if not isinstance(self.reason, PendingReason):
            raise PreemptionContractError("invalid pending reason")
        _nonnegative("at_ns", self.at_ns)
        _prov("pending provenance", self.provenance)


@dataclass(frozen=True, slots=True)
class L2PreemptionReview:
    """Immutable evaluation of one L1 demand against one exact L2 lease."""

    trace: PreemptionTrace
    l2_lease: L2ComputeLease
    waiting_l1_route: ProfileRoute
    l1_required_vram_mib: int
    owner_epoch_ref: str
    result_owner_ref: str
    request_at_ns: int
    fence: OutputFenceReceipt | None = None
    backend_stop: BackendStopReceipt | None = None
    release: ResourceReleaseReceipt | None = None
    grant: L1ComputeGrantReceipt | None = None
    pending: tuple[PreemptionPending, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.trace, PreemptionTrace):
            raise PreemptionContractError("missing original PreemptionTrace")
        if self.trace.scope != self.l2_lease.scope:
            raise PreemptionContractError("trace/lease scope mismatch")
        if (self.trace.l2_task_ref != self.l2_lease.task_ref
                or self.trace.l2_generation != self.l2_lease.generation):
            raise PreemptionContractError("trace/lease task identity mismatch")
        if self.trace.l1_task_ref != self.waiting_l1_route.binding.task.task_ref:
            raise PreemptionContractError("trace/L1 task mismatch")
        if self.waiting_l1_route.binding.task.envelope.scope != self.trace.scope:
            raise PreemptionContractError("L1 scope mismatched")
        _text("owner_epoch_ref", self.owner_epoch_ref)
        _text("result_owner_ref", self.result_owner_ref)
        _positive("L1 required VRAM", self.l1_required_vram_mib)
        _nonnegative("request_at_ns", self.request_at_ns)

    @property
    def l2_fenced(self) -> bool:
        return self.trace.output_fenced

    @property
    def l1_admitted(self) -> bool:
        return self.trace.l1_admitted and self.grant is not None


def request_l2_preemption(
    route: ProfileRoute,
    *,
    l2_lease: L2ComputeLease,
    owner_epoch_ref: str,
    result_owner_ref: str,
    current_l1_generation: int,
    current_l2_generation: int,
    current_l1_source_revision_refs: tuple[str, ...],
    current_resource_revision: int,
    l1_required_vram_mib: int,
    now_ns: int,
    provenance: Provenance,
) -> L2PreemptionReview:
    """Start cancelling exact L2 generation; old result gated immediately."""
    if not isinstance(route, ProfileRoute) or not isinstance(l2_lease, L2ComputeLease):
        raise PreemptionContractError("need existing L1 route and L2 lease")
    _text("owner_epoch_ref", owner_epoch_ref)
    _text("result_owner_ref", result_owner_ref)
    _nonnegative("now_ns", now_ns)
    _nonnegative("current_resource_revision", current_resource_revision)
    _prov("preemption request provenance", provenance)
    task = route.binding.task
    if (
        task.requirement is not TaskRequirement.SELECT_FINITE
        or route.selected is not Profile.DEFER
        or route.decision.reason != "L2_PREEMPTION_REQUIRED"
        or route.preemption_target_task_ref != l2_lease.task_ref
        or route.decision.resource_admission != "NOT_REQUESTED"
    ):
        raise PreemptionContractError("L1 demand is not qualified for L2 preemption")
    if task.envelope.scope != l2_lease.scope:
        raise PreemptionContractError("foreign L2 lease scope")
    if task.generation != current_l1_generation or (
        l2_lease.generation != current_l2_generation
    ):
        raise PreemptionContractError("stale task generation")
    if task.source_revision_refs != current_l1_source_revision_refs:
        raise PreemptionContractError("stale L1 source revisions")
    if route.resource_revision != l2_lease.resource_revision or (
        current_resource_revision != l2_lease.resource_revision
    ):
        raise PreemptionContractError("resource revision mismatch")
    if now_ns < l2_lease.granted_at_ns or now_ns >= task.deadline_ns:
        raise PreemptionContractError("invalid L1 deadline or L2 grant time")
    _positive("l1_required_vram_mib", l1_required_vram_mib)

    trace = PreemptionTrace(
        scope=l2_lease.scope,
        l2_task_ref=l2_lease.task_ref,
        l2_generation=l2_lease.generation,
        l1_task_ref=task.task_ref,
    ).append(PreemptionEvent(PreemptionPhase.CANCEL_REQUESTED, now_ns, provenance))
    return L2PreemptionReview(
        trace=trace, l2_lease=l2_lease, waiting_l1_route=route,
        l1_required_vram_mib=l1_required_vram_mib,
        owner_epoch_ref=owner_epoch_ref, result_owner_ref=result_owner_ref,
        request_at_ns=now_ns,
    )


def confirm_output_fence(
    review: L2PreemptionReview, receipt: OutputFenceReceipt,
    *, current_owner_epoch_ref: str,
) -> L2PreemptionReview:
    _epoch(review, current_owner_epoch_ref)
    if not isinstance(receipt, OutputFenceReceipt):
        raise PreemptionContractError("fence must have typed owner receipt")
    if (
        receipt.lease_ref != review.l2_lease.lease_ref
        or receipt.task_ref != review.l2_lease.task_ref
        or receipt.generation != review.l2_lease.generation
        or receipt.result_owner_ref != review.result_owner_ref
        or not receipt.rejected_generation
    ):
        raise PreemptionContractError("fence receipt identity or rejection failed")
    trace = review.trace.append(PreemptionEvent(
        PreemptionPhase.OUTPUT_FENCED, receipt.at_ns,
        receipt.provenance, verification_ref=receipt.verification_ref,
    ))
    return replace(review, trace=trace, fence=receipt)


def confirm_backend_stopped(
    review: L2PreemptionReview, receipt: BackendStopReceipt,
    *, current_owner_epoch_ref: str,
) -> L2PreemptionReview:
    _epoch(review, current_owner_epoch_ref)
    if not isinstance(receipt, BackendStopReceipt):
        raise PreemptionContractError("stop must have backend receipt")
    if (
        receipt.lease_ref != review.l2_lease.lease_ref
        or receipt.task_ref != review.l2_lease.task_ref
        or receipt.generation != review.l2_lease.generation
        or receipt.backend_instance_ref != review.l2_lease.backend_instance_ref
        or not receipt.stopped_confirmed
        or receipt.active_request_count != 0
    ):
        raise PreemptionContractError("backend stop not verified for exact L2 lease")
    trace = review.trace.append(PreemptionEvent(
        PreemptionPhase.BACKEND_STOPPED, receipt.at_ns, receipt.provenance,
        verification_ref=receipt.verification_ref,
    ))
    return replace(review, trace=trace, backend_stop=receipt)


def confirm_resource_released(
    review: L2PreemptionReview, receipt: ResourceReleaseReceipt,
    *, current_owner_epoch_ref: str,
    now_ns: int,
) -> L2PreemptionReview:
    _epoch(review, current_owner_epoch_ref)
    _nonnegative("now_ns", now_ns)
    if not isinstance(receipt, ResourceReleaseReceipt):
        raise PreemptionContractError("release must be resource owner receipt")
    if review.backend_stop is None:
        raise PreemptionContractError("backend stop must precede release")
    if (
        receipt.scope != review.trace.scope
        or receipt.released_lease_ref != review.l2_lease.lease_ref
        or receipt.gpu_ref != review.l2_lease.gpu_ref
        or receipt.resource_owner_ref != review.l2_lease.resource_owner_ref
        or receipt.resource_revision <= review.l2_lease.resource_revision
        or receipt.gpu_state is not GPUState.FREE
        or receipt.released_lease_active
        or receipt.available_vram_mib < review.l1_required_vram_mib
        or now_ns < receipt.at_ns
        or now_ns >= receipt.expires_at_ns
    ):
        raise PreemptionContractError("GPU release is stale, foreign or insufficient")
    trace = review.trace.append(PreemptionEvent(
        PreemptionPhase.RESOURCE_RELEASED, receipt.at_ns, receipt.provenance,
        verification_ref=receipt.verification_ref,
    ))
    return replace(review, trace=trace, release=receipt)


def confirm_l1_compute_grant(
    review: L2PreemptionReview,
    *,
    grant: L1ComputeGrantReceipt,
    fresh_l1_route: ProfileRoute,
    current_owner_epoch_ref: str,
    current_l1_generation: int,
    current_l1_source_revision_refs: tuple[str, ...],
    now_ns: int,
) -> L2PreemptionReview:
    """Only verify owner-issued grant identity; never issue a GPU grant here."""
    _epoch(review, current_owner_epoch_ref)
    _nonnegative("now_ns", now_ns)
    if not isinstance(grant, L1ComputeGrantReceipt) or not isinstance(
        fresh_l1_route, ProfileRoute
    ):
        raise PreemptionContractError("grant needs typed receipt and refreshed L1 route")
    if review.release is None or review.backend_stop is None or review.fence is None:
        raise PreemptionContractError("fence, stop and GPU release required")
    waiting = review.waiting_l1_route.binding
    task = waiting.task
    if (
        fresh_l1_route.selected is not Profile.L1
        or fresh_l1_route.decision.resource_admission != "PENDING"
        or fresh_l1_route.binding != waiting
        or fresh_l1_route.resource_revision != review.release.resource_revision
        or fresh_l1_route.binding.task.source_revision_refs
        != current_l1_source_revision_refs
        or task.generation != current_l1_generation
        or now_ns >= task.deadline_ns
        or now_ns < review.release.at_ns
        or now_ns >= review.release.expires_at_ns
    ):
        raise PreemptionContractError("L1 fresh route, source or deadline invalid")
    if (
        grant.scope != task.envelope.scope
        or grant.task_ref != task.task_ref
        or grant.generation != task.generation
        or grant.new_lease_ref == review.l2_lease.lease_ref
        or grant.resource_owner_ref != review.l2_lease.resource_owner_ref
        or grant.resource_revision != review.release.resource_revision
        or not grant.grant_confirmed
        or grant.at_ns < review.release.at_ns
        or grant.at_ns > now_ns
    ):
        raise PreemptionContractError("L1 grant not verified for new owner-issued lease")
    trace = review.trace.append(PreemptionEvent(
        PreemptionPhase.L1_ADMITTED, grant.at_ns, grant.provenance,
        verification_ref=grant.verification_ref,
    ))
    return replace(review, trace=trace, grant=grant)


def l2_result_is_admissible(
    review: L2PreemptionReview,
    *,
    result: CognitionResultReceipt,
    l2_task: CognitiveTask,
    l2_decision: ProfileDecision,
    current_source_revision_refs: tuple[str, ...],
    now_ns: int,
    compute_admitted: bool,
) -> bool:
    """Reuse #830's result admission; cancelled L2 generation never revives."""
    if (
        l2_task.task_ref != review.l2_lease.task_ref
        or l2_task.generation != review.l2_lease.generation
        or l2_task.envelope.scope != review.l2_lease.scope
    ):
        return False
    return result_is_current(
        result, l2_task, l2_decision,
        scope=review.trace.scope,
        current_source_revision_refs=current_source_revision_refs,
        now_ns=now_ns, compute_admitted=compute_admitted,
        preemption=review.trace,
    )


def note_preemption_pending(
    review: L2PreemptionReview,
    *,
    reason: PendingReason,
    now_ns: int,
    provenance: Provenance,
) -> L2PreemptionReview:
    """Record a blocker, not a fallback or release/response-revival operation."""
    if review.l1_admitted:
        raise PreemptionContractError("cannot add blocker after L1 admission")
    if not isinstance(reason, PendingReason):
        raise PreemptionContractError("invalid pending reason")
    _nonnegative("now_ns", now_ns)
    _prov("pending provenance", provenance)
    earliest = review.pending[-1].at_ns if review.pending else review.trace.events[-1].at_ns
    if now_ns < earliest:
        raise PreemptionContractError("pending event time regressed")
    return replace(
        review, pending=(*review.pending, PreemptionPending(reason, now_ns, provenance)),
    )


def _epoch(review: L2PreemptionReview, epoch_ref: str) -> None:
    if not isinstance(review, L2PreemptionReview):
        raise PreemptionContractError("missing preemption review")
    _text("current_owner_epoch_ref", epoch_ref)
    if epoch_ref != review.owner_epoch_ref:
        raise PreemptionContractError("stale resource owner epoch")


def _text(name: str, value: object) -> None:
    if not isinstance(value, str) or not value.strip():
        raise PreemptionContractError(f"{name} must be nonempty text")


def _nonnegative(name: str, value: object) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise PreemptionContractError(f"{name} must be a nonnegative integer")


def _positive(name: str, value: object) -> None:
    _nonnegative(name, value)
    if value == 0:
        raise PreemptionContractError(f"{name} must be positive")


def _prov(name: str, value: object) -> None:
    if not isinstance(value, Provenance):
        raise PreemptionContractError(f"{name} must be Provenance")


def _bool(name: str, value: object) -> None:
    if not isinstance(value, bool):
        raise PreemptionContractError(f"{name} must be bool")
