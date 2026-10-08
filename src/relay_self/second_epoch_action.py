"""Stateless second-epoch lineage and bounded World-result guards.

These guards establish *evidence eligibility*, never admission, binding,
authorization, issue, physical execution, or Action outcome by themselves.
The existing S13-S16 transitions remain the only such authority paths.
"""
from __future__ import annotations

from dataclasses import dataclass

from adapters.mineflayer.execution import WorldConsequence
from relay_self.action import ActionLifecycle, ActionState
from relay_self.action_feedback import (
    LearningFeedbackInterpretation,
    LearningFeedbackInterpretationStatus,
)
from relay_self.action_supervision import ActionSupervisor
from relay_self.execution_binding import ExecutionBinding, ExecutionBindingResult
from relay_self.learning import LearningPreferenceState
from relay_self.planning import PlanSelection, PlanSelectionStatus
from relay_self.prediction import PredictionState
from relay_self.provenance import Provenance


class InvalidSecondEpochLineage(ValueError):
    """Caller-provided consecutive-epoch evidence does not match exact owners."""


class InvalidSecondEpochConsequence(ValueError):
    """The second World result is stale, cross-session, late, or mismatched."""


@dataclass(frozen=True, slots=True)
class SecondEpochLineage:
    """Read-only exact ancestry pointer, NOT authorization."""

    first_action_id: str
    first_feedback_id: str
    learning_authority_id: str
    committed_revision: int
    prediction_source_refs: tuple[str, ...]
    selected_candidate_ref: str
    second_binding_id: str
    second_skill_execution_id: str
    second_action_id: str
    provenance: Provenance


def validate_second_epoch_lineage(
    supervisor: ActionSupervisor,
    first_action: ActionLifecycle,
    first_feedback: LearningFeedbackInterpretation,
    retained: LearningPreferenceState,
    prediction: PredictionState,
    plan: PlanSelection,
    binding: ExecutionBinding,
    *,
    provenance: Provenance,
) -> SecondEpochLineage:
    """Validate ancestry and distinct identities before S14 owner transitions."""
    if not isinstance(supervisor, ActionSupervisor):
        raise InvalidSecondEpochLineage("supervisor must be ActionSupervisor")
    if not isinstance(first_action, ActionLifecycle):
        raise InvalidSecondEpochLineage("first_action must be ActionLifecycle")
    if not isinstance(first_feedback, LearningFeedbackInterpretation):
        raise InvalidSecondEpochLineage("first_feedback must be typed interpretation")
    if not isinstance(retained, LearningPreferenceState):
        raise InvalidSecondEpochLineage("retained must be LearningPreferenceState")
    if not isinstance(prediction, PredictionState):
        raise InvalidSecondEpochLineage("prediction must be PredictionState")
    if not isinstance(plan, PlanSelection) or plan.status is not PlanSelectionStatus.SELECTED:
        raise InvalidSecondEpochLineage("second PLAN must select one candidate")
    if not isinstance(binding, ExecutionBinding):
        raise InvalidSecondEpochLineage("binding must be ExecutionBinding")
    if not isinstance(provenance, Provenance):
        raise InvalidSecondEpochLineage("provenance must be Provenance")
    if first_action.state is not ActionState.OUTCOME or not first_action.is_current_snapshot:
        raise InvalidSecondEpochLineage("first Action must be current terminal OUTCOME")
    if supervisor.get(first_action.action_id) is not first_action:
        raise InvalidSecondEpochLineage("first Action is not supervisor current owner snapshot")
    if first_feedback.status is not LearningFeedbackInterpretationStatus.PRODUCED:
        raise InvalidSecondEpochLineage("first Action must have explicit produced feedback")
    feedback = first_feedback.feedback
    update = retained.last_update
    if feedback is None or update is None:
        raise InvalidSecondEpochLineage("missing committed feedback lineage")
    if first_feedback.action_id != first_action.action_id:
        raise InvalidSecondEpochLineage("first feedback Action mismatch")
    if first_feedback.skill_execution_id != first_action.skill_execution_id:
        raise InvalidSecondEpochLineage("first feedback Skill mismatch")
    if first_feedback.intent_id != first_action.intent_id:
        raise InvalidSecondEpochLineage("first feedback Intent mismatch")
    if feedback.feedback_id != update.feedback_id or feedback.target_id != retained.target_id:
        raise InvalidSecondEpochLineage("feedback is not committed to target")
    if update.committed_revision != retained.revision:
        raise InvalidSecondEpochLineage("retained revision is not committed revision")
    if binding.action_id == first_action.action_id:
        raise InvalidSecondEpochLineage("second Action identity must be distinct")
    if binding.skill_execution_id == first_action.skill_execution_id:
        raise InvalidSecondEpochLineage("second Skill execution identity must be distinct")
    if binding.binding_id == first_feedback.binding_id:
        raise InvalidSecondEpochLineage("second binding identity must be distinct")
    if binding.required_intent_id != first_action.intent_id:
        raise InvalidSecondEpochLineage("second binding must name current inherited Intent")
    if plan.selected is None or plan.selected.candidate_id != binding.candidate_ref:
        raise InvalidSecondEpochLineage("binding does not match second PLAN selection")
    required_refs = (
        f"learning-target:{retained.target_id}",
        f"learning-revision:{retained.revision}",
        f"learning-feedback:{update.feedback_id}",
        f"learning-rule:{update.rule_id}:v{update.rule_version}",
        f"learning-authority:{update.authority_id}",
        f"learning-commit-revision:{update.committed_revision}",
    )
    if any(ref not in prediction.source_refs for ref in required_refs):
        raise InvalidSecondEpochLineage("prediction lost exact governed learning refs")
    required_sources = (
        update.feedback_provenance,
        update.authority_provenance,
        update.update_provenance,
    )
    if any(p not in prediction.source_provenance for p in required_sources):
        raise InvalidSecondEpochLineage("prediction lost learning provenance")
    if any(p not in plan.selected.source_provenance for p in required_sources):
        raise InvalidSecondEpochLineage("PLAN lost governed learning provenance")
    return SecondEpochLineage(
        first_action_id=first_action.action_id,
        first_feedback_id=feedback.feedback_id,
        learning_authority_id=update.authority_id,
        committed_revision=retained.revision,
        prediction_source_refs=prediction.source_refs,
        selected_candidate_ref=plan.selected.candidate_id,
        second_binding_id=binding.binding_id,
        second_skill_execution_id=binding.skill_execution_id,
        second_action_id=binding.action_id,
        provenance=provenance,
    )


def require_fresh_second_consequence(
    supervisor: ActionSupervisor,
    issued: ActionLifecycle,
    binding: ExecutionBindingResult,
    consequence: WorldConsequence,
    *,
    expected_session_id: str,
    first_session_id: str,
    at_ns: int,
) -> WorldConsequence:
    """Reject unsupported temporal/session lineage before existing S16 closure.

    The supervisor alone owns Action terminal transitions; this check never
    records the outcome, marks timeout, or grants issuance.
    """
    if not isinstance(supervisor, ActionSupervisor):
        raise InvalidSecondEpochConsequence("supervisor must be ActionSupervisor")
    if not isinstance(issued, ActionLifecycle) or issued.state is not ActionState.ISSUED:
        raise InvalidSecondEpochConsequence("requires ISSUED second Action")
    if not issued.is_current_snapshot or supervisor.get(issued.action_id) is not issued:
        raise InvalidSecondEpochConsequence("second Action is stale or not supervised")
    if not isinstance(binding, ExecutionBindingResult):
        raise InvalidSecondEpochConsequence("requires typed execution binding result")
    if not isinstance(consequence, WorldConsequence):
        raise InvalidSecondEpochConsequence("requires typed WorldConsequence")
    if (
        not isinstance(expected_session_id, str)
        or not expected_session_id.strip()
        or not isinstance(first_session_id, str)
        or not first_session_id.strip()
        or expected_session_id == first_session_id
    ):
        raise InvalidSecondEpochConsequence("sessions must be distinct and explicit")
    if consequence.session_id != expected_session_id:
        raise InvalidSecondEpochConsequence("wrong World session")
    if (
        consequence.action_id != issued.action_id
        or consequence.action_id != binding.action_id
        or consequence.binding_id != binding.binding_id
        or consequence.action_ref != binding.action_ref
        or issued.skill_execution_id != binding.skill_execution_id
        or issued.intent_id != binding.intent_id
    ):
        raise InvalidSecondEpochConsequence("second Action/binding lineage mismatch")
    if isinstance(at_ns, bool) or not isinstance(at_ns, int) or at_ns < 0:
        raise InvalidSecondEpochConsequence("at_ns must be nonnegative integer")
    if at_ns < issued.events[-1].at_ns:
        raise InvalidSecondEpochConsequence("outcome precedes issuance")
    if at_ns <= (supervisor.last_at_ns or 0):
        raise InvalidSecondEpochConsequence("outcome time must follow supervisor issue")
    deadline = issued.events[-1].deadline_ns
    if deadline is None or at_ns >= deadline:
        raise InvalidSecondEpochConsequence("World result arrived at/after deadline")
    return consequence
