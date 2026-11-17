"""Bounded physical Skill IR v0 (CPU-only; no Action issuer or owner).

A selected #844 L1 Option + the existing committed Intent and SkillExecution
are prerequisites. An IR merely describes finite steps; it never creates a
physical capability, a Goal, an Intent, a SkillExecution, an Action authority,
or an Outcome. In particular, EAT@1 is the existing supervised *parent*
capability; equip/consume are NOT two separately dispatched IR Actions.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field, replace
from enum import Enum

from relay_self.action import ActionLifecycle, ActionState
from relay_self.action_supervision import ActionSupervisor
from relay_self.cognitive_minimal_dev import Option, Selection
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
from relay_self.skill_invocation import (
    SkillBudget,
    SkillConstraints,
    SkillDefinition,
    SkillInvocation,
    SkillInvocationRefusal,
    SkillTarget,
    bind_skill_invocation,
)


class SkillIRRefusal(ValueError):
    """Invalid, unowned, stale or physically unsupported Skill step."""


class StepKind(str, Enum):
    CHECK_TARGET = "CHECK_TARGET"
    ACTION = "ACTION"


class SkillOrigin(str, Enum):
    INNATE = "INNATE"
    LEARNED = "LEARNED"


@dataclass(frozen=True, slots=True)
class SkillStep:
    kind: StepKind
    capability_ref: str | None = None
    capability_version: int | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.kind, StepKind):
            raise SkillIRRefusal("unknown Skill instruction")
        if self.kind is StepKind.ACTION:
            if (not _text(self.capability_ref)
                    or type(self.capability_version) is not int
                    or self.capability_version < 1):
                raise SkillIRRefusal("ACTION needs an existing versioned capability")
        elif self.capability_ref is not None or self.capability_version is not None:
            raise SkillIRRefusal("CHECK_TARGET cannot create a capability")


@dataclass(frozen=True, slots=True)
class PhysicalSkillIR:
    """Immutable finite linear IR; learned and innate share this representation.

    No loops, arbitrary predicates/code, nested runs or implicit success.
    A learned IR is executable only when the existing Self owner supplies its
    registered (skill_id, version), not on L2 generation alone.
    """

    skill_id: str
    version: int
    goal_id: str
    target_kind: str
    steps: tuple[SkillStep, ...]
    origin: SkillOrigin
    provenance: Provenance
    invocation: SkillInvocation | None = None

    def __post_init__(self) -> None:
        if not all(_text(s) for s in (self.skill_id, self.goal_id, self.target_kind)):
            raise SkillIRRefusal("Skill and Goal identity required")
        if type(self.version) is not int or self.version < 1:
            raise SkillIRRefusal("positive Skill version required")
        if not isinstance(self.origin, SkillOrigin) or not isinstance(
            self.provenance, Provenance
        ):
            raise SkillIRRefusal("typed Skill provenance required")
        if (type(self.steps) is not tuple or not 1 <= len(self.steps) <= 8
                or not all(isinstance(s, SkillStep) for s in self.steps)
                or not any(s.kind is StepKind.ACTION for s in self.steps)):
            raise SkillIRRefusal("bounded nonempty executable Skill steps required")
        if sum(s.kind is StepKind.ACTION for s in self.steps) > 4:
            raise SkillIRRefusal("at most four physical Actions per Skill")
        if self.invocation is not None and (
            not isinstance(self.invocation, SkillInvocation)
            or self.invocation.skill_id != self.skill_id
            or self.invocation.skill_version != self.version
            or self.invocation.goal_id != self.goal_id
            or self.invocation.target.kind != self.target_kind
        ):
            raise SkillIRRefusal("bound invocation differs from compiled Skill")


@dataclass(frozen=True, slots=True)
class InitialSkillDescriptor:
    """Innate reference, not an unconditional executable Skill/Goal candidate."""

    skill_id: str
    goal_id: str | None
    target_kind: str | None
    capability_ref: str | None
    capability_version: int | None
    status: str


def initial_skill_descriptors() -> tuple[InitialSkillDescriptor, ...]:
    """Grounded in #844 and the existing Mineflayer protocol at its base HEAD.

    MOVE's opt-in bounded DEV parent uses verified bridge look/forward/
    clear_controls effects, but does NOT certify Paper tick STOP/settling.
    REST still lacks a qualified fatigue recovery mapping.
    ATTACK has a one-shot WAL issuer for ACK/hurt correlation.
    """
    return (
        InitialSkillDescriptor("MOVE", "EXPLORE_WORLD", "DESTINATION",
                               "MOVE", 1, "NATIVE_BOUNDED_MOVE_DEV_ISSUER_EXISTS"),
        InitialSkillDescriptor("EAT", "HUNGER_RELIEF", "FOOD", "EAT", 1,
                               "PROPOSAL_AND_EAT_DEV_ISSUER_EXISTS"),
        InitialSkillDescriptor("ATTACK", "DEFEND_SELF", "ZOMBIE",
                               "attack_entity", 1, "NATIVE_ACK_HURT_DEV_ISSUER_EXISTS"),
        InitialSkillDescriptor("REST", None, None, None, None, "UNMAPPED"),
    )


def compile_initial_skill(
    option: Option, *, capability: PhysicalCapability,
) -> PhysicalSkillIR:
    """Compile one already-Schema/L1-selected option; no target/Goal selection."""
    if not isinstance(option, Option) or not isinstance(capability, PhysicalCapability):
        raise SkillIRRefusal("selected Option and typed WorldBody capability required")
    descriptor = next((d for d in initial_skill_descriptors()
                       if d.skill_id == option.skill_id), None)
    definition = next((d for d in initial_skill_definitions()
                       if d.skill_id == option.skill_id), None)
    if (descriptor is None or definition is None
            or descriptor.capability_ref != definition.capability_ref
            or descriptor.capability_version != definition.capability_version
            or descriptor.capability_ref is None
            or option.goal_id != descriptor.goal_id
            or option.target_kind != descriptor.target_kind
            or option.skill_version != 1):
        raise SkillIRRefusal("no grounded initial Skill mapping")
    if (not capability.available or capability.capability_ref != descriptor.capability_ref
            or capability.version != descriptor.capability_version
            or capability.target_kind != descriptor.target_kind):
        raise SkillIRRefusal("WorldBody did not attest selected capability mapping")
    return PhysicalSkillIR(
        option.skill_id, option.skill_version, option.goal_id, option.target_kind,
        (SkillStep(StepKind.CHECK_TARGET),
         SkillStep(StepKind.ACTION, capability.capability_ref, capability.version)),
        SkillOrigin.INNATE, Provenance("innate-skill-ir", "cognitive-v0.1"),
    )



def initial_skill_definitions() -> tuple[SkillDefinition, ...]:
    """Ability ABI, not an innate Goal mapping or an Action authorization.

    The same MOVE@1 supports Goal-specific PLACE, relative step or entity
    range *arguments*. Existing WorldBody/physical issuer still determines
    which calls are executable. REST remains physically unmapped.
    """
    source = Provenance("innate-skill-definition", "cognitive-v0.1")
    return (
        SkillDefinition("MOVE", 1, "INNATE", source,
                        capability_ref="MOVE", capability_version=1),
        SkillDefinition("EAT", 1, "INNATE", source,
                        capability_ref="EAT", capability_version=1),
        SkillDefinition("ATTACK", 1, "INNATE", source,
                        capability_ref="attack_entity", capability_version=1),
        SkillDefinition("REST", 1, "INNATE", source),
    )


def compile_invoked_skill(
    selection: Selection,
    *,
    definition: SkillDefinition,
    target: SkillTarget,
    constraints: SkillConstraints,
    budget: SkillBudget,
    provenance: Provenance,
    capability: PhysicalCapability,
    arguments: tuple = (),
) -> PhysicalSkillIR:
    """Bind a Goal-independent innate/registered learned ability to L1 args.

    Generates the *same finite CHECK_TARGET/ACTION IR*, with a source-bound
    typed Invocation attached. It CANNOT issue an Action, register an L2
    definition, or let new Goals/TargetKinds bypass a physical issuer.
    """
    if (not isinstance(selection, Selection) or selection.status != "READY"
            or not isinstance(selection.option, Option)
            or not isinstance(selection.world_scope, ScopeRef)
            or not isinstance(definition, SkillDefinition)
            or not isinstance(capability, PhysicalCapability)
            or not isinstance(target, SkillTarget)
            or not isinstance(constraints, SkillConstraints)
            or not isinstance(budget, SkillBudget)
            or not isinstance(provenance, Provenance)):
        raise SkillIRRefusal("selected typed Skill Invocation and capability required")
    option = selection.option
    if (option.skill_id != definition.skill_id
            or option.skill_version != definition.version
            or option.target_ref != target.ref
            or option.target_kind != target.kind
            or option.arrival_contract != target.contract
            or definition.capability_ref is None
            or definition.capability_ref != capability.capability_ref
            or definition.capability_version != capability.version
            or not capability.available
            or capability.target_kind != target.kind):
        raise SkillIRRefusal("selected Skill/Target/capability do not match definition")
    if option.invocation is not None:
        # The Schema has already completed and frozen the call. L0 is not
        # allowed to rebind a Budget, constraint, preset, argument or source.
        invocation = option.invocation
        if (invocation.scope != selection.world_scope
                or invocation.definition_ref != definition.definition_ref
                or invocation.target != target
                or invocation.constraints != constraints
                or invocation.budget != budget
                or invocation.provenance != provenance
                or invocation.arguments != arguments):
            raise SkillIRRefusal("compiled parameters differ from L1-bound invocation")
        try:
            bind_skill_invocation(definition, invocation)
        except SkillInvocationRefusal as exc:
            raise SkillIRRefusal("selected invocation ABI is invalid") from exc
    else:
        # Transitional compatibility for existing unparameterized DEV tests.
        # No preset/parameterized physical Action privilege is implied.
        try:
            invocation = bind_skill_invocation(
                definition,
                SkillInvocation(
                    scope=selection.world_scope,
                    skill_id=definition.skill_id,
                    skill_version=definition.version,
                    definition_ref=definition.definition_ref,
                    goal_id=option.goal_id,
                    target=target,
                    constraints=constraints,
                    budget=budget,
                    provenance=provenance,
                    arguments=arguments,
                ),
            )
        except SkillInvocationRefusal as exc:
            raise SkillIRRefusal("typed Skill Invocation arguments invalid") from exc
    return PhysicalSkillIR(
        skill_id=definition.skill_id,
        version=definition.version,
        goal_id=invocation.goal_id,
        target_kind=invocation.target.kind,
        steps=(
            SkillStep(StepKind.CHECK_TARGET),
            SkillStep(StepKind.ACTION, capability.capability_ref, capability.version),
        ),
        origin=SkillOrigin(definition.origin),
        provenance=definition.provenance,
        invocation=invocation,
    )


@dataclass(frozen=True, slots=True)
class SkillCursor:
    """Ephemeral execution index, NOT a replacement SkillExecution owner.

    _lease is an in-process identity fence. Never serialize it as a restart
    permission; a restarted interpreter cannot resume an old cursor.
    """

    scope: ScopeRef
    intent_id: str
    execution_id: str
    skill_id: str
    version: int
    goal_id: str
    target_ref: str
    target_kind: str
    index: int
    action_count: int
    pending_action_id: str | None
    pending_native_source: Provenance | None
    blocked: bool
    deadline_ns: int
    _lease: object = field(repr=False, compare=False)
    invocation_ref: str | None = None


@dataclass(frozen=True, slots=True)
class SkillStepReceipt:
    status: str
    cursor: SkillCursor
    proposal: PhysicalActionProposalReceipt | None = None
    action_ref: str | None = None


@dataclass(frozen=True, slots=True)
class ActionOutcomeWitness:
    """Issuer-supplied evidence join, never fabricated by the interpreter.

    The issuer is responsible for authenticating this witness against its WAL,
    native source, parent Action and physical effect. This typed shape alone is
    not that authentication, nor independent server-side World qualification.
    """

    scope: ScopeRef
    action_id: str
    native_source: Provenance
    journal_closed: bool
    effect_correlated: bool

    def __post_init__(self) -> None:
        if (not isinstance(self.scope, ScopeRef)
                or not self.scope.world_session_id
                or not _text(self.action_id)
                or not isinstance(self.native_source, Provenance)
                or type(self.journal_closed) is not bool
                or type(self.effect_correlated) is not bool):
            raise SkillIRRefusal("malformed physical Outcome witness")


class FiniteSkillInterpreter:
    """Bounded single-run CPU controller, explicitly nonissuing.

    The local cursor table only fences repeated/stale interpreter calls. It is
    NOT durable lifecycle ownership and grants no recovery permission.
    """

    def __init__(self) -> None:
        self._lease = object()
        self._current: SkillCursor | None = None
        self._ir: PhysicalSkillIR | None = None

    def begin(
        self, selection: Selection, *, ir: PhysicalSkillIR,
        intent_owner: IntentCommitment, skill_execution: SkillExecution,
        registered_versions: frozenset[tuple[str, int]],
        deadline_ns: int,
    ) -> SkillCursor:
        if self._current is not None:
            raise SkillIRRefusal("interpreter already holds a Skill cursor")
        if (not isinstance(selection, Selection) or selection.status != "READY"
                or not isinstance(selection.option, Option)
                or not isinstance(selection.world_scope, ScopeRef)
                or not selection.world_scope.world_session_id
                or not isinstance(ir, PhysicalSkillIR)
                or not isinstance(registered_versions, frozenset)
                or (ir.skill_id, ir.version) not in registered_versions):
            raise SkillIRRefusal("Self-selected registered Skill required")
        option = selection.option
        if (ir.skill_id != option.skill_id or ir.version != option.skill_version
                or ir.goal_id != option.goal_id
                or ir.target_kind != option.target_kind
                or not _text(option.target_ref)):
            raise SkillIRRefusal("IR differs from selected Goal/Skill/Target")
        if ir.invocation is not None and (
            ir.invocation.scope != selection.world_scope
            or ir.invocation.target.ref != option.target_ref
            or ir.invocation.target.contract != option.arrival_contract
        ):
            raise SkillIRRefusal("selected Target/condition differs from Skill invocation")
        if option.invocation is not None and ir.invocation != option.invocation:
            raise SkillIRRefusal("L0 IR differs from completed L1 invocation")
        if not isinstance(intent_owner, IntentCommitment) or not isinstance(
            skill_execution, SkillExecution
        ):
            raise SkillIRRefusal("existing lifecycle owners required")
        owner = intent_owner.current_intent
        if (owner is None or owner.objective != option.goal_id
                or intent_owner.pending_reconsideration is not None
                or skill_execution.intent_id != owner.intent_id
                or skill_execution.skill_id != ir.skill_id
                or skill_execution.state is not SkillState.STARTED
                or not skill_execution.is_current_snapshot):
            raise SkillIRRefusal("Intent/Skill owner invalid or stale")
        if (type(deadline_ns) is not int
                or deadline_ns <= skill_execution.events[-1].at_ns):
            raise SkillIRRefusal("finite future deadline required")
        cursor = SkillCursor(
            selection.world_scope, owner.intent_id, skill_execution.execution_id,
            ir.skill_id, ir.version, ir.goal_id, option.target_ref,
            option.target_kind, 0, 0, None, None, False, deadline_ns, self._lease,
        )
        if ir.invocation is not None:
            cursor = replace(cursor, invocation_ref=ir.invocation.invocation_ref)
        self._current, self._ir = cursor, ir
        return cursor

    def _require_cursor(
        self, cursor: SkillCursor, *, at_ns: int,
        intent_owner: IntentCommitment, skill_execution: SkillExecution,
    ) -> PhysicalSkillIR:
        if (not isinstance(cursor, SkillCursor) or cursor is not self._current
                or cursor._lease is not self._lease
                or self._ir is None or cursor.blocked
                or cursor.invocation_ref != (
                    None if self._ir.invocation is None
                    else self._ir.invocation.invocation_ref
                )):
            raise SkillIRRefusal("stale, restarted, blocked or absent Skill cursor")
        if type(at_ns) is not int or not 0 <= at_ns < cursor.deadline_ns:
            raise SkillIRRefusal("Skill deadline expired")
        owner = intent_owner.current_intent if isinstance(
            intent_owner, IntentCommitment
        ) else None
        if (owner is None or owner.intent_id != cursor.intent_id
                or owner.objective != cursor.goal_id
                or intent_owner.pending_reconsideration is not None
                or not isinstance(skill_execution, SkillExecution)
                or skill_execution.execution_id != cursor.execution_id
                or skill_execution.intent_id != cursor.intent_id
                or skill_execution.skill_id != cursor.skill_id
                or skill_execution.state is not SkillState.STARTED
                or not skill_execution.is_current_snapshot):
            raise SkillIRRefusal("Skill/Intent was cancelled, released or stale")
        return self._ir

    def check_target(
        self, cursor: SkillCursor, *, readback: PhysicalReadback,
        intent_owner: IntentCommitment, skill_execution: SkillExecution,
        at_ns: int,
    ) -> SkillStepReceipt:
        ir = self._require_cursor(
            cursor, at_ns=at_ns, intent_owner=intent_owner,
            skill_execution=skill_execution,
        )
        if cursor.pending_action_id is not None or cursor.index >= len(ir.steps):
            raise SkillIRRefusal("not at a CHECK state")
        if ir.steps[cursor.index].kind is not StepKind.CHECK_TARGET:
            raise SkillIRRefusal("not a CHECK_TARGET step")
        if (not isinstance(readback, PhysicalReadback)
                or readback.scope != cursor.scope
                or not readback.body_viable
                or cursor.target_ref not in readback.observed_target_refs):
            # Lack of positive coverage is UNKNOWN, not proof of absence.
            raise SkillIRRefusal("target/viability UNKNOWN or stale: no Action")
        updated = replace(cursor, index=cursor.index + 1)
        self._current = updated
        return SkillStepReceipt("CHECK_PASSED_NOT_AUTHORIZED", updated)

    def propose(
        self, cursor: SkillCursor, *, binding: PhysicalActionBinding,
        capability: PhysicalCapability, readback: PhysicalReadback,
        intent_owner: IntentCommitment, skill_execution: SkillExecution,
        supervisor: ActionSupervisor, at_ns: int, provenance: Provenance,
        place_motion: object | None = None,
    ) -> SkillStepReceipt:
        ir = self._require_cursor(
            cursor, at_ns=at_ns, intent_owner=intent_owner,
            skill_execution=skill_execution,
        )
        if (cursor.pending_action_id is not None or cursor.index >= len(ir.steps)
                or ir.steps[cursor.index].kind is not StepKind.ACTION
                or cursor.action_count >= 4):
            raise SkillIRRefusal("no executable ACTION step or pending prior Action")
        # Stage27c: a scoped, SOURCE-SHAPED PLACE MOVE may be PROPOSED,
        # but remains absolutely nonissuing; the original physical issuer and
        # canonical WAL still reject this DESTINATION binding until an exact
        # parameterized LOOK/start/STOP reservation is implemented.
        if ir.invocation is not None:
            if place_motion is None:
                raise SkillIRRefusal(
                    "parameterized physical issuer not admitted; no Action proposal"
                )
            from relay_self.p0d_stage27b_place_motion_dev import Stage27PlaceMotionPlan
            from relay_self.target_contract import TargetKind

            inv = ir.invocation
            contract = inv.target.contract
            if (
                not isinstance(place_motion, Stage27PlaceMotionPlan)
                or ir.skill_id != "MOVE" or ir.version != 1
                or ir.goal_id != "EXPLORE_WORLD"
                or ir.target_kind != "DESTINATION"
                or contract is None or contract.kind is not TargetKind.PLACE
                or place_motion.self_id != cursor.scope.self_id
                or place_motion.native_session_id != cursor.scope.world_session_id
                or place_motion.intent_id != cursor.intent_id
                or place_motion.skill_execution_id != cursor.execution_id
                or place_motion.invocation_ref != inv.invocation_ref
                or place_motion.parameter_preset_ref != inv.parameter_preset_ref
                or place_motion.target_contract_ref != contract.contract_ref
                or place_motion.target_ref != inv.target.ref
                or place_motion.native_probe_seq != binding.native_seq
                or place_motion.native_probe_request_id != binding.native_request_id
                or place_motion.observation_status != "OUTSIDE"
                or place_motion.next_step
                != "NATIVE_LOOK_AND_BOUNDED_MOVE_RESOLUTION_REQUIRED_NOT_ISSUABLE"
                or place_motion.desired_mineflayer_yaw_rad is None
                or not math.isfinite(place_motion.desired_mineflayer_yaw_rad)
                or not 0 < place_motion.gap_to_arrival_envelope_m <= 1000
                or place_motion.preset_max_distance_m != inv.budget.max_distance_m
                or place_motion.clearance_observed
                or place_motion.facing_aligned_observed
                or place_motion.action_granted
                or place_motion.native_effect_issued
                or place_motion.world_goal_succeeded
                or cursor.action_count >= inv.budget.max_actions
                or inv.budget.max_duration_ms < 1
                or binding.native_source.source != "mineflayer"
                or binding.native_source.reference
                != f"{cursor.scope.world_session_id}:{binding.native_seq}"
            ):
                raise SkillIRRefusal(
                    "original finite MOVE/PLACE source not qualified for L0 proposal"
                )
        elif place_motion is not None:
            raise SkillIRRefusal("nonparameterized Skill cannot borrow PLACE plan")
        step = ir.steps[cursor.index]
        if (not isinstance(binding, PhysicalActionBinding)
                or binding.scope != cursor.scope
                or binding.intent_id != cursor.intent_id
                or binding.goal_id != cursor.goal_id
                or binding.skill_id != cursor.skill_id
                or binding.skill_version != cursor.version
                or binding.skill_execution_id != cursor.execution_id
                or binding.target_ref != cursor.target_ref
                or binding.target_kind != cursor.target_kind
                or binding.capability_ref != step.capability_ref
                or binding.capability_version != step.capability_version):
            raise SkillIRRefusal("selected Action binding differs from compiled Skill")
        receipt = propose_bound_physical_action(
            binding, capability=capability, readback=readback,
            intent_owner=intent_owner, skill_execution=skill_execution,
            supervisor=supervisor, at_ns=at_ns, provenance=provenance,
        )
        updated = replace(
            cursor, pending_action_id=binding.action_id,
            pending_native_source=binding.native_source,
            action_count=cursor.action_count + 1,
        )
        self._current = updated
        return SkillStepReceipt("PROPOSED_NOT_ISSUED", updated, receipt, binding.action_id)

    def observe_action(
        self, cursor: SkillCursor, *, action: ActionLifecycle,
        witness: ActionOutcomeWitness | None,
        intent_owner: IntentCommitment, skill_execution: SkillExecution,
        at_ns: int,
    ) -> SkillStepReceipt:
        ir = self._require_cursor(
            cursor, at_ns=at_ns, intent_owner=intent_owner,
            skill_execution=skill_execution,
        )
        if (cursor.pending_action_id is None
                or not isinstance(action, ActionLifecycle)
                or not action.is_current_snapshot
                or action.action_id != cursor.pending_action_id
                or action.skill_execution_id != cursor.execution_id
                or action.intent_id != cursor.intent_id
                or action.events[-1].at_ns > at_ns):
            raise SkillIRRefusal("Action Outcome identity/currentness mismatch")
        if action.state in (ActionState.PROPOSED, ActionState.AUTHORIZED,
                            ActionState.ISSUED):
            return SkillStepReceipt("AWAITING_OUTCOME", cursor, action_ref=action.action_id)
        if action.state is ActionState.DENIED:
            self._current = replace(cursor, blocked=True)
            return SkillStepReceipt("NOT_EXECUTED", self._current, action_ref=action.action_id)
        if action.state in (ActionState.UNKNOWN, ActionState.TIMEOUT):
            self._current = replace(cursor, blocked=True)
            return SkillStepReceipt("STOP_UNKNOWN", self._current, action_ref=action.action_id)
        if (not isinstance(witness, ActionOutcomeWitness)
                or witness.scope != cursor.scope
                or witness.action_id != action.action_id
                or witness.native_source != cursor.pending_native_source
                or not witness.journal_closed or not witness.effect_correlated):
            # Outcome alone, or an ambiguous disk close, cannot advance a Skill.
            self._current = replace(cursor, blocked=True)
            return SkillStepReceipt("STOP_UNKNOWN", self._current, action_ref=action.action_id)
        updated = replace(
            cursor, index=cursor.index + 1,
            pending_action_id=None, pending_native_source=None,
        )
        self._current = updated
        return SkillStepReceipt(
            "YIELD_EVALUATION" if updated.index == len(ir.steps) else "NEXT_STEP",
            updated, action_ref=action.action_id,
        )


def _text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())
