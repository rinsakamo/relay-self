"""Cognitive v0.1 Physical ActionPort: selected Action -> existing PROPOSED.

No Skill chooser, Goal/Intent owner, native executor, authorization, issue,
disk journal or background scheduler. This deliberately cannot send an Action.

The embodiment adapter must attest real native source and physical affordances;
matching typed refs alone is never authority or a World safety certificate.
"""
from __future__ import annotations

from dataclasses import dataclass

from relay_self.action import ActionLifecycle
from relay_self.action_supervision import ActionSupervisor
from relay_self.common_io import ScopeRef
from relay_self.intent import IntentCommitment
from relay_self.provenance import Provenance
from relay_self.skill import SkillExecution, SkillState


class PhysicalActionPortRefusal(ValueError):
    """A selected binding is stale, unsupported, conflicting or not owned."""


@dataclass(frozen=True, slots=True)
class PhysicalActionBinding:
    """Already-selected Intent/Skill/Target and requested *primitive* Action.

    The caller supplies this from one existing Self choice/Skill controller;
    no field is chosen or replaced by the ActionPort.
    """

    scope: ScopeRef
    intent_id: str
    goal_id: str
    skill_id: str
    skill_version: int
    skill_execution_id: str
    action_id: str
    capability_ref: str
    capability_version: int
    body_channel: str
    target_kind: str
    target_ref: str
    native_seq: int
    native_request_id: str
    native_source: Provenance

    def __post_init__(self) -> None:
        if not isinstance(self.scope, ScopeRef) or not self.scope.world_session_id:
            raise PhysicalActionPortRefusal("Self and World session required")
        for name in (
            "intent_id", "goal_id", "skill_id", "skill_execution_id",
            "action_id", "capability_ref", "body_channel", "target_kind",
            "target_ref", "native_request_id",
        ):
            _text(name, getattr(self, name))
        for value in (self.skill_version, self.capability_version):
            if type(value) is not int or value < 1:
                raise PhysicalActionPortRefusal("Skill/Action version must be positive")
        if type(self.native_seq) is not int or self.native_seq < 0:
            raise PhysicalActionPortRefusal("native seq must be nonnegative")
        if not isinstance(self.native_source, Provenance):
            raise PhysicalActionPortRefusal("typed native source required")


@dataclass(frozen=True, slots=True)
class PhysicalCapability:
    """Read-only WorldBody Action catalogue reference, NOT a grant."""

    capability_ref: str
    version: int
    body_channel: str
    target_kind: str
    available: bool

    def __post_init__(self) -> None:
        for v in (self.capability_ref, self.body_channel, self.target_kind):
            _text("physical capability", v)
        if type(self.version) is not int or self.version < 1:
            raise PhysicalActionPortRefusal("capability version must be positive")
        if type(self.available) is not bool:
            raise PhysicalActionPortRefusal("capability availability must be bool")


@dataclass(frozen=True, slots=True)
class PhysicalReadback:
    """Adapter-projected candidate facts, not proof of authentic source.

    The gateway must verify the native bytes/transport before constructing
    this projection. Its data cannot authorize a physical Action.
    """

    scope: ScopeRef
    source: Provenance
    seq: int
    request_id: str
    observed_target_refs: tuple[str, ...]
    body_viable: bool

    def __post_init__(self) -> None:
        if not isinstance(self.scope, ScopeRef) or not self.scope.world_session_id:
            raise PhysicalActionPortRefusal("readback requires Self/World scope")
        if not isinstance(self.source, Provenance):
            raise PhysicalActionPortRefusal("readback requires source provenance")
        if type(self.seq) is not int or self.seq < 0:
            raise PhysicalActionPortRefusal("readback sequence invalid")
        _text("readback request_id", self.request_id)
        if (
            not isinstance(self.observed_target_refs, tuple)
            or len(self.observed_target_refs) > 32
            or any(not isinstance(x, str) or not x.strip()
                   for x in self.observed_target_refs)
            or len(set(self.observed_target_refs)) != len(self.observed_target_refs)
        ):
            raise PhysicalActionPortRefusal("bounded unique observed targets required")
        if type(self.body_viable) is not bool:
            raise PhysicalActionPortRefusal("body viability must be explicit")


@dataclass(frozen=True, slots=True)
class PhysicalActionProposalReceipt:
    """A real existing ActionLifecycle.PROPOSED, with no physical authority."""

    binding: PhysicalActionBinding
    proposal: ActionLifecycle
    state: str = "PROPOSED_NOT_AUTHORIZED"
    physical_authorized: bool = False
    physical_issued: bool = False
    preissue_persisted: bool = False


def propose_bound_physical_action(
    binding: PhysicalActionBinding,
    *,
    capability: PhysicalCapability,
    readback: PhysicalReadback,
    intent_owner: IntentCommitment,
    skill_execution: SkillExecution,
    supervisor: ActionSupervisor,
    at_ns: int,
    provenance: Provenance,
) -> PhysicalActionProposalReceipt:
    """Bind one selected physical proposal to the *existing* Action owner.

    No commit/authorize/ISSUE/IO occurs. A later separate issuer must verify
    live native facts, channel/physics, owner permissions, durable PRE-ISSUE
    reservation and resulting native effects before it can issue anything.
    """
    if not isinstance(binding, PhysicalActionBinding):
        raise PhysicalActionPortRefusal("typed selected physical binding required")
    if not isinstance(capability, PhysicalCapability) or not isinstance(
        readback, PhysicalReadback
    ):
        raise PhysicalActionPortRefusal("typed capability/readback required")
    if not isinstance(intent_owner, IntentCommitment):
        raise PhysicalActionPortRefusal("existing IntentCommitment owner required")
    if not isinstance(skill_execution, SkillExecution):
        raise PhysicalActionPortRefusal("existing SkillExecution required")
    if not isinstance(supervisor, ActionSupervisor):
        raise PhysicalActionPortRefusal("existing ActionSupervisor required")
    if type(at_ns) is not int or at_ns < 0 or not isinstance(provenance, Provenance):
        raise PhysicalActionPortRefusal("valid proposal clock and provenance required")

    owner = intent_owner.current_intent
    if (
        owner is None
        or owner.intent_id != binding.intent_id
        or owner.objective != binding.goal_id
        or intent_owner.pending_reconsideration is not None
    ):
        raise PhysicalActionPortRefusal("selected Intent is not current/committed")
    if (
        not skill_execution.is_current_snapshot
        or skill_execution.state is not SkillState.STARTED
        or skill_execution.intent_id != owner.intent_id
        or skill_execution.execution_id != binding.skill_execution_id
        or skill_execution.skill_id != binding.skill_id
    ):
        raise PhysicalActionPortRefusal("selected Skill execution not current")
    if (
        not capability.available
        or capability.capability_ref != binding.capability_ref
        or capability.version != binding.capability_version
        or capability.body_channel != binding.body_channel
        or capability.target_kind != binding.target_kind
    ):
        raise PhysicalActionPortRefusal("WorldBody physical capability mismatched/unavailable")
    if (
        readback.scope != binding.scope
        or readback.source != binding.native_source
        or readback.seq != binding.native_seq
        or readback.request_id != binding.native_request_id
        or binding.target_ref not in readback.observed_target_refs
        or not readback.body_viable
    ):
        raise PhysicalActionPortRefusal("native source/Target/WorldBody no longer matches")
    # Until a trusted channel arbiter exists, serialize the whole body rather
    # than guessing which Action channels can run in parallel.
    if supervisor.open_actions:
        raise PhysicalActionPortRefusal("physical body currently has an issued Action")
    if any(x.action_id == binding.action_id for x in supervisor.recorded_actions):
        raise PhysicalActionPortRefusal("physical Action ID already supervised")
    if intent_owner.last_at_ns is not None and at_ns < intent_owner.last_at_ns:
        raise PhysicalActionPortRefusal("proposal time precedes Intent owner")

    # Existing ActionLifecycle enforces live Skill/Intent binding and creates
    # PROPOSED only. This method never touches ActionSupervisor.issue().
    proposed = ActionLifecycle.propose(
        binding.action_id, skill_execution=skill_execution,
        intent_commitment=intent_owner, at_ns=at_ns, provenance=provenance,
    )
    return PhysicalActionProposalReceipt(binding, proposed)


def _text(name: str, value: object) -> None:
    if not isinstance(value, str) or not value.strip():
        raise PhysicalActionPortRefusal(f"{name} must be a nonblank text value")
