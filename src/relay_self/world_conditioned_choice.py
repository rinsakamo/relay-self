"""S42 fixed, World-geometry-conditioned WAIT versus MOVE_AWAY selection.

Bounded source-dependent decision experiment, *not* a new learned policy.
Exact real native probe, retained revision, intent and candidate scores are
traceable. The frozen S35 automatic near-threat event threshold is unchanged.
A far threat needs a separate explicit read; WAIT never issues an Action.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from adapters.mineflayer.s34_native_world_cognition_ci import (
    MAX_GOAL_DISTANCE_M,
    NativeThreat,
    _native_threat,
)
from relay_self.action_feedback import (
    LearningFeedbackInterpretation,
    LearningFeedbackInterpretationStatus,
)
from relay_self.learning import (
    FeedbackDirection,
    LearningCommitResult,
    LearningPreferenceState,
    LearningProposalStatus,
)
from relay_self.planning import (
    PlanCandidate,
    PlanFeature,
    PlanningCriterion,
    PlanningDirection,
    PlanSelectionStatus,
    select_plan,
)
from relay_self.provenance import Provenance


class WorldChoiceRejected(ValueError):
    """Missing actual native source or immutable decision criteria."""


class WorldChoiceKind(str, Enum):
    WAIT = "WAIT"
    MOVE_AWAY = "MOVE_AWAY"


@dataclass(frozen=True, slots=True)
class WorldConditionedChoice:
    session_id: str
    entity_id: int
    probe_seq: int
    request_id: str
    distance_m: float
    retained_target_id: str
    retained_revision: int
    retained_value: int
    threshold_m: float
    criterion_id: str
    wait_score: int
    move_score: int
    selection: WorldChoiceKind
    action_authorized: bool
    provenance: Provenance


def select_world_conditioned_choice(
    native: NativeThreat,
    retained: LearningPreferenceState,
    *,
    expected_session_id: str,
    expected_entity_id: int,
) -> WorldConditionedChoice:
    """S42/S49 frozen rev1/value4 entry point; deliberately unchanged."""
    return _select_world_conditioned_choice(
        native, retained,
        expected_session_id=expected_session_id,
        expected_entity_id=expected_entity_id,
        required_revision=1, required_value=4,
    )


def select_stage_q_dev_committed_world_choice(
    native: NativeThreat,
    retained: LearningPreferenceState,
    *,
    commit: LearningCommitResult,
    original_owner: LearningPreferenceState,
    expected_session_id: str,
    expected_entity_id: int,
) -> WorldConditionedChoice:
    """DEV/OFFLINE: run SAME S42 scoring on exact S10-committed successor.

    This doesn't authorize an Action, replace the frozen original L0's owner,
    independently authenticate an authority issuer, or admit an S14 execution.
    """
    if (
        not isinstance(commit, LearningCommitResult)
        or not isinstance(original_owner, LearningPreferenceState)
        or commit.previous_state is not original_owner
        or commit.new_state is not retained
        or commit.new_state is original_owner
        or commit.new_state.last_update is not commit.record
        or commit.proposal.expected_revision != original_owner.revision
        or commit.proposal.expected_value != original_owner.value
        or commit.proposal.proposed_value != retained.value
        or commit.proposal.feedback.feedback_id != commit.record.feedback_id
        or commit.record.previous_revision != original_owner.revision
        or commit.record.committed_revision != retained.revision
        or retained.target_id != original_owner.target_id
        or retained.revision != original_owner.revision + 1
        or original_owner.target_id != "risk_weight"
        or original_owner.revision != 1
        or original_owner.value != 4
    ):
        raise WorldChoiceRejected("unqualified Stage Q exact S10 owner successor")
    return _select_world_conditioned_choice(
        native, retained,
        expected_session_id=expected_session_id,
        expected_entity_id=expected_entity_id,
        required_revision=retained.revision,
        required_value=retained.value,
    )


def verify_stage_t_dev_directional_commit(
    commit: LearningCommitResult,
    original_owner: LearningPreferenceState,
    typed_s17: LearningFeedbackInterpretation,
) -> LearningPreferenceState:
    """DEV-only exact non-HOLD outcome→S17→S10 lineage, NOT issuer attestation.

    Only the predeclared Stage S same-target separation feedback and a
    one-step, bounded S10 successor are accepted. No command is authorized.
    """
    if (
        not isinstance(commit, LearningCommitResult)
        or not isinstance(original_owner, LearningPreferenceState)
        or not isinstance(typed_s17, LearningFeedbackInterpretation)
        or typed_s17.status is not LearningFeedbackInterpretationStatus.PRODUCED
        or typed_s17.feedback is None
        or typed_s17.feedback is not commit.proposal.feedback
        or typed_s17.feedback.direction not in (
            FeedbackDirection.INCREASE, FeedbackDirection.DECREASE
        )
        or typed_s17.feedback.target_id != "risk_weight"
        or typed_s17.target_id != "risk_weight"
        or typed_s17.outcome_reason != "observed_execution"
        or typed_s17.action_ref != "MOVE_BACKWARD"
        or typed_s17.criterion_provenance.source
        != "stage-s-dev-preregistered-outcome-separation"
        or not typed_s17.criterion_id.startswith(
            "stage-s-same-target-separation-v0:"
        )
        or typed_s17.feedback.consequence_ref != typed_s17.outcome_ref
        or commit.previous_state is not original_owner
        or commit.new_state is original_owner
        or commit.new_state.last_update is not commit.record
        or commit.proposal.expected_revision != original_owner.revision
        or commit.proposal.expected_value != original_owner.value
        or commit.proposal.target_id != "risk_weight"
        or commit.proposal.expected_minimum != original_owner.minimum
        or commit.proposal.expected_maximum != original_owner.maximum
        or commit.proposal.rule.rule_id != "stage-t-dev-risk-weight-one-step"
        or commit.proposal.rule.version != 1
        or commit.proposal.rule.step != 1
        or commit.proposal.status is not LearningProposalStatus.UPDATED
        or commit.record.status is not LearningProposalStatus.UPDATED
        or commit.record.rule_id != commit.proposal.rule.rule_id
        or commit.record.rule_version != commit.proposal.rule.version
        or commit.record.feedback_id != typed_s17.feedback.feedback_id
        or commit.record.previous_revision != original_owner.revision
        or commit.record.committed_revision != commit.new_state.revision
        or commit.record.previous_value != original_owner.value
        or commit.record.resulting_value != commit.new_state.value
        or original_owner.target_id != "risk_weight"
        or original_owner.revision != 1
        or original_owner.value != 4
        or commit.new_state.revision != 2
        or commit.new_state.target_id != "risk_weight"
        or commit.proposal.proposed_value != commit.new_state.value
        or commit.new_state.value != (
            5 if typed_s17.feedback.direction is FeedbackDirection.INCREASE else 3
        )
    ):
        raise WorldChoiceRejected("Stage T exact directional S17/S10 successor required")
    return commit.new_state


def select_stage_t_dev_directional_world_choice(
    native: NativeThreat,
    retained: LearningPreferenceState,
    *,
    commit: LearningCommitResult,
    original_owner: LearningPreferenceState,
    typed_s17: LearningFeedbackInterpretation,
    expected_session_id: str,
    expected_entity_id: int,
) -> WorldConditionedChoice:
    """Explicit alternative DEV policy; preserves original S42 default guard.

    Near-target WAIT can win at retained=3. It remains no-Action, and any
    MOVE requires the original independent S49 Action authorization.
    """
    successor = verify_stage_t_dev_directional_commit(
        commit, original_owner, typed_s17,
    )
    if retained is not successor:
        raise WorldChoiceRejected("Stage T L0 must consume exact committed owner")
    if (
        typed_s17.provenance.reference
        != f"{native.observation.session_id}:{typed_s17.action_id}"
        or typed_s17.feedback.provenance != typed_s17.provenance
        or typed_s17.criterion_id.split(":")[1]
        != native.observation.session_id
        or typed_s17.criterion_id.split(":")[2]
        != typed_s17.action_id.removeprefix("s49-native-move-")
        or typed_s17.criterion_id.split(":")[3]
        != (
            "separation_increased"
            if typed_s17.feedback.direction is FeedbackDirection.INCREASE
            else "separation_decreased"
        )
    ):
        raise WorldChoiceRejected("Stage T feedback native session mismatch")
    return _select_world_conditioned_choice(
        native, retained,
        expected_session_id=expected_session_id,
        expected_entity_id=expected_entity_id,
        required_revision=successor.revision,
        required_value=successor.value,
        allow_near_wait=True,
        criterion_id="stage-t-dev-retained-cost-v0",
    )


def _select_world_conditioned_choice(
    native: NativeThreat,
    retained: LearningPreferenceState,
    *,
    expected_session_id: str,
    expected_entity_id: int,
    required_revision: int,
    required_value: int,
    allow_near_wait: bool = False,
    criterion_id: str = "s42-fixed-native-distance-comparison",
) -> WorldConditionedChoice:
    """One frozen projection of real distance onto original finite PLAN.

    WORLD distance is the only varying comparison input: close WAIT cost
    is 2*risk_weight; far WAIT cost is 0; MOVE cost always 7.
    This is a deliberately fixed *caller* scoring policy, not an inferred
    general cognitive law. S35 doesn't automatically schedule distant probes.
    """
    if (
        not isinstance(native, NativeThreat)
        or not isinstance(retained, LearningPreferenceState)
        or type(expected_entity_id) is not int
        or expected_entity_id < 0
        or not isinstance(expected_session_id, str)
        or not expected_session_id
        or native.entity_id != expected_entity_id
        or native.observation.session_id != expected_session_id
        or native.observation.request_id != native.request_id
        or native.observation.provenance.source != "mineflayer"
        or native.observation.kind != "probe"
        or native.distance_m <= 0
        or native.distance_m > 16
        or retained.target_id != "risk_weight"
        or retained.revision != required_revision
        or retained.value != required_value
    ):
        raise WorldChoiceRejected("exact live probe and frozen governed rev1 required")
    # Validate complete registry, exact request and real positional geometry
    # again through the existing S34 evidence validator.
    checked = _native_threat(
        native.observation, native.request_id,
        expected_entity_id=expected_entity_id,
    )
    if checked != native:
        raise WorldChoiceRejected("source-native distance or target mismatch")

    wait_score = (
        2 * retained.value if native.distance_m < MAX_GOAL_DISTANCE_M else 0
    )
    move_score = 7
    criterion = PlanningCriterion(
        criterion_id, "comparison_score",
        PlanningDirection.MINIMIZE,
    )
    # Source attestation is attached to BOTH candidates, not a mere label
    # pasted on the selected output.
    source_ref = (
        f"native-session:{expected_session_id}",
        f"native-event-entity:{expected_entity_id}",
        f"native-probe:{native.request_id}:{native.observation.seq}",
        f"retained:risk_weight:revision:{retained.revision}",
    )
    candidates = (
        PlanCandidate(
            "WAIT", (PlanFeature("comparison_score", wait_score),),
            native.observation.provenance, source_refs=source_ref,
            source_provenance=(native.observation.provenance,),
        ),
        PlanCandidate(
            "MOVE_AWAY", (PlanFeature("comparison_score", move_score),),
            native.observation.provenance, source_refs=source_ref,
            source_provenance=(native.observation.provenance,),
            action_ref="MOVE_BACKWARD",
        ),
    )
    choice = select_plan(candidates, criterion)
    if choice.status is not PlanSelectionStatus.SELECTED or choice.selected is None:
        raise WorldChoiceRejected("ambiguous or incomparable World-conditioned plan")
    selection = WorldChoiceKind(choice.selected.candidate_id)
    if (
        (native.distance_m < MAX_GOAL_DISTANCE_M)
        != (selection is WorldChoiceKind.MOVE_AWAY)
        and not (
            allow_near_wait
            and native.distance_m < MAX_GOAL_DISTANCE_M
            and selection is WorldChoiceKind.WAIT
            and retained.value == 3
            and criterion_id == "stage-t-dev-retained-cost-v0"
        )
    ):
        raise WorldChoiceRejected("World geometry did not determine required route")
    return WorldConditionedChoice(
        session_id=expected_session_id,
        entity_id=expected_entity_id,
        probe_seq=native.observation.seq,
        request_id=native.request_id,
        distance_m=native.distance_m,
        retained_target_id=retained.target_id,
        retained_revision=retained.revision,
        retained_value=retained.value,
        threshold_m=MAX_GOAL_DISTANCE_M,
        criterion_id=criterion.criterion_id,
        wait_score=wait_score,
        move_score=move_score,
        selection=selection,
        action_authorized=False,  # no PLAN itself authorizes Action
        provenance=native.observation.provenance,
    )


def verify_world_contrast(
    near: WorldConditionedChoice,
    far: WorldConditionedChoice,
) -> None:
    """Adjudicate paired same-session probes holding retained and policy fixed."""
    if (
        not isinstance(near, WorldConditionedChoice)
        or not isinstance(far, WorldConditionedChoice)
        or near.session_id != far.session_id
        or near.entity_id == far.entity_id
        or near.probe_seq == far.probe_seq
        or near.request_id == far.request_id
        or near.provenance == far.provenance
        or near.retained_target_id != far.retained_target_id
        or near.retained_revision != far.retained_revision
        or near.retained_value != far.retained_value
        or near.threshold_m != far.threshold_m
        or near.criterion_id != far.criterion_id
        or near.move_score != far.move_score
        or near.distance_m >= near.threshold_m
        or far.distance_m < far.threshold_m
        or near.selection is not WorldChoiceKind.MOVE_AWAY
        or far.selection is not WorldChoiceKind.WAIT
        or near.action_authorized
        or far.action_authorized
    ):
        raise WorldChoiceRejected("pair not one fixed-policy native World contrast")
