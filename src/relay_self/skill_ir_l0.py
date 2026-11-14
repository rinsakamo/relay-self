"""#843: bounded Skill IR and CPU L0 interpreter (nonissuing DEV shadow).

This is a transient program counter, not another Intent, Skill, Action, or
physical owner. Only an existing Physical ActionPort may propose a physical
Action; only the separately qualified physical issuer may authorize/issue it.
Model-generated IR is always a candidate, never a capability or installation.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TypeAlias

from relay_self.action import ActionState
from relay_self.action_supervision import ActionSupervisor
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
    """An IR, owner, source, or transition is not eligible for L0."""


@dataclass(frozen=True, slots=True)
class CheckStep:
    step_id: str
    predicate_ref: str
    if_true: str
    if_false: str
    if_unknown: str


@dataclass(frozen=True, slots=True)
class ActionStep:
    step_id: str
    capability_ref: str
    capability_version: int
    after_outcome: str


@dataclass(frozen=True, slots=True)
class EndStep:
    step_id: str
    result: str  # SUCCESS_CANDIDATE, FAILURE_CANDIDATE, UNRESOLVED


IRStep: TypeAlias = CheckStep | ActionStep | EndStep


@dataclass(frozen=True, slots=True)
class SkillIR:
    """Immutable task-scoped *candidate*; not an admitted executable grant."""

    skill_id: str
    version: int
    origin_task_ref: str
    generation: int
    scope: ScopeRef
    goal_id: str
    target_kind: str
    target_ref: str
    provenance: Provenance
    entry: str
    steps: tuple[IRStep, ...]
    max_actions: int
    max_duration_ns: int


@dataclass(frozen=True, slots=True)
class CompiledSkillIR:
    """Static validation result, still NOT Self acceptance or physical grant."""

    ir: SkillIR
    capabilities: tuple[PhysicalCapability, ...]
    predicate_refs: frozenset[str]


@dataclass(frozen=True, slots=True)
class PredicateWitness:
    """Typed gateway projection. Construction alone does not authenticate bytes."""

    scope: ScopeRef
    target_ref: str
    predicate_ref: str
    truth: str  # TRUE, FALSE, UNKNOWN
    seq: int
    request_id: str
    source: Provenance


@dataclass(frozen=True, slots=True)
class L0StepReceipt:
    """An *instruction* or read-only status, never a native Action issue."""

    status: str
    step_id: str
    action_id: str | None = None
    capability_ref: str | None = None
    reason: str | None = None


def _text(name: str, value: object) -> None:
    if type(value) is not str or not value.strip():
        raise SkillIRRefusal(f"{name} must be nonblank text")


def _positive(name: str, value: object, maximum: int) -> None:
    if type(value) is not int or not 1 <= value <= maximum:
        raise SkillIRRefusal(f"{name} exceeds its bounded positive range")



def parse_skill_ir_json(
    raw: str,
    *,
    scope: ScopeRef,
    provenance: Provenance,
    origin_task_ref: str,
    generation: int,
) -> SkillIR:
    """Strict untrusted L2 JSON -> typed CANDIDATE, no execution or admission.

    Native scope, task generation and provenance must come from the caller's
    qualified task envelope, never from model-supplied JSON fields.
    """
    if type(raw) is not str or len(raw) > 16_384 or not raw.strip():
        raise SkillIRRefusal("bounded JSON Skill IR required")
    if not isinstance(scope, ScopeRef) or not isinstance(provenance, Provenance):
        raise SkillIRRefusal("trusted task scope and provenance required")
    _text("origin_task_ref", origin_task_ref)
    _positive("generation", generation, 1_000_000_000)

    def exact_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in pairs:
            if key in result:
                raise SkillIRRefusal("duplicate JSON key")
            result[key] = value
        return result

    def invalid_constant(value: str) -> None:
        raise SkillIRRefusal(f"invalid nonfinite JSON constant: {value}")

    try:
        data = json.loads(
            raw, object_pairs_hook=exact_object, parse_constant=invalid_constant
        )
    except (ValueError, TypeError) as exc:
        raise SkillIRRefusal("malformed untrusted Skill IR JSON") from exc
    keys = {
        "skill_id", "version", "goal_id", "target_kind", "target_ref",
        "entry", "steps", "max_actions", "max_duration_ns",
    }
    if type(data) is not dict or set(data) != keys or type(data["steps"]) is not list:
        raise SkillIRRefusal("exact bounded Skill IR JSON fields required")
    if not 1 <= len(data["steps"]) <= 32:
        raise SkillIRRefusal("Skill IR JSON needs 1..32 steps")

    steps: list[IRStep] = []
    for step in data["steps"]:
        if type(step) is not dict or "kind" not in step:
            raise SkillIRRefusal("typed Skill IR JSON step required")
        kind = step["kind"]
        if kind == "CHECK":
            expected = {
                "kind", "step_id", "predicate_ref",
                "if_true", "if_false", "if_unknown",
            }
            if set(step) != expected:
                raise SkillIRRefusal("CHECK step has invalid fields")
            steps.append(CheckStep(
                step["step_id"], step["predicate_ref"], step["if_true"],
                step["if_false"], step["if_unknown"],
            ))
        elif kind == "ACTION":
            expected = {
                "kind", "step_id", "capability_ref",
                "capability_version", "after_outcome",
            }
            if set(step) != expected:
                raise SkillIRRefusal("ACTION step has invalid fields")
            steps.append(ActionStep(
                step["step_id"], step["capability_ref"],
                step["capability_version"], step["after_outcome"],
            ))
        elif kind == "END":
            if set(step) != {"kind", "step_id", "result"}:
                raise SkillIRRefusal("END step has invalid fields")
            steps.append(EndStep(step["step_id"], step["result"]))
        else:
            raise SkillIRRefusal("unknown IR JSON kind")
    return SkillIR(
        skill_id=data["skill_id"], version=data["version"],
        origin_task_ref=origin_task_ref, generation=generation,
        scope=scope, goal_id=data["goal_id"], target_kind=data["target_kind"],
        target_ref=data["target_ref"], provenance=provenance,
        entry=data["entry"], steps=tuple(steps),
        max_actions=data["max_actions"], max_duration_ns=data["max_duration_ns"],
    )


def compile_skill_ir(
    ir: SkillIR,
    *,
    capabilities: tuple[PhysicalCapability, ...],
    predicate_refs: frozenset[str],
) -> CompiledSkillIR:
    """Validate a finite DAG against an externally supplied WorldBody catalogue.

    No JSON code execution, arbitrary predicates, loops, native issue, or
    installation. The caller must independently attest catalogue provenance.
    """
    if not isinstance(ir, SkillIR):
        raise SkillIRRefusal("typed SkillIR required")
    for name in ("skill_id", "origin_task_ref", "goal_id", "target_kind", "target_ref", "entry"):
        _text(name, getattr(ir, name))
    _positive("version", ir.version, 1_000_000)
    _positive("generation", ir.generation, 1_000_000_000)
    _positive("max_actions", ir.max_actions, 10)
    _positive("max_duration_ns", ir.max_duration_ns, 60_000_000_000)
    if not isinstance(ir.scope, ScopeRef) or not ir.scope.world_session_id:
        raise SkillIRRefusal("Skill IR must bind a real Self/World session")
    if not isinstance(ir.provenance, Provenance):
        raise SkillIRRefusal("Skill IR requires task provenance")
    if type(ir.steps) is not tuple or not 1 <= len(ir.steps) <= 32:
        raise SkillIRRefusal("Skill IR needs at most 32 immutable steps")
    if type(capabilities) is not tuple or not all(
        isinstance(cap, PhysicalCapability) for cap in capabilities
    ):
        raise SkillIRRefusal("trusted typed capability catalogue required")
    if type(predicate_refs) is not frozenset or not all(
        type(x) is str and x.strip() for x in predicate_refs
    ):
        raise SkillIRRefusal("trusted predicate catalogue required")

    catalogue = {(cap.capability_ref, cap.version): cap for cap in capabilities}
    if len(catalogue) != len(capabilities):
        raise SkillIRRefusal("duplicate WorldBody capability identity")
    steps: dict[str, IRStep] = {}
    for step in ir.steps:
        if type(step) not in (CheckStep, ActionStep, EndStep):
            raise SkillIRRefusal("unknown IR step; no executable Python or code")
        _text("step_id", step.step_id)
        if step.step_id in steps:
            raise SkillIRRefusal("duplicate IR step identity")
        steps[step.step_id] = step
        if isinstance(step, CheckStep):
            if step.predicate_ref not in predicate_refs:
                raise SkillIRRefusal("predicate not present in trusted catalogue")
            for ref in (step.if_true, step.if_false, step.if_unknown):
                _text("check transition", ref)
        elif isinstance(step, ActionStep):
            _positive("capability_version", step.capability_version, 1_000_000)
            cap = catalogue.get((step.capability_ref, step.capability_version))
            if cap is None or not cap.available or cap.target_kind != ir.target_kind:
                raise SkillIRRefusal("Action not admitted by WorldBody catalogue")
            _text("action next step", step.after_outcome)
        elif step.result not in {
            "SUCCESS_CANDIDATE", "FAILURE_CANDIDATE", "UNRESOLVED"
        }:
            raise SkillIRRefusal("unknown terminal candidate status")

    if ir.entry not in steps:
        raise SkillIRRefusal("entry step missing")
    # All branches must terminate; reject unreachable payload and every cycle.
    visiting: set[str] = set()
    visited: dict[str, int] = {}

    def bound(ref: str) -> int:
        if ref not in steps:
            raise SkillIRRefusal("IR transition points to missing step")
        if ref in visiting:
            raise SkillIRRefusal("unbounded/cyclic Skill IR is forbidden")
        if ref in visited:
            return visited[ref]
        visiting.add(ref)
        step = steps[ref]
        if isinstance(step, CheckStep):
            children = (step.if_true, step.if_false, step.if_unknown)
            count = max(bound(child) for child in children)
        elif isinstance(step, ActionStep):
            count = 1 + bound(step.after_outcome)
        else:
            count = 0
        visiting.remove(ref)
        visited[ref] = count
        return count

    longest = bound(ir.entry)
    if len(visited) != len(steps):
        raise SkillIRRefusal("unreachable IR steps are not admitted")
    if longest > ir.max_actions:
        raise SkillIRRefusal("longest Action path exceeds budget")
    return CompiledSkillIR(ir, capabilities, predicate_refs)


class L0SkillInterpreter:
    """One bounded, CPU-only, nonissuing sequential cursor over a compiled IR.

    One Action request is emitted once per interpreter cursor. A physical
    proposal must still traverse Physical ActionPort; Action outcomes must be
    read from the existing ActionSupervisor, never from an LLM assertion.
    """

    def __init__(
        self,
        compiled: CompiledSkillIR,
        *,
        intent_owner: IntentCommitment,
        skill_execution: SkillExecution,
        supervisor: ActionSupervisor,
        scope: ScopeRef,
        admitted_version: int,
        admitted_generation: int,
        started_ns: int,
    ) -> None:
        if not isinstance(compiled, CompiledSkillIR):
            raise SkillIRRefusal("compile and verify Skill IR before L0")
        if compile_skill_ir(
            compiled.ir, capabilities=compiled.capabilities,
            predicate_refs=compiled.predicate_refs,
        ) != compiled:
            raise SkillIRRefusal("forged compiled Skill IR")
        if not isinstance(intent_owner, IntentCommitment) or not isinstance(
            skill_execution, SkillExecution
        ) or not isinstance(supervisor, ActionSupervisor):
            raise SkillIRRefusal("existing Intent/Skill/Action owners required")
        if scope != compiled.ir.scope or (
            admitted_version != compiled.ir.version
            or admitted_generation != compiled.ir.generation
        ):
            raise SkillIRRefusal("stale Skill version/generation or foreign World")
        if type(started_ns) is not int or started_ns < 0:
            raise SkillIRRefusal("host-monotonic start is required")
        self.compiled = compiled
        self.intent_owner = intent_owner
        self.skill_execution = skill_execution
        self.supervisor = supervisor
        self._pc = compiled.ir.entry
        self._started_ns = started_ns
        self._last_ns = started_ns
        self._last_seq = -1
        self._action_count = 0
        self._pending: str | None = None
        self._proposed = False
        self._stopped: str | None = None
        if not self._current_owner():
            raise SkillIRRefusal("IR does not match current committed Intent/Skill")

    def _current_owner(self) -> bool:
        owner = self.intent_owner.current_intent
        ir = self.compiled.ir
        skill = self.skill_execution
        return bool(
            owner is not None and owner.objective == ir.goal_id
            and owner.intent_id == skill.intent_id
            and self.intent_owner.pending_reconsideration is None
            and skill.is_current_snapshot and skill.state is SkillState.STARTED
            and skill.skill_id == ir.skill_id
        )

    def _step(self) -> IRStep:
        return next(step for step in self.compiled.ir.steps if step.step_id == self._pc)

    @property
    def pending_action_id(self) -> str | None:
        return self._pending

    def interrupt(self, reason: str) -> L0StepReceipt:
        """Local halt only. The Intent/Skill owner and any issued Action survive."""
        _text("interrupt reason", reason)
        self._stopped = "INTERRUPTED"
        return L0StepReceipt("STOP", self._pc, reason=reason)

    def tick(
        self, *, now_ns: int, witness: PredicateWitness | None = None
    ) -> L0StepReceipt:
        if type(now_ns) is not int or now_ns < self._last_ns:
            raise SkillIRRefusal("nonmonotonic L0 host clock")
        self._last_ns = now_ns
        if self._stopped is not None:
            return L0StepReceipt("STOP", self._pc, reason=self._stopped)
        if now_ns - self._started_ns > self.compiled.ir.max_duration_ns:
            self._stopped = "DEADLINE"
            return L0StepReceipt("STOP", self._pc, reason="DEADLINE")

        # Never re-emit an already offered Action. Supervision is external and
        # must continue even after L0 is interrupted or the deadline expires.
        if self._pending is not None:
            if witness is not None:
                raise SkillIRRefusal("native witness cannot replace Action outcome")
            matching = [
                x for x in self.supervisor.recorded_actions
                if x.action_id == self._pending
            ]
            if not matching or matching[0].state is ActionState.ISSUED:
                return L0StepReceipt("AWAIT_ACTION", self._pc, action_id=self._pending)
            if not self._proposed:
                self._stopped = "UNPROPOSED_ACTION"
                return L0StepReceipt("STOP", self._pc, reason=self._stopped)
            action = matching[0]
            if (
                action.intent_id != self.skill_execution.intent_id
                or action.skill_execution_id != self.skill_execution.execution_id
            ):
                self._stopped = "FOREIGN_ACTION"
                return L0StepReceipt("STOP", self._pc, reason=self._stopped)
            if action.state is not ActionState.OUTCOME:
                self._stopped = "ACTION_NOT_OUTCOME"
                return L0StepReceipt("STOP", self._pc, reason=self._stopped)
            node = self._step()
            if not isinstance(node, ActionStep):
                raise SkillIRRefusal("pending Action not at an Action step")
            self._pending = None
            self._proposed = False
            self._pc = node.after_outcome
            if not self._current_owner():
                self._stopped = "OWNER_CHANGED"
                return L0StepReceipt("STOP", self._pc, reason=self._stopped)
            return L0StepReceipt("ADVANCED", self._pc)

        if not self._current_owner():
            self._stopped = "OWNER_CHANGED"
            return L0StepReceipt("STOP", self._pc, reason=self._stopped)
        node = self._step()
        if isinstance(node, EndStep):
            self._stopped = "TERMINAL_CANDIDATE"
            return L0StepReceipt("TERMINAL_CANDIDATE", node.step_id, reason=node.result)
        if isinstance(node, CheckStep):
            if witness is None:
                return L0StepReceipt("NEED_OBSERVATION", node.step_id)
            ir = self.compiled.ir
            if (
                not isinstance(witness, PredicateWitness)
                or witness.scope != ir.scope or witness.target_ref != ir.target_ref
                or witness.predicate_ref != node.predicate_ref
                or witness.truth not in {"TRUE", "FALSE", "UNKNOWN"}
                or type(witness.seq) is not int or witness.seq <= self._last_seq
                or type(witness.request_id) is not str or not witness.request_id
                or not isinstance(witness.source, Provenance)
                or witness.source.reference != f"{ir.scope.world_session_id}:{witness.seq}"
            ):
                self._stopped = "UNQUALIFIED_OBSERVATION"
                return L0StepReceipt("STOP", node.step_id, reason=self._stopped)
            self._last_seq = witness.seq
            self._pc = {
                "TRUE": node.if_true,
                "FALSE": node.if_false,
                "UNKNOWN": node.if_unknown,
            }[witness.truth]
            return L0StepReceipt("ADVANCED", self._pc)

        if witness is not None:
            raise SkillIRRefusal("unexpected observation at Action step")
        if self._action_count >= self.compiled.ir.max_actions:
            self._stopped = "ACTION_BUDGET"
            return L0StepReceipt("STOP", self._pc, reason=self._stopped)
        if self.supervisor.open_actions or any(
            x.state in {ActionState.UNKNOWN, ActionState.TIMEOUT}
            for x in self.supervisor.recorded_actions
        ):
            self._stopped = "BODY_BUSY_OR_UNKNOWN"
            return L0StepReceipt("STOP", self._pc, reason=self._stopped)
        candidate_id = f"{self.skill_execution.execution_id}-l0-{self._action_count + 1}"
        if any(x.action_id == candidate_id for x in self.supervisor.recorded_actions):
            self._stopped = "DUPLICATE_ACTION_ID"
            return L0StepReceipt("STOP", self._pc, reason=self._stopped)
        self._action_count += 1
        self._pending = candidate_id
        return L0StepReceipt(
            "PROPOSE_ACTION", node.step_id, self._pending, node.capability_ref
        )

    def propose_pending(
        self, *, readback: PhysicalReadback, at_ns: int, provenance: Provenance
    ) -> PhysicalActionProposalReceipt:
        """Only make a PROPOSED Action; never authorize, journal or issue."""
        if self._stopped is not None or self._pending is None or self._proposed:
            raise SkillIRRefusal("no new unproposed L0 Action request")
        if not self._current_owner():
            raise SkillIRRefusal("Intent/Skill changed before proposal")
        if not isinstance(readback, PhysicalReadback):
            raise SkillIRRefusal("typed native readback required")
        ir = self.compiled.ir
        if (
            readback.scope != ir.scope or readback.seq <= self._last_seq
            or readback.source.reference != f"{ir.scope.world_session_id}:{readback.seq}"
        ):
            raise SkillIRRefusal("stale or foreign native readback")
        node = self._step()
        if not isinstance(node, ActionStep):
            raise SkillIRRefusal("no active Action IR step")
        cap = next(
            (c for c in self.compiled.capabilities
             if c.capability_ref == node.capability_ref
             and c.version == node.capability_version),
            None,
        )
        if cap is None:
            raise SkillIRRefusal("trusted capability disappeared")
        owner = self.intent_owner.current_intent
        assert owner is not None
        binding = PhysicalActionBinding(
            scope=ir.scope, intent_id=owner.intent_id, goal_id=ir.goal_id,
            skill_id=ir.skill_id, skill_version=ir.version,
            skill_execution_id=self.skill_execution.execution_id,
            action_id=self._pending, capability_ref=cap.capability_ref,
            capability_version=cap.version, body_channel=cap.body_channel,
            target_kind=cap.target_kind, target_ref=ir.target_ref,
            native_seq=readback.seq, native_request_id=readback.request_id,
            native_source=readback.source,
        )
        result = propose_bound_physical_action(
            binding, capability=cap, readback=readback,
            intent_owner=self.intent_owner, skill_execution=self.skill_execution,
            supervisor=self.supervisor, at_ns=at_ns, provenance=provenance,
        )
        self._proposed = True
        self._last_seq = readback.seq
        return result
