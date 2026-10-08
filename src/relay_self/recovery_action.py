"""S23: caller-explicit Action proposal under one already-started recovery Skill.

This is a narrow S22 -> S13/S14 -> existing ActionLifecycle seam.
It does not start another Skill, authorize/issue an Action, or create an epoch.
"""
from __future__ import annotations

from dataclasses import dataclass

from relay_self.action import ActionLifecycle, ActionState
from relay_self.action_supervision import ActionSupervisor, UnknownSupervisedAction
from relay_self.execution_admission import (
    AdmissionDecision,
    AdmissionDecisionStatus,
    ExecutionAdmissionCriterion,
)
from relay_self.execution_binding import (
    ExecutionBinding,
    ExecutionBindingResult,
    resolve_execution_binding,
)
from relay_self.route_adjudication import ControlCandidate, RouteDecision
from relay_self.skill import SkillExecution, SkillState
from relay_self.skill_exit_routing import (
    SkillExitAssessment,
    SkillExitAuthority,
    SkillExitRoute,
    assess_skill_exit,
)
from relay_self.provenance import Provenance


class InvalidRecoveryActionLineage(ValueError):
    """The recovered Skill / admission / Action ownership chain is not exact."""


@dataclass(frozen=True, slots=True)
class RecoveryActionHandoff:
    """Evidence only; not a second Action or Skill authority owner."""

    failed_skill_execution_id: str
    recovery_skill_execution_id: str
    recovery_skill_id: str
    intent_id: str
    route_candidate_ref: str
    admission_criterion_id: str
    binding_id: str
    action_id: str
    authority_id: str
    provenance: Provenance


def propose_explicit_recovery_action(
    assessment: SkillExitAssessment,
    route_authority: SkillExitAuthority,
    recovery_skill: SkillExecution,
    previous_action: ActionLifecycle,
    supervisor: ActionSupervisor,
    previous_admission: AdmissionDecision,
    new_admission: AdmissionDecision,
    control: ControlCandidate,
    route: RouteDecision,
    criterion: ExecutionAdmissionCriterion,
    binding: ExecutionBinding,
    *,
    at_ns: int,
    provenance: Provenance,
) -> tuple[ActionLifecycle, ExecutionBindingResult, RecoveryActionHandoff]:
    """Use a fresh S13 decision and already-running S22 Skill for Action PROPOSED.

    Unlike S14 start_and_propose_bound_execution, this path must NOT call
    SkillExecution.start a second time. Issuance remains ActionSupervisor-owned.
    """
    if not isinstance(assessment, SkillExitAssessment):
        raise InvalidRecoveryActionLineage("requires S22 assessment")
    if not isinstance(route_authority, SkillExitAuthority) or not route_authority.granted:
        raise InvalidRecoveryActionLineage("missing S22 route authority")
    if not isinstance(recovery_skill, SkillExecution):
        raise InvalidRecoveryActionLineage("recovery Skill must be SkillExecution")
    if not isinstance(previous_action, ActionLifecycle) or not isinstance(
        supervisor, ActionSupervisor
    ):
        raise InvalidRecoveryActionLineage("requires supervised previous Action")
    if not isinstance(previous_admission, AdmissionDecision):
        raise InvalidRecoveryActionLineage("requires previous S13 admission")
    if not isinstance(new_admission, AdmissionDecision):
        raise InvalidRecoveryActionLineage("requires distinct fresh S13 admission")
    if not isinstance(criterion, ExecutionAdmissionCriterion):
        raise InvalidRecoveryActionLineage("requires explicit S13 admission criterion")
    if not isinstance(binding, ExecutionBinding):
        raise InvalidRecoveryActionLineage("requires explicit Action mapping")
    if not isinstance(provenance, Provenance):
        raise InvalidRecoveryActionLineage("provenance must be typed")
    if not isinstance(at_ns, int) or isinstance(at_ns, bool) or at_ns < 0:
        raise InvalidRecoveryActionLineage("at_ns must be nonnegative integer")
    if assessment.intent.events != assessment.intent_events:
        raise InvalidRecoveryActionLineage("Intent owner changed since S22 assessment")
    if assessment.intent.pending_reconsideration is not None:
        raise InvalidRecoveryActionLineage("cannot recover while reconsideration pending")
    if not assessment.skill.is_current_snapshot or assessment.skill.state is not SkillState.FAILED:
        raise InvalidRecoveryActionLineage("original Skill must remain current FAILED")
    fresh = assess_skill_exit(
        assessment.skill, assessment.intent, assessment.criterion, assessment.evidence,
    )
    if (\n        assessment.route is not fresh.route\n        or fresh.route is not SkillExitRoute.LOCAL_RECOVERY_CANDIDATE\n    ):
        raise InvalidRecoveryActionLineage("route is not an admitted local recovery")
    if not (
        route_authority.route is SkillExitRoute.LOCAL_RECOVERY_CANDIDATE
        and route_authority.criterion_id == assessment.criterion.criterion_id
        and route_authority.intent_id == assessment.skill.intent_id
    ):
        raise InvalidRecoveryActionLineage("S22 authority scope mismatch")
    if not recovery_skill.is_current_snapshot or recovery_skill.state is not SkillState.STARTED:
        raise InvalidRecoveryActionLineage("recovery Skill is stale or not STARTED")
    if (
        recovery_skill.execution_id == assessment.skill.execution_id
        or recovery_skill.skill_id != assessment.evidence.alternative_skill_id
        or recovery_skill.intent_id != assessment.skill.intent_id
        or recovery_skill.events[0].at_ns < assessment.evidence.observed_at_ns
    ):
        raise InvalidRecoveryActionLineage("recovered Skill does not match S22 path")
    current = assessment.intent.current_intent
    if current is None or current.intent_id != recovery_skill.intent_id:
        raise InvalidRecoveryActionLineage("Current Intent was released/replaced")
    if previous_action.state is not ActionState.OUTCOME or not previous_action.is_current_snapshot:
        raise InvalidRecoveryActionLineage("previous Action must be terminal OUTCOME")
    if (
        supervisor.get(previous_action.action_id) is not previous_action
        or previous_action.skill_execution_id != assessment.skill.execution_id
        or previous_action.intent_id != recovery_skill.intent_id
    ):
        raise InvalidRecoveryActionLineage("previous Action is not matching current owner")
    if (
        new_admission.status is not AdmissionDecisionStatus.ADMITTED
        or previous_admission.status is not AdmissionDecisionStatus.ADMITTED
        or new_admission == previous_admission
        or new_admission.admission_criterion_id == previous_admission.admission_criterion_id
        or new_admission.provenance == previous_admission.provenance
    ):
        raise InvalidRecoveryActionLineage("recovery requires independently evaluated S13")
    if (
        binding.action_id == previous_action.action_id
        or binding.skill_execution_id != recovery_skill.execution_id
        or binding.skill_ref != recovery_skill.skill_id
        or binding.required_intent_id != recovery_skill.intent_id
    ):
        raise InvalidRecoveryActionLineage("Action/Skill binding mismatch")
    try:
        supervisor.get(binding.action_id)
    except UnknownSupervisedAction:
        pass
    else:
        raise InvalidRecoveryActionLineage("Action ID already supervised")
    if at_ns < max(recovery_skill.events[0].at_ns, assessment.evidence.observed_at_ns):
        raise InvalidRecoveryActionLineage("proposal precedes recovery admission evidence")
    if supervisor.last_at_ns is not None and at_ns < supervisor.last_at_ns:
        raise InvalidRecoveryActionLineage("proposal predates supervisor clock")

    # The established S14 validator recomputes admission from S12/S13 inputs.
    bound = resolve_execution_binding(
        new_admission, control, route, assessment.intent, criterion,
        binding, provenance=provenance,
    )
    if bound.intent_id != recovery_skill.intent_id:
        raise InvalidRecoveryActionLineage("bound candidate Intent mismatch")

    # Reuse existing Action owner seam. No S14 SkillExecution.start repeat.
    proposed = ActionLifecycle.propose(
        binding.action_id, skill_execution=recovery_skill,
        intent_commitment=assessment.intent, at_ns=at_ns, provenance=provenance,
    )
    result = ExecutionBindingResult(
        binding_id=binding.binding_id, candidate_ref=binding.candidate_ref,
        intent_id=recovery_skill.intent_id, skill_execution_id=recovery_skill.execution_id,
        skill_ref=recovery_skill.skill_id, action_id=proposed.action_id,
        action_ref=binding.action_ref, skill_state=recovery_skill.state,
        action_state=proposed.state, provenance=provenance,
    )
    handoff = RecoveryActionHandoff(
        failed_skill_execution_id=assessment.skill.execution_id,
        recovery_skill_execution_id=recovery_skill.execution_id,
        recovery_skill_id=recovery_skill.skill_id,
        intent_id=recovery_skill.intent_id,
        route_candidate_ref=binding.candidate_ref,
        admission_criterion_id=criterion.criterion_id,
        binding_id=binding.binding_id,
        action_id=binding.action_id,
        authority_id=route_authority.authority_id,
        provenance=provenance,
    )
    return proposed, result, handoff
