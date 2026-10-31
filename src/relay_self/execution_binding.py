from __future__ import annotations

from dataclasses import dataclass

from relay_self.action import ActionEvent, ActionLifecycle, ActionState
from relay_self.execution_admission import (
    AdmissionDecision,
    AdmissionDecisionStatus,
    ExecutionAdmissionCriterion,
    admit_control_candidate,
)
from relay_self.intent import IntentCommitment
from relay_self.provenance import Provenance
from relay_self.route_adjudication import ControlCandidate, RouteDecision
from relay_self.skill import SkillEvent, SkillExecution, SkillState


class ExecutionBindingError(ValueError):
    """Base error for explicit admitted-candidate execution binding."""


class InvalidExecutionBindingData(ExecutionBindingError):
    """Raised when binding data or lineage does not satisfy S14 contracts."""


@dataclass(frozen=True, slots=True)
class ExecutionBinding:
    """Caller-owned declarative mapping from one admitted candidate to SKL/Action IDs."""

    binding_id: str
    candidate_ref: str
    required_intent_id: str
    skill_execution_id: str
    skill_ref: str
    action_id: str
    action_ref: str
    provenance: Provenance

    def __post_init__(self) -> None:
        _require_identifier("binding_id", self.binding_id)
        _require_identifier("candidate_ref", self.candidate_ref)
        _require_identifier("required_intent_id", self.required_intent_id)
        _require_identifier("skill_execution_id", self.skill_execution_id)
        _require_identifier("skill_ref", self.skill_ref)
        _require_identifier("action_id", self.action_id)
        _require_identifier("action_ref", self.action_ref)
        _require_provenance("binding provenance", self.provenance)


@dataclass(frozen=True, slots=True)
class BoundExecutionCandidate:
    """Pure validated bridge; no Skill or Action owner transition has occurred."""

    binding: ExecutionBinding
    candidate_ref: str
    intent_id: str
    admission_criterion_id: str
    route_criterion_id: str
    control_criterion_id: str
    admission_provenance: Provenance
    control_provenance: Provenance
    route_provenance: Provenance
    provenance: Provenance

    def __post_init__(self) -> None:
        if not isinstance(self.binding, ExecutionBinding):
            raise InvalidExecutionBindingData(
                "bound execution candidate requires ExecutionBinding"
            )
        _require_identifier("bound candidate_ref", self.candidate_ref)
        _require_identifier("bound intent_id", self.intent_id)
        _require_identifier(
            "bound admission_criterion_id",
            self.admission_criterion_id,
        )
        _require_identifier("bound route_criterion_id", self.route_criterion_id)
        _require_identifier(
            "bound control_criterion_id",
            self.control_criterion_id,
        )
        _require_provenance(
            "bound admission provenance",
            self.admission_provenance,
        )
        _require_provenance(
            "bound control provenance",
            self.control_provenance,
        )
        _require_provenance("bound route provenance", self.route_provenance)
        _require_provenance("bound provenance", self.provenance)

        if self.candidate_ref != self.binding.candidate_ref:
            raise InvalidExecutionBindingData(
                "bound candidate_ref must match binding candidate_ref"
            )
        if self.intent_id != self.binding.required_intent_id:
            raise InvalidExecutionBindingData(
                "bound intent_id must match binding required_intent_id"
            )


@dataclass(frozen=True, slots=True)
class ExecutionBindingResult:
    """Audit snapshot for one successful STARTED -> PROPOSED integration."""

    binding_id: str
    candidate_ref: str
    intent_id: str
    skill_execution_id: str
    skill_ref: str
    action_id: str
    action_ref: str
    skill_state: SkillState
    action_state: ActionState
    provenance: Provenance

    def __post_init__(self) -> None:
        _require_identifier("result binding_id", self.binding_id)
        _require_identifier("result candidate_ref", self.candidate_ref)
        _require_identifier("result intent_id", self.intent_id)
        _require_identifier(
            "result skill_execution_id",
            self.skill_execution_id,
        )
        _require_identifier("result skill_ref", self.skill_ref)
        _require_identifier("result action_id", self.action_id)
        _require_identifier("result action_ref", self.action_ref)
        if self.skill_state is not SkillState.STARTED:
            raise InvalidExecutionBindingData(
                "S14 result requires STARTED Skill state"
            )
        if self.action_state is not ActionState.PROPOSED:
            raise InvalidExecutionBindingData(
                "S14 result requires PROPOSED Action state"
            )
        _require_provenance("result provenance", self.provenance)


def resolve_execution_binding(
    admission: AdmissionDecision,
    control_candidate: ControlCandidate,
    route_decision: RouteDecision,
    intent_commitment: IntentCommitment,
    admission_criterion: ExecutionAdmissionCriterion,
    binding: ExecutionBinding,
    *,
    provenance: Provenance,
) -> BoundExecutionCandidate:
    """Purely validate S12/S13 lineage and one explicit caller-owned binding."""

    if not isinstance(admission, AdmissionDecision):
        raise InvalidExecutionBindingData(
            "admission must be AdmissionDecision"
        )
    if not isinstance(control_candidate, ControlCandidate):
        raise InvalidExecutionBindingData(
            "control_candidate must be ControlCandidate"
        )
    if not isinstance(route_decision, RouteDecision):
        raise InvalidExecutionBindingData(
            "route_decision must be RouteDecision"
        )
    if not isinstance(intent_commitment, IntentCommitment):
        raise InvalidExecutionBindingData(
            "intent_commitment must be IntentCommitment"
        )
    if not isinstance(admission_criterion, ExecutionAdmissionCriterion):
        raise InvalidExecutionBindingData(
            "admission_criterion must be ExecutionAdmissionCriterion"
        )
    if not isinstance(binding, ExecutionBinding):
        raise InvalidExecutionBindingData(
            "binding must be ExecutionBinding"
        )
    _require_provenance("binding resolution provenance", provenance)

    expected_admission = admit_control_candidate(
        control_candidate,
        route_decision,
        intent_commitment,
        admission_criterion,
        provenance=admission.provenance,
    )
    if admission != expected_admission:
        raise InvalidExecutionBindingData(
            "admission lineage does not match supplied route/control/intent guard"
        )
    if admission.status is not AdmissionDecisionStatus.ADMITTED:
        raise InvalidExecutionBindingData(
            "execution binding requires ADMITTED AdmissionDecision"
        )
    if admission.candidate_ref != control_candidate.candidate_ref:
        raise InvalidExecutionBindingData(
            "admission candidate_ref does not match ControlCandidate"
        )
    if binding.candidate_ref != admission.candidate_ref:
        raise InvalidExecutionBindingData(
            "binding candidate_ref does not match admitted candidate"
        )

    current_intent = intent_commitment.current_intent
    if current_intent is None:
        raise InvalidExecutionBindingData(
            "execution binding requires a current intent"
        )
    if admission.current_intent_id != current_intent.intent_id:
        raise InvalidExecutionBindingData(
            "admission current intent no longer matches actual Current Intent"
        )
    if binding.required_intent_id != current_intent.intent_id:
        raise InvalidExecutionBindingData(
            "binding required intent does not match actual Current Intent"
        )

    return BoundExecutionCandidate(
        binding=binding,
        candidate_ref=binding.candidate_ref,
        intent_id=current_intent.intent_id,
        admission_criterion_id=admission.admission_criterion_id,
        route_criterion_id=admission.route_criterion_id,
        control_criterion_id=admission.control_criterion_id,
        admission_provenance=admission.provenance,
        control_provenance=control_candidate.provenance,
        route_provenance=route_decision.provenance,
        provenance=provenance,
    )


def start_and_propose_bound_execution(
    bound: BoundExecutionCandidate,
    intent_commitment: IntentCommitment,
    *,
    at_ns: int,
    provenance: Provenance,
) -> tuple[SkillExecution, ActionLifecycle, ExecutionBindingResult]:
    """Use the real SKL and Action owner seams exactly once, then stop PROPOSED.

    All static proposal inputs are validated before SkillExecution.start().
    There is no callback, registry lookup, model call, authorization, or issue.
    """

    if not isinstance(bound, BoundExecutionCandidate):
        raise InvalidExecutionBindingData(
            "bound must be BoundExecutionCandidate"
        )
    if not isinstance(intent_commitment, IntentCommitment):
        raise InvalidExecutionBindingData(
            "intent_commitment must be IntentCommitment"
        )
    _require_at_ns(at_ns)
    _require_provenance("execution transition provenance", provenance)

    binding = bound.binding
    # Revalidate every downstream identifier before the first owner transition.
    _require_identifier("binding_id", binding.binding_id)
    _require_identifier("candidate_ref", binding.candidate_ref)
    _require_identifier("required_intent_id", binding.required_intent_id)
    _require_identifier("skill_execution_id", binding.skill_execution_id)
    _require_identifier("skill_ref", binding.skill_ref)
    _require_identifier("action_id", binding.action_id)
    _require_identifier("action_ref", binding.action_ref)

    current_intent = intent_commitment.current_intent
    if current_intent is None:
        raise InvalidExecutionBindingData(
            "execution transition requires a current intent"
        )
    if current_intent.intent_id != bound.intent_id:
        raise InvalidExecutionBindingData(
            "bound intent no longer matches actual Current Intent"
        )
    if current_intent.intent_id != binding.required_intent_id:
        raise InvalidExecutionBindingData(
            "binding required intent no longer matches actual Current Intent"
        )

    # Validate the exact event inputs used by the owner constructors before
    # SkillExecution.start() creates the first lifecycle snapshot.
    SkillEvent(
        state=SkillState.STARTED,
        at_ns=at_ns,
        provenance=provenance,
    )
    ActionEvent(
        state=ActionState.PROPOSED,
        at_ns=at_ns,
        provenance=provenance,
    )

    skill_execution = SkillExecution.start(
        binding.skill_execution_id,
        skill_id=binding.skill_ref,
        intent_commitment=intent_commitment,
        at_ns=at_ns,
        provenance=provenance,
    )

    action_lifecycle = ActionLifecycle.propose(
        binding.action_id,
        skill_execution=skill_execution,
        intent_commitment=intent_commitment,
        at_ns=at_ns,
        provenance=provenance,
    )

    result = ExecutionBindingResult(
        binding_id=binding.binding_id,
        candidate_ref=binding.candidate_ref,
        intent_id=current_intent.intent_id,
        skill_execution_id=skill_execution.execution_id,
        skill_ref=skill_execution.skill_id,
        action_id=action_lifecycle.action_id,
        action_ref=binding.action_ref,
        skill_state=skill_execution.state,
        action_state=action_lifecycle.state,
        provenance=provenance,
    )
    return skill_execution, action_lifecycle, result


def _require_identifier(name: str, value: object) -> None:
    if not isinstance(value, str) or not value.strip():
        raise InvalidExecutionBindingData(
            f"{name} must be a non-empty string"
        )
    if value != value.strip() or any(character.isspace() for character in value):
        raise InvalidExecutionBindingData(
            f"{name} must be one structured identifier without whitespace"
        )


def _require_at_ns(value: object) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise InvalidExecutionBindingData(
            "execution transition time must be a non-negative integer"
        )


def _require_provenance(name: str, value: object) -> None:
    if not isinstance(value, Provenance):
        raise InvalidExecutionBindingData(f"{name} must be Provenance")
