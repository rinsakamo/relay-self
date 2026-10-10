"""B21: read-only typed S17/S10 source compatibility and S11 nonpromotion.

This test-only module validates the ACTUAL existing S17/S10 typed API on a
deterministic fake-Mineflayer test fixture. C15 information here is a
CALLER-SUPPLIED DESCRIPTION of an independent UNMERGED static spatial
witness, not an imported EndpointWitness or authenticated physical result.
No caller can obtain a production S11 authorization through this module.
"""
from __future__ import annotations

from dataclasses import dataclass

from relay_self.action import ActionLifecycle, ActionState
from relay_self.action_feedback import (
    ActionFeedbackCriterion,
    LearningFeedbackInterpretation,
    LearningFeedbackInterpretationStatus,
)
from relay_self.action_outcome import (
    ActionOutcomeDisposition,
    ActionOutcomeInterpretation,
)
from relay_self.habit import HabitRepertoire
from relay_self.learning import (
    LearningCommitResult,
    LearningProposalStatus,
)

C15_FROZEN_DRAFT_HEAD = "5e738596b805522d8516b43fa1b7ee001bfc5b2b"
S17_LOCAL_CLASS = "TYPED_LOCAL_S17_TO_S10_CHAIN_CONSISTENT"
NO_AUTHENTICATED_LINK = "NO_SHARED_AUTHENTICATED_PHYSICAL_ACTION_WITNESS"
BLOCKED = "PRODUCTION_S11_RETENTION_BLOCKED"
MISSING = (
    "LIVE_S16_S17_SAME_ACTION_PHYSICAL_SOURCE_ATTESTATION",
    "PHYSICAL_C15_ENDPOINT_BOUND_TO_S17_TASK_GOAL_CRITERION",
    "NONBYPASSABLE_PRODUCTION_S11_OWNER_WITH_REPLAY_GUARD",
    "DISCRIMINATING_L2_VS_CHEAP_NOVEL_RELEVANT_CUES",
    "INDEPENDENTLY_METERED_COST_FOR_ANY_PHYSICAL_RESOURCE_CLAIM",
)


class InvalidB21Chain(ValueError):
    """Local predecessor/feedback/retention mismatch; no product admission."""


@dataclass(frozen=True, slots=True)
class StaticC15Description:
    """Caller-supplied METADATA ONLY, not the C15 EndpointWitness itself."""

    source_draft_head: str
    status: str
    session_id: str
    start_action_id: str
    stop_action_id: str
    evidence: tuple[str, ...]
    live_qualification: str = "NOT_RUN"
    signed_action_label: str = "BLOCKED_UNDERDETERMINED"

    def __post_init__(self) -> None:
        if (
            self.source_draft_head != C15_FROZEN_DRAFT_HEAD
            or self.status not in (
                "GOAL_REGION_OBSERVED",
                "ALTERNATIVE_REGION_OBSERVED",
                "UNDETERMINED",
            )
            or self.live_qualification != "NOT_RUN"
            or self.signed_action_label != "BLOCKED_UNDERDETERMINED"
            or not self.session_id
            or not self.start_action_id
            or not self.stop_action_id
            or self.start_action_id == self.stop_action_id
            or not isinstance(self.evidence, tuple)
            or not all(isinstance(x, str) and x for x in self.evidence)
        ):
            raise InvalidB21Chain("C15 static description malformed or promoted")


@dataclass(frozen=True, slots=True)
class TypedLocalChain:
    action_id: str
    binding_id: str
    skill_execution_id: str
    intent_id: str
    local_session_id: str
    feedback_id: str
    native_s10_target: str
    old_revision: int
    new_revision: int
    terminal_classification: str = S17_LOCAL_CLASS
    physical_source_verified: bool = False
    task_goal_verified: bool = False
    authorizes_s11: bool = False


@dataclass(frozen=True, slots=True)
class B21BoundaryReport:
    typed_local_chain: TypedLocalChain
    c15_static_description_seen: bool
    static_endpoint_status: str | None
    c15_matches_claimed_strings: bool
    real_c15_endpoint_signed_goal: bool
    real_s17_source_attested: bool
    production_s11_owner_authorized: bool
    production_habit_acquired: bool
    owner_revision_unchanged: int
    reason: str
    missing_witnesses: tuple[str, ...]


def validate_typed_s17_s10(
    action: ActionLifecycle,
    outcome: ActionOutcomeInterpretation,
    interpreted: LearningFeedbackInterpretation,
    committed: LearningCommitResult,
    criterion: ActionFeedbackCriterion,
) -> TypedLocalChain:
    """Only local typed API consistency; NEVER authenticate a sensor."""
    if (
        not isinstance(action, ActionLifecycle)
        or not isinstance(outcome, ActionOutcomeInterpretation)
        or not isinstance(interpreted, LearningFeedbackInterpretation)
        or not isinstance(committed, LearningCommitResult)
        or not isinstance(criterion, ActionFeedbackCriterion)
    ):
        raise InvalidB21Chain("all five actual S17/S10 typed objects required")
    if (
        not action.is_current_snapshot
        or action.state is not ActionState.OUTCOME
        or outcome.disposition is not ActionOutcomeDisposition.OUTCOME
        or outcome.reason_code != "observed_execution"
    ):
        raise InvalidB21Chain("real typed S17 terminal OUTCOME required")
    if (
        action.action_id != outcome.action_id
        or action.skill_execution_id != outcome.skill_execution_id
        or action.intent_id != outcome.intent_id
        or not outcome.session_id
        or outcome.action_id != criterion.required_action_id
        or outcome.binding_id != criterion.required_binding_id
        or outcome.action_ref != criterion.required_action_ref
        or criterion.required_action_state is not action.state
        or criterion.required_outcome_disposition is not outcome.disposition
        or criterion.required_outcome_reason != outcome.reason_code
    ):
        raise InvalidB21Chain("exact original Action/binding/criterion mismatch")
    feedback = interpreted.feedback
    if (
        interpreted.status is not LearningFeedbackInterpretationStatus.PRODUCED
        or feedback is None
        or interpreted.action_id != action.action_id
        or interpreted.skill_execution_id != action.skill_execution_id
        or interpreted.intent_id != action.intent_id
        or interpreted.binding_id != outcome.binding_id
        or interpreted.action_ref != outcome.action_ref
        or interpreted.target_id != criterion.target_id
        or interpreted.criterion_id != criterion.criterion_id
        or interpreted.criterion_provenance != criterion.provenance
        or interpreted.outcome_reason != outcome.reason_code
        or interpreted.action_outcome_provenance != outcome.provenance
        or interpreted.world_provenance != outcome.world_provenance
        or interpreted.outcome_ref != (
            "action-outcome:"
            f"{outcome.action_id}:{outcome.binding_id}:"
            f"{outcome.session_id}:{outcome.reason_code}"
        )
        or feedback.consequence_ref != interpreted.outcome_ref
        or feedback.feedback_id != (
            "feedback:"
            f"{criterion.criterion_id}:{criterion.target_id}:"
            f"{outcome.action_id}:{outcome.binding_id}:"
            f"{outcome.session_id}:{outcome.reason_code}"
        )
        or feedback.direction is not criterion.feedback_direction
    ):
        raise InvalidB21Chain("S17 interpretation not original criterion/outcome")
    if (
        committed.proposal.feedback is not feedback
        or committed.proposal.target_id != criterion.target_id
        or committed.record.feedback_id != feedback.feedback_id
        or committed.record.feedback_provenance != feedback.provenance
        or committed.record.authority_id == ""
        or committed.previous_state.target_id != criterion.target_id
        or committed.new_state.target_id != criterion.target_id
        or committed.previous_state.revision
        != committed.proposal.expected_revision
        or committed.new_state.revision != committed.previous_state.revision + 1
        or committed.record.committed_revision != committed.new_state.revision
        or committed.record.previous_revision != committed.previous_state.revision
        or committed.record.previous_value != committed.previous_state.value
        or committed.record.resulting_value != committed.new_state.value
        or committed.new_state.last_update != committed.record
        or committed.proposal.status is not LearningProposalStatus.UPDATED
    ):
        raise InvalidB21Chain("actual native S10 original feedback/owner commit absent")
    return TypedLocalChain(
        action_id=action.action_id,
        binding_id=outcome.binding_id,
        skill_execution_id=action.skill_execution_id,
        intent_id=action.intent_id,
        local_session_id=outcome.session_id,
        feedback_id=feedback.feedback_id,
        native_s10_target=criterion.target_id,
        old_revision=committed.previous_state.revision,
        new_revision=committed.new_state.revision,
    )


def assess_production_s11_boundary(
    action: ActionLifecycle,
    outcome: ActionOutcomeInterpretation,
    interpreted: LearningFeedbackInterpretation,
    committed: LearningCommitResult,
    criterion: ActionFeedbackCriterion,
    owner: HabitRepertoire,
    *,
    c15_static: StaticC15Description | None = None,
) -> B21BoundaryReport:
    """Do not issue grants/mutate retained owner; static C15 never qualifies."""
    local = validate_typed_s17_s10(
        action, outcome, interpreted, committed, criterion,
    )
    if not isinstance(owner, HabitRepertoire):
        raise InvalidB21Chain("actual immutable S11 repertoire required")
    if c15_static is not None and not isinstance(
        c15_static, StaticC15Description
    ):
        raise InvalidB21Chain("C15 data is at most typed static description")
    # Even this *maximally* matching caller description is not a signed goal
    # proof: C15's independent Draft has no physical trust root or production
    # action-to-task success semantics.
    match = (
        c15_static is not None
        and c15_static.session_id == local.local_session_id
        and c15_static.start_action_id == local.action_id
    )
    return B21BoundaryReport(
        typed_local_chain=local,
        c15_static_description_seen=c15_static is not None,
        static_endpoint_status=(
            None if c15_static is None else c15_static.status
        ),
        c15_matches_claimed_strings=match,
        real_c15_endpoint_signed_goal=False,
        real_s17_source_attested=False,
        production_s11_owner_authorized=False,
        production_habit_acquired=False,
        owner_revision_unchanged=owner.revision,
        reason=BLOCKED,
        missing_witnesses=MISSING,
    )
