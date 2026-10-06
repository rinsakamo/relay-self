from __future__ import annotations

import inspect
from dataclasses import FrozenInstanceError

import pytest

import relay_self
from relay_self.action import ActionLifecycle, ActionState
from relay_self.action_supervision import ActionSupervisor
from relay_self.admission_profile import AdmissionProfileId, s13_admission_profile
from relay_self.attention import (
    AttentionCandidate,
    AttentionCriterion,
    AttentionSelection,
    require_attention_selection,
    select_attention,
)
from relay_self.belief import (
    BeliefAssessment,
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
    ConceptRepresentation,
    ConceptStatus,
    classify_concept,
    concept_candidate_from_belief,
)
from relay_self.epoch_plan import (
    EpochBinding,
    EpochWorkItem,
    MissingEpochBinding,
    compile_epoch_plan,
    coordinate_planned_epoch,
)
from relay_self.execution_admission import (
    AdmissionDecision,
    AdmissionDecisionStatus,
    AdmissionPolicy,
    ExecutionAdmissionCriterion,
    admit_control_candidate,
)
from relay_self.execution_binding import (
    BoundExecutionCandidate,
    ExecutionBinding,
    ExecutionBindingResult,
    InvalidExecutionBindingData,
    resolve_execution_binding,
    start_and_propose_bound_execution,
)
from relay_self.execution_binding_profile import (
    S14_EXECUTION_BINDING_PROFILES,
    ExecutionBindingProfileId,
    s14_execution_binding_profile,
)
from relay_self.execution_descriptor import (
    S14_DESCRIPTOR_SET,
    S14_EXEC_BIND_CAPABILITY_SPEC,
    S14_EXEC_BIND_CRITERION_DESCRIPTOR,
    S14_EXEC_BIND_RESOLVE_OPERATOR_DESCRIPTOR,
    S14_EXEC_BIND_TRANSITION_OPERATOR_DESCRIPTOR,
    CriterionKind,
    OperatorEffect,
    s14_capability_plan,
)
from relay_self.habit import (
    CueFeature,
    HabitCue,
    HabitRepertoire,
    HabitRule,
    HabitSelection,
    select_habit,
)
from relay_self.intent import IntentCommitment
from relay_self.learning import (
    InvalidLearningData,
    LearningPreferenceState,
    LearningUpdateRule,
    propose_learning_update,
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
    plan_candidate_from_prediction,
    select_plan,
)
from relay_self.prediction import (
    PredictionResult,
    StateVariable,
    TransitionRule,
    predict_transition,
    prediction_state_from_concept,
)
from relay_self.provenance import Provenance
from relay_self.relay_engine import ProviderExpression
from relay_self.route_adjudication import (
    ControlCandidate,
    RouteConflictPolicy,
    RouteCriterion,
    RouteDecision,
    RouteDecisionStatus,
    adjudicate_routes,
    control_candidate_from_route_decision,
)
from relay_self.skill import SkillExecution, SkillState


def provenance(reference: str) -> Provenance:
    return Provenance(
        source="s14-execution-binding-qualification",
        reference=reference,
    )


def intent_owner(intent_id: str = "escape-threat") -> IntentCommitment:
    owner = IntentCommitment()
    owner.commit(
        intent_id,
        objective=f"objective:{intent_id}",
        at_ns=1,
        provenance=provenance(f"intent:{intent_id}"),
    )
    return owner


def route_criterion() -> RouteCriterion:
    return RouteCriterion(
        criterion_id="route-fail-closed",
        conflict_policy=RouteConflictPolicy.FAIL_CLOSED,
    )


def admission_criterion(
    *allowed: str,
    required_intent_id: str = "escape-threat",
) -> ExecutionAdmissionCriterion:
    if not allowed:
        allowed = ("MOVE_AWAY",)
    return ExecutionAdmissionCriterion(
        criterion_id="escape-threat-allow-list",
        policy=AdmissionPolicy.CURRENT_INTENT_ALLOW_LIST,
        required_intent_id=required_intent_id,
        allowed_candidate_refs=tuple(allowed),
    )


def execution_binding(
    *,
    candidate_ref: str = "MOVE_AWAY",
    required_intent_id: str = "escape-threat",
    skill_execution_id: str = "skill-exec-escape-1",
    skill_ref: str = "escape-movement",
    action_id: str = "action-move-backward-1",
    action_ref: str = "MOVE_BACKWARD",
) -> ExecutionBinding:
    return ExecutionBinding(
        binding_id="binding-move-away-1",
        candidate_ref=candidate_ref,
        required_intent_id=required_intent_id,
        skill_execution_id=skill_execution_id,
        skill_ref=skill_ref,
        action_id=action_id,
        action_ref=action_ref,
        provenance=provenance("execution-binding"),
    )


def plan_selection(
    *,
    wait_score: int = 8,
    move_score: int = 3,
) -> PlanSelection:
    wait = PlanCandidate(
        candidate_id="WAIT",
        outcome_features=(PlanFeature("comparison_score", wait_score),),
        provenance=provenance("plan:wait"),
        action_ref="WAIT",
    )
    move = PlanCandidate(
        candidate_id="MOVE_AWAY",
        outcome_features=(PlanFeature("comparison_score", move_score),),
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


def habit_repertoire() -> HabitRepertoire:
    return HabitRepertoire(
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


def habit_selection() -> HabitSelection:
    return select_habit(
        habit_repertoire(),
        HabitCue(
            cue_id="nearby-threat",
            features=(
                CueFeature("concept", "spatial:nearby_threat"),
            ),
            provenance=provenance("habit-cue"),
        ),
    )


def admitted_chain(
    *,
    owner: IntentCommitment | None = None,
    wait_score: int = 8,
    move_score: int = 3,
    allowed: tuple[str, ...] = ("MOVE_AWAY",),
) -> tuple[
    IntentCommitment,
    RouteDecision,
    ControlCandidate | None,
    ExecutionAdmissionCriterion,
    AdmissionDecision | None,
]:
    if owner is None:
        owner = intent_owner()
    route = adjudicate_routes(
        plan_selection(wait_score=wait_score, move_score=move_score),
        habit_selection(),
        route_criterion(),
        provenance=provenance("route"),
    )
    control = control_candidate_from_route_decision(route)
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
    return owner, route, control, criterion, admission


def identity() -> IdentitySpecification:
    return IdentitySpecification(
        self_id="self-s14",
        directives=("proposal is not authorization",),
        provenance=provenance("identity"),
    )


def memory(memory_id: str) -> Memory:
    return Memory(
        memory_id=memory_id,
        content=f"memory:{memory_id}",
        source_provenance=provenance(f"memory-source:{memory_id}"),
        integration_provenance=provenance(f"memory-integration:{memory_id}"),
    )


def full_upstream() -> tuple[
    AttentionSelection,
    BeliefAssessment,
    ConceptRepresentation,
    PredictionResult,
    PredictionResult,
    PlanSelection,
    HabitSelection,
]:
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
            assignments=(StateVariable("comparison_score", 8),),
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
            assignments=(StateVariable("comparison_score", 3),),
            provenance=provenance("rule:move-away"),
        ),
    )
    wait = plan_candidate_from_prediction(
        wait_prediction,
        candidate_id="WAIT",
        feature_keys=("comparison_score",),
        provenance=provenance("prediction-to-plan:wait"),
    )
    move = plan_candidate_from_prediction(
        move_prediction,
        candidate_id="MOVE_AWAY",
        feature_keys=("comparison_score",),
        provenance=provenance("prediction-to-plan:move"),
    )
    plan = select_plan(
        (wait, move),
        PlanningCriterion(
            criterion_id="minimize-comparison-score",
            feature_key="comparison_score",
            direction=PlanningDirection.MINIMIZE,
        ),
    )
    habit = select_habit(
        habit_repertoire(),
        HabitCue(
            cue_id="concept-nearby-threat",
            features=(
                CueFeature("concept", concept.concept.canonical),
            ),
            provenance=provenance("concept-to-habit-cue"),
        ),
    )
    return (
        attention,
        belief,
        concept,
        wait_prediction,
        move_prediction,
        plan,
        habit,
    )


def test_package_exports_s14_surface() -> None:
    assert relay_self.ExecutionBinding is ExecutionBinding
    assert relay_self.BoundExecutionCandidate is BoundExecutionCandidate
    assert relay_self.ExecutionBindingResult is ExecutionBindingResult
    assert relay_self.resolve_execution_binding is resolve_execution_binding
    assert (
        relay_self.start_and_propose_bound_execution
        is start_and_propose_bound_execution
    )
    assert (
        relay_self.ExecutionBindingProfileId
        is ExecutionBindingProfileId
    )
    assert (
        relay_self.S14_EXECUTION_BINDING_PROFILES
        is S14_EXECUTION_BINDING_PROFILES
    )


def test_s14_metadata_is_integration_only_and_guard_is_contract() -> None:
    assert S14_EXEC_BIND_CAPABILITY_SPEC.capability_id == "EXEC_BIND"
    assert S14_EXEC_BIND_CAPABILITY_SPEC.state_scopes == ()
    assert S14_EXEC_BIND_CAPABILITY_SPEC.dependencies == (
        "ADMISSION",
        "SKL",
    )
    assert (
        S14_EXEC_BIND_RESOLVE_OPERATOR_DESCRIPTOR.effect
        is OperatorEffect.READ_ONLY
    )
    assert (
        S14_EXEC_BIND_TRANSITION_OPERATOR_DESCRIPTOR.effect
        is OperatorEffect.OWNER_TRANSITION
    )
    assert (
        S14_EXEC_BIND_CRITERION_DESCRIPTOR.kind
        is CriterionKind.CONTRACT_GUARD
    )


def test_profiles_include_existing_ctl_skl_dependencies_explicitly() -> None:
    assert [profile.profile_id for profile in S14_EXECUTION_BINDING_PROFILES] == [
        ExecutionBindingProfileId.EXEC_BIND,
        ExecutionBindingProfileId.ROUTE_ADMISSION_EXEC_BIND,
        ExecutionBindingProfileId.FULL_DETERMINISTIC_EXECUTION_BINDING,
    ]
    assert s14_execution_binding_profile(
        ExecutionBindingProfileId.EXEC_BIND
    ).enabled_ids == frozenset(
        {"CTL", "SKL", "ADMISSION", "EXEC_BIND"}
    )


def test_exact_admitted_candidate_resolves_then_starts_and_proposes() -> None:
    owner, route, control, criterion, admission = admitted_chain()
    assert control is not None
    assert admission is not None
    before_intent = (owner.events, owner.current_intent)

    bound = resolve_execution_binding(
        admission,
        control,
        route,
        owner,
        criterion,
        execution_binding(),
        provenance=provenance("binding-resolution"),
    )
    skill, action, result = start_and_propose_bound_execution(
        bound,
        owner,
        at_ns=10,
        provenance=provenance("start-and-propose"),
    )

    assert skill.state is SkillState.STARTED
    assert skill.skill_id == "escape-movement"
    assert skill.intent_id == "escape-threat"
    assert action.state is ActionState.PROPOSED
    assert action.skill_execution_id == skill.execution_id
    assert action.intent_id == "escape-threat"
    assert action.events[-1].authority is None
    assert action.events[-1].deadline_ns is None
    assert result.skill_state is SkillState.STARTED
    assert result.action_state is ActionState.PROPOSED
    assert result.action_ref == "MOVE_BACKWARD"
    assert (owner.events, owner.current_intent) == before_intent


def test_binding_mismatch_fails_before_any_owner_transition() -> None:
    owner, route, control, criterion, admission = admitted_chain()
    assert control is not None
    assert admission is not None
    before = (owner.events, owner.current_intent)

    with pytest.raises(
        InvalidExecutionBindingData,
        match="binding candidate_ref",
    ):
        resolve_execution_binding(
            admission,
            control,
            route,
            owner,
            criterion,
            execution_binding(candidate_ref="WAIT"),
            provenance=provenance("bad-binding"),
        )

    assert (owner.events, owner.current_intent) == before


def test_intent_mismatch_fails_before_skill_start() -> None:
    owner, route, control, criterion, admission = admitted_chain()
    assert control is not None
    assert admission is not None
    before = (owner.events, owner.current_intent)

    with pytest.raises(
        InvalidExecutionBindingData,
        match="binding required intent",
    ):
        resolve_execution_binding(
            admission,
            control,
            route,
            owner,
            criterion,
            execution_binding(required_intent_id="hold-position"),
            provenance=provenance("intent-mismatch"),
        )

    assert (owner.events, owner.current_intent) == before


def test_rejected_admission_cannot_resolve_execution_binding() -> None:
    owner, route, control, criterion, admission = admitted_chain(
        allowed=("WAIT",),
    )
    assert control is not None
    assert admission is not None
    assert admission.status is AdmissionDecisionStatus.REJECTED

    with pytest.raises(
        InvalidExecutionBindingData,
        match="ADMITTED",
    ):
        resolve_execution_binding(
            admission,
            control,
            route,
            owner,
            criterion,
            execution_binding(),
            provenance=provenance("rejected-admission"),
        )


def test_s12_conflict_cannot_reach_binding() -> None:
    owner, route, control, criterion, admission = admitted_chain(
        wait_score=1,
        move_score=5,
    )
    assert route.status is RouteDecisionStatus.CONFLICT
    assert control is None
    assert admission is None

    with pytest.raises(
        InvalidExecutionBindingData,
        match="ControlCandidate",
    ):
        resolve_execution_binding(
            AdmissionDecision,  # type: ignore[arg-type]
            None,  # type: ignore[arg-type]
            route,
            owner,
            criterion,
            execution_binding(),
            provenance=provenance("conflict-binding"),
        )


def test_fabricated_admission_lineage_cannot_start_or_propose() -> None:
    owner, route, control, criterion, admission = admitted_chain()
    assert control is not None
    assert admission is not None
    fabricated = AdmissionDecision(
        status=admission.status,
        candidate_ref=admission.candidate_ref,
        route_status=admission.route_status,
        selected_source=admission.selected_source,
        route_criterion_id=admission.route_criterion_id,
        control_criterion_id=admission.control_criterion_id,
        admission_criterion_id=admission.admission_criterion_id,
        current_intent_id=admission.current_intent_id,
        reason=admission.reason,
        control_provenance=admission.control_provenance,
        route_provenance=admission.route_provenance,
        provenance=provenance("fabricated-admission"),
    )
    with pytest.raises(
        InvalidExecutionBindingData,
        match="admission lineage",
    ):
        resolve_execution_binding(
            fabricated,
            control,
            route,
            owner,
            criterion,
            execution_binding(),
            provenance=provenance("fabricated-lineage"),
        )


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("binding_id", ""),
        ("candidate_ref", "MOVE AWAY"),
        ("skill_execution_id", ""),
        ("skill_ref", "escape movement"),
        ("action_id", ""),
        ("action_ref", "MOVE BACKWARD"),
    ),
)
def test_malformed_binding_identifiers_fail_closed(
    field: str,
    value: str,
) -> None:
    kwargs = {
        "binding_id": "binding-move-away-1",
        "candidate_ref": "MOVE_AWAY",
        "required_intent_id": "escape-threat",
        "skill_execution_id": "skill-exec-escape-1",
        "skill_ref": "escape-movement",
        "action_id": "action-move-backward-1",
        "action_ref": "MOVE_BACKWARD",
        "provenance": provenance("binding"),
    }
    kwargs[field] = value
    with pytest.raises(
        InvalidExecutionBindingData,
        match="non-empty|string without whitespace",
    ):
        ExecutionBinding(**kwargs)  # type: ignore[arg-type]


def test_malformed_transition_inputs_fail_before_skill_start() -> None:
    owner, route, control, criterion, admission = admitted_chain()
    assert control is not None
    assert admission is not None
    bound = resolve_execution_binding(
        admission,
        control,
        route,
        owner,
        criterion,
        execution_binding(),
        provenance=provenance("binding-resolution"),
    )
    before = (owner.events, owner.current_intent)

    with pytest.raises(
        InvalidExecutionBindingData,
        match="non-negative integer",
    ):
        start_and_propose_bound_execution(
            bound,
            owner,
            at_ns=-1,
            provenance=provenance("bad-time"),
        )

    with pytest.raises(
        InvalidExecutionBindingData,
        match="Provenance",
    ):
        start_and_propose_bound_execution(
            bound,
            owner,
            at_ns=10,
            provenance=None,  # type: ignore[arg-type]
        )

    assert (owner.events, owner.current_intent) == before


def test_current_intent_change_after_resolution_fails_before_transition() -> None:
    owner, route, control, criterion, admission = admitted_chain()
    assert control is not None
    assert admission is not None
    bound = resolve_execution_binding(
        admission,
        control,
        route,
        owner,
        criterion,
        execution_binding(),
        provenance=provenance("binding-resolution"),
    )
    owner.complete(
        "escape-threat",
        reason="threat gone",
        at_ns=2,
        provenance=provenance("intent-complete"),
    )
    before = owner.events

    with pytest.raises(
        InvalidExecutionBindingData,
        match="current intent",
    ):
        start_and_propose_bound_execution(
            bound,
            owner,
            at_ns=10,
            provenance=provenance("transition-after-release"),
        )

    assert owner.events == before


def test_s14_does_not_accept_existing_skill_or_action_state_objects() -> None:
    parameters = inspect.signature(
        start_and_propose_bound_execution
    ).parameters
    assert "skill_execution" not in parameters
    assert "action_lifecycle" not in parameters
    assert "action" not in parameters

    owner = intent_owner()
    existing_skill = SkillExecution.start(
        "existing-skill",
        skill_id="escape-movement",
        intent_commitment=owner,
        at_ns=2,
        provenance=provenance("existing-skill"),
    ).succeed(
        reason="already terminal",
        at_ns=3,
        provenance=provenance("existing-skill-terminal"),
    )
    existing_action = ActionLifecycle.propose(
        "existing-action",
        skill_execution=SkillExecution.start(
            "existing-action-skill",
            skill_id="other",
            intent_commitment=owner,
            at_ns=2,
            provenance=provenance("existing-action-skill"),
        ),
        intent_commitment=owner,
        at_ns=3,
        provenance=provenance("existing-action-proposed"),
    )
    assert existing_skill.state is SkillState.SUCCEEDED
    assert existing_action.state is ActionState.PROPOSED


def test_provider_expression_cannot_be_execution_binding() -> None:
    owner, route, control, criterion, admission = admitted_chain()
    assert control is not None
    assert admission is not None
    expression = ProviderExpression(
        text="Use the escape skill.",
        provenance=provenance("provider-binding"),
    )
    with pytest.raises(
        InvalidExecutionBindingData,
        match="ExecutionBinding",
    ):
        resolve_execution_binding(
            admission,
            control,
            route,
            owner,
            criterion,
            expression,  # type: ignore[arg-type]
            provenance=provenance("provider-not-binding"),
        )


def test_exec_bind_off_preserves_admission_without_skill_or_action() -> None:
    box: dict[str, object] = {}
    owner, route, control, criterion, _ = admitted_chain()
    assert control is not None

    def admission_work() -> None:
        box["admission"] = admit_control_candidate(
            control,
            route,
            owner,
            criterion,
            provenance=provenance("admission:epoch"),
        )

    binding = EpochBinding(
        "admission-1",
        "execution.admit_candidate",
        admission_work,
    )
    epoch = compile_epoch_plan(
        s13_admission_profile(AdmissionProfileId.ROUTE_ADMISSION).plan(),
        S14_DESCRIPTOR_SET,
        due_items=(
            EpochWorkItem(
                "admission-1",
                "execution.admit_candidate",
                "control-ready",
            ),
            EpochWorkItem(
                "binding-1",
                "execution.resolve_binding",
                "exec-bind-disabled",
            ),
            EpochWorkItem(
                "transition-1",
                "execution.start_and_propose",
                "exec-bind-disabled",
            ),
        ),
        bindings=(binding,),
    )
    result = coordinate_planned_epoch(
        ActionSupervisor(),
        epoch,
        bindings=(binding,),
        at_ns=10,
        provenance=provenance("epoch:exec-bind-off"),
    )
    assert box["admission"].status is AdmissionDecisionStatus.ADMITTED
    assert "bound" not in box
    assert "skill" not in box
    assert "action" not in box
    assert result.executed_work_ids == ("admission-1",)
    assert result.suppressed_work_ids == ("binding-1", "transition-1")


def test_missing_exec_bind_epoch_binding_fails_closed() -> None:
    with pytest.raises(MissingEpochBinding, match="binding-1"):
        compile_epoch_plan(
            s14_execution_binding_profile(
                ExecutionBindingProfileId.EXEC_BIND
            ).plan(),
            S14_DESCRIPTOR_SET,
            due_items=(
                EpochWorkItem(
                    "binding-1",
                    "execution.resolve_binding",
                    "explicit-binding-due",
                ),
            ),
            bindings=(),
        )


def test_action_supervisor_deadline_is_serviced_before_transition_work() -> None:
    owner, route, control, criterion, admission = admitted_chain()
    assert control is not None
    assert admission is not None
    bound = resolve_execution_binding(
        admission,
        control,
        route,
        owner,
        criterion,
        execution_binding(),
        provenance=provenance("binding-resolution"),
    )

    supervised_skill = SkillExecution.start(
        "supervised-skill",
        skill_id="WAIT",
        intent_commitment=owner,
        at_ns=2,
        provenance=provenance("supervised-skill"),
    )
    supervised_action = ActionLifecycle.propose(
        "supervised-action",
        skill_execution=supervised_skill,
        intent_commitment=owner,
        at_ns=3,
        provenance=provenance("supervised-action"),
    ).authorize(
        at_ns=4,
        provenance=provenance("supervised-authorized"),
        authority="explicit-authority",
    )
    supervisor = ActionSupervisor()
    supervisor.issue(
        supervised_action,
        at_ns=5,
        deadline_ns=9,
        provenance=provenance("supervised-issued"),
    )

    box: dict[str, object] = {}

    def transition_work() -> None:
        assert supervisor.get("supervised-action").state is ActionState.TIMEOUT
        skill, action, result = start_and_propose_bound_execution(
            bound,
            owner,
            at_ns=10,
            provenance=provenance("transition-after-supervision"),
        )
        box["skill"] = skill
        box["action"] = action
        box["result"] = result

    binding = EpochBinding(
        "transition-1",
        "execution.start_and_propose",
        transition_work,
    )
    epoch = compile_epoch_plan(
        s14_execution_binding_profile(
            ExecutionBindingProfileId.EXEC_BIND
        ).plan(),
        S14_DESCRIPTOR_SET,
        due_items=(
            EpochWorkItem(
                "transition-1",
                "execution.start_and_propose",
                "bound-candidate-ready",
            ),
        ),
        bindings=(binding,),
    )
    epoch_result = coordinate_planned_epoch(
        supervisor,
        epoch,
        bindings=(binding,),
        at_ns=10,
        provenance=provenance("epoch:supervision-first"),
    )
    assert epoch_result.timed_out_actions[0].state is ActionState.TIMEOUT
    assert box["skill"].state is SkillState.STARTED
    assert box["action"].state is ActionState.PROPOSED


def test_full_deterministic_path_reaches_proposed_with_zero_provider_calls() -> None:
    box: dict[str, object] = {}
    invocations = {
        "ATT": 0,
        "BLF": 0,
        "CNC": 0,
        "PRD": 0,
        "PLAN": 0,
        "HABIT": 0,
        "ROUTE": 0,
        "ADMISSION": 0,
        "EXEC_BIND": 0,
        "PROVIDER": 0,
    }
    owner = intent_owner()
    before_intent = (owner.events, owner.current_intent)
    proposition = PropositionKey("entity", "zombie-1", "nearby")
    evidence = BeliefEvidence(
        "E1",
        proposition,
        EvidenceRelation.SUPPORT,
        provenance("evidence:E1"),
    )

    def attend() -> None:
        invocations["ATT"] += 1
        box["attention"] = select_attention(
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

    def believe() -> None:
        invocations["BLF"] += 1
        selection = require_attention_selection(box.get("attention"))
        assert selection.candidate_ids == ("E1",)
        box["belief"] = assess_belief(
            (evidence,),
            BeliefCriterion("zombie-nearby", proposition),
        )

    def conceptualize() -> None:
        invocations["CNC"] += 1
        source = concept_candidate_from_belief(
            box.get("belief"),
            candidate_id="belief:zombie-nearby",
            payload_ref="transient:belief:zombie-nearby",
            provenance=provenance("belief-to-concept"),
        )
        box["concept"] = classify_concept(
            source,
            ConceptCriterion(
                criterion_id="supported-nearby",
                concept=ConceptKey("spatial", "nearby_threat"),
                required_features=(
                    ConceptFeature("belief_status", "supported"),
                    ConceptFeature("proposition", proposition.canonical),
                ),
            ),
        )

    def prediction_base():
        return prediction_state_from_concept(
            box.get("concept"),
            state_id="threat:zombie-1",
            extra_variables=(StateVariable("comparison_score", 99),),
            provenance=provenance("concept-to-prediction"),
        )

    def predict_wait() -> None:
        invocations["PRD"] += 1
        box["wait_prediction"] = predict_transition(
            prediction_base(),
            TransitionRule(
                rule_id="wait",
                preconditions=(
                    StateVariable("concept", "spatial:nearby_threat"),
                ),
                assignments=(StateVariable("comparison_score", 8),),
                provenance=provenance("rule:wait"),
            ),
        )

    def predict_move() -> None:
        invocations["PRD"] += 1
        box["move_prediction"] = predict_transition(
            prediction_base(),
            TransitionRule(
                rule_id="move-away",
                preconditions=(
                    StateVariable("concept", "spatial:nearby_threat"),
                ),
                assignments=(StateVariable("comparison_score", 3),),
                provenance=provenance("rule:move-away"),
            ),
        )

    def choose_plan() -> None:
        invocations["PLAN"] += 1
        wait = plan_candidate_from_prediction(
            box.get("wait_prediction"),
            candidate_id="WAIT",
            feature_keys=("comparison_score",),
            provenance=provenance("prediction-to-plan:wait"),
        )
        move = plan_candidate_from_prediction(
            box.get("move_prediction"),
            candidate_id="MOVE_AWAY",
            feature_keys=("comparison_score",),
            provenance=provenance("prediction-to-plan:move"),
        )
        box["plan"] = select_plan(
            (wait, move),
            PlanningCriterion(
                criterion_id="minimize-comparison-score",
                feature_key="comparison_score",
                direction=PlanningDirection.MINIMIZE,
            ),
        )

    def choose_habit() -> None:
        invocations["HABIT"] += 1
        concept = box["concept"]
        assert isinstance(concept, ConceptRepresentation)
        box["habit"] = select_habit(
            habit_repertoire(),
            HabitCue(
                cue_id="concept-nearby-threat",
                features=(
                    CueFeature("concept", concept.concept.canonical),
                ),
                provenance=provenance("concept-to-habit-cue"),
            ),
        )

    def route_work() -> None:
        invocations["ROUTE"] += 1
        route = adjudicate_routes(
            box.get("plan"),  # type: ignore[arg-type]
            box.get("habit"),  # type: ignore[arg-type]
            route_criterion(),
            provenance=provenance("route:full"),
        )
        box["route"] = route
        box["control"] = control_candidate_from_route_decision(route)

    def admission_work() -> None:
        invocations["ADMISSION"] += 1
        box["admission_criterion"] = admission_criterion("MOVE_AWAY")
        box["admission"] = admit_control_candidate(
            box.get("control"),  # type: ignore[arg-type]
            box.get("route"),  # type: ignore[arg-type]
            owner,
            box["admission_criterion"],  # type: ignore[arg-type]
            provenance=provenance("admission:full"),
        )

    def resolve_work() -> None:
        invocations["EXEC_BIND"] += 1
        box["bound"] = resolve_execution_binding(
            box.get("admission"),  # type: ignore[arg-type]
            box.get("control"),  # type: ignore[arg-type]
            box.get("route"),  # type: ignore[arg-type]
            owner,
            box.get("admission_criterion"),  # type: ignore[arg-type]
            execution_binding(),
            provenance=provenance("binding:full"),
        )

    def transition_work() -> None:
        invocations["EXEC_BIND"] += 1
        skill, action, result = start_and_propose_bound_execution(
            box.get("bound"),  # type: ignore[arg-type]
            owner,
            at_ns=10,
            provenance=provenance("transition:full"),
        )
        box["skill"] = skill
        box["action"] = action
        box["binding_result"] = result

    bindings = (
        EpochBinding("att-1", "att.select", attend),
        EpochBinding("blf-1", "blf.assess", believe),
        EpochBinding("cnc-1", "cnc.classify", conceptualize),
        EpochBinding("prd-wait", "prd.predict", predict_wait),
        EpochBinding("prd-move", "prd.predict", predict_move),
        EpochBinding("plan-1", "plan.select", choose_plan),
        EpochBinding("habit-1", "habit.select", choose_habit),
        EpochBinding("route-1", "route.adjudicate", route_work),
        EpochBinding(
            "admission-1",
            "execution.admit_candidate",
            admission_work,
        ),
        EpochBinding(
            "binding-1",
            "execution.resolve_binding",
            resolve_work,
        ),
        EpochBinding(
            "transition-1",
            "execution.start_and_propose",
            transition_work,
        ),
    )
    epoch = compile_epoch_plan(
        s14_execution_binding_profile(
            ExecutionBindingProfileId.FULL_DETERMINISTIC_EXECUTION_BINDING
        ).plan(),
        S14_DESCRIPTOR_SET,
        due_items=(
            EpochWorkItem("att-1", "att.select", "evidence-ready"),
            EpochWorkItem("blf-1", "blf.assess", "attention-ready"),
            EpochWorkItem("cnc-1", "cnc.classify", "belief-ready"),
            EpochWorkItem("prd-wait", "prd.predict", "concept-ready-wait"),
            EpochWorkItem("prd-move", "prd.predict", "concept-ready-move"),
            EpochWorkItem("plan-1", "plan.select", "predictions-ready"),
            EpochWorkItem("habit-1", "habit.select", "concept-ready-habit"),
            EpochWorkItem("route-1", "route.adjudicate", "routes-ready"),
            EpochWorkItem(
                "admission-1",
                "execution.admit_candidate",
                "control-ready",
            ),
            EpochWorkItem(
                "binding-1",
                "execution.resolve_binding",
                "admission-ready",
            ),
            EpochWorkItem(
                "transition-1",
                "execution.start_and_propose",
                "binding-ready",
            ),
        ),
        bindings=bindings,
    )
    epoch_result = coordinate_planned_epoch(
        ActionSupervisor(),
        epoch,
        bindings=bindings,
        at_ns=10,
        provenance=provenance("epoch:full"),
    )

    assert box["route"].status is RouteDecisionStatus.AGREED
    assert box["admission"].status is AdmissionDecisionStatus.ADMITTED
    assert box["skill"].state is SkillState.STARTED
    assert box["action"].state is ActionState.PROPOSED
    assert box["action"].events[-1].authority is None
    assert box["action"].events[-1].deadline_ns is None
    assert (owner.events, owner.current_intent) == before_intent
    assert invocations == {
        "ATT": 1,
        "BLF": 1,
        "CNC": 1,
        "PRD": 2,
        "PLAN": 1,
        "HABIT": 1,
        "ROUTE": 1,
        "ADMISSION": 1,
        "EXEC_BIND": 2,
        "PROVIDER": 0,
    }
    assert epoch_result.cognition_requested is False
    assert epoch_result.cognition_result is None


def test_success_changes_only_skill_and_action_authority_boundary() -> None:
    cognition = PersistentCognition(
        identity=identity(),
        memories=(memory("existing"),),
    )
    learned = LearningPreferenceState(
        target_id="risk_weight",
        value=3,
        minimum=0,
        maximum=10,
        revision=0,
        origin_provenance=provenance("learning-origin"),
    )
    (
        attention,
        belief,
        concept,
        wait_prediction,
        move_prediction,
        plan,
        habit,
    ) = full_upstream()
    owner = intent_owner()
    intent_before = (owner.events, owner.current_intent)
    route = adjudicate_routes(
        plan,
        habit,
        route_criterion(),
        provenance=provenance("route:authority-negative"),
    )
    control = control_candidate_from_route_decision(route)
    assert control is not None
    criterion = admission_criterion("MOVE_AWAY")
    admission = admit_control_candidate(
        control,
        route,
        owner,
        criterion,
        provenance=provenance("admission:authority-negative"),
    )
    before = (
        cognition,
        cognition.memories,
        attention,
        belief,
        concept,
        wait_prediction,
        move_prediction,
        plan,
        learned,
        habit.repertoire,
        habit,
        route,
        control,
        admission,
    )
    bound = resolve_execution_binding(
        admission,
        control,
        route,
        owner,
        criterion,
        execution_binding(),
        provenance=provenance("binding:authority-negative"),
    )
    skill, action, result = start_and_propose_bound_execution(
        bound,
        owner,
        at_ns=10,
        provenance=provenance("transition:authority-negative"),
    )

    assert skill.state is SkillState.STARTED
    assert action.state is ActionState.PROPOSED
    assert action.events[-1].authority is None
    assert action.events[-1].deadline_ns is None
    assert result.skill_state is SkillState.STARTED
    assert result.action_state is ActionState.PROPOSED
    assert (owner.events, owner.current_intent) == intent_before
    assert cognition == before[0]
    assert cognition.memories == before[1]
    assert attention == before[2]
    assert belief == before[3]
    assert belief.status is BeliefStatus.SUPPORTED
    assert concept == before[4]
    assert concept.status is ConceptStatus.MATCHED
    assert wait_prediction == before[5]
    assert move_prediction == before[6]
    assert plan == before[7]
    assert learned == before[8]
    assert habit.repertoire == before[9]
    assert habit == before[10]
    assert route == before[11]
    assert control == before[12]
    assert admission == before[13]

    with pytest.raises(InvalidLearningData, match="LearningFeedback"):
        propose_learning_update(
            learned,
            result,  # type: ignore[arg-type]
            LearningUpdateRule(
                rule_id="bounded-step",
                version=1,
                step=1,
            ),
        )


def test_result_is_immutable_and_no_central_owner_is_added() -> None:
    owner, route, control, criterion, admission = admitted_chain()
    assert control is not None
    assert admission is not None
    bound = resolve_execution_binding(
        admission,
        control,
        route,
        owner,
        criterion,
        execution_binding(),
        provenance=provenance("binding-resolution"),
    )
    _, _, result = start_and_propose_bound_execution(
        bound,
        owner,
        at_ns=10,
        provenance=provenance("transition"),
    )
    with pytest.raises(FrozenInstanceError):
        result.action_state = ActionState.AUTHORIZED  # type: ignore[misc]

    forbidden = {
        "intent_commitment",
        "skill_execution",
        "action_lifecycle",
        "action_supervisor",
        "authorization",
        "scheduler",
        "deadline",
        "learning",
        "memory",
        "world",
        "callback",
        "registry",
    }
    assert forbidden.isdisjoint(ExecutionBindingResult.__dataclass_fields__)
    assert S14_EXEC_BIND_CAPABILITY_SPEC.state_scopes == ()
    assert (
        S14_EXEC_BIND_RESOLVE_OPERATOR_DESCRIPTOR.hidden_persistent_state
        is False
    )
    assert (
        S14_EXEC_BIND_TRANSITION_OPERATOR_DESCRIPTOR.hidden_persistent_state
        is False
    )
