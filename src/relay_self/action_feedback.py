from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from relay_self.action import ActionLifecycle, ActionState
from relay_self.action_outcome import (
    ActionOutcomeDisposition,
    ActionOutcomeInterpretation,
)
from relay_self.learning import FeedbackDirection, LearningFeedback
from relay_self.provenance import Provenance


class ActionFeedbackError(ValueError):
    """Base error for explicit Action-outcome learning-feedback integration."""


class InvalidActionFeedbackData(ActionFeedbackError):
    """Raised when Action-feedback data violates the bounded S17 contract."""


class LearningFeedbackInterpretationStatus(str, Enum):
    PRODUCED = "produced"
    NOT_APPLICABLE = "not_applicable"
    UNDETERMINED = "undetermined"


@dataclass(frozen=True, slots=True)
class ActionFeedbackCriterion:
    """Explicit orientation from one exact known Action result to one LRN target."""

    criterion_id: str
    target_id: str
    required_action_id: str
    required_binding_id: str
    required_action_ref: str
    required_action_state: ActionState
    required_outcome_disposition: ActionOutcomeDisposition
    required_outcome_reason: str
    feedback_direction: FeedbackDirection
    provenance: Provenance

    def __post_init__(self) -> None:
        _require_identifier("criterion_id", self.criterion_id)
        _require_identifier("target_id", self.target_id)
        _require_identifier("required_action_id", self.required_action_id)
        _require_identifier("required_binding_id", self.required_binding_id)
        _require_identifier("required_action_ref", self.required_action_ref)
        if self.required_action_state not in {
            ActionState.OUTCOME,
            ActionState.UNKNOWN,
        }:
            raise InvalidActionFeedbackData(
                "feedback criterion requires OUTCOME or UNKNOWN Action state"
            )
        if self.required_outcome_disposition not in {
            ActionOutcomeDisposition.OUTCOME,
            ActionOutcomeDisposition.UNKNOWN,
        }:
            raise InvalidActionFeedbackData(
                "feedback criterion requires OUTCOME or UNKNOWN disposition"
            )
        expected_state = (
            ActionState.OUTCOME
            if self.required_outcome_disposition
            is ActionOutcomeDisposition.OUTCOME
            else ActionState.UNKNOWN
        )
        if self.required_action_state is not expected_state:
            raise InvalidActionFeedbackData(
                "feedback criterion Action state must match outcome disposition"
            )
        _require_identifier(
            "required_outcome_reason",
            self.required_outcome_reason,
        )
        if not isinstance(self.feedback_direction, FeedbackDirection):
            raise InvalidActionFeedbackData(
                "feedback_direction must be FeedbackDirection"
            )
        _require_provenance("criterion provenance", self.provenance)


@dataclass(frozen=True, slots=True)
class LearningFeedbackInterpretation:
    """Immutable audit result; never mutates the retained LRN owner."""

    status: LearningFeedbackInterpretationStatus
    action_id: str
    skill_execution_id: str
    intent_id: str
    criterion_id: str
    target_id: str
    binding_id: str | None
    action_ref: str | None
    outcome_ref: str | None
    outcome_reason: str | None
    feedback: LearningFeedback | None
    reason_code: str
    criterion_provenance: Provenance
    outcome_provenance: Provenance | None
    provenance: Provenance

    def __post_init__(self) -> None:
        if not isinstance(self.status, LearningFeedbackInterpretationStatus):
            raise InvalidActionFeedbackData(
                "status must be LearningFeedbackInterpretationStatus"
            )
        _require_identifier("action_id", self.action_id)
        _require_identifier("skill_execution_id", self.skill_execution_id)
        _require_identifier("intent_id", self.intent_id)
        _require_identifier("criterion_id", self.criterion_id)
        _require_identifier("target_id", self.target_id)
        for name, value in (
            ("binding_id", self.binding_id),
            ("action_ref", self.action_ref),
            ("outcome_ref", self.outcome_ref),
            ("outcome_reason", self.outcome_reason),
        ):
            if value is not None:
                _require_identifier(name, value)
        if self.feedback is not None and not isinstance(
            self.feedback,
            LearningFeedback,
        ):
            raise InvalidActionFeedbackData(
                "feedback must be LearningFeedback or None"
            )
        _require_identifier("reason_code", self.reason_code)
        _require_provenance(
            "criterion_provenance",
            self.criterion_provenance,
        )
        if self.outcome_provenance is not None:
            _require_provenance(
                "outcome_provenance",
                self.outcome_provenance,
            )
        _require_provenance("interpretation provenance", self.provenance)

        if self.status is LearningFeedbackInterpretationStatus.PRODUCED:
            if (
                self.feedback is None
                or self.binding_id is None
                or self.action_ref is None
                or self.outcome_ref is None
                or self.outcome_reason is None
                or self.outcome_provenance is None
            ):
                raise InvalidActionFeedbackData(
                    "PRODUCED interpretation requires exact outcome and feedback"
                )
            if self.feedback.target_id != self.target_id:
                raise InvalidActionFeedbackData(
                    "produced feedback target must match interpretation target"
                )
            if self.feedback.consequence_ref != self.outcome_ref:
                raise InvalidActionFeedbackData(
                    "produced feedback consequence_ref must match outcome_ref"
                )
        elif self.feedback is not None:
            raise InvalidActionFeedbackData(
                "non-PRODUCED interpretation cannot carry LearningFeedback"
            )


def interpret_action_outcome_as_learning_feedback(
    action: ActionLifecycle,
    outcome: ActionOutcomeInterpretation | None,
    criterion: ActionFeedbackCriterion,
    *,
    provenance: Provenance,
) -> LearningFeedbackInterpretation:
    """Purely orient one exact Action outcome into structured S10 feedback.

    The function never proposes or commits a learning update. It uses only
    already-structured Action/S16 data and one explicit caller-owned criterion.
    """

    if not isinstance(action, ActionLifecycle):
        raise InvalidActionFeedbackData("action must be ActionLifecycle")
    if outcome is not None and not isinstance(
        outcome,
        ActionOutcomeInterpretation,
    ):
        raise InvalidActionFeedbackData(
            "outcome must be ActionOutcomeInterpretation or None"
        )
    if not isinstance(criterion, ActionFeedbackCriterion):
        raise InvalidActionFeedbackData(
            "criterion must be ActionFeedbackCriterion"
        )
    _require_provenance("feedback interpretation provenance", provenance)

    if not action.is_current_snapshot:
        raise InvalidActionFeedbackData(
            "feedback interpretation requires current Action snapshot"
        )

    if outcome is None:
        return _without_feedback(
            action,
            criterion,
            status=LearningFeedbackInterpretationStatus.NOT_APPLICABLE,
            reason_code="missing_action_outcome_interpretation",
            provenance=provenance,
        )

    _require_exact_outcome_lineage(action, outcome)

    if outcome.disposition is ActionOutcomeDisposition.UNAVAILABLE:
        return _without_feedback(
            action,
            criterion,
            status=LearningFeedbackInterpretationStatus.UNDETERMINED,
            reason_code="action_outcome_unavailable",
            provenance=provenance,
            outcome=outcome,
        )

    expected_state = (
        ActionState.OUTCOME
        if outcome.disposition is ActionOutcomeDisposition.OUTCOME
        else ActionState.UNKNOWN
    )
    if action.state is not expected_state:
        raise InvalidActionFeedbackData(
            "Action terminal state does not match S16 outcome disposition"
        )

    if not _criterion_matches(action, outcome, criterion):
        return _without_feedback(
            action,
            criterion,
            status=LearningFeedbackInterpretationStatus.NOT_APPLICABLE,
            reason_code="explicit_feedback_criterion_not_matched",
            provenance=provenance,
            outcome=outcome,
        )

    outcome_ref = _outcome_ref(outcome)
    feedback_id = _feedback_id(criterion, outcome)
    feedback = LearningFeedback(
        feedback_id=feedback_id,
        target_id=criterion.target_id,
        direction=criterion.feedback_direction,
        provenance=provenance,
        consequence_ref=outcome_ref,
    )
    return LearningFeedbackInterpretation(
        status=LearningFeedbackInterpretationStatus.PRODUCED,
        action_id=action.action_id,
        skill_execution_id=action.skill_execution_id,
        intent_id=action.intent_id,
        criterion_id=criterion.criterion_id,
        target_id=criterion.target_id,
        binding_id=outcome.binding_id,
        action_ref=outcome.action_ref,
        outcome_ref=outcome_ref,
        outcome_reason=outcome.reason_code,
        feedback=feedback,
        reason_code="explicit_feedback_criterion_matched",
        criterion_provenance=criterion.provenance,
        outcome_provenance=outcome.world_provenance,
        provenance=provenance,
    )


def _criterion_matches(
    action: ActionLifecycle,
    outcome: ActionOutcomeInterpretation,
    criterion: ActionFeedbackCriterion,
) -> bool:
    return (
        action.action_id == criterion.required_action_id
        and outcome.binding_id == criterion.required_binding_id
        and outcome.action_ref == criterion.required_action_ref
        and action.state is criterion.required_action_state
        and outcome.disposition is criterion.required_outcome_disposition
        and outcome.reason_code == criterion.required_outcome_reason
    )


def _require_exact_outcome_lineage(
    action: ActionLifecycle,
    outcome: ActionOutcomeInterpretation,
) -> None:
    if action.action_id != outcome.action_id:
        raise InvalidActionFeedbackData(
            "Action action_id does not match S16 outcome interpretation"
        )
    if action.skill_execution_id != outcome.skill_execution_id:
        raise InvalidActionFeedbackData(
            "Action skill_execution_id does not match S16 outcome interpretation"
        )
    if action.intent_id != outcome.intent_id:
        raise InvalidActionFeedbackData(
            "Action intent_id does not match S16 outcome interpretation"
        )


def _without_feedback(
    action: ActionLifecycle,
    criterion: ActionFeedbackCriterion,
    *,
    status: LearningFeedbackInterpretationStatus,
    reason_code: str,
    provenance: Provenance,
    outcome: ActionOutcomeInterpretation | None = None,
) -> LearningFeedbackInterpretation:
    return LearningFeedbackInterpretation(
        status=status,
        action_id=action.action_id,
        skill_execution_id=action.skill_execution_id,
        intent_id=action.intent_id,
        criterion_id=criterion.criterion_id,
        target_id=criterion.target_id,
        binding_id=None if outcome is None else outcome.binding_id,
        action_ref=None if outcome is None else outcome.action_ref,
        outcome_ref=None if outcome is None else _outcome_ref(outcome),
        outcome_reason=None if outcome is None else outcome.reason_code,
        feedback=None,
        reason_code=reason_code,
        criterion_provenance=criterion.provenance,
        outcome_provenance=None if outcome is None else outcome.world_provenance,
        provenance=provenance,
    )


def _outcome_ref(outcome: ActionOutcomeInterpretation) -> str:
    return (
        "action-outcome:"
        f"{outcome.action_id}:"
        f"{outcome.binding_id}:"
        f"{outcome.session_id}:"
        f"{outcome.reason_code}"
    )


def _feedback_id(
    criterion: ActionFeedbackCriterion,
    outcome: ActionOutcomeInterpretation,
) -> str:
    return (
        "feedback:"
        f"{criterion.criterion_id}:"
        f"{criterion.target_id}:"
        f"{outcome.action_id}:"
        f"{outcome.binding_id}:"
        f"{outcome.session_id}:"
        f"{outcome.reason_code}"
    )


def _require_identifier(name: str, value: object) -> None:
    if not isinstance(value, str) or not value.strip():
        raise InvalidActionFeedbackData(f"{name} must be a non-empty string")
    if value != value.strip() or any(character.isspace() for character in value):
        raise InvalidActionFeedbackData(
            f"{name} must be one structured identifier without whitespace"
        )


def _require_provenance(name: str, value: object) -> None:
    if not isinstance(value, Provenance):
        raise InvalidActionFeedbackData(f"{name} must be Provenance")
