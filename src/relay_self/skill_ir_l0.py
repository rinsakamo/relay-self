"""Cognitive v0.1: bounded Skill IR and nonissuing CPU L0 interpreter (#843).

Skill IR is data, never Python/model executable code. This layer selects only
an already-declared WorldBody capability and calls the EXISTING PhysicalActionPort
for PROPOSED; an external single physical owner alone may authorize/issue/WAL.
Neither a proposed Action nor an Action OUTCOME proves Skill/Intent success.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import Enum

from relay_self.action import ActionState
from relay_self.action_supervision import ActionSupervisor, UnknownSupervisedAction
from relay_self.common_io import ScopeRef
from relay_self.intent import IntentCommitment
from relay_self.physical_action_port import (
    PhysicalActionBinding,
    PhysicalActionProposalReceipt,
    PhysicalCapability,
    PhysicalReadback,
    propose_bound_physical_action,
)
from relay_self.provenance import Provenance
from relay_self.skill import SkillExecution, SkillState


class SkillIRRefusal(ValueError):
    """Malformed IR, stale owner/source, unsupported capability or unsafe resume."""


class StepKind(str, Enum):
    CHECK = "CHECK"
    ACTION = "ACTION"
    SUCCEED = "SUCCEED"
    FAIL = "FAIL"


@dataclass(frozen=True, slots=True)
class SkillIRStep:
    """One finite, inspectable step. No code, arbitrary expressions or retargeting."""

    step_id: str
    kind: StepKind
    predicate_ref: str | None = None
    capability_ref: str | None = None
    capability_version: int | None = None
    body_channel: str | None = None
    on_true: str | None = None
    on_false: str | None = None
    on_outcome: str | None = None
    on_denied: str | None = None

    def __post_init__(self) -> None:
        _text("step_id", self.step_id)
        if not isinstance(self.kind, StepKind):
            raise SkillIRRefusal("unknown Skill IR step kind")
        fields = {
            "predicate_ref": self.predicate_ref,
            "capability_ref": self.capability_ref,
            "capability_version": self.capability_version,
            "body_channel": self.body_channel,
            "on_true": self.on_true,
            "on_false": self.on_false,
            "on_outcome": self.on_outcome,
            "on_denied": self.on_denied,
        }
        allowed = {
            StepKind.CHECK: {"predicate_ref", "on_true", "on_false"},
            StepKind.ACTION: {
                "capability_ref", "capability_version", "body_channel",
                "on_outcome", "on_denied",
            },
            StepKind.SUCCEED: set(),
            StepKind.FAIL: set(),
        }[self.kind]
        if any((v is None) != (k not in allowed) for k, v in fields.items()):
            raise SkillIRRefusal("step has missing or extraneous kind-specific fields")
        for key in allowed - {"capability_version"}:
            _text(key, fields[key])
        if self.kind is StepKind.ACTION and (
            type(self.capability_version) is not int or self.capability_version < 1
        ):
            raise SkillIRRefusal("capability version must be positive")


@dataclass(frozen=True, slots=True)
class SkillIR:
    skill_id: str
    version: int
    goal_id: str
    target_kind: str
    entry_step_id: str
    steps: tuple[SkillIRStep, ...]
    provenance: Provenance
    max_steps: int = 32
    max_actions: int = 10

    def __post_init__(self) -> None:
        for key in ("skill_id", "goal_id", "target_kind", "entry_step_id"):
            _text(key, getattr(self, key))
        if type(self.version) is not int or self.version < 1:
            raise SkillIRRefusal("version must be positive")
        if not isinstance(self.provenance, Provenance):
            raise SkillIRRefusal("Skill provenance is required")
        if (type(self.max_steps) is not int or not 1 <= self.max_steps <= 32
                or type(self.max_actions) is not int
                or not 1 <= self.max_actions <= 10):
            raise SkillIRRefusal("bounded step/action budgets required")
        if (not isinstance(self.steps, tuple) or not 1 <= len(self.steps) <= 32
                or any(not isinstance(s, SkillIRStep) for s in self.steps)):
            raise SkillIRRefusal("bounded typed Skill IR steps required")


@dataclass(frozen=True, slots=True)
class CompiledSkillIR:
    """Only returned after checking against an externally trusted Body catalogue."""

    program: SkillIR
    capabilities: tuple[PhysicalCapability, ...]
    predicates: frozenset[str]


def compile_skill_ir(
    program: SkillIR,
    *,
    trusted_capabilities: tuple[PhysicalCapability, ...],
    trusted_predicates: frozenset[str],
) -> CompiledSkillIR:
    """Pure compile-time admission. NOT installation/physical authorization."""
    if not isinstance(program, SkillIR):
        raise SkillIRRefusal("typed Skill IR required")
    if not isinstance(trusted_capabilities, tuple) or any(
        not isinstance(c, PhysicalCapability) for c in trusted_capabilities
    ):
        raise SkillIRRefusal("trusted WorldBody capabilities required")
    if not isinstance(trusted_predicates, frozenset) or any(
        not isinstance(p, str) or not p.strip() for p in trusted_predicates
    ):
        raise SkillIRRefusal("trusted predicate identifiers required")
    nodes = {s.step_id: s for s in program.steps}
    if len(nodes) != len(program.steps) or program.entry_step_id not in nodes:
        raise SkillIRRefusal("duplicate or missing entry step")
    caps = {(c.capability_ref, c.version): c for c in trusted_capabilities}
    if len(caps) != len(trusted_capabilities):
        raise SkillIRRefusal("ambiguous WorldBody capability catalogue")
    for step in program.steps:
        if step.kind is StepKind.CHECK and step.predicate_ref not in trusted_predicates:
            raise SkillIRRefusal("unsupported observation predicate")
        if step.kind is StepKind.ACTION:
            cap = caps.get((step.capability_ref, step.capability_version))
            if (cap is None or not cap.available
                    or cap.body_channel != step.body_channel
                    or cap.target_kind != program.target_kind):
                raise SkillIRRefusal("unavailable or mismatched WorldBody capability")

    visiting: set[str] = set()
    cost: dict[str, tuple[int, int]] = {}

    def bound(step_id: str) -> tuple[int, int]:
        if step_id not in nodes:
            raise SkillIRRefusal("Skill IR transition target missing")
        if step_id in visiting:
            raise SkillIRRefusal("Skill IR cycles/recursion not admitted in v0.1")
        if step_id in cost:
            return cost[step_id]
        visiting.add(step_id)
        step = nodes[step_id]
        successors = (
            (step.on_true, step.on_false) if step.kind is StepKind.CHECK else
            (step.on_outcome, step.on_denied) if step.kind is StepKind.ACTION else ()
        )
        tails = [bound(ref) for ref in successors]
        result = (
            1 + max((n for n, _ in tails), default=0),
            (1 if step.kind is StepKind.ACTION else 0)
            + max((n for _, n in tails), default=0),
        )
        visiting.remove(step_id)
        cost[step_id] = result
        return result

    steps, actions = bound(program.entry_step_id)
    if len(cost) != len(nodes):
        raise SkillIRRefusal("unreachable Skill IR step")
    if steps > program.max_steps or actions > program.max_actions:
        raise SkillIRRefusal("Skill IR exceeds finite execution budget")
    return CompiledSkillIR(program, trusted_capabilities, trusted_predicates)


@dataclass(slots=True)
class _CursorLineage:
    revision: int = 0


@dataclass(frozen=True, slots=True)
class L0SkillCursor:
    """Immutable, lineage-fenced one-Skill execution position (not durable state)."""

    compiled: CompiledSkillIR
    scope: ScopeRef
    intent_id: str
    skill_execution_id: str
    target_ref: str
    step_id: str
    steps_taken: int = 0
    actions_proposed: int = 0
    pending_action_id: str | None = None
    pending_native_seq: int | None = None
    stopped: bool = False
    _lineage: _CursorLineage = field(
        default_factory=_CursorLineage, repr=False, compare=False,
    )
    _revision: int = field(default=0, repr=False, compare=False)

    @property
    def current(self) -> bool:
        return self._revision == self._lineage.revision


@dataclass(frozen=True, slots=True)
class QualifiedPredicate:
    """Read-only trusted adapter verdict, tied to the actual native readback."""

    predicate_ref: str
    readback: PhysicalReadback
    value: bool | None


@dataclass(frozen=True, slots=True)
class QualifiedActionOutcome:
    """Physical owner witness, not something the LLM/L0 may manufacture.

    Real integration must verify original native ACK/readback and WAL close
    before supplying this object. A typed object alone is not proof of either.
    """

    action_id: str
    scope: ScopeRef
    native_seq: int
    source: Provenance
    consequence_attested: bool
    durable_closed: bool


@dataclass(frozen=True, slots=True)
class L0Decision:
    status: str
    cursor: L0SkillCursor
    proposal: PhysicalActionProposalReceipt | None = None


def start_l0_skill(
    compiled: CompiledSkillIR,
    *, scope: ScopeRef, intent_owner: IntentCommitment,
    skill_execution: SkillExecution, target_ref: str,
) -> L0SkillCursor:
    if not isinstance(compiled, CompiledSkillIR):
        raise SkillIRRefusal("compile Skill IR before starting")
    if not isinstance(scope, ScopeRef) or not scope.world_session_id:
        raise SkillIRRefusal("live Self/World scope required")
    _text("target_ref", target_ref)
    program = compiled.program
    _require_owner(program, intent_owner, skill_execution)
    assert intent_owner.current_intent is not None
    return L0SkillCursor(
        compiled, scope, intent_owner.current_intent.intent_id,
        skill_execution.execution_id, target_ref, program.entry_step_id,
    )


def step_l0_skill(
    cursor: L0SkillCursor, *,
    intent_owner: IntentCommitment,
    skill_execution: SkillExecution,
    supervisor: ActionSupervisor,
    readback: PhysicalReadback | None,
    at_ns: int, provenance: Provenance,
    action_id: str | None = None,
    predicate: QualifiedPredicate | None = None,
    outcome: QualifiedActionOutcome | None = None,
) -> L0Decision:
    """At most one pure CPU step; only ACTION calls the nonissuing ActionPort."""
    if not isinstance(cursor, L0SkillCursor) or not cursor.current or cursor.stopped:
        raise SkillIRRefusal("stopped or stale L0 Skill cursor")
    if (not isinstance(supervisor, ActionSupervisor)
            or type(at_ns) is not int or at_ns < 0
            or not isinstance(provenance, Provenance)):
        raise SkillIRRefusal("invalid supervisor/time/provenance")
    program = cursor.compiled.program
    _require_owner(program, intent_owner, skill_execution)
    if (intent_owner.current_intent is None
            or intent_owner.current_intent.intent_id != cursor.intent_id
            or skill_execution.execution_id != cursor.skill_execution_id):
        raise SkillIRRefusal("L0 cursor owner changed")
    if (readback is not None and (
        not isinstance(readback, PhysicalReadback)
        or readback.scope != cursor.scope or not readback.body_viable
    )):
        raise SkillIRRefusal("World/session/Body readback stale or unviable")

    # A proposal is not a native issue. Never propose a second one until the
    # existing supervisor and trusted physical owner both settle the first.
    if cursor.pending_action_id is not None:
        if action_id is not None or predicate is not None:
            raise SkillIRRefusal("cannot choose another Action while one is pending")
        try:
            terminal = supervisor.get(cursor.pending_action_id)
        except UnknownSupervisedAction:
            return L0Decision("AWAIT_PHYSICAL_OUTCOME", cursor)
        if (terminal.intent_id != cursor.intent_id
                or terminal.skill_execution_id != cursor.skill_execution_id):
            raise SkillIRRefusal("supervised Action belongs to a different owner")
        if terminal.state in {ActionState.UNKNOWN, ActionState.TIMEOUT}:
            return L0Decision("STOP_UNKNOWN", _advance(cursor, stopped=True))
        if terminal.state not in {ActionState.OUTCOME, ActionState.DENIED}:
            return L0Decision("AWAIT_PHYSICAL_OUTCOME", cursor)
        if terminal.state is ActionState.OUTCOME:
            if outcome is None or readback is None:
                return L0Decision("AWAIT_QUALIFIED_OUTCOME", cursor)
            if (not isinstance(outcome, QualifiedActionOutcome)
                    or outcome.action_id != cursor.pending_action_id
                    or outcome.scope != cursor.scope
                    or type(outcome.native_seq) is not int
                    or outcome.native_seq <= cursor.pending_native_seq
                    or not isinstance(outcome.source, Provenance)
                    or outcome.native_seq != readback.seq
                    or outcome.source != readback.source
                    or not outcome.consequence_attested
                    or not outcome.durable_closed):
                return L0Decision("STOP_UNKNOWN", _advance(cursor, stopped=True))
        elif outcome is not None:
            raise SkillIRRefusal("denied Action must not carry native success")
        node = _find_node(program, cursor.step_id)
        if node.kind is not StepKind.ACTION:
            raise SkillIRRefusal("pending Action no longer matches IR node")
        return L0Decision(
            "ADVANCED",
            _advance(
                cursor,
                step_id=(
                    node.on_outcome if terminal.state is ActionState.OUTCOME
                    else node.on_denied
                ),
                steps_taken=cursor.steps_taken + 1,
                pending_action_id=None, pending_native_seq=None,
            ),
        )

    if action_id is not None and _find_node(program, cursor.step_id).kind is not StepKind.ACTION:
        raise SkillIRRefusal("Action ID provided outside Action IR step")
    if outcome is not None:
        raise SkillIRRefusal("unrequested physical outcome")

    node = _find_node(program, cursor.step_id)
    if node.kind in {StepKind.SUCCEED, StepKind.FAIL}:
        if action_id is not None or predicate is not None:
            raise SkillIRRefusal("terminal IR step cannot create new Action")
        return L0Decision(
            "SKILL_SUCCESS_CANDIDATE" if node.kind is StepKind.SUCCEED
            else "SKILL_FAILURE_CANDIDATE",
            _advance(cursor, stopped=True, steps_taken=cursor.steps_taken + 1),
        )

    if readback is None:
        return L0Decision("YIELD_OBSERVATION", cursor)
    if cursor.target_ref not in readback.observed_target_refs:
        raise SkillIRRefusal("selected Target no longer observed; never retarget")
    if cursor.steps_taken >= program.max_steps:
        raise SkillIRRefusal("L0 step budget exhausted")

    if node.kind is StepKind.CHECK:
        if predicate is None:
            return L0Decision("YIELD_OBSERVATION", cursor)
        if (not isinstance(predicate, QualifiedPredicate)
                or predicate.predicate_ref != node.predicate_ref
                or predicate.readback != readback
                or predicate.value is not None
                and type(predicate.value) is not bool):
            raise SkillIRRefusal("unqualified predicate observation")
        if predicate.value is None:
            return L0Decision("YIELD_OBSERVATION", cursor)
        return L0Decision(
            "ADVANCED",
            _advance(
                cursor,
                step_id=node.on_true if predicate.value else node.on_false,
                steps_taken=cursor.steps_taken + 1,
            ),
        )

    if predicate is not None:
        raise SkillIRRefusal("unexpected predicate on Action step")
    if cursor.actions_proposed >= program.max_actions:
        raise SkillIRRefusal("L0 Action budget exhausted")
    _text("action_id", action_id)
    cap = next(
        (c for c in cursor.compiled.capabilities
         if c.capability_ref == node.capability_ref
         and c.version == node.capability_version), None,
    )
    if cap is None:
        raise SkillIRRefusal("compiled physical capability unavailable")
    binding = PhysicalActionBinding(
        scope=cursor.scope, intent_id=cursor.intent_id,
        goal_id=program.goal_id, skill_id=program.skill_id,
        skill_version=program.version,
        skill_execution_id=cursor.skill_execution_id,
        action_id=action_id, capability_ref=cap.capability_ref,
        capability_version=cap.version, body_channel=cap.body_channel,
        target_kind=program.target_kind, target_ref=cursor.target_ref,
        native_seq=readback.seq, native_request_id=readback.request_id,
        native_source=readback.source,
    )
    proposed = propose_bound_physical_action(
        binding, capability=cap, readback=readback,
        intent_owner=intent_owner, skill_execution=skill_execution,
        supervisor=supervisor, at_ns=at_ns, provenance=provenance,
    )
    return L0Decision(
        "ACTION_PROPOSED",
        _advance(
            cursor, pending_action_id=action_id, pending_native_seq=readback.seq,
            actions_proposed=cursor.actions_proposed + 1,
        ),
        proposed,
    )


def _find_node(program: SkillIR, step_id: str) -> SkillIRStep:
    return next(s for s in program.steps if s.step_id == step_id)


def _require_owner(
    program: SkillIR, intent_owner: IntentCommitment,
    skill_execution: SkillExecution,
) -> None:
    if (not isinstance(intent_owner, IntentCommitment)
            or not isinstance(skill_execution, SkillExecution)
            or intent_owner.current_intent is None
            or intent_owner.pending_reconsideration is not None
            or intent_owner.current_intent.objective != program.goal_id
            or skill_execution.intent_id != intent_owner.current_intent.intent_id
            or skill_execution.skill_id != program.skill_id
            or skill_execution.state is not SkillState.STARTED
            or not skill_execution.is_current_snapshot):
        raise SkillIRRefusal("current owned Intent/Skill required")


def _advance(cursor: L0SkillCursor, **changes: object) -> L0SkillCursor:
    if not cursor.current:
        raise SkillIRRefusal("cannot advance stale cursor")
    next_cursor = replace(cursor, **changes, _revision=cursor._revision + 1)
    cursor._lineage.revision = next_cursor._revision
    return next_cursor


def _text(name: str, value: object) -> None:
    if not isinstance(value, str) or not value.strip():
        raise SkillIRRefusal(f"{name} must be nonblank")
