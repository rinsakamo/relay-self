"""Cognitive Task / CPU Profile Selection v0.1 (Issue #835).

Pure read-only checks layered on #829's CognitiveTask/select_profile.
Never owns Goal/Question/Intent, attests GPU availability, performs inference,
installs L0 rules, preempts L2, retries, or issues an Action.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum

from relay_self.common_io import (
    CognitiveTask,
    CommonEnvelope,
    Profile,
    ProfileDecision,
    ScopeRef,
    TaskRequirement,
    select_profile,
)
from relay_self.provenance import Provenance
from relay_self.relay_engine import BoundedChoice, DecisionStatus
from relay_self.three_self_present import PresentFrame


class ProfileContractError(ValueError):
    """Malformed task binding, resource estimate or decision owner input."""


class OriginKind(str, Enum):
    QUESTION = "QUESTION"
    GOAL = "GOAL"
    INTENT = "INTENT"


class GPUState(str, Enum):
    FREE = "FREE"
    BUSY_L2 = "BUSY_L2"
    BUSY_OTHER = "BUSY_OTHER"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class TaskOrigin:
    kind: OriginKind
    ref: str
    owner_revision: int

    def __post_init__(self) -> None:
        if not isinstance(self.kind, OriginKind):
            raise ProfileContractError("invalid task origin kind")
        _text("origin ref", self.ref)
        _nonnegative("owner revision", self.owner_revision)


@dataclass(frozen=True, slots=True)
class BoundCognitiveTask:
    """One compute task bound to a *previously active* Present owner referent."""

    task: CognitiveTask
    origin: TaskOrigin
    present_revision: int
    schema_registry_revision: int

    def __post_init__(self) -> None:
        if not isinstance(self.task, CognitiveTask) or not isinstance(
            self.origin, TaskOrigin
        ):
            raise ProfileContractError("binding must carry typed task and origin")
        _nonnegative("Present revision", self.present_revision)
        _nonnegative("Schema registry revision", self.schema_registry_revision)
        if self.origin.kind is OriginKind.QUESTION:
            if self.task.question_ref != self.origin.ref or self.task.intent_ref is not None:
                raise ProfileContractError("Question task origin mismatched")
        elif self.origin.kind is OriginKind.INTENT:
            if self.task.intent_ref != self.origin.ref or self.task.question_ref is not None:
                raise ProfileContractError("Intent task origin mismatched")
        elif self.task.question_ref is not None or self.task.intent_ref is not None:
            raise ProfileContractError("Goal origin must remain separate from task's refs")


def _active_refs(present: PresentFrame, kind: OriginKind) -> tuple[str, ...]:
    return {
        OriginKind.QUESTION: present.active_question_refs,
        OriginKind.GOAL: present.active_goal_refs,
        OriginKind.INTENT: present.active_intent_refs,
    }[kind]


def bind_present_task(
    *,
    present: PresentFrame,
    envelope: CommonEnvelope,
    origin: TaskOrigin,
    task_ref: str,
    requirement: TaskRequirement,
    generation: int,
    deadline_ns: int,
    choices: tuple[BoundedChoice, ...] = (),
) -> BoundCognitiveTask:
    """Build the existing #829 CognitiveTask without adopting a Goal or Intent."""
    if not isinstance(present, PresentFrame) or not isinstance(origin, TaskOrigin):
        raise ProfileContractError("Present and origin must be typed")
    if not isinstance(envelope, CommonEnvelope) or envelope.kind != "COGNITIVE_TASK":
        raise ProfileContractError("task requires COGNITIVE_TASK envelope")
    if envelope.scope != present.three_self.scope:
        raise ProfileContractError("foreign scope for Present-origin task")
    if origin.ref not in _active_refs(present, origin.kind):
        raise ProfileContractError("origin is not active in the supplied Present")
    if envelope.received_at is None:
        raise ProfileContractError("task needs a monotonic host reception time")
    if deadline_ns <= envelope.received_at.value:
        raise ProfileContractError("deadline must follow task reception")
    task = CognitiveTask(
        envelope=envelope,
        task_ref=task_ref,
        requirement=requirement,
        source_revision_refs=present.three_self.source_revision_refs,
        deadline_ns=deadline_ns,
        generation=generation,
        choices=choices,
        question_ref=origin.ref if origin.kind is OriginKind.QUESTION else None,
        intent_ref=origin.ref if origin.kind is OriginKind.INTENT else None,
    )
    return BoundCognitiveTask(
        task=task,
        origin=origin,
        present_revision=present.frame_revision,
        schema_registry_revision=present.registry_revision,
    )


@dataclass(frozen=True, slots=True)
class ProfileCostEstimate:
    """Owner-supplied conservative budget estimate, NOT a measured guarantee."""

    profile: Profile
    estimated_duration_ns: int
    required_vram_mib: int
    prompt_tokens: int
    output_tokens: int
    context_limit_tokens: int
    provenance: Provenance
    installed_l0_rule_ref: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.profile, Profile) or self.profile is Profile.DEFER:
            raise ProfileContractError("estimate requires L0/L1/L2")
        _positive("estimated duration", self.estimated_duration_ns)
        for name in (
            "required_vram_mib", "prompt_tokens", "output_tokens",
            "context_limit_tokens",
        ):
            _nonnegative(name, getattr(self, name))
        if not isinstance(self.provenance, Provenance):
            raise ProfileContractError("estimate needs provenance")
        if self.profile is Profile.L0:
            if self.required_vram_mib != 0 or self.installed_l0_rule_ref is None:
                raise ProfileContractError("L0 must use a referenced installed CPU rule")
            _text("installed_l0_rule_ref", self.installed_l0_rule_ref)
            if self.prompt_tokens or self.output_tokens:
                raise ProfileContractError("L0 must not depend on model token generation")
        elif self.installed_l0_rule_ref is not None:
            raise ProfileContractError("L1/L2 cannot install a CPU rule")
        elif self.required_vram_mib <= 0:
            raise ProfileContractError("v0.1 L1/L2 require a positive GPU estimate")


@dataclass(frozen=True, slots=True)
class ResourceReadout:
    """A stale-fenced input supplied by an existing owner, never a hardware grant."""

    scope: ScopeRef
    revision: int
    captured_at_ns: int
    expires_at_ns: int
    provenance: Provenance
    cpu_l0_ready: bool
    installed_l0_rule_refs: frozenset[str]
    l1_backend_ready: bool
    l2_backend_ready: bool
    gpu_state: GPUState
    available_vram_mib: int
    gpu_l2_owner_task_ref: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.scope, ScopeRef):
            raise ProfileContractError("resource readout requires Self/world scope")
        for name in ("revision", "captured_at_ns", "expires_at_ns", "available_vram_mib"):
            _nonnegative(name, getattr(self, name))
        if self.expires_at_ns <= self.captured_at_ns:
            raise ProfileContractError("resource readout expiry must follow capture")
        if not isinstance(self.provenance, Provenance):
            raise ProfileContractError("resource readout needs provenance")
        if not isinstance(self.installed_l0_rule_refs, frozenset) or any(
            not isinstance(r, str) or not r.strip()
            for r in self.installed_l0_rule_refs
        ):
            raise ProfileContractError("installed CPU rules must be explicit refs")
        for key in ("cpu_l0_ready", "l1_backend_ready", "l2_backend_ready"):
            if not isinstance(getattr(self, key), bool):
                raise ProfileContractError("backend readiness must be bool")
        if not isinstance(self.gpu_state, GPUState):
            raise ProfileContractError("invalid GPU state")
        if self.gpu_state is GPUState.BUSY_L2:
            _text("gpu_l2_owner_task_ref", self.gpu_l2_owner_task_ref)
        elif self.gpu_l2_owner_task_ref is not None:
            raise ProfileContractError("non-L2-busy state cannot claim L2 owner")


@dataclass(frozen=True, slots=True)
class ProfileRoute:
    """CPU routing decision; selected does not mean compute or Action admitted."""

    binding: BoundCognitiveTask
    decision: ProfileDecision
    resource_revision: int
    cost_provenance: Provenance | None
    preemption_target_task_ref: str | None = None

    @property
    def selected(self) -> Profile:
        return self.decision.selected


_PROFILE_FOR_REQUIREMENT = {
    TaskRequirement.FAST_REACTION: Profile.L0,
    TaskRequirement.SELECT_FINITE: Profile.L1,
    TaskRequirement.OPEN_REASONING: Profile.L2,
}


def route_bound_task(
    binding: BoundCognitiveTask,
    *,
    present: PresentFrame,
    scope: ScopeRef,
    current_source_revision_refs: tuple[str, ...],
    current_owner_revision: int,
    current_present_revision: int,
    current_registry_revision: int,
    current_task_generation: int,
    resource: ResourceReadout,
    current_resource_revision: int,
    estimates: tuple[ProfileCostEstimate, ...],
    now_ns: int,
) -> ProfileRoute:
    """Check one task against current owner frames and CPU cost/scope predicates.

    Reuses #829 select_profile. Resource flags/estimates are NOT authentic
    hardware admission; #828/05 must verify actual L2 release before L1 runs.
    """
    if not isinstance(binding, BoundCognitiveTask) or not isinstance(
        present, PresentFrame
    ) or not isinstance(scope, ScopeRef) or not isinstance(resource, ResourceReadout):
        raise ProfileContractError("invalid routing input")
    for name, value in (
        ("now_ns", now_ns),
        ("current_owner_revision", current_owner_revision),
        ("current_present_revision", current_present_revision),
        ("current_registry_revision", current_registry_revision),
        ("current_task_generation", current_task_generation),
        ("current_resource_revision", current_resource_revision),
    ):
        _nonnegative(name, value)
    if not isinstance(estimates, tuple) or any(
        not isinstance(estimate, ProfileCostEstimate) for estimate in estimates
    ):
        raise ProfileContractError("estimates must be ProfileCostEstimate tuple")
    if len({estimate.profile for estimate in estimates}) != len(estimates):
        raise ProfileContractError("duplicate profile estimate")

    task = binding.task

    def defer(reason: str, *, cost: ProfileCostEstimate | None = None,
              preempt_target: str | None = None) -> ProfileRoute:
        base = select_profile(
            task, scope=scope,
            current_source_revision_refs=current_source_revision_refs,
            now_ns=now_ns,
        )
        return ProfileRoute(
            binding=binding,
            decision=replace(base, selected=Profile.DEFER, reason=reason,
                             resource_admission="NOT_REQUESTED"),
            resource_revision=resource.revision,
            cost_provenance=cost.provenance if cost is not None else None,
            preemption_target_task_ref=preempt_target,
        )

    if task.envelope.scope != scope or present.three_self.scope != scope:
        return defer("FOREIGN_SCOPE")
    if task.source_revision_refs != current_source_revision_refs or (
        present.three_self.source_revision_refs != current_source_revision_refs
    ):
        return defer("STALE_SOURCE")
    if binding.present_revision != present.frame_revision or (
        present.frame_revision != current_present_revision
    ):
        return defer("STALE_PRESENT")
    if binding.schema_registry_revision != present.registry_revision or (
        present.registry_revision != current_registry_revision
    ):
        return defer("STALE_SCHEMA_REGISTRY")
    if binding.origin.owner_revision != current_owner_revision:
        return defer("STALE_OWNER")
    if task.generation != current_task_generation:
        return defer("STALE_GENERATION")
    if binding.origin.ref not in _active_refs(present, binding.origin.kind):
        return defer("REVOKED_ORIGIN")
    if task.envelope.received_at is None or (
        now_ns < task.envelope.received_at.value
    ):
        return defer("INVALID_HOST_CLOCK")
    if now_ns >= task.deadline_ns:
        return defer("DEADLINE_EXPIRED")
    if resource.scope != scope:
        return defer("FOREIGN_RESOURCE_SCOPE")
    if resource.revision != current_resource_revision or (
        now_ns < resource.captured_at_ns or now_ns >= resource.expires_at_ns
    ):
        return defer("STALE_RESOURCE")

    profile = _PROFILE_FOR_REQUIREMENT[task.requirement]
    cost = next((x for x in estimates if x.profile is profile), None)
    if cost is None:
        return defer("NO_COST_ESTIMATE")
    # Fail closed if estimated work ends at or after the deadline.
    if now_ns + cost.estimated_duration_ns >= task.deadline_ns:
        return defer("INSUFFICIENT_SLACK", cost=cost)
    if profile in (Profile.L1, Profile.L2):
        if cost.context_limit_tokens == 0 or (
            cost.prompt_tokens + cost.output_tokens > cost.context_limit_tokens
        ):
            return defer("CONTEXT_OVERFLOW", cost=cost)

    ready = False
    reason = "UNAVAILABLE"
    preempt_target = None
    if profile is Profile.L0:
        ready = resource.cpu_l0_ready and (
            cost.installed_l0_rule_ref in resource.installed_l0_rule_refs
        )
        reason = "CPU_RULE_NOT_INSTALLED_OR_READY"
    else:
        backend_ready = (
            resource.l1_backend_ready if profile is Profile.L1
            else resource.l2_backend_ready
        )
        if not backend_ready:
            reason = "BACKEND_UNAVAILABLE"
        elif resource.gpu_state is GPUState.UNKNOWN:
            reason = "GPU_UNKNOWN"
        elif resource.gpu_state is GPUState.BUSY_L2 and profile is Profile.L1:
            reason = "L2_PREEMPTION_REQUIRED"
            preempt_target = resource.gpu_l2_owner_task_ref
        elif resource.gpu_state is not GPUState.FREE:
            reason = "GPU_BUSY"
        elif resource.available_vram_mib < cost.required_vram_mib:
            reason = "VRAM_INSUFFICIENT"
        else:
            ready = True

    if not ready:
        return defer(reason, cost=cost, preempt_target=preempt_target)
    chosen = select_profile(
        task,
        scope=scope,
        current_source_revision_refs=current_source_revision_refs,
        now_ns=now_ns,
        l0_rule_ready=profile is Profile.L0,
        l1_available=profile is Profile.L1,
        l2_available=profile is Profile.L2,
    )
    if chosen.selected is not profile:
        return defer("PROFILE_ROUTING_MISMATCH", cost=cost)
    return ProfileRoute(
        binding=binding, decision=chosen, resource_revision=resource.revision,
        cost_provenance=cost.provenance,
    )


@dataclass(frozen=True, slots=True)
class FiniteAbstentionReceipt:
    """One unresolved L1 response; does not authorize fallback or physical Action."""

    task_ref: str
    generation: int
    status: DecisionStatus
    reason: str
    provenance: Provenance

    def __post_init__(self) -> None:
        _text("task_ref", self.task_ref)
        _nonnegative("generation", self.generation)
        if self.status is not DecisionStatus.UNRESOLVED:
            raise ProfileContractError("finite abstention must be UNRESOLVED")
        _text("reason", self.reason)
        if not isinstance(self.provenance, Provenance):
            raise ProfileContractError("abstention must preserve provenance")


def note_l1_abstention(
    route: ProfileRoute, *, reason: str, provenance: Provenance
) -> FiniteAbstentionReceipt:
    """Convert existing RelayEngine UNRESOLVED into a non-Action trace."""
    if not isinstance(route, ProfileRoute) or route.selected is not Profile.L1:
        raise ProfileContractError("L1 abstention requires selected bounded task")
    return FiniteAbstentionReceipt(
        task_ref=route.binding.task.task_ref,
        generation=route.binding.task.generation,
        status=DecisionStatus.UNRESOLVED,
        reason=reason,
        provenance=provenance,
    )


def _text(name: str, value: object) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ProfileContractError(f"{name} must be nonempty text")


def _nonnegative(name: str, value: object) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ProfileContractError(f"{name} must be nonnegative integer")


def _positive(name: str, value: object) -> None:
    _nonnegative(name, value)
    if value == 0:
        raise ProfileContractError(f"{name} must be positive")
