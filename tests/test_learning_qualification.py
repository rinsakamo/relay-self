from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

import relay_self
from relay_self.action import ActionLifecycle, ActionState
from relay_self.action_supervision import ActionSupervisor
from relay_self.attention import AttentionCandidate, AttentionCriterion, select_attention
from relay_self.belief import (
    BeliefCriterion,
    BeliefEvidence,
    BeliefStatus,
    EvidenceRelation,
    PropositionKey,
    assess_belief,
)
from relay_self.concept import (
    ConceptCriterion,
    ConceptFeature,
    ConceptKey,
    ConceptStatus,
    classify_concept,
    concept_candidate_from_belief,
)
from relay_self.epoch_plan import (
    EpochBinding,
    EpochWorkItem,
    compile_epoch_plan,
    coordinate_planned_epoch,
)
from relay_self.execution_descriptor import (
    S2_DESCRIPTOR_SET,
    S10_DESCRIPTOR_SET,
    S10_LRN_APPLY_OPERATOR_DESCRIPTOR,
    S10_LRN_CAPABILITY_SPEC,
    S10_LRN_CRITERION_DESCRIPTOR,
    S10_LRN_PROPOSE_OPERATOR_DESCRIPTOR,
    CriterionKind,
    OperatorEffect,
    s10_capability_plan,
)
from relay_self.intent import IntentCommitment
from relay_self.learning import (
    FeedbackDirection,
    InvalidLearningAuthority,
    InvalidLearningData,
    LearningCommitResult,
    LearningFeedback,
    LearningPreferenceState,
    LearningProposalStatus,
    LearningTargetMismatch,
    LearningUpdateAuthority,
    LearningUpdateRule,
    MissingLearningAuthority,
    ReplayLearningFeedback,
    StaleLearningUpdate,
    commit_learning_update,
    propose_learning_update,
)
from relay_self.learning_profile import (
    S10_LEARNING_PROFILES,
    LearningProfileId,
    s10_learning_profile,
)
from relay_self.persistent_cognition import (
    IdentitySpecification,
    Memory,
    PersistentCognition,
)
from relay_self.planning import (
    PlanCandidate,
    PlanFeature,
    PlanningCriterion,
    PlanningDirection,
    PlanSelection,
    PlanSelectionStatus,
    select_plan,
)
from relay_self.prediction import (
    PredictionState,
    PredictionStatus,
    StateVariable,
    TransitionRule,
    predict_transition,
)
from relay_self.provenance import Provenance
from relay_self.relay_engine import ProviderExpression
from relay_self.skill import SkillExecution, SkillState


def provenance(reference: str) -> Provenance:
    return Provenance(source="s10-learning-qualification", reference=reference)


def preference(
    value: int = 3,
    *,
    revision: int = 0,
    last_update=None,
) -> LearningPreferenceState:
    return LearningPreferenceState(
        target_id="risk_weight",
        value=value,
        minimum=0,
        maximum=10,
        revision=revision,
        origin_provenance=provenance("preference-origin"),
        last_update=last_update,
    )


def feedback(
    direction: FeedbackDirection,
    *,
    feedback_id: str = "fb-001",
    target_id: str = "risk_weight",
    consequence_ref: str | None = "consequence:explicit",
) -> LearningFeedback:
    return LearningFeedback(
        feedback_id=feedback_id,
        target_id=target_id,
        direction=direction,
        provenance=provenance(f"feedback:{feedback_id}"),
        consequence_ref=consequence_ref,
    )


def rule(step: int = 1) -> LearningUpdateRule:
    return LearningUpdateRule(
        rule_id="bounded-preference-step",
        version=1,
        step=step,
    )


def authority(
    *,
    target_id: str = "risk_weight",
    granted: bool = True,
) -> LearningUpdateAuthority:
    return LearningUpdateAuthority(
        authority_id="learning-owner-authority",
        target_id=target_id,
        provenance=provenance("learning-authority"),
        granted=granted,
    )


def commit(
    state: LearningPreferenceState,
    direction: FeedbackDirection,
    *,
    feedback_id: str,
) -> LearningCommitResult:
    proposal = propose_learning_update(
        state,
        feedback(direction, feedback_id=feedback_id),
        rule(),
    )
    return commit_learning_update(
        state,
        proposal,
        authority(),
        provenance=provenance(f"commit:{feedback_id}"),
    )


def plan_selection() -> PlanSelection:
    wait = PlanCandidate(
        candidate_id="WAIT",
        outcome_features=(PlanFeature("comparison_score", 8),),
        provenance=provenance("plan:wait"),
        action_ref="WAIT",
    )
    move = PlanCandidate(
        candidate_id="MOVE_AWAY",
        outcome_features=(PlanFeature("comparison_score", 3),),
        provenance=provenance("plan:move-away"),
        action_ref="MOVE_BACKWARD",
    )
    return select_plan(
        (wait, move),
        PlanningCriterion(
            criterion_id="minimize-comparison-score",
            feature_key="comparison_score",
            direction=PlanningDirection.MINIMIZE,
        ),
    )


def identity() -> IdentitySpecification:
    return IdentitySpecification(
        self_id="self-s10",
        directives=("learning authority remains owner-local",),
        provenance=provenance("identity"),
    )


def memory(memory_id: str) -> Memory:
    return Memory(
        memory_id=memory_id,
        content=f"memory:{memory_id}",
        source_provenance=provenance(f"memory-source:{memory_id}"),
        integration_provenance=provenance(f"memory-integration:{memory_id}"),
    )


def committed_intent() -> IntentCommitment:
    owner = IntentCommitment()
    owner.commit(
        "intent-s10",
        objective="maintain current objective",
        at_ns=1,
        provenance=provenance("intent"),
    )
    return owner


def upstream_objects():
    p = PropositionKey("entity", "zombie-1", "nearby")
    belief = assess_belief(
        (
            BeliefEvidence(
                "E1",
                p,
                EvidenceRelation.SUPPORT,
                provenance("evidence:E1"),
            ),
        ),
        BeliefCriterion("zombie-nearby", p),
    )
    concept_input = concept_candidate_from_belief(
        belief,
        candidate_id="belief:zombie-nearby",
        payload_ref="transient:belief:zombie-nearby",
        provenance=provenance("belief-to-concept"),
    )
    concept = classify_concept(
        concept_input,
        ConceptCriterion(
            criterion_id="supported-nearby",
            concept=ConceptKey("spatial", "nearby_threat"),
            required_features=(
                ConceptFeature("belief_status", "supported"),
                ConceptFeature("proposition", p.canonical),
            ),
        ),
    )
    prediction = predict_transition(
        PredictionState(
            state_id="threat:0",
            variables=(
                StateVariable("threat_state", "near"),
                StateVariable("moving_toward_self", True),
            ),
            provenance=provenance("prediction-source"),
        ),
        TransitionRule(
            rule_id="threat-approaches",
            preconditions=(
                StateVariable("threat_state", "near"),
                StateVariable("moving_toward_self", True),
            ),
            assignments=(StateVariable("threat_state", "immediate"),),
            provenance=provenance("transition-rule"),
        ),
    )
    attention = select_attention(
        (
            AttentionCandidate(
                "E1",
                "belief-evidence:E1",
                provenance("attention:E1"),
                focus_keys=("zombie-1",),
            ),
        ),
        AttentionCriterion("focus-zombie", focus_key="zombie-1"),
    )
    selection = plan_selection()
    return attention, belief, concept, prediction, selection


def test_package_exports_s10_learning_surface() -> None:
    assert relay_self.LearningPreferenceState is LearningPreferenceState
    assert relay_self.LearningFeedback is LearningFeedback
    assert relay_self.LearningUpdateRule is LearningUpdateRule
    assert relay_self.LearningUpdateAuthority is LearningUpdateAuthority
    assert relay_self.propose_learning_update is propose_learning_update
    assert relay_self.commit_learning_update is commit_learning_update
    assert relay_self.LearningProfileId is LearningProfileId
    assert relay_self.S10_LEARNING_PROFILES is S10_LEARNING_PROFILES
    assert relay_self.s10_learning_profile is s10_learning_profile


def test_s10_profiles_are_exactly_lrn_and_plan_lrn() -> None:
    assert [profile.profile_id for profile in S10_LEARNING_PROFILES] == [
        LearningProfileId.LRN,
        LearningProfileId.PLAN_LRN,
    ]
    assert s10_learning_profile(
        LearningProfileId.LRN
    ).enabled_ids == frozenset({"LRN"})
    assert s10_learning_profile(
        LearningProfileId.PLAN_LRN
    ).enabled_ids == frozenset({"PLAN", "LRN"})


def test_lrn_descriptor_has_narrow_owner_scope_and_two_real_operator_seams() -> None:
    assert S10_LRN_CAPABILITY_SPEC.state_scopes == (
        "owner_local.learning_preference",
    )
    assert S10_LRN_CAPABILITY_SPEC.dependencies == ()
    assert S10_LRN_CAPABILITY_SPEC.operator_ids == (
        "lrn.propose_update",
        "lrn.apply_update",
    )

    assert S10_LRN_PROPOSE_OPERATOR_DESCRIPTOR.effect is OperatorEffect.READ_ONLY
    assert (
        S10_LRN_PROPOSE_OPERATOR_DESCRIPTOR.implementation_ref
        == "relay_self.learning.propose_learning_update"
    )
    assert S10_LRN_PROPOSE_OPERATOR_DESCRIPTOR.hidden_persistent_state is False

    assert (
        S10_LRN_APPLY_OPERATOR_DESCRIPTOR.effect
        is OperatorEffect.OWNER_TRANSITION
    )
    assert (
        S10_LRN_APPLY_OPERATOR_DESCRIPTOR.implementation_ref
        == "relay_self.learning.commit_learning_update"
    )
    assert S10_LRN_APPLY_OPERATOR_DESCRIPTOR.hidden_persistent_state is False

    assert (
        S10_LRN_CRITERION_DESCRIPTOR.criterion_id
        == "lrn.explicit_feedback_orientation"
    )
    assert (
        S10_LRN_CRITERION_DESCRIPTOR.kind
        is CriterionKind.COGNITIVE_ORIENTATION
    )
    assert all(
        descriptor.kind is CriterionKind.CONTRACT_GUARD
        for descriptor in S2_DESCRIPTOR_SET.criteria
    )


@pytest.mark.parametrize(
    ("direction", "old", "expected", "status"),
    [
        (
            FeedbackDirection.INCREASE,
            3,
            4,
            LearningProposalStatus.UPDATED,
        ),
        (
            FeedbackDirection.DECREASE,
            3,
            2,
            LearningProposalStatus.UPDATED,
        ),
        (
            FeedbackDirection.HOLD,
            3,
            3,
            LearningProposalStatus.UNCHANGED_HOLD,
        ),
        (
            FeedbackDirection.INCREASE,
            10,
            10,
            LearningProposalStatus.UNCHANGED_AT_BOUND,
        ),
        (
            FeedbackDirection.DECREASE,
            0,
            0,
            LearningProposalStatus.UNCHANGED_AT_BOUND,
        ),
    ],
)
def test_deterministic_learning_proposal_semantics(
    direction: FeedbackDirection,
    old: int,
    expected: int,
    status: LearningProposalStatus,
) -> None:
    state = preference(old)
    signal = feedback(direction)
    update_rule = rule()

    first = propose_learning_update(state, signal, update_rule)
    second = propose_learning_update(state, signal, update_rule)

    assert first == second
    assert first.expected_revision == 0
    assert first.expected_value == old
    assert first.proposed_value == expected
    assert first.status is status
    assert state.value == old
    assert state.revision == 0


def test_learning_owner_and_proposal_are_immutable_snapshots() -> None:
    state = preference(3)
    proposal = propose_learning_update(
        state,
        feedback(FeedbackDirection.INCREASE),
        rule(),
    )

    with pytest.raises(FrozenInstanceError):
        state.value = 9  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        proposal.proposed_value = 9  # type: ignore[misc]


def test_commit_requires_authority_and_exact_revision_then_returns_new_owner_snapshot() -> None:
    state = preference(3)
    signal = feedback(FeedbackDirection.INCREASE)
    proposal = propose_learning_update(state, signal, rule())

    with pytest.raises(MissingLearningAuthority):
        commit_learning_update(
            state,
            proposal,
            None,
            provenance=provenance("commit-missing-authority"),
        )

    assert state.value == 3
    assert state.revision == 0

    result = commit_learning_update(
        state,
        proposal,
        authority(),
        provenance=provenance("commit-authorized"),
    )

    assert result.previous_state is state
    assert result.new_state.value == 4
    assert result.new_state.revision == 1
    assert state.value == 3
    assert state.revision == 0
    assert result.record.feedback_id == "fb-001"
    assert result.record.feedback_provenance == signal.provenance
    assert result.record.rule_id == "bounded-preference-step"
    assert result.record.rule_version == 1
    assert result.record.authority_id == "learning-owner-authority"
    assert result.record.authority_provenance == authority().provenance
    assert result.record.update_provenance == provenance("commit-authorized")


def test_hold_and_bound_noops_are_committed_feedback_and_advance_revision() -> None:
    hold_state = preference(3)
    hold_result = commit_learning_update(
        hold_state,
        propose_learning_update(
            hold_state,
            feedback(FeedbackDirection.HOLD),
            rule(),
        ),
        authority(),
        provenance=provenance("commit-hold"),
    )
    assert hold_result.new_state.value == 3
    assert hold_result.new_state.revision == 1
    assert (
        hold_result.record.status
        is LearningProposalStatus.UNCHANGED_HOLD
    )

    bound_state = preference(10)
    bound_result = commit_learning_update(
        bound_state,
        propose_learning_update(
            bound_state,
            feedback(FeedbackDirection.INCREASE),
            rule(),
        ),
        authority(),
        provenance=provenance("commit-bound"),
    )
    assert bound_result.new_state.value == 10
    assert bound_result.new_state.revision == 1
    assert (
        bound_result.record.status
        is LearningProposalStatus.UNCHANGED_AT_BOUND
    )


def test_stale_proposal_and_replay_fail_closed() -> None:
    state = preference(3)
    signal = feedback(FeedbackDirection.INCREASE)
    proposal = propose_learning_update(state, signal, rule())
    first = commit_learning_update(
        state,
        proposal,
        authority(),
        provenance=provenance("commit-first"),
    )

    with pytest.raises(StaleLearningUpdate):
        commit_learning_update(
            first.new_state,
            proposal,
            authority(),
            provenance=provenance("commit-replay-proposal"),
        )

    with pytest.raises(ReplayLearningFeedback):
        propose_learning_update(
            first.new_state,
            signal,
            rule(),
        )

    assert first.new_state.value == 4
    assert first.new_state.revision == 1


def test_target_and_authority_mismatch_fail_closed() -> None:
    state = preference(3)

    with pytest.raises(LearningTargetMismatch):
        propose_learning_update(
            state,
            feedback(
                FeedbackDirection.INCREASE,
                target_id="other_target",
            ),
            rule(),
        )

    proposal = propose_learning_update(
        state,
        feedback(FeedbackDirection.INCREASE),
        rule(),
    )

    with pytest.raises(LearningTargetMismatch):
        commit_learning_update(
            state,
            proposal,
            authority(target_id="other_target"),
            provenance=provenance("commit-wrong-authority-target"),
        )

    with pytest.raises(InvalidLearningAuthority):
        commit_learning_update(
            state,
            proposal,
            authority(granted=False),
            provenance=provenance("commit-denied-authority"),
        )

    with pytest.raises(InvalidLearningAuthority):
        commit_learning_update(
            state,
            proposal,
            object(),  # type: ignore[arg-type]
            provenance=provenance("commit-invalid-authority"),
        )

    assert state.value == 3
    assert state.revision == 0


def test_invalid_learning_state_rule_feedback_and_payload_fail_closed() -> None:
    with pytest.raises(InvalidLearningData, match="structured identifier"):
        LearningPreferenceState(
            target_id="bad target",
            value=3,
            minimum=0,
            maximum=10,
            revision=0,
            origin_provenance=provenance("bad-target"),
        )

    with pytest.raises(InvalidLearningData, match="inside retained bounds"):
        preference(11)

    with pytest.raises(InvalidLearningData, match="minimum cannot exceed"):
        LearningPreferenceState(
            target_id="risk_weight",
            value=3,
            minimum=5,
            maximum=4,
            revision=0,
            origin_provenance=provenance("bad-bounds"),
        )

    with pytest.raises(InvalidLearningData, match="positive"):
        rule(step=0)

    with pytest.raises(InvalidLearningData, match="structured identifier"):
        LearningFeedback(
            feedback_id="bad feedback",
            target_id="risk_weight",
            direction=FeedbackDirection.INCREASE,
            provenance=provenance("bad-feedback"),
        )

    with pytest.raises(InvalidLearningData, match="consequence_ref"):
        LearningFeedback(
            feedback_id="fb-payload",
            target_id="risk_weight",
            direction=FeedbackDirection.INCREASE,
            provenance=provenance("bad-payload"),
            consequence_ref=["mutable"],  # type: ignore[arg-type]
        )


def test_provider_text_and_plan_selection_are_not_learning_feedback() -> None:
    state = preference()
    generated = ProviderExpression(
        text="That went badly.",
        provenance=provenance("provider-expression"),
    )
    selection = plan_selection()

    with pytest.raises(InvalidLearningData, match="LearningFeedback"):
        propose_learning_update(
            state,
            generated,  # type: ignore[arg-type]
            rule(),
        )

    with pytest.raises(InvalidLearningData, match="LearningFeedback"):
        propose_learning_update(
            state,
            selection,  # type: ignore[arg-type]
            rule(),
        )

    assert state.value == 3
    assert state.revision == 0


def test_lrn_on_executes_proposal_and_governed_owner_transition_with_zero_cognition() -> None:
    box: dict[str, object] = {"state": preference(3)}
    signal = feedback(
        FeedbackDirection.INCREASE,
        consequence_ref="consequence:explicit-negative-result",
    )

    def propose() -> None:
        box["proposal"] = propose_learning_update(
            box["state"],
            signal,
            rule(),
        )

    def apply() -> None:
        result = commit_learning_update(
            box["state"],
            box["proposal"],
            authority(),
            provenance=provenance("epoch-learning-commit"),
        )
        box["commit_result"] = result
        box["state"] = result.new_state

    bindings = (
        EpochBinding("lrn-propose", "lrn.propose_update", propose),
        EpochBinding("lrn-apply", "lrn.apply_update", apply),
    )
    plan = compile_epoch_plan(
        s10_learning_profile(LearningProfileId.LRN).plan(),
        S10_DESCRIPTOR_SET,
        due_items=(
            EpochWorkItem(
                "lrn-propose",
                "lrn.propose_update",
                "explicit-structured-feedback",
            ),
            EpochWorkItem(
                "lrn-apply",
                "lrn.apply_update",
                "explicit-owner-authority",
            ),
        ),
        bindings=bindings,
    )

    result = coordinate_planned_epoch(
        ActionSupervisor(),
        plan,
        bindings=bindings,
        at_ns=10,
        provenance=provenance("epoch-learning"),
    )

    assert isinstance(box["commit_result"], LearningCommitResult)
    assert box["state"].value == 4
    assert box["state"].revision == 1
    assert result.executed_work_ids == ("lrn-propose", "lrn-apply")
    assert result.cognition_requested is False
    assert result.cognition_result is None


def test_plan_on_lrn_off_preserves_retained_state_and_fabricates_no_update() -> None:
    state = preference(4)
    selection_box: dict[str, object] = {}

    def choose() -> None:
        selection_box["plan"] = plan_selection()

    binding = EpochBinding("plan-1", "plan.select", choose)
    plan = compile_epoch_plan(
        s10_capability_plan(enabled_ids=frozenset({"PLAN"})),
        S10_DESCRIPTOR_SET,
        due_items=(
            EpochWorkItem("plan-1", "plan.select", "finite-candidates"),
            EpochWorkItem(
                "lrn-propose",
                "lrn.propose_update",
                "learning-disabled",
            ),
            EpochWorkItem(
                "lrn-apply",
                "lrn.apply_update",
                "learning-disabled",
            ),
        ),
        bindings=(binding,),
    )

    result = coordinate_planned_epoch(
        ActionSupervisor(),
        plan,
        bindings=(binding,),
        at_ns=10,
        provenance=provenance("epoch-learning-off"),
    )

    assert isinstance(selection_box["plan"], PlanSelection)
    assert selection_box["plan"].status is PlanSelectionStatus.SELECTED
    assert result.executed_work_ids == ("plan-1",)
    assert result.suppressed_work_ids == ("lrn-propose", "lrn-apply")
    assert state.value == 4
    assert state.revision == 0
    assert result.cognition_requested is False

    enabled_again = s10_capability_plan(enabled_ids=frozenset({"LRN"}))
    assert enabled_again.is_enabled("LRN")
    assert state.value == 4
    assert state.revision == 0


def test_plan_plus_lrn_consumes_only_explicit_feedback_and_leaves_plan_semantics_unchanged() -> None:
    box: dict[str, object] = {"state": preference(3)}
    explicit_feedback = feedback(
        FeedbackDirection.INCREASE,
        feedback_id="fb-after-outcome",
        consequence_ref="action-outcome:move-away:threat-remained",
    )

    def choose() -> None:
        box["plan"] = plan_selection()

    def propose() -> None:
        box["proposal"] = propose_learning_update(
            box["state"],
            explicit_feedback,
            rule(),
        )

    def apply() -> None:
        result = commit_learning_update(
            box["state"],
            box["proposal"],
            authority(),
            provenance=provenance("plan-plus-learning-commit"),
        )
        box["learning"] = result
        box["state"] = result.new_state

    bindings = (
        EpochBinding("plan-1", "plan.select", choose),
        EpochBinding("lrn-propose", "lrn.propose_update", propose),
        EpochBinding("lrn-apply", "lrn.apply_update", apply),
    )
    epoch = compile_epoch_plan(
        s10_learning_profile(LearningProfileId.PLAN_LRN).plan(),
        S10_DESCRIPTOR_SET,
        due_items=(
            EpochWorkItem("plan-1", "plan.select", "finite-candidates"),
            EpochWorkItem(
                "lrn-propose",
                "lrn.propose_update",
                "explicit-post-outcome-feedback",
            ),
            EpochWorkItem(
                "lrn-apply",
                "lrn.apply_update",
                "explicit-owner-authority",
            ),
        ),
        bindings=bindings,
    )

    result = coordinate_planned_epoch(
        ActionSupervisor(),
        epoch,
        bindings=bindings,
        at_ns=10,
        provenance=provenance("epoch-plan-plus-learning"),
    )

    selection = box["plan"]
    learning = box["learning"]
    assert isinstance(selection, PlanSelection)
    assert isinstance(learning, LearningCommitResult)
    assert selection.status is PlanSelectionStatus.SELECTED
    assert selection.selected is not None
    assert selection.selected.candidate_id == "MOVE_AWAY"
    assert explicit_feedback.consequence_ref == (
        "action-outcome:move-away:threat-remained"
    )
    assert learning.proposal.feedback is explicit_feedback
    assert learning.new_state.value == 4
    assert learning.new_state.revision == 1
    assert selection.status is PlanSelectionStatus.SELECTED
    assert selection.selected.candidate_id == "MOVE_AWAY"
    assert result.cognition_requested is False


def test_learning_does_not_mutate_other_cognitive_or_execution_authorities() -> None:
    intent_owner = committed_intent()
    skill = SkillExecution.start(
        "skill-s10",
        skill_id="FLEE",
        intent_commitment=intent_owner,
        at_ns=2,
        provenance=provenance("skill"),
    )
    proposed_action = ActionLifecycle.propose(
        "action-s10-proposed",
        skill_execution=skill,
        intent_commitment=intent_owner,
        at_ns=3,
        provenance=provenance("action-proposed"),
    )

    second_action = ActionLifecycle.propose(
        "action-s10-issued",
        skill_execution=skill,
        intent_commitment=intent_owner,
        at_ns=4,
        provenance=provenance("action2-proposed"),
    )
    authorized_action = second_action.authorize(
        at_ns=5,
        provenance=provenance("action2-authorized"),
        authority="action-authority",
    )
    issued_action = authorized_action.issue(
        at_ns=6,
        deadline_ns=100,
        provenance=provenance("action2-issued"),
    )

    cognition = PersistentCognition(
        identity=identity(),
        memories=(memory("existing"),),
    )
    attention, belief, concept, prediction, selection = upstream_objects()

    state = preference(3)
    proposal = propose_learning_update(
        state,
        feedback(FeedbackDirection.INCREASE),
        rule(),
    )

    before_memories = cognition.memories
    before_intent_events = intent_owner.events
    before_skill_events = skill.events
    before_proposed_events = proposed_action.events
    before_issued_events = issued_action.events
    before_attention = attention
    before_belief = belief
    before_concept = concept
    before_prediction = prediction
    before_selection = selection

    result = commit_learning_update(
        state,
        proposal,
        authority(),
        provenance=provenance("authority-negative-commit"),
    )

    assert result.new_state.value == 4
    assert cognition.memories == before_memories
    assert intent_owner.events == before_intent_events
    assert intent_owner.current_intent is not None
    assert intent_owner.current_intent.intent_id == "intent-s10"
    assert skill.events == before_skill_events
    assert skill.state is SkillState.STARTED
    assert proposed_action.events == before_proposed_events
    assert proposed_action.state is ActionState.PROPOSED
    assert issued_action.events == before_issued_events
    assert issued_action.state is ActionState.ISSUED
    assert attention == before_attention
    assert belief == before_belief
    assert belief.status is BeliefStatus.SUPPORTED
    assert concept == before_concept
    assert concept.status is ConceptStatus.MATCHED
    assert prediction == before_prediction
    assert prediction.status is PredictionStatus.PREDICTED
    assert selection == before_selection
    assert selection.status is PlanSelectionStatus.SELECTED
