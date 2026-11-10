"""Innate Schema v0.1: pure activation, dependency, and signal contracts.

Child of #828, Issue #831. This is NOT a schema execution runtime, Goal owner,
Memory writer, L0 rule installer, resource scheduler, or physical Action issuer.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum

from relay_self.common_io import CommonEnvelope, ScopeRef
from relay_self.provenance import Provenance


class SchemaContractError(ValueError):
    """Malformed module, activation, or source-bound candidate."""


class SchemaMode(str, Enum):
    OFF = "OFF"
    FAST = "FAST"
    FULL = "FULL"


_MODE_LEVEL = {SchemaMode.OFF: 0, SchemaMode.FAST: 1, SchemaMode.FULL: 2}


@dataclass(frozen=True, slots=True)
class SchemaDependency:
    schema_id: str
    minimum_mode: SchemaMode = SchemaMode.FAST

    def __post_init__(self) -> None:
        _text("dependency schema_id", self.schema_id)
        if not isinstance(self.minimum_mode, SchemaMode) or self.minimum_mode is SchemaMode.OFF:
            raise SchemaContractError("dependency minimum_mode must be FAST or FULL")


@dataclass(frozen=True, slots=True)
class SchemaModuleSpec:
    """A cognitive mechanism specification; no Minecraft targets or physical grants."""

    schema_id: str
    version: int
    supported_modes: frozenset[SchemaMode]
    signal_kinds: tuple[str, ...]
    dependencies: tuple[SchemaDependency, ...]
    provenance: Provenance

    def __post_init__(self) -> None:
        _text("schema_id", self.schema_id)
        _positive("schema version", self.version)
        if (
            not isinstance(self.supported_modes, frozenset)
            or not self.supported_modes
            or SchemaMode.OFF in self.supported_modes
            or any(not isinstance(m, SchemaMode) for m in self.supported_modes)
        ):
            raise SchemaContractError("supported_modes must contain FAST and/or FULL")
        _refs("signal_kinds", self.signal_kinds, require_nonempty=True)
        if not isinstance(self.dependencies, tuple) or any(
            not isinstance(d, SchemaDependency) for d in self.dependencies
        ):
            raise SchemaContractError("dependencies must be SchemaDependency tuple")
        if len({d.schema_id for d in self.dependencies}) != len(self.dependencies):
            raise SchemaContractError("duplicate dependency")
        if not isinstance(self.provenance, Provenance):
            raise SchemaContractError("module provenance must be Provenance")


@dataclass(frozen=True, slots=True)
class SchemaActivation:
    spec: SchemaModuleSpec
    mode: SchemaMode

    def __post_init__(self) -> None:
        if not isinstance(self.spec, SchemaModuleSpec):
            raise SchemaContractError("activation must reference SchemaModuleSpec")
        if not isinstance(self.mode, SchemaMode):
            raise SchemaContractError("invalid schema mode")
        if self.mode is not SchemaMode.OFF and self.mode not in self.spec.supported_modes:
            raise SchemaContractError("unsupported activation mode")


@dataclass(frozen=True, slots=True)
class SchemaSnapshot:
    """Caller-owned immutable per-Self configuration, not a new state owner."""

    self_id: str
    revision: int
    modules: tuple[SchemaActivation, ...]

    def __post_init__(self) -> None:
        _text("self_id", self.self_id)
        _nonnegative("registry revision", self.revision)
        if not isinstance(self.modules, tuple) or any(
            not isinstance(m, SchemaActivation) for m in self.modules
        ):
            raise SchemaContractError("modules must be SchemaActivation tuple")
        by_id = {a.spec.schema_id: a for a in self.modules}
        if len(by_id) != len(self.modules):
            raise SchemaContractError("duplicate schema id")

        # All dependencies, even OFF ones, must have a registered spec.
        for a in self.modules:
            for d in a.spec.dependencies:
                if d.schema_id not in by_id:
                    raise SchemaContractError("unknown schema dependency")
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(schema_id: str) -> None:
            if schema_id in visiting:
                raise SchemaContractError("schema dependency cycle")
            if schema_id in visited:
                return
            visiting.add(schema_id)
            for dep in by_id[schema_id].spec.dependencies:
                visit(dep.schema_id)
            visiting.remove(schema_id)
            visited.add(schema_id)

        for schema_id in by_id:
            visit(schema_id)

    def get(self, schema_id: str) -> SchemaActivation | None:
        return next((a for a in self.modules if a.spec.schema_id == schema_id), None)


def with_schema_mode(
    snapshot: SchemaSnapshot, *, schema_id: str, mode: SchemaMode
) -> SchemaSnapshot:
    """Pure proposal of a new config epoch; owner must publish it atomically."""
    _text("schema_id", schema_id)
    if not isinstance(mode, SchemaMode):
        raise SchemaContractError("invalid schema mode")
    prior = snapshot.get(schema_id)
    if prior is None:
        raise SchemaContractError("unknown schema id")
    if prior.mode is mode:
        return snapshot
    return SchemaSnapshot(
        self_id=snapshot.self_id,
        revision=snapshot.revision + 1,
        modules=tuple(
            replace(a, mode=mode) if a.spec.schema_id == schema_id else a
            for a in snapshot.modules
        ),
    )


@dataclass(frozen=True, slots=True)
class SchemaEligibility:
    schema_id: str
    requested_mode: SchemaMode
    registry_revision: int
    allowed: bool
    reason: str


def check_schema_eligibility(
    snapshot: SchemaSnapshot,
    *,
    scope: ScopeRef,
    schema_id: str,
    requested_mode: SchemaMode,
    current_registry_revision: int,
) -> SchemaEligibility:
    """No Goal, compute, action, installed-rule or Memory authorization."""
    _text("schema_id", schema_id)
    _nonnegative("current_registry_revision", current_registry_revision)
    if not isinstance(requested_mode, SchemaMode) or requested_mode is SchemaMode.OFF:
        raise SchemaContractError("requested mode must be FAST or FULL")

    reason = "ELIGIBLE"
    if scope.self_id != snapshot.self_id:
        reason = "FOREIGN_SELF"
    elif snapshot.revision != current_registry_revision:
        reason = "STALE_REGISTRY"
    elif snapshot.get(schema_id) is None:
        reason = "UNKNOWN_SCHEMA"
    else:
        def reason_for(module_id: str, need: SchemaMode) -> str:
            activation = snapshot.get(module_id)
            assert activation is not None  # graph validated in SchemaSnapshot
            if activation.mode is SchemaMode.OFF:
                return "DISABLED"
            if _MODE_LEVEL[activation.mode] < _MODE_LEVEL[need]:
                return "INSUFFICIENT_MODE"
            if need not in activation.spec.supported_modes:
                return "UNSUPPORTED_MODE"
            for dependency in activation.spec.dependencies:
                problem = reason_for(dependency.schema_id, dependency.minimum_mode)
                if problem != "ELIGIBLE":
                    return "DEPENDENCY_UNAVAILABLE"
            return "ELIGIBLE"

        reason = reason_for(schema_id, requested_mode)

    return SchemaEligibility(
        schema_id=schema_id,
        requested_mode=requested_mode,
        registry_revision=snapshot.revision,
        allowed=reason == "ELIGIBLE",
        reason=reason,
    )


class NeedPressure(str, Enum):
    LOW = "LOW"
    URGENT = "URGENT"
    UNKNOWN = "UNKNOWN"


class Engagement(str, Enum):
    IDLE = "IDLE"
    BUSY = "BUSY"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class ExplorationOpportunity:
    """Present-owned source-bounded unknown target and existing action catalog refs."""

    envelope: CommonEnvelope
    source_revision_refs: tuple[str, ...]
    target_observation_ref: Provenance
    unknown_target_ref: str
    reference_action_refs: tuple[str, ...]
    action_catalog_provenance: Provenance
    engagement: Engagement
    need_pressure: NeedPressure

    def __post_init__(self) -> None:
        if self.envelope.kind != "PRESENT_FRAME":
            raise SchemaContractError("exploration input must come from PresentFrame")
        if self.envelope.scope.world_session_id is None or not self.envelope.source_refs:
            raise SchemaContractError("exploration requires World-scoped source evidence")
        _refs("source_revision_refs", self.source_revision_refs, require_nonempty=True)
        if self.target_observation_ref not in self.envelope.source_refs:
            raise SchemaContractError("target observation must occur in source refs")
        _text("unknown_target_ref", self.unknown_target_ref)
        _refs("reference_action_refs", self.reference_action_refs, require_nonempty=False)
        if not isinstance(self.action_catalog_provenance, Provenance):
            raise SchemaContractError("reference Action catalog must have provenance")
        if not isinstance(self.engagement, Engagement):
            raise SchemaContractError("invalid engagement state")
        if not isinstance(self.need_pressure, NeedPressure):
            raise SchemaContractError("invalid Need pressure")


@dataclass(frozen=True, slots=True)
class ExplorationQuestion:
    """A question candidate about effects; no chosen plan or issued action."""

    unknown_target_ref: str
    reference_action_refs: tuple[str, ...]
    inquiry: str = "OBSERVE_UNKNOWN_EFFECT"


@dataclass(frozen=True, slots=True)
class CognitiveSignal:
    envelope: CommonEnvelope
    schema_id: str
    module_version: int
    registry_revision: int
    source_revision_refs: tuple[str, ...]
    signal_kind: str
    execution_mode: SchemaMode
    epistemic_status: str
    question_candidate: ExplorationQuestion | None = None

    def __post_init__(self) -> None:
        if self.envelope.kind != "COGNITIVE_SIGNAL":
            raise SchemaContractError("signal requires COGNITIVE_SIGNAL envelope")
        _text("schema_id", self.schema_id)
        _positive("module_version", self.module_version)
        _nonnegative("registry_revision", self.registry_revision)
        _refs("source_revision_refs", self.source_revision_refs, require_nonempty=True)
        _text("signal_kind", self.signal_kind)
        if not isinstance(self.execution_mode, SchemaMode) or self.execution_mode is SchemaMode.OFF:
            raise SchemaContractError("signal execution mode must be FAST or FULL")
        if self.epistemic_status not in ("HYPOTHETICAL", "INFERRED", "UNKNOWN"):
            raise SchemaContractError("schema output cannot masquerade as observed World fact")
        if (self.signal_kind == "QUESTION_CANDIDATE") != (
            self.question_candidate is not None
        ):
            raise SchemaContractError("question candidate payload/kind mismatch")


def signal_is_current(
    signal: CognitiveSignal,
    *,
    snapshot: SchemaSnapshot,
    scope: ScopeRef,
    source_revision_refs: tuple[str, ...],
    current_registry_revision: int,
    requested_mode: SchemaMode,
) -> bool:
    """Recheck from currently owned config and Present, not a cached old snapshot."""
    if (
        signal.envelope.scope != scope
        or signal.registry_revision != snapshot.revision
        or signal.source_revision_refs != source_revision_refs
        or signal.execution_mode is not requested_mode
        or not isinstance(signal.envelope.provenance, Provenance)
    ):
        return False
    module = snapshot.get(signal.schema_id)
    if (
        module is None
        or module.spec.version != signal.module_version
        or signal.signal_kind not in module.spec.signal_kinds
    ):
        return False
    return check_schema_eligibility(
        snapshot, scope=scope, schema_id=signal.schema_id,
        requested_mode=requested_mode, current_registry_revision=current_registry_revision,
    ).allowed


def propose_exploratory_question(
    *,
    snapshot: SchemaSnapshot,
    schema_id: str,
    opportunity: ExplorationOpportunity,
    signal_envelope: CommonEnvelope,
    current_registry_revision: int,
    current_source_revision_refs: tuple[str, ...],
) -> CognitiveSignal | None:
    """A generic inquiry candidate; no discovery claim, Goal, Skill, or Action.

    The *caller* provides witnessed unknown target and Action catalog refs.
    No Minecraft item, monster, tactic or physical effect is seeded.
    """
    eligibility = check_schema_eligibility(
        snapshot,
        scope=opportunity.envelope.scope,
        schema_id=schema_id,
        requested_mode=SchemaMode.FULL,
        current_registry_revision=current_registry_revision,
    )
    module = snapshot.get(schema_id)
    if (
        not eligibility.allowed
        or module is None
        or "QUESTION_CANDIDATE" not in module.spec.signal_kinds
        or opportunity.engagement is not Engagement.IDLE
        or opportunity.need_pressure is not NeedPressure.LOW
        or not opportunity.reference_action_refs
        or opportunity.source_revision_refs != current_source_revision_refs
        or signal_envelope.kind != "COGNITIVE_SIGNAL"
        or signal_envelope.scope != opportunity.envelope.scope
        or opportunity.target_observation_ref not in signal_envelope.source_refs
    ):
        return None
    return CognitiveSignal(
        envelope=signal_envelope,
        schema_id=module.spec.schema_id,
        module_version=module.spec.version,
        registry_revision=snapshot.revision,
        source_revision_refs=opportunity.source_revision_refs,
        signal_kind="QUESTION_CANDIDATE",
        execution_mode=SchemaMode.FULL,
        epistemic_status="HYPOTHETICAL",
        question_candidate=ExplorationQuestion(
            unknown_target_ref=opportunity.unknown_target_ref,
            reference_action_refs=opportunity.reference_action_refs,
        ),
    )


def _text(name: str, value: object) -> None:
    if not isinstance(value, str) or not value.strip():
        raise SchemaContractError(f"{name} must be non-empty text")


def _nonnegative(name: str, value: object) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise SchemaContractError(f"{name} must be a non-negative integer")


def _positive(name: str, value: object) -> None:
    _nonnegative(name, value)
    if value == 0:
        raise SchemaContractError(f"{name} must be positive")


def _refs(name: str, refs: object, *, require_nonempty: bool = False) -> None:
    if not isinstance(refs, tuple):
        raise SchemaContractError(f"{name} must be tuple")
    if require_nonempty and not refs:
        raise SchemaContractError(f"{name} cannot be empty")
    for ref in refs:
        _text(name, ref)
    if len(set(refs)) != len(refs):
        raise SchemaContractError(f"{name} contains duplicates")
