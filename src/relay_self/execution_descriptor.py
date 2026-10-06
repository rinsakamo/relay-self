from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from relay_self.capability import CapabilityPlan, CapabilitySpec


class ExecutionDescriptorError(ValueError):
    """Base error for non-executing runtime seam descriptors."""


class InvalidExecutionDescriptor(ExecutionDescriptorError):
    """Raised when descriptor metadata is malformed."""


class DuplicateExecutionDescriptor(ExecutionDescriptorError):
    """Raised when a descriptor identity is duplicated."""


class MissingExecutionDescriptor(ExecutionDescriptorError):
    """Raised when a capability references a descriptor that is not declared."""


class CrossCapabilityDescriptor(ExecutionDescriptorError):
    """Raised when a capability references another capability's descriptor."""


class OperatorEffect(str, Enum):
    """Observable effect class of an already-existing execution seam."""

    READ_ONLY = "read_only"
    OWNER_TRANSITION = "owner_transition"
    COGNITION_CALL = "cognition_call"
    COORDINATION = "coordination"


class CriterionKind(str, Enum):
    """Distinguish contract guards from cognitive orientation criteria."""

    CONTRACT_GUARD = "contract_guard"
    COGNITIVE_ORIENTATION = "cognitive_orientation"


@dataclass(frozen=True, slots=True)
class OperatorDescriptor:
    """Pure metadata for one already-existing operator seam.

    This descriptor contains no callable and performs no dispatch. The
    implementation_ref is a stable human/audit reference to an existing seam.
    Any state mutation remains owned by the referenced runtime owner.
    """

    operator_id: str
    capability_id: str
    implementation_ref: str
    reads: tuple[str, ...]
    writes: tuple[str, ...]
    effect: OperatorEffect
    hidden_persistent_state: bool = False

    def __post_init__(self) -> None:
        _require_text("operator_id", self.operator_id)
        _require_text("capability_id", self.capability_id)
        _require_text("implementation_ref", self.implementation_ref)
        _validate_text_tuple("reads", self.reads)
        _validate_text_tuple("writes", self.writes)
        if not isinstance(self.effect, OperatorEffect):
            raise InvalidExecutionDescriptor(
                "operator effect must be OperatorEffect"
            )
        if not isinstance(self.hidden_persistent_state, bool):
            raise InvalidExecutionDescriptor(
                "hidden_persistent_state must be bool"
            )
        if self.hidden_persistent_state:
            raise InvalidExecutionDescriptor(
                "operator descriptors cannot admit hidden persistent state"
            )


@dataclass(frozen=True, slots=True)
class CriterionDescriptor:
    """Pure metadata for one already-existing criterion or contract guard."""

    criterion_id: str
    capability_id: str
    implementation_ref: str
    reads: tuple[str, ...]
    kind: CriterionKind
    semantics: str
    mutates_state: bool = False

    def __post_init__(self) -> None:
        _require_text("criterion_id", self.criterion_id)
        _require_text("capability_id", self.capability_id)
        _require_text("implementation_ref", self.implementation_ref)
        _validate_text_tuple("reads", self.reads)
        if not isinstance(self.kind, CriterionKind):
            raise InvalidExecutionDescriptor(
                "criterion kind must be CriterionKind"
            )
        _require_text("criterion semantics", self.semantics)
        if not isinstance(self.mutates_state, bool):
            raise InvalidExecutionDescriptor("mutates_state must be bool")
        if self.mutates_state:
            raise InvalidExecutionDescriptor(
                "criterion descriptors cannot mutate state"
            )


@dataclass(frozen=True, slots=True)
class CapabilityDescriptorSet:
    """Immutable descriptor inventory with validation only.

    The set is not a runtime registry: it has no callable bindings, discovery,
    scheduler, execution order, state ownership, or dispatch behavior.
    """

    operators: tuple[OperatorDescriptor, ...] = ()
    criteria: tuple[CriterionDescriptor, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.operators, tuple) or not all(
            isinstance(value, OperatorDescriptor)
            for value in self.operators
        ):
            raise InvalidExecutionDescriptor(
                "operators must be a tuple of OperatorDescriptor values"
            )
        if not isinstance(self.criteria, tuple) or not all(
            isinstance(value, CriterionDescriptor)
            for value in self.criteria
        ):
            raise InvalidExecutionDescriptor(
                "criteria must be a tuple of CriterionDescriptor values"
            )

        _unique_by_id(
            "operator",
            tuple(value.operator_id for value in self.operators),
        )
        _unique_by_id(
            "criterion",
            tuple(value.criterion_id for value in self.criteria),
        )

    def validate_spec(self, spec: CapabilitySpec) -> None:
        """Validate that one spec's descriptor identifiers are explicitly covered."""

        if not isinstance(spec, CapabilitySpec):
            raise InvalidExecutionDescriptor("spec must be CapabilitySpec")

        operators = {
            value.operator_id: value
            for value in self.operators
        }
        criteria = {
            value.criterion_id: value
            for value in self.criteria
        }

        for operator_id in spec.operator_ids:
            descriptor = operators.get(operator_id)
            if descriptor is None:
                raise MissingExecutionDescriptor(
                    f"missing operator descriptor: {operator_id}"
                )
            if descriptor.capability_id != spec.capability_id:
                raise CrossCapabilityDescriptor(
                    f"{spec.capability_id} references operator {operator_id} "
                    f"owned by capability {descriptor.capability_id}"
                )

        for criterion_id in spec.criterion_ids:
            descriptor = criteria.get(criterion_id)
            if descriptor is None:
                raise MissingExecutionDescriptor(
                    f"missing criterion descriptor: {criterion_id}"
                )
            if descriptor.capability_id != spec.capability_id:
                raise CrossCapabilityDescriptor(
                    f"{spec.capability_id} references criterion {criterion_id} "
                    f"owned by capability {descriptor.capability_id}"
                )

    def validate_plan(self, plan: CapabilityPlan) -> None:
        """Validate enabled capability metadata without executing any seam."""

        if not isinstance(plan, CapabilityPlan):
            raise InvalidExecutionDescriptor("plan must be CapabilityPlan")
        for spec in plan.enabled_specs:
            self.validate_spec(spec)


def _unique_by_id(kind: str, values: tuple[str, ...]) -> None:
    seen: set[str] = set()
    for value in values:
        if value in seen:
            raise DuplicateExecutionDescriptor(
                f"duplicate {kind} descriptor id: {value}"
            )
        seen.add(value)


def _validate_text_tuple(name: str, values: object) -> None:
    if not isinstance(values, tuple):
        raise InvalidExecutionDescriptor(f"{name} must be a tuple")
    seen: set[str] = set()
    for index, value in enumerate(values):
        _require_text(f"{name}[{index}]", value)
        if value in seen:
            raise InvalidExecutionDescriptor(
                f"{name} must not contain duplicates: {value}"
            )
        seen.add(value)


def _require_text(name: str, value: object) -> None:
    if not isinstance(value, str) or not value.strip():
        raise InvalidExecutionDescriptor(f"{name} must be a non-empty string")

S2_CAPABILITY_SPECS = (
    CapabilitySpec(
        capability_id="MEM",
        state_scopes=("durable.memory",),
        operator_ids=("mem.retain",),
        criterion_ids=("mem.unique_identity_guard",),
        port_ids=("memory.write",),
    ),
    CapabilitySpec(
        capability_id="CTL",
        state_scopes=(
            "present",
            "execution.intent",
            "execution.action",
        ),
        operator_ids=(
            "ctl.coordinate_decision_epoch",
            "ctl.bounded_cognition",
        ),
        criterion_ids=("ctl.bounded_choice_admissibility",),
        port_ids=("cognition.bounded",),
    ),
    CapabilitySpec(
        capability_id="SKL",
        state_scopes=(
            "execution.intent",
            "execution.skill",
            "execution.action",
        ),
        operator_ids=(
            "skl.start_execution",
            "skl.propose_action",
        ),
        criterion_ids=(
            "skl.current_intent_guard",
            "skl.current_started_guard",
        ),
        port_ids=("action.proposal",),
        dependencies=("CTL",),
    ),
    CapabilitySpec(
        capability_id="TALK",
        state_scopes=(
            "durable.identity",
            "durable.memory",
            "present",
        ),
        operator_ids=("talk.open_cognition",),
        criterion_ids=("talk.nonempty_expression_guard",),
        port_ids=("expression.out",),
    ),
)


S2_DESCRIPTOR_SET = CapabilityDescriptorSet(
    operators=(
        OperatorDescriptor(
            operator_id="mem.retain",
            capability_id="MEM",
            implementation_ref=(
                "relay_self.persistent_cognition."
                "PersistentCognition.retain_memory"
            ),
            reads=("durable.memory", "candidate.memory"),
            writes=("durable.memory",),
            effect=OperatorEffect.OWNER_TRANSITION,
        ),
        OperatorDescriptor(
            operator_id="ctl.coordinate_decision_epoch",
            capability_id="CTL",
            implementation_ref=(
                "relay_self.runtime_coordination.coordinate_decision_epoch"
            ),
            reads=(
                "execution.action_supervision",
                "caller_owned.decision_step",
            ),
            writes=("execution.action_supervision",),
            effect=OperatorEffect.COORDINATION,
        ),
        OperatorDescriptor(
            operator_id="ctl.bounded_cognition",
            capability_id="CTL",
            implementation_ref="relay_self.relay_engine.RelayEngine.__call__",
            reads=("cognition.bounded_request",),
            writes=("transient.cognition_result",),
            effect=OperatorEffect.COGNITION_CALL,
        ),
        OperatorDescriptor(
            operator_id="skl.start_execution",
            capability_id="SKL",
            implementation_ref="relay_self.skill.SkillExecution.start",
            reads=("execution.intent", "skill.definition_reference"),
            writes=("execution.skill",),
            effect=OperatorEffect.OWNER_TRANSITION,
        ),
        OperatorDescriptor(
            operator_id="skl.propose_action",
            capability_id="SKL",
            implementation_ref="relay_self.action.ActionLifecycle.propose",
            reads=("execution.intent", "execution.skill"),
            writes=("execution.action",),
            effect=OperatorEffect.OWNER_TRANSITION,
        ),
        OperatorDescriptor(
            operator_id="talk.open_cognition",
            capability_id="TALK",
            implementation_ref="relay_self.relay_engine.RelayEngine.open",
            reads=("cognition.open_request",),
            writes=("transient.expression",),
            effect=OperatorEffect.COGNITION_CALL,
        ),
    ),
    criteria=(
        CriterionDescriptor(
            criterion_id="mem.unique_identity_guard",
            capability_id="MEM",
            implementation_ref=(
                "relay_self.persistent_cognition."
                "PersistentCognition.retain_memory"
            ),
            reads=("durable.memory", "candidate.memory"),
            kind=CriterionKind.CONTRACT_GUARD,
            semantics=(
                "Retained Memory must be valid governed Memory data and must "
                "not reuse an existing memory_id."
            ),
        ),
        CriterionDescriptor(
            criterion_id="ctl.bounded_choice_admissibility",
            capability_id="CTL",
            implementation_ref="relay_self.relay_engine.RelayEngine.__call__",
            reads=("cognition.bounded_request", "provider.decision"),
            kind=CriterionKind.CONTRACT_GUARD,
            semantics=(
                "A resolved provider choice must be one of the request's "
                "explicit admissible choice identifiers."
            ),
        ),
        CriterionDescriptor(
            criterion_id="skl.current_intent_guard",
            capability_id="SKL",
            implementation_ref="relay_self.skill.SkillExecution.start",
            reads=("execution.intent",),
            kind=CriterionKind.CONTRACT_GUARD,
            semantics=(
                "Starting a Skill execution requires an actually current "
                "IntentCommitment-owned Current Intent."
            ),
        ),
        CriterionDescriptor(
            criterion_id="skl.current_started_guard",
            capability_id="SKL",
            implementation_ref="relay_self.action.ActionLifecycle.propose",
            reads=("execution.intent", "execution.skill"),
            kind=CriterionKind.CONTRACT_GUARD,
            semantics=(
                "Action proposal requires the current STARTED Skill snapshot "
                "whose intent matches the actual Current Intent."
            ),
        ),
        CriterionDescriptor(
            criterion_id="talk.nonempty_expression_guard",
            capability_id="TALK",
            implementation_ref="relay_self.relay_engine.ProviderExpression.__post_init__",
            reads=("provider.expression",),
            kind=CriterionKind.CONTRACT_GUARD,
            semantics=(
                "OPEN cognition requires a non-empty provider expression with "
                "explicit provenance; expression remains transient."
            ),
        ),
    ),
)


def s2_capability_plan(
    *,
    enabled_ids: frozenset[str] = frozenset(),
) -> CapabilityPlan:
    """Build the explicit S2 plan; no capability is enabled implicitly."""

    plan = CapabilityPlan(
        specs=S2_CAPABILITY_SPECS,
        enabled_ids=enabled_ids,
    )
    S2_DESCRIPTOR_SET.validate_plan(plan)
    return plan


S5_ATT_CAPABILITY_SPEC = CapabilitySpec(
    capability_id="ATT",
    operator_ids=("att.select",),
    criterion_ids=("att.explicit_orientation",),
    port_ids=("attention.selection.out",),
)

S5_ATT_OPERATOR_DESCRIPTOR = OperatorDescriptor(
    operator_id="att.select",
    capability_id="ATT",
    implementation_ref="relay_self.attention.select_attention",
    reads=("caller_owned.candidates", "attention.criterion"),
    writes=("transient.attention_selection",),
    effect=OperatorEffect.READ_ONLY,
)

S5_ATT_CRITERION_DESCRIPTOR = CriterionDescriptor(
    criterion_id="att.explicit_orientation",
    capability_id="ATT",
    implementation_ref="relay_self.attention.select_attention",
    reads=("caller_owned.candidates", "attention.criterion"),
    kind=CriterionKind.COGNITIVE_ORIENTATION,
    semantics=(
        "Among otherwise valid caller-owned structured candidates, apply only "
        "explicit focus, minimum-priority, descending-priority, and bounded "
        "top-k orientation without mutating an owner."
    ),
)

S5_CAPABILITY_SPECS = (
    *S2_CAPABILITY_SPECS,
    S5_ATT_CAPABILITY_SPEC,
)

S5_DESCRIPTOR_SET = CapabilityDescriptorSet(
    operators=(
        *S2_DESCRIPTOR_SET.operators,
        S5_ATT_OPERATOR_DESCRIPTOR,
    ),
    criteria=(
        *S2_DESCRIPTOR_SET.criteria,
        S5_ATT_CRITERION_DESCRIPTOR,
    ),
)


def s5_capability_plan(
    *,
    enabled_ids: frozenset[str] = frozenset(),
) -> CapabilityPlan:
    """Build the bounded S5 plan; no capability is enabled implicitly."""

    plan = CapabilityPlan(
        specs=S5_CAPABILITY_SPECS,
        enabled_ids=enabled_ids,
    )
    S5_DESCRIPTOR_SET.validate_plan(plan)
    return plan


S6_BLF_CAPABILITY_SPEC = CapabilitySpec(
    capability_id="BLF",
    operator_ids=("blf.assess",),
    criterion_ids=("blf.evidence_support_orientation",),
    port_ids=("belief.assessment.out",),
)

S6_BLF_OPERATOR_DESCRIPTOR = OperatorDescriptor(
    operator_id="blf.assess",
    capability_id="BLF",
    implementation_ref="relay_self.belief.assess_belief",
    reads=("qualified.belief_evidence", "belief.criterion"),
    writes=("transient.belief_assessment",),
    effect=OperatorEffect.READ_ONLY,
)

S6_BLF_CRITERION_DESCRIPTOR = CriterionDescriptor(
    criterion_id="blf.evidence_support_orientation",
    capability_id="BLF",
    implementation_ref="relay_self.belief.assess_belief",
    reads=("qualified.belief_evidence", "belief.criterion"),
    kind=CriterionKind.COGNITIVE_ORIENTATION,
    semantics=(
        "For one explicit structured proposition, orient over admitted SUPPORT "
        "and OPPOSE evidence to produce SUPPORTED, UNSUPPORTED, CONFLICTED, "
        "or UNDETERMINED without claiming World truth."
    ),
)

S6_CAPABILITY_SPECS = (
    *S5_CAPABILITY_SPECS,
    S6_BLF_CAPABILITY_SPEC,
)

S6_DESCRIPTOR_SET = CapabilityDescriptorSet(
    operators=(
        *S5_DESCRIPTOR_SET.operators,
        S6_BLF_OPERATOR_DESCRIPTOR,
    ),
    criteria=(
        *S5_DESCRIPTOR_SET.criteria,
        S6_BLF_CRITERION_DESCRIPTOR,
    ),
)


def s6_capability_plan(
    *,
    enabled_ids: frozenset[str] = frozenset(),
) -> CapabilityPlan:
    """Build the bounded S6 plan; no capability is enabled implicitly."""

    plan = CapabilityPlan(
        specs=S6_CAPABILITY_SPECS,
        enabled_ids=enabled_ids,
    )
    S6_DESCRIPTOR_SET.validate_plan(plan)
    return plan


S7_CNC_CAPABILITY_SPEC = CapabilitySpec(
    capability_id="CNC",
    operator_ids=("cnc.classify",),
    criterion_ids=("cnc.explicit_membership_orientation",),
    port_ids=("concept.representation.out",),
)

S7_CNC_OPERATOR_DESCRIPTOR = OperatorDescriptor(
    operator_id="cnc.classify",
    capability_id="CNC",
    implementation_ref="relay_self.concept.classify_concept",
    reads=("qualified.concept_candidate", "concept.criterion"),
    writes=("transient.concept_representation",),
    effect=OperatorEffect.READ_ONLY,
)

S7_CNC_CRITERION_DESCRIPTOR = CriterionDescriptor(
    criterion_id="cnc.explicit_membership_orientation",
    capability_id="CNC",
    implementation_ref="relay_self.concept.classify_concept",
    reads=("qualified.concept_candidate", "concept.criterion"),
    kind=CriterionKind.COGNITIVE_ORIENTATION,
    semantics=(
        "For one valid structured candidate and explicit concept membership "
        "rule, distinguish exact membership, explicit mismatch, and missing "
        "required features without claiming World truth."
    ),
)

S7_CAPABILITY_SPECS = (
    *S6_CAPABILITY_SPECS,
    S7_CNC_CAPABILITY_SPEC,
)

S7_DESCRIPTOR_SET = CapabilityDescriptorSet(
    operators=(
        *S6_DESCRIPTOR_SET.operators,
        S7_CNC_OPERATOR_DESCRIPTOR,
    ),
    criteria=(
        *S6_DESCRIPTOR_SET.criteria,
        S7_CNC_CRITERION_DESCRIPTOR,
    ),
)


def s7_capability_plan(
    *,
    enabled_ids: frozenset[str] = frozenset(),
) -> CapabilityPlan:
    """Build the bounded S7 plan; no capability is enabled implicitly."""

    plan = CapabilityPlan(
        specs=S7_CAPABILITY_SPECS,
        enabled_ids=enabled_ids,
    )
    S7_DESCRIPTOR_SET.validate_plan(plan)
    return plan


S8_PRD_CAPABILITY_SPEC = CapabilitySpec(
    capability_id="PRD",
    operator_ids=("prd.predict",),
    criterion_ids=(),
    port_ids=("prediction.result.out",),
)

S8_PRD_OPERATOR_DESCRIPTOR = OperatorDescriptor(
    operator_id="prd.predict",
    capability_id="PRD",
    implementation_ref="relay_self.prediction.predict_transition",
    reads=("qualified.prediction_state", "prediction.transition_rule"),
    writes=("transient.prediction_result",),
    effect=OperatorEffect.READ_ONLY,
)

S8_CAPABILITY_SPECS = (
    *S7_CAPABILITY_SPECS,
    S8_PRD_CAPABILITY_SPEC,
)

S8_DESCRIPTOR_SET = CapabilityDescriptorSet(
    operators=(
        *S7_DESCRIPTOR_SET.operators,
        S8_PRD_OPERATOR_DESCRIPTOR,
    ),
    criteria=S7_DESCRIPTOR_SET.criteria,
)


def s8_capability_plan(
    *,
    enabled_ids: frozenset[str] = frozenset(),
) -> CapabilityPlan:
    """Build the bounded S8 plan; no capability is enabled implicitly."""

    plan = CapabilityPlan(
        specs=S8_CAPABILITY_SPECS,
        enabled_ids=enabled_ids,
    )
    S8_DESCRIPTOR_SET.validate_plan(plan)
    return plan


S9_PLAN_CAPABILITY_SPEC = CapabilitySpec(
    capability_id="PLAN",
    operator_ids=("plan.select",),
    criterion_ids=("plan.explicit_preference_orientation",),
    port_ids=("plan.selection.out",),
)

S9_PLAN_OPERATOR_DESCRIPTOR = OperatorDescriptor(
    operator_id="plan.select",
    capability_id="PLAN",
    implementation_ref="relay_self.planning.select_plan",
    reads=("qualified.plan_candidates", "planning.criterion"),
    writes=("transient.plan_selection",),
    effect=OperatorEffect.READ_ONLY,
)

S9_PLAN_CRITERION_DESCRIPTOR = CriterionDescriptor(
    criterion_id="plan.explicit_preference_orientation",
    capability_id="PLAN",
    implementation_ref="relay_self.planning.select_plan",
    reads=("qualified.plan_candidates", "planning.criterion"),
    kind=CriterionKind.COGNITIVE_ORIENTATION,
    semantics=(
        "Among a finite valid candidate set, compare one explicit integer "
        "outcome feature under an explicit MINIMIZE or MAXIMIZE direction, "
        "returning a unique selection only when preference is determined."
    ),
)

S9_CAPABILITY_SPECS = (
    *S8_CAPABILITY_SPECS,
    S9_PLAN_CAPABILITY_SPEC,
)

S9_DESCRIPTOR_SET = CapabilityDescriptorSet(
    operators=(
        *S8_DESCRIPTOR_SET.operators,
        S9_PLAN_OPERATOR_DESCRIPTOR,
    ),
    criteria=(
        *S8_DESCRIPTOR_SET.criteria,
        S9_PLAN_CRITERION_DESCRIPTOR,
    ),
)


def s9_capability_plan(
    *,
    enabled_ids: frozenset[str] = frozenset(),
) -> CapabilityPlan:
    """Build the bounded S9 plan; no capability is enabled implicitly."""

    plan = CapabilityPlan(
        specs=S9_CAPABILITY_SPECS,
        enabled_ids=enabled_ids,
    )
    S9_DESCRIPTOR_SET.validate_plan(plan)
    return plan


S10_LRN_CAPABILITY_SPEC = CapabilitySpec(
    capability_id="LRN",
    state_scopes=("owner_local.learning_preference",),
    operator_ids=("lrn.propose_update", "lrn.apply_update"),
    criterion_ids=("lrn.explicit_feedback_orientation",),
    port_ids=("learning.update_proposal.out", "learning.retained_state.out"),
)

S10_LRN_PROPOSE_OPERATOR_DESCRIPTOR = OperatorDescriptor(
    operator_id="lrn.propose_update",
    capability_id="LRN",
    implementation_ref="relay_self.learning.propose_learning_update",
    reads=(
        "owner_local.learning_preference",
        "learning.feedback",
        "learning.update_rule",
    ),
    writes=("transient.learning_update_proposal",),
    effect=OperatorEffect.READ_ONLY,
)

S10_LRN_APPLY_OPERATOR_DESCRIPTOR = OperatorDescriptor(
    operator_id="lrn.apply_update",
    capability_id="LRN",
    implementation_ref="relay_self.learning.commit_learning_update",
    reads=(
        "owner_local.learning_preference",
        "transient.learning_update_proposal",
        "learning.update_authority",
    ),
    writes=("owner_local.learning_preference",),
    effect=OperatorEffect.OWNER_TRANSITION,
)

S10_LRN_CRITERION_DESCRIPTOR = CriterionDescriptor(
    criterion_id="lrn.explicit_feedback_orientation",
    capability_id="LRN",
    implementation_ref="relay_self.learning.propose_learning_update",
    reads=(
        "owner_local.learning_preference",
        "learning.feedback",
        "learning.update_rule",
    ),
    kind=CriterionKind.COGNITIVE_ORIENTATION,
    semantics=(
        "For one explicit retained target, orient a bounded deterministic "
        "proposal according to structured INCREASE, DECREASE, or HOLD "
        "feedback without granting commit authority."
    ),
)

S10_CAPABILITY_SPECS = (
    *S9_CAPABILITY_SPECS,
    S10_LRN_CAPABILITY_SPEC,
)

S10_DESCRIPTOR_SET = CapabilityDescriptorSet(
    operators=(
        *S9_DESCRIPTOR_SET.operators,
        S10_LRN_PROPOSE_OPERATOR_DESCRIPTOR,
        S10_LRN_APPLY_OPERATOR_DESCRIPTOR,
    ),
    criteria=(
        *S9_DESCRIPTOR_SET.criteria,
        S10_LRN_CRITERION_DESCRIPTOR,
    ),
)


def s10_capability_plan(
    *,
    enabled_ids: frozenset[str] = frozenset(),
) -> CapabilityPlan:
    """Build the bounded S10 plan; no capability is enabled implicitly."""

    plan = CapabilityPlan(
        specs=S10_CAPABILITY_SPECS,
        enabled_ids=enabled_ids,
    )
    S10_DESCRIPTOR_SET.validate_plan(plan)
    return plan


S11_HABIT_CAPABILITY_SPEC = CapabilitySpec(
    capability_id="HABIT",
    state_scopes=("owner_local.habit_repertoire",),
    operator_ids=("habit.select",),
    criterion_ids=("habit.explicit_priority_orientation",),
    port_ids=("habit.selection.out",),
)

S11_HABIT_OPERATOR_DESCRIPTOR = OperatorDescriptor(
    operator_id="habit.select",
    capability_id="HABIT",
    implementation_ref="relay_self.habit.select_habit",
    reads=("owner_local.habit_repertoire", "habit.cue"),
    writes=("transient.habit_selection",),
    effect=OperatorEffect.READ_ONLY,
)

S11_HABIT_CRITERION_DESCRIPTOR = CriterionDescriptor(
    criterion_id="habit.explicit_priority_orientation",
    capability_id="HABIT",
    implementation_ref="relay_self.habit.select_habit",
    reads=("owner_local.habit_repertoire", "habit.cue"),
    kind=CriterionKind.COGNITIVE_ORIENTATION,
    semantics=(
        "Among retained rules whose explicit cue requirements exactly match, "
        "prefer one unique highest retained integer priority; equal top "
        "priority remains an explicit tie."
    ),
)

S11_CAPABILITY_SPECS = (
    *S10_CAPABILITY_SPECS,
    S11_HABIT_CAPABILITY_SPEC,
)

S11_DESCRIPTOR_SET = CapabilityDescriptorSet(
    operators=(
        *S10_DESCRIPTOR_SET.operators,
        S11_HABIT_OPERATOR_DESCRIPTOR,
    ),
    criteria=(
        *S10_DESCRIPTOR_SET.criteria,
        S11_HABIT_CRITERION_DESCRIPTOR,
    ),
)


def s11_capability_plan(
    *,
    enabled_ids: frozenset[str] = frozenset(),
) -> CapabilityPlan:
    """Build the bounded S11 plan; no capability is enabled implicitly."""

    plan = CapabilityPlan(
        specs=S11_CAPABILITY_SPECS,
        enabled_ids=enabled_ids,
    )
    S11_DESCRIPTOR_SET.validate_plan(plan)
    return plan


S12_ROUTE_CAPABILITY_SPEC = CapabilitySpec(
    capability_id="ROUTE",
    operator_ids=("route.adjudicate",),
    criterion_ids=("route.explicit_arbitration_orientation",),
    port_ids=("route.decision.out",),
)

S12_ROUTE_OPERATOR_DESCRIPTOR = OperatorDescriptor(
    operator_id="route.adjudicate",
    capability_id="ROUTE",
    implementation_ref="relay_self.route_adjudication.adjudicate_routes",
    reads=(
        "transient.plan_selection",
        "transient.habit_selection",
        "route.criterion",
    ),
    writes=("transient.route_decision",),
    effect=OperatorEffect.READ_ONLY,
)

S12_ROUTE_CRITERION_DESCRIPTOR = CriterionDescriptor(
    criterion_id="route.explicit_arbitration_orientation",
    capability_id="ROUTE",
    implementation_ref="relay_self.route_adjudication.adjudicate_routes",
    reads=(
        "transient.plan_selection",
        "transient.habit_selection",
        "route.criterion",
    ),
    kind=CriterionKind.COGNITIVE_ORIENTATION,
    semantics=(
        "Admit already-selected PLAN/HABIT candidate references only under "
        "an explicit conflict policy and explicit single-source permission; "
        "otherwise preserve disagreement or absence without execution authority."
    ),
)

S12_CAPABILITY_SPECS = (
    *S11_CAPABILITY_SPECS,
    S12_ROUTE_CAPABILITY_SPEC,
)

S12_DESCRIPTOR_SET = CapabilityDescriptorSet(
    operators=(
        *S11_DESCRIPTOR_SET.operators,
        S12_ROUTE_OPERATOR_DESCRIPTOR,
    ),
    criteria=(
        *S11_DESCRIPTOR_SET.criteria,
        S12_ROUTE_CRITERION_DESCRIPTOR,
    ),
)


def s12_capability_plan(
    *,
    enabled_ids: frozenset[str] = frozenset(),
) -> CapabilityPlan:
    """Build the bounded S12 integration plan; nothing is enabled implicitly."""

    plan = CapabilityPlan(
        specs=S12_CAPABILITY_SPECS,
        enabled_ids=enabled_ids,
    )
    S12_DESCRIPTOR_SET.validate_plan(plan)
    return plan


S13_ADMISSION_CAPABILITY_SPEC = CapabilitySpec(
    capability_id="ADMISSION",
    operator_ids=("execution.admit_candidate",),
    criterion_ids=("admission.explicit_execution_guard",),
    port_ids=("execution.admission_decision.out",),
)

S13_ADMISSION_OPERATOR_DESCRIPTOR = OperatorDescriptor(
    operator_id="execution.admit_candidate",
    capability_id="ADMISSION",
    implementation_ref="relay_self.execution_admission.admit_control_candidate",
    reads=(
        "transient.control_candidate",
        "transient.route_decision",
        "execution.intent",
        "admission.criterion",
    ),
    writes=("transient.admission_decision",),
    effect=OperatorEffect.READ_ONLY,
)

S13_ADMISSION_CRITERION_DESCRIPTOR = CriterionDescriptor(
    criterion_id="admission.explicit_execution_guard",
    capability_id="ADMISSION",
    implementation_ref="relay_self.execution_admission.admit_control_candidate",
    reads=(
        "transient.control_candidate",
        "transient.route_decision",
        "execution.intent",
        "admission.criterion",
    ),
    kind=CriterionKind.CONTRACT_GUARD,
    semantics=(
        "A ControlCandidate enters later execution-authority handling only when "
        "it exactly matches its S12 RouteDecision, the required Current Intent "
        "is actually current, and its candidate_ref is explicitly allow-listed."
    ),
)

S13_CAPABILITY_SPECS = (
    *S12_CAPABILITY_SPECS,
    S13_ADMISSION_CAPABILITY_SPEC,
)

S13_DESCRIPTOR_SET = CapabilityDescriptorSet(
    operators=(
        *S12_DESCRIPTOR_SET.operators,
        S13_ADMISSION_OPERATOR_DESCRIPTOR,
    ),
    criteria=(
        *S12_DESCRIPTOR_SET.criteria,
        S13_ADMISSION_CRITERION_DESCRIPTOR,
    ),
)


def s13_capability_plan(
    *,
    enabled_ids: frozenset[str] = frozenset(),
) -> CapabilityPlan:
    """Build S13 authority-boundary metadata; nothing is enabled implicitly."""

    plan = CapabilityPlan(
        specs=S13_CAPABILITY_SPECS,
        enabled_ids=enabled_ids,
    )
    S13_DESCRIPTOR_SET.validate_plan(plan)
    return plan


S14_EXEC_BIND_CAPABILITY_SPEC = CapabilitySpec(
    capability_id="EXEC_BIND",
    operator_ids=(
        "execution.resolve_binding",
        "execution.start_and_propose",
    ),
    criterion_ids=("execution.explicit_binding_guard",),
    port_ids=(
        "execution.bound_candidate.out",
        "action.proposal",
    ),
    dependencies=("ADMISSION", "SKL"),
)

S14_EXEC_BIND_RESOLVE_OPERATOR_DESCRIPTOR = OperatorDescriptor(
    operator_id="execution.resolve_binding",
    capability_id="EXEC_BIND",
    implementation_ref="relay_self.execution_binding.resolve_execution_binding",
    reads=(
        "transient.admission_decision",
        "transient.control_candidate",
        "transient.route_decision",
        "execution.intent",
        "admission.criterion",
        "execution.binding",
    ),
    writes=("transient.bound_execution_candidate",),
    effect=OperatorEffect.READ_ONLY,
)

S14_EXEC_BIND_TRANSITION_OPERATOR_DESCRIPTOR = OperatorDescriptor(
    operator_id="execution.start_and_propose",
    capability_id="EXEC_BIND",
    implementation_ref=(
        "relay_self.execution_binding.start_and_propose_bound_execution"
    ),
    reads=(
        "transient.bound_execution_candidate",
        "execution.intent",
    ),
    writes=(
        "execution.skill",
        "execution.action",
        "transient.execution_binding_result",
    ),
    effect=OperatorEffect.OWNER_TRANSITION,
)

S14_EXEC_BIND_CRITERION_DESCRIPTOR = CriterionDescriptor(
    criterion_id="execution.explicit_binding_guard",
    capability_id="EXEC_BIND",
    implementation_ref="relay_self.execution_binding.resolve_execution_binding",
    reads=(
        "transient.admission_decision",
        "transient.control_candidate",
        "transient.route_decision",
        "execution.intent",
        "admission.criterion",
        "execution.binding",
    ),
    kind=CriterionKind.CONTRACT_GUARD,
    semantics=(
        "An ADMITTED candidate may bind to Skill/Action proposal only when "
        "its S12/S13 lineage is exact, the actual Current Intent still "
        "matches, and one explicit caller-owned ExecutionBinding exactly "
        "names the candidate, Skill identity/reference, and Action identity/reference."
    ),
)

S14_CAPABILITY_SPECS = (
    *S13_CAPABILITY_SPECS,
    S14_EXEC_BIND_CAPABILITY_SPEC,
)

S14_DESCRIPTOR_SET = CapabilityDescriptorSet(
    operators=(
        *S13_DESCRIPTOR_SET.operators,
        S14_EXEC_BIND_RESOLVE_OPERATOR_DESCRIPTOR,
        S14_EXEC_BIND_TRANSITION_OPERATOR_DESCRIPTOR,
    ),
    criteria=(
        *S13_DESCRIPTOR_SET.criteria,
        S14_EXEC_BIND_CRITERION_DESCRIPTOR,
    ),
)


def s14_capability_plan(
    *,
    enabled_ids: frozenset[str] = frozenset(),
) -> CapabilityPlan:
    """Build S14 execution-binding metadata; nothing is enabled implicitly."""

    plan = CapabilityPlan(
        specs=S14_CAPABILITY_SPECS,
        enabled_ids=enabled_ids,
    )
    S14_DESCRIPTOR_SET.validate_plan(plan)
    return plan


S15_WORLD_EXEC_CAPABILITY_SPEC = CapabilitySpec(
    capability_id="WORLD_EXEC",
    operator_ids=(
        "world.build_mineflayer_command",
        "world.execute_mineflayer_command",
    ),
    criterion_ids=("world.issued_action_binding_guard",),
    port_ids=(
        "world.mineflayer_command.out",
        "world.consequence.out",
    ),
    dependencies=("EXEC_BIND",),
)

S15_WORLD_EXEC_COMMAND_OPERATOR_DESCRIPTOR = OperatorDescriptor(
    operator_id="world.build_mineflayer_command",
    capability_id="WORLD_EXEC",
    implementation_ref="adapters.mineflayer.execution.build_mineflayer_command",
    reads=(
        "execution.action",
        "transient.execution_binding_result",
    ),
    writes=("transient.mineflayer_command",),
    effect=OperatorEffect.READ_ONLY,
)

S15_WORLD_EXEC_EXECUTE_OPERATOR_DESCRIPTOR = OperatorDescriptor(
    operator_id="world.execute_mineflayer_command",
    capability_id="WORLD_EXEC",
    implementation_ref="adapters.mineflayer.execution.execute_mineflayer_command",
    reads=(
        "transient.mineflayer_command",
        "environment.mineflayer_session",
    ),
    writes=(
        "environment.mineflayer",
        "transient.world_consequence",
    ),
    effect=OperatorEffect.COORDINATION,
)

S15_WORLD_EXEC_CRITERION_DESCRIPTOR = CriterionDescriptor(
    criterion_id="world.issued_action_binding_guard",
    capability_id="WORLD_EXEC",
    implementation_ref="adapters.mineflayer.execution.build_mineflayer_command",
    reads=(
        "execution.action",
        "transient.execution_binding_result",
    ),
    kind=CriterionKind.CONTRACT_GUARD,
    semantics=(
        "Physical Mineflayer eligibility requires one current ISSUED "
        "ActionLifecycle and one exact matching ExecutionBindingResult across "
        "action, Skill execution, Intent, and explicit closed action_ref."
    ),
)

S15_CAPABILITY_SPECS = (
    *S14_CAPABILITY_SPECS,
    S15_WORLD_EXEC_CAPABILITY_SPEC,
)

S15_DESCRIPTOR_SET = CapabilityDescriptorSet(
    operators=(
        *S14_DESCRIPTOR_SET.operators,
        S15_WORLD_EXEC_COMMAND_OPERATOR_DESCRIPTOR,
        S15_WORLD_EXEC_EXECUTE_OPERATOR_DESCRIPTOR,
    ),
    criteria=(
        *S14_DESCRIPTOR_SET.criteria,
        S15_WORLD_EXEC_CRITERION_DESCRIPTOR,
    ),
)


def s15_capability_plan(
    *,
    enabled_ids: frozenset[str] = frozenset(),
) -> CapabilityPlan:
    """Build S15 environment-integration metadata; nothing is enabled implicitly."""

    plan = CapabilityPlan(
        specs=S15_CAPABILITY_SPECS,
        enabled_ids=enabled_ids,
    )
    S15_DESCRIPTOR_SET.validate_plan(plan)
    return plan


S16_ACTION_OUTCOME_CAPABILITY_SPEC = CapabilitySpec(
    capability_id="ACTION_OUTCOME",
    operator_ids=(
        "action.interpret_world_consequence",
        "action.record_interpreted_outcome",
    ),
    criterion_ids=("action.exact_outcome_lineage_guard",),
    port_ids=(
        "action.outcome_interpretation.out",
        "action.outcome_closure",
    ),
    dependencies=("WORLD_EXEC",),
)

S16_ACTION_OUTCOME_TRANSLATE_OPERATOR_DESCRIPTOR = OperatorDescriptor(
    operator_id="action.interpret_world_consequence",
    capability_id="ACTION_OUTCOME",
    implementation_ref=(
        "adapters.mineflayer.action_outcome.interpret_world_consequence"
    ),
    reads=(
        "execution.action",
        "transient.execution_binding_result",
        "transient.world_consequence",
    ),
    writes=("transient.action_outcome_interpretation",),
    effect=OperatorEffect.READ_ONLY,
)

S16_ACTION_OUTCOME_RECORD_OPERATOR_DESCRIPTOR = OperatorDescriptor(
    operator_id="action.record_interpreted_outcome",
    capability_id="ACTION_OUTCOME",
    implementation_ref=(
        "relay_self.action_outcome.record_interpreted_action_outcome"
    ),
    reads=(
        "transient.action_outcome_interpretation",
        "execution.action_supervisor",
    ),
    writes=("execution.action",),
    effect=OperatorEffect.OWNER_TRANSITION,
)

S16_ACTION_OUTCOME_CRITERION_DESCRIPTOR = CriterionDescriptor(
    criterion_id="action.exact_outcome_lineage_guard",
    capability_id="ACTION_OUTCOME",
    implementation_ref=(
        "adapters.mineflayer.action_outcome.interpret_world_consequence"
    ),
    reads=(
        "execution.action",
        "transient.execution_binding_result",
        "transient.world_consequence",
    ),
    kind=CriterionKind.CONTRACT_GUARD,
    semantics=(
        "One S15 WorldConsequence may reach the existing ActionSupervisor "
        "terminal owner only when the current ISSUED Action, exact S14 "
        "ExecutionBindingResult, consequence identity, Mineflayer session "
        "evidence, and closed physical action reference all match."
    ),
)

S16_CAPABILITY_SPECS = (
    *S15_CAPABILITY_SPECS,
    S16_ACTION_OUTCOME_CAPABILITY_SPEC,
)

S16_DESCRIPTOR_SET = CapabilityDescriptorSet(
    operators=(
        *S15_DESCRIPTOR_SET.operators,
        S16_ACTION_OUTCOME_TRANSLATE_OPERATOR_DESCRIPTOR,
        S16_ACTION_OUTCOME_RECORD_OPERATOR_DESCRIPTOR,
    ),
    criteria=(
        *S15_DESCRIPTOR_SET.criteria,
        S16_ACTION_OUTCOME_CRITERION_DESCRIPTOR,
    ),
)


def s16_capability_plan(
    *,
    enabled_ids: frozenset[str] = frozenset(),
) -> CapabilityPlan:
    """Build S16 Action-outcome integration metadata; nothing is enabled implicitly."""

    plan = CapabilityPlan(
        specs=S16_CAPABILITY_SPECS,
        enabled_ids=enabled_ids,
    )
    S16_DESCRIPTOR_SET.validate_plan(plan)
    return plan


S17_FEEDBACK_CAPABILITY_SPEC = CapabilitySpec(
    capability_id="FEEDBACK",
    operator_ids=("learning.interpret_action_outcome_feedback",),
    criterion_ids=("learning.explicit_outcome_feedback_orientation",),
    port_ids=(
        "learning.feedback_interpretation.out",
        "learning.feedback",
    ),
    dependencies=("ACTION_OUTCOME",),
)

S17_FEEDBACK_OPERATOR_DESCRIPTOR = OperatorDescriptor(
    operator_id="learning.interpret_action_outcome_feedback",
    capability_id="FEEDBACK",
    implementation_ref=(
        "relay_self.action_feedback."
        "interpret_action_outcome_as_learning_feedback"
    ),
    reads=(
        "execution.action",
        "transient.action_outcome_interpretation",
        "learning.feedback_criterion",
    ),
    writes=(
        "transient.learning_feedback_interpretation",
        "learning.feedback",
    ),
    effect=OperatorEffect.READ_ONLY,
)

S17_FEEDBACK_CRITERION_DESCRIPTOR = CriterionDescriptor(
    criterion_id="learning.explicit_outcome_feedback_orientation",
    capability_id="FEEDBACK",
    implementation_ref=(
        "relay_self.action_feedback."
        "interpret_action_outcome_as_learning_feedback"
    ),
    reads=(
        "execution.action",
        "transient.action_outcome_interpretation",
        "learning.feedback_criterion",
    ),
    kind=CriterionKind.COGNITIVE_ORIENTATION,
    semantics=(
        "For one exact already-closed Action result, explicitly orient one "
        "named retained learning target toward INCREASE, DECREASE, or HOLD "
        "only when exact Action/binding/action-ref/state/outcome-reason "
        "constraints match; no commit authority is granted."
    ),
)

S17_CAPABILITY_SPECS = (
    *S16_CAPABILITY_SPECS,
    S17_FEEDBACK_CAPABILITY_SPEC,
)

S17_DESCRIPTOR_SET = CapabilityDescriptorSet(
    operators=(
        *S16_DESCRIPTOR_SET.operators,
        S17_FEEDBACK_OPERATOR_DESCRIPTOR,
    ),
    criteria=(
        *S16_DESCRIPTOR_SET.criteria,
        S17_FEEDBACK_CRITERION_DESCRIPTOR,
    ),
)


def s17_capability_plan(
    *,
    enabled_ids: frozenset[str] = frozenset(),
) -> CapabilityPlan:
    """Build S17 feedback-integration metadata; nothing is enabled implicitly."""

    plan = CapabilityPlan(
        specs=S17_CAPABILITY_SPECS,
        enabled_ids=enabled_ids,
    )
    S17_DESCRIPTOR_SET.validate_plan(plan)
    return plan
