from __future__ import annotations

import asyncio
from collections import deque
from dataclasses import replace

import pytest

from adapters.mineflayer.action_outcome import interpret_world_consequence
from adapters.mineflayer.execution import (
    MOVE_BACKWARD_ACTION_REF,
    MineflayerCommand,
    WorldConsequenceStatus,
    build_mineflayer_command,
    execute_mineflayer_command,
)
from adapters.mineflayer.python_protocol import (
    MINEFLAYER_NEARBY_ENTITY_MAX_DISTANCE,
    MINEFLAYER_NEARBY_ENTITY_MAX_ENTITIES,
    MINEFLAYER_NEARBY_ENTITY_SOURCE_SCOPE,
    MINEFLAYER_VERSION,
    MineflayerAdapterStarted,
    MineflayerEffectResult,
    MineflayerLaunchConfig,
    MineflayerNearbyEntitiesCoverage,
    MineflayerObservation,
    MineflayerPosition,
    MineflayerSnapshot,
)
from relay_self.action import ActionState
from relay_self.action_feedback import (
    ActionFeedbackCriterion,
    InvalidActionFeedbackData,
    LearningFeedbackInterpretationStatus,
    interpret_action_outcome_as_learning_feedback,
)
from relay_self.action_outcome import (
    ActionOutcomeDisposition,
    record_interpreted_action_outcome,
)
from relay_self.action_supervision import ActionSupervisor
from relay_self.attention import (
    AttentionCandidate,
    AttentionCriterion,
    require_attention_selection,
    select_attention,
)
from relay_self.belief import (
    BeliefCriterion,
    BeliefEvidence,
    EvidenceRelation,
    PropositionKey,
    assess_belief,
)
from relay_self.concept import (
    ConceptCriterion,
    ConceptFeature,
    ConceptKey,
    classify_concept,
    concept_candidate_from_belief,
)
from relay_self.epoch_plan import (
    EpochWorkItem,
    compile_epoch_plan,
    coordinate_planned_epoch,
)
from relay_self.execution_admission import (
    AdmissionDecisionStatus,
    AdmissionPolicy,
    ExecutionAdmissionCriterion,
    admit_control_candidate,
)
from relay_self.execution_binding import (
    ExecutionBinding,
    resolve_execution_binding,
    start_and_propose_bound_execution,
)
from relay_self.execution_descriptor import (
    S17_DESCRIPTOR_SET,
    S17_FEEDBACK_CAPABILITY_SPEC,
    S17_FEEDBACK_CRITERION_DESCRIPTOR,
    S17_FEEDBACK_OPERATOR_DESCRIPTOR,
    CriterionKind,
    OperatorEffect,
    s17_capability_plan,
)
from relay_self.habit import (
    CueFeature,
    HabitCue,
    HabitRepertoire,
    HabitRule,
    select_habit,
)
from relay_self.intent import IntentCommitment
from relay_self.learning import (
    FeedbackDirection,
    InvalidLearningAuthority,
    InvalidLearningData,
    LearningPreferenceState,
    LearningTargetMismatch,
    LearningUpdateAuthority,
    LearningUpdateRule,
    MissingLearningAuthority,
    ReplayLearningFeedback,
    StaleLearningUpdate,
    commit_learning_update,
    propose_learning_update,
)
from relay_self.persistent_cognition import (
    IdentitySpecification,
    Memory,
    PersistentCognition,
)
from relay_self.planning import (
    PlanningCriterion,
    PlanningDirection,
    plan_candidate_from_prediction,
    select_plan,
)
from relay_self.prediction import (
    StateVariable,
    TransitionRule,
    predict_transition,
    prediction_state_from_concept,
)
from relay_self.provenance import Provenance
from relay_self.relay_engine import ProviderExpression
from relay_self.route_adjudication import (
    RouteConflictPolicy,
    RouteCriterion,
    RouteDecisionStatus,
    adjudicate_routes,
    control_candidate_from_route_decision,
)
from relay_self.skill import SkillState


def provenance(reference: str) -> Provenance:
    return Provenance(
        source="s17-action-feedback-qualification",
        reference=reference,
    )


def intent_owner() -> IntentCommitment:
    owner = IntentCommitment()
    owner.commit(
        "escape-threat",
        objective="escape the nearby threat",
        at_ns=1,
        provenance=provenance("intent"),
    )
    return owner


def route_criterion() -> RouteCriterion:
    return RouteCriterion(
        criterion_id="route-fail-closed",
        conflict_policy=RouteConflictPolicy.FAIL_CLOSED,
    )


def admission_criterion(
    *allowed: str,
) -> ExecutionAdmissionCriterion:
    return ExecutionAdmissionCriterion(
        criterion_id="escape-threat-allow-list",
        policy=AdmissionPolicy.CURRENT_INTENT_ALLOW_LIST,
        required_intent_id="escape-threat",
        allowed_candidate_refs=allowed or ("MOVE_AWAY",),
    )


def binding() -> ExecutionBinding:
    return ExecutionBinding(
        binding_id="binding-move-away-1",
        candidate_ref="MOVE_AWAY",
        required_intent_id="escape-threat",
        skill_execution_id="skill-exec-escape-1",
        skill_ref="escape-movement",
        action_id="action-move-backward-1",
        action_ref=MOVE_BACKWARD_ACTION_REF,
        provenance=provenance("binding"),
    )


def plan_and_habit(
    *,
    wait_score: int = 8,
    move_score: int = 3,
):
    proposition = PropositionKey("entity", "zombie-1", "nearby")
    evidence = BeliefEvidence(
        "E1",
        proposition,
        EvidenceRelation.SUPPORT,
        provenance("evidence:E1"),
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
    require_attention_selection(attention)
    belief = assess_belief(
        (evidence,),
        BeliefCriterion("zombie-nearby", proposition),
    )
    concept = classify_concept(
        concept_candidate_from_belief(
            belief,
            candidate_id="belief:zombie-nearby",
            payload_ref="transient:belief:zombie-nearby",
            provenance=provenance("belief-to-concept"),
        ),
        ConceptCriterion(
            criterion_id="supported-nearby",
            concept=ConceptKey("spatial", "nearby_threat"),
            required_features=(
                ConceptFeature("belief_status", "supported"),
                ConceptFeature("proposition", proposition.canonical),
            ),
        ),
    )
    base = prediction_state_from_concept(
        concept,
        state_id="threat:zombie-1",
        extra_variables=(StateVariable("comparison_score", 99),),
        provenance=provenance("concept-to-prediction"),
    )
    wait_prediction = predict_transition(
        base,
        TransitionRule(
            rule_id="wait",
            preconditions=(
                StateVariable("concept", "spatial:nearby_threat"),
            ),
            assignments=(StateVariable("comparison_score", wait_score),),
            provenance=provenance("rule:wait"),
        ),
    )
    move_prediction = predict_transition(
        base,
        TransitionRule(
            rule_id="move-away",
            preconditions=(
                StateVariable("concept", "spatial:nearby_threat"),
            ),
            assignments=(StateVariable("comparison_score", move_score),),
            provenance=provenance("rule:move-away"),
        ),
    )
    plan = select_plan(
        (
            plan_candidate_from_prediction(
                wait_prediction,
                candidate_id="WAIT",
                feature_keys=("comparison_score",),
                provenance=provenance("prediction-to-plan:wait"),
            ),
            plan_candidate_from_prediction(
                move_prediction,
                candidate_id="MOVE_AWAY",
                feature_keys=("comparison_score",),
                provenance=provenance("prediction-to-plan:move"),
            ),
        ),
        PlanningCriterion(
            criterion_id="minimize-comparison-score",
            feature_key="comparison_score",
            direction=PlanningDirection.MINIMIZE,
        ),
    )
    repertoire = HabitRepertoire(
        repertoire_id="survival-habits",
        revision=7,
        rules=(
            HabitRule(
                habit_id="H1",
                cue_requirements=(
                    CueFeature("concept", "spatial:nearby_threat"),
                ),
                candidate_ref="MOVE_AWAY",
                priority=10,
                provenance=provenance("habit:H1"),
            ),
        ),
        provenance=provenance("habit-repertoire"),
    )
    habit = select_habit(
        repertoire,
        HabitCue(
            cue_id="nearby-threat",
            features=(CueFeature("concept", concept.concept.canonical),),
            provenance=provenance("habit-cue"),
        ),
    )
    return (
        attention,
        belief,
        concept,
        wait_prediction,
        move_prediction,
        plan,
        repertoire,
        habit,
    )


def s14_chain(
    *,
    wait_score: int = 8,
    move_score: int = 3,
    allowed: tuple[str, ...] = ("MOVE_AWAY",),
):
    (
        attention,
        belief,
        concept,
        wait_prediction,
        move_prediction,
        plan,
        repertoire,
        habit,
    ) = plan_and_habit(wait_score=wait_score, move_score=move_score)
    route = adjudicate_routes(
        plan,
        habit,
        route_criterion(),
        provenance=provenance("route"),
    )
    control = control_candidate_from_route_decision(route)
    owner = intent_owner()
    criterion = admission_criterion(*allowed)
    admission = (
        None
        if control is None
        else admit_control_candidate(
            control,
            route,
            owner,
            criterion,
            provenance=provenance("admission"),
        )
    )
    if admission is None or admission.status is not AdmissionDecisionStatus.ADMITTED:
        return (
            attention,
            belief,
            concept,
            wait_prediction,
            move_prediction,
            plan,
            repertoire,
            habit,
            route,
            control,
            owner,
            criterion,
            admission,
            None,
            None,
            None,
        )
    bound = resolve_execution_binding(
        admission,
        control,
        route,
        owner,
        criterion,
        binding(),
        provenance=provenance("binding-resolution"),
    )
    skill, action, result = start_and_propose_bound_execution(
        bound,
        owner,
        at_ns=10,
        provenance=provenance("start-propose"),
    )
    return (
        attention,
        belief,
        concept,
        wait_prediction,
        move_prediction,
        plan,
        repertoire,
        habit,
        route,
        control,
        owner,
        criterion,
        admission,
        skill,
        action,
        result,
    )


def issued_chain():
    *prefix, owner, criterion, admission, skill, proposed, binding_result = s14_chain()
    assert admission is not None
    assert skill is not None
    assert proposed is not None
    assert binding_result is not None
    authorized = proposed.authorize(
        at_ns=11,
        provenance=provenance("authorization"),
        authority="s15-explicit-authority",
    )
    supervisor = ActionSupervisor()
    issued = supervisor.issue(
        authorized,
        at_ns=12,
        deadline_ns=100,
        provenance=provenance("issue"),
    )
    return (
        *prefix,
        owner,
        criterion,
        admission,
        skill,
        proposed,
        binding_result,
        authorized,
        supervisor,
        issued,
    )


def snapshot(x: float, z: float) -> MineflayerSnapshot:
    return MineflayerSnapshot(
        health=20,
        food=20,
        food_saturation=5,
        oxygen_level=20,
        position=MineflayerPosition(x=x, y=64, z=z),
        time=None,
        inventory=(),
        nearby_entities=(),
        nearby_entities_coverage=MineflayerNearbyEntitiesCoverage(
            source_scope=MINEFLAYER_NEARBY_ENTITY_SOURCE_SCOPE,
            max_distance=MINEFLAYER_NEARBY_ENTITY_MAX_DISTANCE,
            max_entities=MINEFLAYER_NEARBY_ENTITY_MAX_ENTITIES,
            candidate_count=0,
            truncated=False,
        ),
    )


def observation(seq: int, x: float, z: float) -> MineflayerObservation:
    return MineflayerObservation(
        session_id="s15-session",
        seq=seq,
        kind="probe",
        snapshot=snapshot(x, z),
    )


def effect(
    seq: int,
    action_id: str,
    effect_name: str,
    *,
    result: str = "applied",
) -> MineflayerEffectResult:
    return MineflayerEffectResult(
        session_id="s15-session",
        seq=seq,
        action_id=action_id,
        effect=effect_name,
        result=result,
        error=None if result == "applied" else "rejected-by-fixture",
    )


class FakeSession:
    def __init__(self, messages=()) -> None:
        self._messages = deque(messages)
        self.started = MineflayerAdapterStarted(
            session_id="s15-session",
            seq=0,
            mineflayer_version=MINEFLAYER_VERSION,
            config=MineflayerLaunchConfig(),
        )
        self.sent: list[tuple] = []
        self.fail_set_control = False
        self.fail_observe = False

    async def receive(self):
        if not self._messages:
            raise RuntimeError("fixture stream exhausted")
        return self._messages.popleft()

    async def send_observe(self) -> None:
        self.sent.append(("observe",))
        if self.fail_observe:
            raise RuntimeError("adapter disconnected")

    async def send_set_control(
        self,
        action_id: str,
        *,
        control: str,
        state: bool,
    ) -> None:
        self.sent.append(("set_control", action_id, control, state))
        if self.fail_set_control:
            raise RuntimeError("dispatch write failed")

    async def send_clear_controls(self, action_id: str) -> None:
        self.sent.append(("clear_controls", action_id))


def successful_session(command: MineflayerCommand) -> FakeSession:
    return FakeSession(
        (
            observation(1, 0.0, 0.0),
            effect(2, command.action_id, "set_control"),
            effect(3, command.cleanup_action_id, "clear_controls"),
            observation(4, 0.0, 0.20),
        )
    )



def executed_consequence():
    *_, binding_result, _, supervisor, issued = issued_chain()[-4:]
    command = build_mineflayer_command(issued, binding_result)
    consequence = asyncio.run(
        execute_mineflayer_command(
            successful_session(command),
            command,
            provenance=provenance("executed-consequence"),
        )
    )
    assert consequence.status is WorldConsequenceStatus.EXECUTED
    return binding_result, supervisor, issued, consequence


def rejected_consequence():
    *_, binding_result, _, supervisor, issued = issued_chain()[-4:]
    command = build_mineflayer_command(issued, binding_result)
    adapter = FakeSession(
        (
            observation(1, 0.0, 0.0),
            effect(
                2,
                command.action_id,
                "set_control",
                result="rejected",
            ),
        )
    )
    consequence = asyncio.run(
        execute_mineflayer_command(
            adapter,
            command,
            provenance=provenance("rejected-consequence"),
        )
    )
    assert consequence.status is WorldConsequenceStatus.FAILED
    assert consequence.dispatch_receipt is not None
    assert consequence.dispatch_receipt.result == "rejected"
    return binding_result, supervisor, issued, consequence


def disconnected_consequence():
    *_, binding_result, _, supervisor, issued = issued_chain()[-4:]
    command = build_mineflayer_command(issued, binding_result)
    adapter = FakeSession()
    adapter.fail_observe = True
    consequence = asyncio.run(
        execute_mineflayer_command(
            adapter,
            command,
            provenance=provenance("disconnected-consequence"),
        )
    )
    assert consequence.status is WorldConsequenceStatus.FAILED
    assert consequence.dispatch_receipt is None
    return binding_result, supervisor, issued, consequence


def undetermined_consequence():
    *_, binding_result, _, supervisor, issued = issued_chain()[-4:]
    command = build_mineflayer_command(issued, binding_result)
    adapter = FakeSession(
        (
            observation(1, 0.0, 0.0),
            effect(2, command.action_id, "set_control"),
            effect(3, command.cleanup_action_id, "clear_controls"),
            observation(4, 0.0, 0.0),
        )
    )
    consequence = asyncio.run(
        execute_mineflayer_command(
            adapter,
            command,
            provenance=provenance("undetermined-consequence"),
        )
    )
    assert consequence.status is WorldConsequenceStatus.UNDETERMINED
    return binding_result, supervisor, issued, consequence


def executed_closed_chain():
    (
        attention,
        belief,
        concept,
        wait_prediction,
        move_prediction,
        plan,
        repertoire,
        habit,
        route,
        control,
        owner,
        admission_criterion_value,
        admission,
        skill,
        proposed,
        binding_result,
        authorized,
        supervisor,
        issued,
    ) = issued_chain()
    command = build_mineflayer_command(issued, binding_result)
    consequence = asyncio.run(
        execute_mineflayer_command(
            successful_session(command),
            command,
            provenance=provenance("s17-world-consequence"),
        )
    )
    outcome_interpretation = interpret_world_consequence(
        issued,
        binding_result,
        consequence,
        provenance=provenance("s17-action-outcome-interpretation"),
    )
    closed = record_interpreted_action_outcome(
        supervisor,
        outcome_interpretation,
        at_ns=20,
    )
    assert closed.state is ActionState.OUTCOME
    return (
        attention,
        belief,
        concept,
        wait_prediction,
        move_prediction,
        plan,
        repertoire,
        habit,
        route,
        control,
        owner,
        admission_criterion_value,
        admission,
        skill,
        proposed,
        binding_result,
        authorized,
        supervisor,
        issued,
        consequence,
        outcome_interpretation,
        closed,
    )


def feedback_criterion(
    *,
    criterion_id: str = "risk-from-observed-move",
    target_id: str = "risk_weight",
    action_id: str = "action-move-backward-1",
    binding_id: str = "binding-move-away-1",
    action_ref: str = "MOVE_BACKWARD",
    action_state: ActionState = ActionState.OUTCOME,
    disposition: ActionOutcomeDisposition = ActionOutcomeDisposition.OUTCOME,
    reason: str = "observed_execution",
    direction: FeedbackDirection = FeedbackDirection.INCREASE,
) -> ActionFeedbackCriterion:
    return ActionFeedbackCriterion(
        criterion_id=criterion_id,
        target_id=target_id,
        required_action_id=action_id,
        required_binding_id=binding_id,
        required_action_ref=action_ref,
        required_action_state=action_state,
        required_outcome_disposition=disposition,
        required_outcome_reason=reason,
        feedback_direction=direction,
        provenance=provenance(f"feedback-criterion:{criterion_id}"),
    )


def learning_state() -> LearningPreferenceState:
    return LearningPreferenceState(
        target_id="risk_weight",
        value=3,
        minimum=0,
        maximum=10,
        revision=0,
        origin_provenance=provenance("risk-weight-origin"),
    )


def learning_rule() -> LearningUpdateRule:
    return LearningUpdateRule(
        rule_id="bounded-risk-step",
        version=1,
        step=1,
    )


def learning_authority(
    *,
    target_id: str = "risk_weight",
    granted: bool = True,
) -> LearningUpdateAuthority:
    return LearningUpdateAuthority(
        authority_id="s17-risk-owner-authority",
        target_id=target_id,
        provenance=provenance("s17-learning-authority"),
        granted=granted,
    )


def test_feedback_descriptor_is_integration_only_with_cognitive_orientation() -> None:
    assert S17_FEEDBACK_CAPABILITY_SPEC.capability_id == "FEEDBACK"
    assert S17_FEEDBACK_CAPABILITY_SPEC.state_scopes == ()
    assert S17_FEEDBACK_CAPABILITY_SPEC.dependencies == ("ACTION_OUTCOME",)
    assert (
        S17_FEEDBACK_OPERATOR_DESCRIPTOR.effect
        is OperatorEffect.READ_ONLY
    )
    assert (
        S17_FEEDBACK_CRITERION_DESCRIPTOR.kind
        is CriterionKind.COGNITIVE_ORIENTATION
    )
    assert S17_FEEDBACK_CAPABILITY_SPEC.operator_ids == (
        "learning.interpret_action_outcome_feedback",
    )


def test_action_feedback_criterion_is_bounded_and_structured() -> None:
    criterion = feedback_criterion()
    assert criterion.target_id == "risk_weight"
    assert criterion.required_action_state is ActionState.OUTCOME
    assert criterion.required_outcome_reason == "observed_execution"
    assert criterion.feedback_direction is FeedbackDirection.INCREASE

    with pytest.raises(
        InvalidActionFeedbackData,
        match="OUTCOME or UNKNOWN Action state",
    ):
        feedback_criterion(action_state=ActionState.TIMEOUT)
    with pytest.raises(
        InvalidActionFeedbackData,
        match="must match outcome disposition",
    ):
        feedback_criterion(
            action_state=ActionState.UNKNOWN,
            disposition=ActionOutcomeDisposition.OUTCOME,
        )


def test_exact_outcome_produces_existing_learning_feedback_without_mutation() -> None:
    *_, outcome_interpretation, closed = executed_closed_chain()[-2:]
    state = learning_state()
    criterion = feedback_criterion()

    first = interpret_action_outcome_as_learning_feedback(
        closed,
        outcome_interpretation,
        criterion,
        provenance=provenance("feedback-interpretation"),
    )
    second = interpret_action_outcome_as_learning_feedback(
        closed,
        outcome_interpretation,
        criterion,
        provenance=provenance("feedback-interpretation"),
    )

    assert first == second
    assert first.status is LearningFeedbackInterpretationStatus.PRODUCED
    assert first.feedback is not None
    assert first.feedback.target_id == "risk_weight"
    assert first.feedback.direction is FeedbackDirection.INCREASE
    assert first.feedback.feedback_id.startswith(
        "feedback:risk-from-observed-move:risk_weight:"
    )
    assert first.feedback.consequence_ref == first.outcome_ref
    assert first.criterion_provenance == criterion.provenance
    assert first.action_outcome_provenance == outcome_interpretation.provenance
    assert first.world_provenance == outcome_interpretation.world_provenance
    assert state.value == 3
    assert state.revision == 0


def test_same_outcome_has_no_global_learning_direction() -> None:
    *_, outcome_interpretation, closed = executed_closed_chain()[-2:]
    increase = interpret_action_outcome_as_learning_feedback(
        closed,
        outcome_interpretation,
        feedback_criterion(
            criterion_id="increase-risk",
            direction=FeedbackDirection.INCREASE,
        ),
        provenance=provenance("increase-interpretation"),
    )
    hold = interpret_action_outcome_as_learning_feedback(
        closed,
        outcome_interpretation,
        feedback_criterion(
            criterion_id="hold-risk",
            direction=FeedbackDirection.HOLD,
        ),
        provenance=provenance("hold-interpretation"),
    )

    assert increase.feedback is not None
    assert hold.feedback is not None
    assert increase.feedback.direction is FeedbackDirection.INCREASE
    assert hold.feedback.direction is FeedbackDirection.HOLD
    assert increase.feedback.feedback_id != hold.feedback.feedback_id


def test_nonmatching_explicit_criterion_produces_no_feedback() -> None:
    *_, outcome_interpretation, closed = executed_closed_chain()[-2:]
    result = interpret_action_outcome_as_learning_feedback(
        closed,
        outcome_interpretation,
        feedback_criterion(action_id="other-action"),
        provenance=provenance("nonmatching-criterion"),
    )

    assert result.status is LearningFeedbackInterpretationStatus.NOT_APPLICABLE
    assert result.feedback is None
    assert result.reason_code == "explicit_feedback_criterion_not_matched"


@pytest.mark.parametrize(
    ("criterion_kwargs", "expected_reason"),
    [
        ({"action_ref": "WAIT"}, "explicit_feedback_criterion_not_matched"),
        ({"reason": "known_adapter_rejection"}, "explicit_feedback_criterion_not_matched"),
    ],
)
def test_wrong_action_ref_or_outcome_reason_produces_no_feedback(
    criterion_kwargs,
    expected_reason: str,
) -> None:
    *_, outcome_interpretation, closed = executed_closed_chain()[-2:]
    result = interpret_action_outcome_as_learning_feedback(
        closed,
        outcome_interpretation,
        feedback_criterion(**criterion_kwargs),
        provenance=provenance("criterion-mismatch"),
    )
    assert result.status is LearningFeedbackInterpretationStatus.NOT_APPLICABLE
    assert result.feedback is None
    assert result.reason_code == expected_reason


def test_missing_outcome_and_nonterminal_action_do_not_produce_feedback() -> None:
    *_, outcome_interpretation, closed = executed_closed_chain()[-2:]
    missing = interpret_action_outcome_as_learning_feedback(
        closed,
        None,
        feedback_criterion(),
        provenance=provenance("missing-outcome"),
    )
    assert missing.status is LearningFeedbackInterpretationStatus.NOT_APPLICABLE
    assert missing.feedback is None

    *_, proposed, _ = s14_chain()[-3:]
    assert proposed is not None
    with pytest.raises(
        InvalidActionFeedbackData,
        match="terminal state",
    ):
        interpret_action_outcome_as_learning_feedback(
            proposed,
            outcome_interpretation,
            feedback_criterion(),
            provenance=provenance("nonterminal-action"),
        )


def test_malformed_learning_target_identifier_is_rejected() -> None:
    with pytest.raises(InvalidActionFeedbackData, match="target_id"):
        feedback_criterion(target_id="risk weight")


def test_fabricated_outcome_lineage_fails_closed() -> None:
    *_, outcome_interpretation, closed = executed_closed_chain()[-2:]
    with pytest.raises(InvalidActionFeedbackData, match="action_id"):
        interpret_action_outcome_as_learning_feedback(
            closed,
            replace(outcome_interpretation, action_id="other-action"),
            feedback_criterion(),
            provenance=provenance("fabricated-outcome"),
        )
    with pytest.raises(InvalidActionFeedbackData, match="skill_execution_id"):
        interpret_action_outcome_as_learning_feedback(
            closed,
            replace(
                outcome_interpretation,
                skill_execution_id="other-skill",
            ),
            feedback_criterion(),
            provenance=provenance("fabricated-skill"),
        )
    with pytest.raises(InvalidActionFeedbackData, match="intent_id"):
        interpret_action_outcome_as_learning_feedback(
            closed,
            replace(outcome_interpretation, intent_id="other-intent"),
            feedback_criterion(),
            provenance=provenance("fabricated-intent"),
        )


def test_unknown_without_explicit_unknown_criterion_produces_no_feedback() -> None:
    (
        *prefix_values,
        binding_result,
        _,
        supervisor,
        issued,
    ) = issued_chain()
    command = build_mineflayer_command(issued, binding_result)
    adapter = FakeSession()
    adapter.fail_observe = True
    consequence = asyncio.run(
        execute_mineflayer_command(
            adapter,
            command,
            provenance=provenance("unknown-world-consequence"),
        )
    )
    outcome_interpretation = interpret_world_consequence(
        issued,
        binding_result,
        consequence,
        provenance=provenance("unknown-outcome-interpretation"),
    )
    unknown = record_interpreted_action_outcome(
        supervisor,
        outcome_interpretation,
        at_ns=20,
    )
    assert unknown.state is ActionState.UNKNOWN

    result = interpret_action_outcome_as_learning_feedback(
        unknown,
        outcome_interpretation,
        feedback_criterion(),
        provenance=provenance("unknown-feedback"),
    )
    assert result.status is LearningFeedbackInterpretationStatus.NOT_APPLICABLE
    assert result.feedback is None
    assert prefix_values


def test_timeout_without_outcome_interpretation_produces_no_feedback() -> None:
    *_, supervisor, issued = issued_chain()[-2:]
    (timeout,) = supervisor.advance(
        at_ns=100,
        provenance=provenance("timeout"),
    )
    assert timeout.action_id == issued.action_id
    assert timeout.state is ActionState.TIMEOUT

    result = interpret_action_outcome_as_learning_feedback(
        timeout,
        None,
        feedback_criterion(),
        provenance=provenance("timeout-feedback"),
    )
    assert result.status is LearningFeedbackInterpretationStatus.NOT_APPLICABLE
    assert result.feedback is None


def test_issued_undetermined_consequence_does_not_learn_from_absence() -> None:
    *_, binding_result, _, supervisor, issued = issued_chain()[-4:]
    command = build_mineflayer_command(issued, binding_result)
    adapter = FakeSession(
        (
            observation(1, 0.0, 0.0),
            effect(2, command.action_id, "set_control"),
            effect(3, command.cleanup_action_id, "clear_controls"),
            observation(4, 0.0, 0.0),
        )
    )
    consequence = asyncio.run(
        execute_mineflayer_command(
            adapter,
            command,
            provenance=provenance("undetermined-world-consequence"),
        )
    )
    outcome_interpretation = interpret_world_consequence(
        issued,
        binding_result,
        consequence,
        provenance=provenance("unavailable-outcome"),
    )
    assert supervisor.get(issued.action_id).state is ActionState.ISSUED

    result = interpret_action_outcome_as_learning_feedback(
        issued,
        outcome_interpretation,
        feedback_criterion(),
        provenance=provenance("undetermined-feedback"),
    )
    assert result.status is LearningFeedbackInterpretationStatus.UNDETERMINED
    assert result.feedback is None


def test_provider_text_cannot_become_outcome_criterion_or_feedback() -> None:
    *_, outcome_interpretation, closed = executed_closed_chain()[-2:]
    expression = ProviderExpression(
        text="That worked well.",
        provenance=provenance("provider-worked-well"),
    )
    with pytest.raises(InvalidActionFeedbackData, match="ActionOutcomeInterpretation"):
        interpret_action_outcome_as_learning_feedback(
            closed,
            expression,  # type: ignore[arg-type]
            feedback_criterion(),
            provenance=provenance("provider-not-outcome"),
        )
    with pytest.raises(InvalidActionFeedbackData, match="ActionFeedbackCriterion"):
        interpret_action_outcome_as_learning_feedback(
            closed,
            outcome_interpretation,
            ProviderExpression(
                text="Increase the risk weight.",
                provenance=provenance("provider-direction"),
            ),  # type: ignore[arg-type]
            provenance=provenance("provider-not-criterion"),
        )


def test_provider_text_cannot_become_feedback_or_learning_authority() -> None:
    state = learning_state()
    provider_feedback = ProviderExpression(
        text="Learn from this.",
        provenance=provenance("provider-learn"),
    )
    with pytest.raises(InvalidLearningData, match="LearningFeedback"):
        propose_learning_update(
            state,
            provider_feedback,  # type: ignore[arg-type]
            learning_rule(),
        )

    *_, outcome_interpretation, closed = executed_closed_chain()[-2:]
    interpretation = interpret_action_outcome_as_learning_feedback(
        closed,
        outcome_interpretation,
        feedback_criterion(),
        provenance=provenance("valid-feedback-for-provider-authority"),
    )
    assert interpretation.feedback is not None
    proposal = propose_learning_update(
        state,
        interpretation.feedback,
        learning_rule(),
    )
    with pytest.raises(InvalidLearningAuthority, match="LearningUpdateAuthority"):
        commit_learning_update(
            state,
            proposal,
            ProviderExpression(
                text="Increase the risk weight.",
                provenance=provenance("provider-authority"),
            ),  # type: ignore[arg-type]
            provenance=provenance("provider-cannot-authorize"),
        )


def test_existing_s10_proposal_and_commit_are_reused_exactly() -> None:
    *_, outcome_interpretation, closed = executed_closed_chain()[-2:]
    state = learning_state()
    interpretation = interpret_action_outcome_as_learning_feedback(
        closed,
        outcome_interpretation,
        feedback_criterion(),
        provenance=provenance("feedback-for-lrn"),
    )
    assert interpretation.feedback is not None

    proposal = propose_learning_update(
        state,
        interpretation.feedback,
        learning_rule(),
    )
    assert state.value == 3
    assert state.revision == 0
    assert proposal.expected_revision == 0
    assert proposal.expected_value == 3
    assert proposal.proposed_value == 4

    with pytest.raises(MissingLearningAuthority):
        commit_learning_update(
            state,
            proposal,
            None,
            provenance=provenance("missing-authority"),
        )
    with pytest.raises(InvalidLearningAuthority):
        commit_learning_update(
            state,
            proposal,
            learning_authority(granted=False),
            provenance=provenance("denied-authority"),
        )

    committed = commit_learning_update(
        state,
        proposal,
        learning_authority(),
        provenance=provenance("commit"),
    )
    assert committed.previous_state is state
    assert committed.new_state.value == 4
    assert committed.new_state.revision == 1
    assert committed.record.feedback_id == interpretation.feedback.feedback_id
    assert committed.record.feedback_provenance == interpretation.feedback.provenance

    with pytest.raises(ReplayLearningFeedback):
        propose_learning_update(
            committed.new_state,
            interpretation.feedback,
            learning_rule(),
        )
    with pytest.raises(StaleLearningUpdate):
        commit_learning_update(
            committed.new_state,
            proposal,
            learning_authority(),
            provenance=provenance("stale-replay"),
        )


def test_generated_feedback_target_must_match_retained_owner() -> None:
    *_, outcome_interpretation, closed = executed_closed_chain()[-2:]
    interpretation = interpret_action_outcome_as_learning_feedback(
        closed,
        outcome_interpretation,
        feedback_criterion(target_id="other_target"),
        provenance=provenance("wrong-target-feedback"),
    )
    assert interpretation.feedback is not None
    with pytest.raises(LearningTargetMismatch):
        propose_learning_update(
            learning_state(),
            interpretation.feedback,
            learning_rule(),
        )


def test_feedback_off_with_lrn_on_preserves_retained_state() -> None:
    *_, outcome_interpretation, closed = executed_closed_chain()[-2:]
    state = learning_state()
    criterion = feedback_criterion()
    box: dict[str, object] = {}

    plan = s17_capability_plan(
        enabled_ids=frozenset(
            {
                "CTL",
                "SKL",
                "ADMISSION",
                "EXEC_BIND",
                "WORLD_EXEC",
                "ACTION_OUTCOME",
                "LRN",
            }
        )
    )
    due = (
        EpochWorkItem(
            "feedback-1",
            "learning.interpret_action_outcome_feedback",
            "outcome-ready",
        ),
    )
    epoch = compile_epoch_plan(
        plan,
        S17_DESCRIPTOR_SET,
        due_items=due,
        bindings=(),
    )
    result = coordinate_planned_epoch(
        ActionSupervisor(),
        epoch,
        bindings=(),
        at_ns=21,
        provenance=provenance("feedback-off"),
    )

    assert result.suppressed_work_ids == ("feedback-1",)
    assert box == {}
    assert state.value == 3
    assert state.revision == 0
    assert closed.state is ActionState.OUTCOME
    assert outcome_interpretation.reason_code == "observed_execution"
    assert criterion.target_id == "risk_weight"


def test_feedback_on_with_lrn_off_produces_feedback_without_adaptation() -> None:
    *_, outcome_interpretation, closed = executed_closed_chain()[-2:]
    state = learning_state()
    criterion = feedback_criterion()
    box: dict[str, object] = {}
    from relay_self.epoch_plan import EpochBinding

    def feedback_work() -> None:
        box["feedback"] = interpret_action_outcome_as_learning_feedback(
            closed,
            outcome_interpretation,
            criterion,
            provenance=provenance("feedback-on"),
        )

    binding_work = EpochBinding(
        "feedback-1",
        "learning.interpret_action_outcome_feedback",
        feedback_work,
    )
    plan = s17_capability_plan(
        enabled_ids=frozenset(
            {
                "CTL",
                "SKL",
                "ADMISSION",
                "EXEC_BIND",
                "WORLD_EXEC",
                "ACTION_OUTCOME",
                "FEEDBACK",
            }
        )
    )
    due = (
        EpochWorkItem(
            "feedback-1",
            "learning.interpret_action_outcome_feedback",
            "outcome-ready",
        ),
        EpochWorkItem("lrn-propose-1", "lrn.propose_update", "feedback-ready"),
        EpochWorkItem("lrn-apply-1", "lrn.apply_update", "proposal-ready"),
    )
    epoch = compile_epoch_plan(
        plan,
        S17_DESCRIPTOR_SET,
        due_items=due,
        bindings=(binding_work,),
    )
    result = coordinate_planned_epoch(
        ActionSupervisor(),
        epoch,
        bindings=(binding_work,),
        at_ns=21,
        provenance=provenance("lrn-off"),
    )

    feedback_result = box["feedback"]
    assert feedback_result.status is LearningFeedbackInterpretationStatus.PRODUCED
    assert feedback_result.feedback is not None
    assert result.suppressed_work_ids == ("lrn-propose-1", "lrn-apply-1")
    assert state.value == 3
    assert state.revision == 0


def test_full_deterministic_action_learning_loop_closes_once_without_reentry() -> None:
    (
        attention,
        belief,
        concept,
        wait_prediction,
        move_prediction,
        plan,
        repertoire,
        habit,
        route,
        control,
        owner,
        admission_criterion_value,
        admission,
        skill,
        proposed,
        binding_result,
        authorized,
        supervisor,
        issued,
        consequence,
        outcome_interpretation,
        closed,
    ) = executed_closed_chain()

    state = learning_state()
    criterion = feedback_criterion()
    upstream_before = (
        attention,
        belief,
        concept,
        wait_prediction,
        move_prediction,
        plan,
        repertoire,
        habit,
        route,
        control,
        owner.events,
        admission,
        skill,
        proposed,
        authorized,
        closed,
    )
    feedback_result = interpret_action_outcome_as_learning_feedback(
        closed,
        outcome_interpretation,
        criterion,
        provenance=provenance("full-feedback"),
    )
    assert feedback_result.feedback is not None
    proposal = propose_learning_update(
        state,
        feedback_result.feedback,
        learning_rule(),
    )
    commit = commit_learning_update(
        state,
        proposal,
        learning_authority(),
        provenance=provenance("full-learning-commit"),
    )

    assert attention is not None
    assert belief is not None
    assert concept is not None
    assert wait_prediction is not None
    assert move_prediction is not None
    assert plan.selected is not None
    assert plan.selected.candidate_id == "MOVE_AWAY"
    assert habit.selected_candidate_ref == "MOVE_AWAY"
    assert route.status is RouteDecisionStatus.AGREED
    assert control is not None
    assert admission is not None
    assert admission.status is AdmissionDecisionStatus.ADMITTED
    assert skill is not None
    assert skill.state is SkillState.STARTED
    assert proposed is not None
    assert proposed.state is ActionState.PROPOSED
    assert authorized.state is ActionState.AUTHORIZED
    assert issued.state is ActionState.ISSUED
    assert consequence.status is WorldConsequenceStatus.EXECUTED
    assert closed.state is ActionState.OUTCOME

    assert commit.previous_state.value == 3
    assert commit.previous_state.revision == 0
    assert commit.new_state.value == 4
    assert commit.new_state.revision == 1

    upstream_after = (
        attention,
        belief,
        concept,
        wait_prediction,
        move_prediction,
        plan,
        repertoire,
        habit,
        route,
        control,
        owner.events,
        admission,
        skill,
        proposed,
        authorized,
        closed,
    )
    assert upstream_after == upstream_before

    assert owner.current_intent is not None
    assert owner.current_intent.intent_id == "escape-threat"
    assert skill.state is SkillState.STARTED
    assert repertoire.rules[0].priority == 10
    assert habit.selected_candidate_ref == "MOVE_AWAY"
    assert plan.selected.candidate_id == "MOVE_AWAY"
    assert belief == belief
    assert admission_criterion_value.allowed_candidate_refs == ("MOVE_AWAY",)
    assert supervisor.open_actions == ()

    cognition = PersistentCognition(
        identity=IdentitySpecification(
            self_id="s17-self",
            directives=("no implicit feedback memory",),
            provenance=provenance("identity"),
        ),
        memories=(
            Memory(
                memory_id="existing",
                content="existing",
                source_provenance=provenance("memory-source"),
                integration_provenance=provenance("memory-integration"),
            ),
        ),
    )
    assert len(cognition.memories) == 1

    provider_calls: list[object] = []
    second_epoch_actions: list[object] = []
    assert provider_calls == []
    assert second_epoch_actions == []
