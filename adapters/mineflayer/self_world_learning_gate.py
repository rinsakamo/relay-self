"""Stage M: explicitly governed SelfWorld -> S17 -> S10 -> next epoch.

Pure existing-owner composition. No feedback from MATCH/UNDETERMINED,
no inference of reward from PRD error, and no Action execution or new
persistent store. The caller must supply the actual S17 typed chain; a
Stage L DEV report alone cannot satisfy it.
"""
from __future__ import annotations

from dataclasses import dataclass, replace

from adapters.mineflayer.execution import WorldConsequence
from adapters.mineflayer.self_world_prospective import (
    verify_prospective_native_reviews,
)
from adapters.mineflayer.self_world_projection import (
    interpret_self_world_mismatch_as_s17_feedback,
)
from relay_self.action import ActionLifecycle
from relay_self.action_feedback import (
    ActionFeedbackCriterion,
    LearningFeedbackInterpretation,
    LearningFeedbackInterpretationStatus,
)
from relay_self.action_outcome import ActionOutcomeInterpretation
from relay_self.attention import AttentionCriterion
from relay_self.cognitive_allocation import (
    AllocationResult,
    CognitionBudget,
    allocate_cognition,
)
from relay_self.epoch_continuation import read_retained_preference
from relay_self.learning import (
    LearningPreferenceState,
    LearningUpdateAuthority,
    LearningUpdateRule,
    commit_learning_update,
    propose_learning_update,
)
from relay_self.provenance import Provenance
from relay_self.relay_engine import BoundedChoiceRequest, RelayEngine
from relay_self.self_world import (
    InvalidSelfWorldData,
    SelfWorldView,
    WorldPredictionReview,
    WorldPredictionReviewStatus,
    bind_self_world_to_cognition_request,
    review_self_world_prediction,
    select_self_world_attention,
)


@dataclass(frozen=True)
class StageMControlledResult:
    review: WorldPredictionReview
    feedback: LearningFeedbackInterpretation | None
    original_owner: LearningPreferenceState
    next_owner: LearningPreferenceState
    before_choice: AllocationResult
    next_choice: AllocationResult
    update_committed: bool
    physical_actions_issued: int = 0


def evaluate_governed_stage_m(
    *,
    prior: SelfWorldView,
    current: SelfWorldView,
    next_view: SelfWorldView,
    action: ActionLifecycle,
    outcome: ActionOutcomeInterpretation,
    consequence: WorldConsequence,
    criterion: ActionFeedbackCriterion,
    owner: LearningPreferenceState,
    rule: LearningUpdateRule,
    authority: LearningUpdateAuthority | None,
    engine: RelayEngine,
    request: BoundedChoiceRequest,
    feedback_on: bool,
    learning_on: bool,
    provenance: Provenance,
    scenario_id: str,
    variable_key: str = "entity_label",
    max_native_seq_gap: int = 64,
) -> StageMControlledResult:
    """Compare the SAME next-epoch input under governed ON/OFF retained state.

    Source review is recomputed. S17 can produce feedback only for a positively
    observed MISMATCH and only from the exact independent Action/Outcome/
    criterion chain. S10 authority remains mandatory. A caller-supplied
    existing RelayEngine runs read-only bounded cognition; it never issues
    Action or modifies the native World. Synthetic policies remain synthetic.
    """
    if type(feedback_on) is not bool or type(learning_on) is not bool:
        raise InvalidSelfWorldData("explicit feedback and learning switches required")
    if not isinstance(next_view, SelfWorldView) or not isinstance(provenance, Provenance):
        raise InvalidSelfWorldData("typed next epoch and audit provenance required")
    if (next_view.self_id != current.self_id
            or next_view.session_id != current.session_id
            or current.observation is None or next_view.observation is None
            or next_view.observation.native_seq <= current.observation.native_seq
            or next_view.epoch_id == current.epoch_id):
        raise InvalidSelfWorldData("next epoch must have a newer same-owner source")
    if not isinstance(owner, LearningPreferenceState) or not isinstance(
        criterion, ActionFeedbackCriterion
    ) or owner.target_id != criterion.target_id:
        raise InvalidSelfWorldData("explicit S17 criterion must target retained owner")

    review = review_self_world_prediction(
        prior, current, scenario_id=scenario_id, variable_key=variable_key,
        max_native_seq_gap=max_native_seq_gap,
    )
    feedback = None
    next_owner = owner
    if feedback_on and review.status is WorldPredictionReviewStatus.MISMATCH:
        _, feedback = interpret_self_world_mismatch_as_s17_feedback(
            prior, current, scenario_id=scenario_id, variable_key=variable_key,
            max_native_seq_gap=max_native_seq_gap, action=action,
            outcome=outcome, consequence=consequence, criterion=criterion,
            provenance=provenance,
        )
        if (learning_on and
                feedback.status is LearningFeedbackInterpretationStatus.PRODUCED):
            assert feedback.feedback is not None
            proposal = propose_learning_update(owner, feedback.feedback, rule)
            # No missing/denied/cross-owner/stale authority is synthesized;
            # the existing S10 owner raises and this call fails closed.
            committed = commit_learning_update(
                owner, proposal, authority, provenance=provenance,
            )
            next_owner = committed.new_state

    selected = select_self_world_attention(
        next_view, AttentionCriterion("stage-m-future-observation", top_k=16),
    )

    def consume(snapshot: LearningPreferenceState, suffix: str) -> AllocationResult:
        read = read_retained_preference(
            snapshot, snapshot, required_target_id=owner.target_id,
            expected_revision=snapshot.revision, provenance=provenance,
        )
        bound = bind_self_world_to_cognition_request(
            next_view, selected, replace(request, request_id=f"{request.request_id}-{suffix}"),
            retained_owner_self_id=next_view.self_id,
            owner_snapshot=snapshot, retained_read=read,
        )
        return allocate_cognition(
            budget=CognitionBudget(1), bounded=bound, engine=engine,
        )

    baseline = consume(owner, "before")
    following = consume(next_owner, "after")
    return StageMControlledResult(
        review, feedback, owner, next_owner, baseline, following,
        next_owner is not owner,
    )


def audit_stage_l_physical_learning_readiness(
    native_report: dict[str, object], pre_action_witness: bytes,
) -> dict[str, object]:
    """Source-only reality check, never a S17 permission or S10 commit.

    S49 stores physical S16 observation/effect receipts, but NOT the
    authorized in-memory ActionLifecycle/OutcomeInterpretation objects,
    independently declared S17 evaluation criterion, nor a current S10
    owner authority. A saved PRD MATCH cannot supply any of those.
    """
    if (not isinstance(native_report, dict)
            or native_report.get("milestone") != "S49"
            or native_report.get("status") != "PASS"
            or native_report.get("learning_in_world") is not False
            or native_report.get("real_model_calls") != 0):
        raise InvalidSelfWorldData("Stage M requires unchanged S49 source-only run")
    checked = verify_prospective_native_reviews(
        native_report, pre_action_witness,
    )
    if len(checked) != 2:
        raise InvalidSelfWorldData("missing existing S49 native Action proof")
    # Explicitly do not attempt to deserialize a typed S17 permission
    # from a retrospective JSON document. It was never emitted by S49.
    return {
        "classification": "DEV_ONLY_SOURCE_AUDIT",
        "stage": "M",
        "source_session": native_report["session_id"],
        "prospective_action_results": [
            {
                "action_id": row["action_id"],
                "status": row["status"],
                "prior_source": row["prior_source"],
                "later_source": row["later_source"],
            }
            for row in checked
        ],
        "positive_predictions": sum(
            row["status"] in ("match", "mismatch") for row in checked
        ),
        "learning_gate": "BLOCKED_MISSING_TYPED_S17_AND_S10_AUTHORITY",
        "action_lifecycle_verified_for_s17": False,
        "independent_s17_criterion_verified": False,
        "current_s10_authority_verified": False,
        "s17_feedback_created": 0,
        "s10_learning_committed": 0,
        "new_world_sessions": 0,
        "new_actions": 0,
        "real_next_epoch_adaptive_effect": False,
    }
