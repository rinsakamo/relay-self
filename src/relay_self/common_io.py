"""Common I/O v0.1: pure, owner-neutral admission checks (Issue #829).

These values carry references; they do not authenticate native evidence, schedule
hardware, write memory, select goals, or issue physical Actions.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum

from relay_self.provenance import Provenance
from relay_self.relay_engine import BoundedChoice


class CommonIOError(ValueError):
    """Malformed or inadmissible cross-boundary data."""


class Clock(str, Enum):
    HOST_MONOTONIC_NS = "host_monotonic_ns"
    WORLD_TICK = "world_tick"
    WALL_MS = "wall_ms"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class ClockStamp:
    domain: Clock
    value: int | None

    def __post_init__(self) -> None:
        if not isinstance(self.domain, Clock):
            raise CommonIOError("unknown clock domain")
        if self.domain is Clock.UNKNOWN:
            if self.value is not None:
                raise CommonIOError("unknown time cannot have a numeric value")
        else:
            _nonnegative("time value", self.value)


@dataclass(frozen=True, slots=True)
class ScopeRef:
    self_id: str
    world_session_id: str | None = None

    def __post_init__(self) -> None:
        _text("self_id", self.self_id)
        if self.world_session_id is not None:
            _text("world_session_id", self.world_session_id)


@dataclass(frozen=True, slots=True)
class CommonEnvelope:
    event_id: str
    kind: str
    scope: ScopeRef
    occurred_at: ClockStamp
    provenance: Provenance
    source_refs: tuple[Provenance, ...] = ()
    cause_event_refs: tuple[str, ...] = ()
    received_at: ClockStamp | None = None
    schema_version: int = 1

    def __post_init__(self) -> None:
        _text("event_id", self.event_id)
        _text("kind", self.kind)
        if not isinstance(self.scope, ScopeRef):
            raise CommonIOError("scope must be ScopeRef")
        if not isinstance(self.occurred_at, ClockStamp):
            raise CommonIOError("occurred_at must be ClockStamp")
        if not isinstance(self.provenance, Provenance):
            raise CommonIOError("provenance must be existing Provenance")
        if not isinstance(self.source_refs, tuple) or not all(
            isinstance(ref, Provenance) for ref in self.source_refs
        ):
            raise CommonIOError("source_refs must be provenance pointers")
        _refs("cause_event_refs", self.cause_event_refs)
        if self.received_at is not None and (
            not isinstance(self.received_at, ClockStamp)
            or self.received_at.domain is not Clock.HOST_MONOTONIC_NS
        ):
            raise CommonIOError("received_at must be host monotonic or absent")
        if self.schema_version != 1 or isinstance(self.schema_version, bool):
            raise CommonIOError("unsupported common I/O schema version")


@dataclass(frozen=True, slots=True)
class FastCue:
    envelope: CommonEnvelope
    source_revision_ref: str
    installed_rule_ref: str
    expires_at_ns: int

    def __post_init__(self) -> None:
        if self.envelope.kind != "FAST_CUE":
            raise CommonIOError("fast cue requires FAST_CUE envelope")
        if self.envelope.scope.world_session_id is None or not self.envelope.source_refs:
            raise CommonIOError("fast cue requires world session and native source")
        if self.envelope.received_at is None:
            raise CommonIOError("fast cue requires host reception time")
        _text("source_revision_ref", self.source_revision_ref)
        _text("installed_rule_ref", self.installed_rule_ref)
        _nonnegative("expires_at_ns", self.expires_at_ns)
        if self.expires_at_ns < self.envelope.received_at.value:
            raise CommonIOError("cue expires before it is received")


def fast_cue_eligible(
    cue: FastCue,
    *,
    scope: ScopeRef,
    source_revision_ref: str,
    installed_rule_refs: frozenset[str],
    now_ns: int,
) -> bool:
    """Qualify a CPU rule input, never authorize or issue an Action."""
    _nonnegative("now_ns", now_ns)
    return (
        cue.envelope.scope == scope
        and cue.source_revision_ref == source_revision_ref
        and cue.installed_rule_ref in installed_rule_refs
        and cue.envelope.received_at.value <= now_ns < cue.expires_at_ns
    )


class TaskRequirement(str, Enum):
    FAST_REACTION = "FAST_REACTION"
    SELECT_FINITE = "SELECT_FINITE"
    OPEN_REASONING = "OPEN_REASONING"


class Profile(str, Enum):
    L0 = "L0"
    L1 = "L1"
    L2 = "L2"
    DEFER = "DEFER"


@dataclass(frozen=True, slots=True)
class CognitiveTask:
    envelope: CommonEnvelope
    task_ref: str
    requirement: TaskRequirement
    source_revision_refs: tuple[str, ...]
    deadline_ns: int
    generation: int
    choices: tuple[BoundedChoice, ...] = ()
    question_ref: str | None = None
    intent_ref: str | None = None

    def __post_init__(self) -> None:
        if self.envelope.kind != "COGNITIVE_TASK":
            raise CommonIOError("task requires COGNITIVE_TASK envelope")
        _text("task_ref", self.task_ref)
        if not isinstance(self.requirement, TaskRequirement):
            raise CommonIOError("invalid task requirement")
        _refs("source_revision_refs", self.source_revision_refs)
        _nonnegative("deadline_ns", self.deadline_ns)
        _nonnegative("generation", self.generation)
        if not isinstance(self.choices, tuple) or not all(
            isinstance(c, BoundedChoice) for c in self.choices
        ):
            raise CommonIOError("choices must reuse BoundedChoice")
        if len({c.choice_id for c in self.choices}) != len(self.choices):
            raise CommonIOError("duplicate choices")
        if self.requirement is TaskRequirement.SELECT_FINITE and len(self.choices) < 2:
            raise CommonIOError("finite selection requires at least two choices")
        if self.requirement is not TaskRequirement.SELECT_FINITE and self.choices:
            raise CommonIOError("non-finite task must not silently define choices")
        for ref in (self.question_ref, self.intent_ref):
            if ref is not None:
                _text("question/intent reference", ref)


@dataclass(frozen=True, slots=True)
class ProfileDecision:
    task_ref: str
    generation: int
    selected: Profile
    reason: str
    source_revision_refs: tuple[str, ...]
    resource_admission: str = "PENDING"


def select_profile(
    task: CognitiveTask,
    *,
    scope: ScopeRef,
    current_source_revision_refs: tuple[str, ...],
    now_ns: int,
    l0_rule_ready: bool = False,
    l1_available: bool = False,
    l2_available: bool = False,
) -> ProfileDecision:
    """CPU-only routing. PENDING is not GPU admission or Action authorization."""
    _nonnegative("now_ns", now_ns)
    _refs("current_source_revision_refs", current_source_revision_refs)
    selected, reason = Profile.DEFER, "UNAVAILABLE"
    if task.envelope.scope != scope:
        reason = "FOREIGN_SCOPE"
    elif task.source_revision_refs != current_source_revision_refs:
        reason = "STALE_SOURCE"
    elif now_ns >= task.deadline_ns:
        reason = "DEADLINE_EXPIRED"
    elif task.requirement is TaskRequirement.FAST_REACTION and l0_rule_ready:
        selected, reason = Profile.L0, "QUALIFIED_CPU_RULE"
    elif task.requirement is TaskRequirement.SELECT_FINITE and l1_available:
        selected, reason = Profile.L1, "FINITE_CHOICES"
    elif task.requirement is TaskRequirement.OPEN_REASONING and l2_available:
        selected, reason = Profile.L2, "OPEN_REASONING"
    return ProfileDecision(
        task_ref=task.task_ref,
        generation=task.generation,
        selected=selected,
        reason=reason,
        source_revision_refs=task.source_revision_refs,
        resource_admission="PENDING" if selected is not Profile.DEFER else "NOT_REQUESTED",
    )


@dataclass(frozen=True, slots=True)
class CognitionResultReceipt:
    task_ref: str
    scope: ScopeRef
    generation: int
    profile: Profile
    source_revision_refs: tuple[str, ...]
    status: str
    provenance: Provenance
    choice_id: str | None = None


def result_is_current(
    result: CognitionResultReceipt,
    task: CognitiveTask,
    decision: ProfileDecision,
    *,
    scope: ScopeRef,
    current_source_revision_refs: tuple[str, ...],
    now_ns: int,
    compute_admitted: bool,
    preemption: PreemptionTrace | None = None,
) -> bool:
    """Check a model receipt before caller-owned Intent/Skill/Action admission."""
    _nonnegative("now_ns", now_ns)
    if (
        task.envelope.scope != scope
        or result.scope != scope
        or result.task_ref != task.task_ref
        or result.generation != task.generation
        or result.profile != decision.selected
        or decision.selected is Profile.DEFER
        or decision.task_ref != task.task_ref
        or decision.generation != task.generation
        or result.source_revision_refs != task.source_revision_refs
        or current_source_revision_refs != task.source_revision_refs
        or now_ns >= task.deadline_ns
        or result.status != "SELECTED"
        or not isinstance(result.provenance, Provenance)
    ):
        return False
    if result.profile in {Profile.L1, Profile.L2} and not compute_admitted:
        return False
    if result.profile is Profile.L1:
        if result.choice_id not in {c.choice_id for c in task.choices}:
            return False
    elif result.choice_id is not None:
        return False
    if result.profile is Profile.L2:
        if preemption is None:
            return False
        if (
            preemption.l2_task_ref != result.task_ref
            or preemption.l2_generation != result.generation
            or preemption.scope != scope
            or preemption.events
        ):
            return False
    return True


class PreemptionPhase(str, Enum):
    CANCEL_REQUESTED = "CANCEL_REQUESTED"
    OUTPUT_FENCED = "OUTPUT_FENCED"
    BACKEND_STOPPED = "BACKEND_STOPPED"
    RESOURCE_RELEASED = "RESOURCE_RELEASED"
    L1_ADMITTED = "L1_ADMITTED"


_PHASE_ORDER = tuple(PreemptionPhase)


@dataclass(frozen=True, slots=True)
class PreemptionEvent:
    phase: PreemptionPhase
    at_ns: int
    provenance: Provenance
    verification_ref: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.phase, PreemptionPhase):
            raise CommonIOError("unknown preemption phase")
        _nonnegative("at_ns", self.at_ns)
        if not isinstance(self.provenance, Provenance):
            raise CommonIOError("preemption requires source provenance")
        if self.phase in {
            PreemptionPhase.BACKEND_STOPPED,
            PreemptionPhase.RESOURCE_RELEASED,
            PreemptionPhase.L1_ADMITTED,
        }:
            if self.verification_ref is None:
                raise CommonIOError("stop/release/admission requires verification ref")
            _text("verification_ref", self.verification_ref)


@dataclass(frozen=True, slots=True)
class PreemptionTrace:
    """Immutable ordering validator, NOT a backend cancellation/scheduler service."""

    scope: ScopeRef
    l2_task_ref: str
    l2_generation: int
    l1_task_ref: str
    events: tuple[PreemptionEvent, ...] = ()

    def __post_init__(self) -> None:
        _text("l2_task_ref", self.l2_task_ref)
        _text("l1_task_ref", self.l1_task_ref)
        _nonnegative("l2_generation", self.l2_generation)

    @property
    def output_fenced(self) -> bool:
        # The request itself already revokes result admission, even before
        # the backend acknowledges stop or GPU release.
        return bool(self.events)

    @property
    def l1_admitted(self) -> bool:
        return bool(self.events) and self.events[-1].phase is PreemptionPhase.L1_ADMITTED

    def append(self, event: PreemptionEvent) -> PreemptionTrace:
        if len(self.events) >= len(_PHASE_ORDER):
            raise CommonIOError("preemption already terminal")
        expected = _PHASE_ORDER[len(self.events)]
        if event.phase is not expected:
            raise CommonIOError(f"out-of-order preemption: expected {expected.value}")
        if self.events and event.at_ns < self.events[-1].at_ns:
            raise CommonIOError("preemption event time regressed")
        return replace(self, events=(*self.events, event))


def _text(name: str, value: object) -> None:
    if not isinstance(value, str) or not value.strip():
        raise CommonIOError(f"{name} must be non-empty text")


def _nonnegative(name: str, value: object) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise CommonIOError(f"{name} must be a non-negative integer")


def _refs(name: str, refs: object) -> None:
    if not isinstance(refs, tuple):
        raise CommonIOError(f"{name} must be tuple")
    for ref in refs:
        _text(name, ref)
    if len(set(refs)) != len(refs):
        raise CommonIOError(f"{name} contains duplicates")
