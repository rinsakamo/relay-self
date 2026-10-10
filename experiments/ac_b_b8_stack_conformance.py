"""AC-B B8: actual S17-stack read-only contract compatibility.

This is layered on exact unmerged S17 Draft HEAD, NEVER on main. Uses the
real S17 Action feedback, S10 governed learning and S11 read-only selection.
It owns neither source attestation nor a new Habit/Memory state. B7's signed
receipt handoff is a separate experiment and is NOT accepted here as S17 data.
"""
from __future__ import annotations

from dataclasses import dataclass

from relay_self.action import ActionLifecycle
from relay_self.action_feedback import (
    ActionFeedbackCriterion,
    LearningFeedbackInterpretation,
    LearningFeedbackInterpretationStatus,
    interpret_action_outcome_as_learning_feedback,
)
from relay_self.action_outcome import ActionOutcomeInterpretation
from relay_self.habit import (
    HabitCue,
    HabitRepertoire,
    HabitSelection,
    select_habit,
)
from relay_self.learning import (
    LearningCommitResult,
    LearningPreferenceState,
    LearningUpdateAuthority,
    LearningUpdateProposal,
    LearningUpdateRule,
    commit_learning_update,
    propose_learning_update,
)
from relay_self.provenance import Provenance


class NoQualifiedFeedback(ValueError):
    """Nothing observed and oriented by S17 to propose or commit as learning."""


@dataclass(frozen=True, slots=True)
class CrossOwnerRead:
    """Immutable result: feedback/proposal and independent HABIT read."""

    interpretation: LearningFeedbackInterpretation | None
    learning_proposal: LearningUpdateProposal | None
    habit_selection: HabitSelection
    original_state: LearningPreferenceState
    original_repertoire: HabitRepertoire
    no_action_authority: bool = True

    @property
    def qualified_feedback(self) -> bool:
        return (
            self.interpretation is not None
            and self.interpretation.status
            is LearningFeedbackInterpretationStatus.PRODUCED
            and self.interpretation.feedback is not None
        )


def inspect_existing_stack(
    *,
    action: ActionLifecycle,
    outcome: ActionOutcomeInterpretation | None,
    criterion: ActionFeedbackCriterion | None,
    preference: LearningPreferenceState,
    update_rule: LearningUpdateRule,
    repertoire: HabitRepertoire,
    cue: HabitCue,
    provenance: Provenance,
) -> CrossOwnerRead:
    """Read actual owner outputs, never infer S17 criteria from text or HABIT.

    Absence of an explicit ActionFeedbackCriterion means NO S17 feedback.
    HABIT always selects strictly from a caller-supplied retained repertoire
    and never becomes a source of World truth, Action issue or S10 feedback.
    """
    if not isinstance(preference, LearningPreferenceState):
        raise TypeError("exact S10 retained learning state required")
    if not isinstance(update_rule, LearningUpdateRule):
        raise TypeError("exact S10 bounded update rule required")
    if criterion is not None and not isinstance(criterion, ActionFeedbackCriterion):
        raise TypeError("S17 explicit typed criterion required")
    if not isinstance(provenance, Provenance):
        raise TypeError("integration provenance must be typed")
    # Let the actual S11 API validate existing repertoire and cue.
    selection = select_habit(repertoire, cue)
    interpreted = None
    proposal = None
    if criterion is not None:
        interpreted = interpret_action_outcome_as_learning_feedback(
            action, outcome, criterion, provenance=provenance,
        )
        if interpreted.status is LearningFeedbackInterpretationStatus.PRODUCED:
            if interpreted.feedback is None:
                raise NoQualifiedFeedback("S17 PRODUCED has no structured feedback")
            # Use actual S10 proposal semantics incl. exact target/replay checks.
            proposal = propose_learning_update(
                preference, interpreted.feedback, update_rule,
            )
    return CrossOwnerRead(
        interpretation=interpreted,
        learning_proposal=proposal,
        habit_selection=selection,
        original_state=preference,
        original_repertoire=repertoire,
    )


def commit_only_by_explicit_owner(
    inspected: CrossOwnerRead,
    authority: LearningUpdateAuthority | None,
    *, provenance: Provenance,
) -> LearningCommitResult:
    """Exact S10 owner transition, called only after separate caller grant.

    This is explicitly callable in an *offline test fixture*. The bridge
    never silently creates LearningUpdateAuthority, commits Habit, or issues
    Action.
    """
    if not isinstance(inspected, CrossOwnerRead):
        raise TypeError("valid B8 read-only inspection required")
    if inspected.learning_proposal is None or not inspected.qualified_feedback:
        raise NoQualifiedFeedback("no S17-qualified LearningFeedback for update")
    return commit_learning_update(
        inspected.original_state,
        inspected.learning_proposal,
        authority,
        provenance=provenance,
    )
