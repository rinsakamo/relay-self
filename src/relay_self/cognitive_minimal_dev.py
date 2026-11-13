"""Minimal Cognitive v0.1 DEV seam: CPU Schema -> numbered L1 -> existing owners.

This module owns no World observation, Goal/Intent ledger, physical Action issuer,
GPU resource scheduler, or memory store. WorldBody/ActionPort remains authoritative.
It composes the existing #829/#831/RelayEngine/Intent/Skill/Action contracts.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from enum import Enum

from relay_self.action import ActionLifecycle
from relay_self.common_io import ScopeRef
from relay_self.intent import IntentCommitment
from relay_self.provenance import Provenance
from relay_self.relay_engine import (
    BoundedChoice,
    BoundedChoiceRequest,
    CognitionDatum,
    DecisionStatus,
    RelayEngineResult,
)
from relay_self.skill import SkillExecution


class MinimalCognitionError(ValueError):
    """Invalid source, learned pattern, selected option, or owner state."""


class Predicate(str, Enum):
    HUNGRY = "HUNGRY"
    ZOMBIE_NEAR = "ZOMBIE_NEAR"
    FATIGUE_HIGH = "FATIGUE_HIGH"


class PatternKind(str, Enum):
    GOAL = "GOAL"
    CONSTRAINT = "CONSTRAINT"


class Origin(str, Enum):
    INNATE = "INNATE"
    LEARNED = "LEARNED"


@dataclass(frozen=True, slots=True)
class SchemaPattern:
    """Same finite, typed CPU matcher for innate and L2-proposed patterns.

    Data only: no model calls, Python source, expression eval, recursion, or IO.
    """
    pattern_id: str
    version: int
    schema_id: str
    kind: PatternKind
    predicate: Predicate
    goal_id: str | None
    skill_id: str | None
    skill_version: int | None
    target_kind: str | None
    origin: Origin
    provenance: Provenance

    def __post_init__(self) -> None:
        for name in ("pattern_id", "schema_id"):
            if not isinstance(getattr(self, name), str) or not getattr(self, name).strip():
                raise MinimalCognitionError(f"{name} missing")
        if type(self.version) is not int or self.version < 1:
            raise MinimalCognitionError("invalid pattern version")
        if not isinstance(self.kind, PatternKind) or not isinstance(self.predicate, Predicate):
            raise MinimalCognitionError("unsupported CPU pattern/predicate")
        if not isinstance(self.origin, Origin) or not isinstance(self.provenance, Provenance):
            raise MinimalCognitionError("unqualified pattern")
        if self.kind is PatternKind.GOAL:
            if not all(isinstance(x, str) and x for x in (
                self.goal_id, self.skill_id, self.target_kind
            )):
                raise MinimalCognitionError("goal needs bound skill and target kind")
            if type(self.skill_version) is not int or self.skill_version < 1:
                raise MinimalCognitionError("goal needs positive skill version")
            if self.predicate is Predicate.FATIGUE_HIGH:
                raise MinimalCognitionError("fatigue is constraint-only in minimal DEV")
            if self.predicate is Predicate.HUNGRY and self.target_kind != "FOOD":
                raise MinimalCognitionError("HUNGRY must match FOOD")
            if self.predicate is Predicate.ZOMBIE_NEAR and self.target_kind != "ZOMBIE":
                raise MinimalCognitionError("ZOMBIE_NEAR must match ZOMBIE")
        elif any(x is not None for x in (
            self.goal_id, self.skill_id, self.skill_version, self.target_kind
        )) or self.predicate is not Predicate.FATIGUE_HIGH:
            raise MinimalCognitionError("invalid goal-less constraint pattern")


@dataclass(frozen=True, slots=True)
class PatternRegistry:
    revision: int
    patterns: tuple[SchemaPattern, ...]

    def __post_init__(self) -> None:
        if type(self.revision) is not int or self.revision < 0:
            raise MinimalCognitionError("invalid registry revision")
        if not isinstance(self.patterns, tuple) or len(self.patterns) > 64:
            raise MinimalCognitionError("CPU registry is bounded to 64 patterns")
        if len({(p.pattern_id, p.version) for p in self.patterns}) != len(self.patterns):
            raise MinimalCognitionError("duplicate pattern version")
        if any(not isinstance(p, SchemaPattern) for p in self.patterns):
            raise MinimalCognitionError("invalid CPU pattern")


def initial_patterns() -> PatternRegistry:
    """Bootstrap primitives; natural motivation still depends on observations."""
    provenance = Provenance("innate-schema", "cognitive-v0.1")
    return PatternRegistry(0, (
        SchemaPattern("hunger-eat", 1, "homeostatic", PatternKind.GOAL,
                      Predicate.HUNGRY, "HUNGER_RELIEF", "EAT", 1, "FOOD",
                      Origin.INNATE, provenance),
        SchemaPattern("defense-attack", 1, "defensive", PatternKind.GOAL,
                      Predicate.ZOMBIE_NEAR, "DEFEND_SELF", "ATTACK", 1, "ZOMBIE",
                      Origin.INNATE, provenance),
        SchemaPattern("body-fatigue", 1, "body", PatternKind.CONSTRAINT,
                      Predicate.FATIGUE_HIGH, None, None, None, None,
                      Origin.INNATE, provenance),
    ))


def accept_learned_pattern(
    registry: PatternRegistry,
    proposed: SchemaPattern,
    *,
    accepted_by_self: bool,
    expected_revision: int,
    allowed_skills: frozenset[tuple[str, int]],
) -> PatternRegistry:
    """Return candidate atomic snapshot for Self owner publication only.

    This is NOT a Self-acceptance policy: caller must provide actual owner decision.
    Never creates WorldBody capabilities; old versions remain in prior snapshots.
    """
    if not accepted_by_self:
        raise MinimalCognitionError("L2 proposal is not Self-accepted")
    if expected_revision != registry.revision:
        raise MinimalCognitionError("stale registry revision")
    if proposed.origin is not Origin.LEARNED:
        raise MinimalCognitionError("only learned patterns may be proposed")
    if proposed.schema_id not in {"homeostatic", "defensive", "body"}:
        raise MinimalCognitionError("unknown owning schema")
    if proposed.kind is PatternKind.GOAL and (
        proposed.skill_id, proposed.skill_version
    ) not in allowed_skills:
        raise MinimalCognitionError("unavailable physical skill capability")
    if any(p.pattern_id == proposed.pattern_id for p in registry.patterns):
        raise MinimalCognitionError("pattern ID already registered; retain old versions")
    return PatternRegistry(registry.revision + 1, registry.patterns + (proposed,))


@dataclass(frozen=True, slots=True)
class Target:
    ref: str
    kind: str
    provenance: Provenance
    world_session_id: str
    observed_sequence: int
    live: bool = True

    def __post_init__(self) -> None:
        if not self.ref or not self.kind or not self.world_session_id:
            raise MinimalCognitionError("target identity missing")
        if type(self.observed_sequence) is not int or self.observed_sequence < 0:
            raise MinimalCognitionError("invalid target sequence")
        if not isinstance(self.provenance, Provenance) or type(self.live) is not bool:
            raise MinimalCognitionError("invalid target evidence")


@dataclass(frozen=True, slots=True)
class WorldPercept:
    scope: ScopeRef
    source: Provenance
    sequence: int
    hunger: int | None
    fatigue_high: bool | None
    targets: tuple[Target, ...]

    def __post_init__(self) -> None:
        if self.scope.world_session_id is None or not isinstance(self.source, Provenance):
            raise MinimalCognitionError("source-qualified World session required")
        if type(self.sequence) is not int or self.sequence < 0:
            raise MinimalCognitionError("invalid Percept sequence")
        if self.hunger is not None and (
            type(self.hunger) is not int or not 0 <= self.hunger <= 20
        ):
            raise MinimalCognitionError("invalid observed hunger")
        if self.fatigue_high is not None and type(self.fatigue_high) is not bool:
            raise MinimalCognitionError("invalid fatigue")
        if not isinstance(self.targets, tuple) or len(self.targets) > 16:
            raise MinimalCognitionError("at most 16 source-qualified targets")
        if len({t.ref for t in self.targets}) != len(self.targets):
            raise MinimalCognitionError("duplicate target identity")
        if any(not isinstance(t, Target) or t.world_session_id != self.scope.world_session_id
               or t.observed_sequence > self.sequence for t in self.targets):
            raise MinimalCognitionError("foreign/future/unqualified target")


@dataclass(frozen=True, slots=True)
class Goal:
    goal_id: str
    schema_id: str
    skill_id: str
    skill_version: int
    strength: str
    unresolved: bool


@dataclass(frozen=True, slots=True)
class Option:
    goal_id: str
    skill_id: str
    skill_version: int
    target_ref: str
    target_kind: str
    schema_id: str
    pattern_id: str


@dataclass(frozen=True, slots=True)
class ConstraintSensation:
    schema_id: str
    sensation: str
    epistemic_status: str


@dataclass(frozen=True, slots=True)
class SchemaFrame:
    scope: ScopeRef
    epoch: int
    source: Provenance
    registry_revision: int
    goals: tuple[Goal, ...]
    options: tuple[Option, ...]
    constraints: tuple[ConstraintSensation, ...]
    fast_cues: tuple[str, ...]
    pattern_checks: int
    elapsed_ns: int


def cpu_schema_epoch(
    percept: WorldPercept,
    registry: PatternRegistry,
    *,
    allowed_skills: frozenset[tuple[str, int]],
    epoch: int,
) -> SchemaFrame:
    """Synchronous finite CPU-only step; caller controls event-loop cadence.

    No LLM/backend/Memory access. Source Percept comes from the existing gateway.
    """
    t0 = time.perf_counter_ns()
    if type(epoch) is not int or epoch < 0:
        raise MinimalCognitionError("invalid epoch")
    goals: list[Goal] = []
    options: list[Option] = []
    constraints: list[ConstraintSensation] = []
    checks = 0
    threats = tuple(t for t in percept.targets if t.kind == "ZOMBIE" and t.live)
    for pattern in registry.patterns:
        checks += 1
        triggered = (
            pattern.predicate is Predicate.HUNGRY
            and percept.hunger is not None and percept.hunger < 18
        ) or (
            pattern.predicate is Predicate.ZOMBIE_NEAR and bool(threats)
        ) or (
            pattern.predicate is Predicate.FATIGUE_HIGH
            and percept.fatigue_high is True
        )
        if not triggered:
            continue
        if pattern.kind is PatternKind.CONSTRAINT:
            constraints.append(ConstraintSensation(
                pattern.schema_id, "FATIGUE_LIMIT", "INFERRED"
            ))
            continue
        matching = tuple(t for t in percept.targets if t.live and
                         t.kind == pattern.target_kind)
        available = (pattern.skill_id, pattern.skill_version) in allowed_skills
        goals.append(Goal(pattern.goal_id or "", pattern.schema_id,
                          pattern.skill_id or "", pattern.skill_version or 0,
                          "URGENT" if pattern.predicate is Predicate.ZOMBIE_NEAR
                          else "ACTIVE", not (matching and available)))
        if available:
            for t in matching:
                checks += 1
                if len(options) >= 8:
                    break
                options.append(Option(pattern.goal_id or "", pattern.skill_id or "",
                                      pattern.skill_version or 0, t.ref, t.kind,
                                      pattern.schema_id, pattern.pattern_id))
    return SchemaFrame(
        percept.scope, epoch, percept.source, registry.revision,
        tuple(goals), tuple(options), tuple(constraints),
        ("ZOMBIE_NEAR",) if threats else (), checks,
        time.perf_counter_ns() - t0,
    )


@dataclass(frozen=True, slots=True)
class L1Round:
    frame: SchemaFrame
    request: BoundedChoiceRequest
    numbered: tuple[tuple[str, Option | str], ...]


def assemble_l1_select(
    frame: SchemaFrame,
    *,
    intent_owner: IntentCommitment,
    recent_3self: tuple[str, ...] = (),
    max_context_chars: int = 4096,
) -> L1Round:
    """Bounded numbered concrete options; no mandatory Memory retrieval."""
    if not isinstance(intent_owner, IntentCommitment) or len(recent_3self) > 3:
        raise MinimalCognitionError("invalid current Owner / Recent3SelfView")
    if type(max_context_chars) is not int or max_context_chars < 256:
        raise MinimalCognitionError("invalid context bound")
    entries: list[Option | str] = list(frame.options)
    entries.extend(("ESCALATE_L2", "DEFER"))
    numbered = tuple((str(i), e) for i, e in enumerate(entries, 1))
    active = intent_owner.current_intent
    summary = {
        "goals": [{"id":g.goal_id, "strength":g.strength,
                   "skill":f"{g.skill_id}@{g.skill_version}",
                   "unresolved":g.unresolved} for g in frame.goals],
        "constraints": [{"schema":c.schema_id, "sense":c.sensation,
                         "status":c.epistemic_status} for c in frame.constraints],
        "fast_cues": list(frame.fast_cues),
        "live_intent": None if active is None else active.intent_id,
        "recent_3self": list(recent_3self),
    }
    datum = CognitionDatum.from_value("schema_current_and_recent", summary, frame.source)
    if len(datum.value_json) > max_context_chars:
        raise MinimalCognitionError("L1 CURRENT context exceeds bound")
    choices = []
    for choice_id, entry in numbered:
        if isinstance(entry, str):
            desc = entry
        else:
            desc = (f"{entry.goal_id}: {entry.skill_id}@{entry.skill_version}"
                    f"({entry.target_ref}) [schema={entry.schema_id}]")
        choices.append(BoundedChoice(choice_id, desc))
    request = BoundedChoiceRequest(
        request_id=f"schema-l1-{frame.scope.self_id}-{frame.epoch}",
        instruction=("Select exactly one numbered choice from CURRENT. "
                     "Defend if threatened when justified; do not invent targets. "
                     "Choose ESCALATE_L2 for unresolved needs with no usable target. "
                     "Return only a bounded choice ID."),
        intent_id=None if active is None else active.intent_id,
        focus="GOAL_SKILL_TARGET",
        choices=tuple(choices),
        context=(datum,),
        think_allowed=False,
    )
    return L1Round(frame, request, numbered)


@dataclass(frozen=True, slots=True)
class Selection:
    status: str
    option: Option | None
    reason: str
    world_scope: ScopeRef | None = None


def resolve_l1_choice(
    round_: L1Round,
    result: RelayEngineResult,
    *,
    current_frame: SchemaFrame,
    intent_owner: IntentCommitment,
    available_skills: frozenset[tuple[str, int]],
) -> Selection:
    """Recheck only chosen dependencies, not unrelated global epoch/observations.

    This is NOT a native Action grant; WorldBody must still refuse unqualified
    targets or BUSY/unsupported operations at actual issuance.
    """
    if result.status is not DecisionStatus.RESOLVED or result.choice_id is None:
        return Selection("RECONSIDER", None, "L1 unresolved")
    chosen = dict(round_.numbered).get(result.choice_id)
    if chosen is None:
        return Selection("REJECTED", None, "unknown numbered L1 choice")
    if chosen == "ESCALATE_L2":
        return Selection("ESCALATE_L2", None, "L1 requested cognitive escalation")
    if chosen == "DEFER":
        return Selection("DEFER", None, "L1 deferred")
    assert isinstance(chosen, Option)
    if round_.frame.scope != current_frame.scope:
        return Selection("REJECTED", None, "World/Self session changed")
    if (chosen.skill_id, chosen.skill_version) not in available_skills:
        return Selection("REJECTED", None, "Skill version unavailable")
    if chosen not in current_frame.options:
        return Selection("REJECTED", None, "Goal/Target/Skill dependencies stale")
    if intent_owner.current_intent is not None:
        return Selection("DEFER", None, "legacy single CurrentIntent is busy")
    return Selection("READY", chosen, "current selected dependencies", current_frame.scope)


@dataclass(frozen=True, slots=True)
class OwnerProposal:
    intent_id: str
    skill: SkillExecution
    action: ActionLifecycle
    option: Option
    world_scope: ScopeRef


def prepare_existing_owner_action(
    selection: Selection,
    *,
    intent_owner: IntentCommitment,
    intent_id: str,
    skill_run_id: str,
    action_id: str,
    at_ns: int,
    provenance: Provenance,
) -> OwnerProposal:
    """Reuse actual owner lifecycle and create PROPOSED only, never issue.

    The existing S49/ActionPort must authorize and issue this grounded proposal
    with native capability/currentness/session/target checks before World effect.
    """
    if (selection.status != "READY" or selection.option is None
            or selection.world_scope is None):
        raise MinimalCognitionError("only scoped READY selections may start Skill")
    if intent_owner.current_intent is not None:
        raise MinimalCognitionError("legacy Intent owner busy")
    option = selection.option
    intent_owner.commit(intent_id, objective=option.goal_id,
                        at_ns=at_ns, provenance=provenance)
    skill = SkillExecution.start(skill_run_id, skill_id=option.skill_id,
                                 intent_commitment=intent_owner, at_ns=at_ns,
                                 provenance=provenance)
    action = ActionLifecycle.propose(action_id, skill_execution=skill,
                                     intent_commitment=intent_owner, at_ns=at_ns,
                                     provenance=provenance)
    return OwnerProposal(intent_id, skill, action, option, selection.world_scope)
