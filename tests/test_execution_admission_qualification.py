from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

import relay_self
from relay_self.action import ActionLifecycle, ActionState
from relay_self.action_supervision import ActionSupervisor
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
    AdmissionReason,
    ExecutionAdmissionCriterion,
    InvalidExecutionAdmissionData,
    admit_control_candidate,
)
from relay_self.execution_descriptor import (
    S13_ADMISSION_CAPABILITY_SPEC,
    S13_ADMISSION_CRITERION_DESCRIPTOR,
    S13_ADMISSION_OPERATOR_DESCRIPTOR,
    S13_DESCRIPTOR_SET,
    CriterionKind,
    OperatorEffect,
    s13_capability_plan,
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
    InvalidRouteData,
    RouteConflictPolicy,
    RouteCriterion,
    RouteDecision,
    RouteDecisionStatus,
    RouteSource,
    adjudicate_routes,
    control_candidate_from_route_decision,
)
from relay_self.admission_profile import (
    S13_ADMISSION_PROFILES,
    AdmissionProfileId,
    s13_admission_profile,
)
from relay_self.skill import SkillExecution, SkillState


def provenance(reference: str) -> Provenance:
    return Provenance(
        source="s13-execution-admission-qualification",
        reference=reference,
    )


def committed_intent(intent_id: str = "escape-threat") -> IntentCommitment:
    owner = IntentCommitment()
    owner.commit(
        intent_id,
        objective=f"objective:{intent_id}",
        at_ns=1,
        provenance=provenance(f"intent:{intent_id}"),
    )
    return owner


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


def habit_repertoire(
    *,
    candidate_ref: str = "MOVE_AWAY",
) -> HabitRepertoire:
    return HabitRepertoire(
        repertoire_id="survival-habits",
        revision=7,
        rules=(
            HabitRule(
                habit_id="H1",
                cue_requirements=(
                    CueFeature("concept", "spatial:nearby_threat"),
                ),
                candidate_ref=candidate_ref,
                priority=10,
                provenance=provenance("habit:H1"),
            ),
        ),
        provenance=provenance("habit-repertoire"),
    )


def habit_selection(
    *,
    candidate_ref: str = "MOVE_AWAY",
    no_match: bool = False,
) -> HabitSelection:
    cue = HabitCue(
        cue_id="nearby-threat",
        features=(
            CueFeature(
                "concept",
                "spatial:other" if no_match else "spatial:nearby_threat",
            ),
        ),
        provenance=provenance("habit-cue"),
    )
    return select_habit(
        habit_repertoire(candidate_ref=candidate_ref),
        cue,
    )


def route_agreement() -> tuple[RouteDecision, ControlCandidate]:
    decision = adjudicate_routes(
        plan_selection(),
        habit_selection(),
        RouteCriterion(
            criterion_id="route-fail-closed",
            conflict_policy=RouteConflictPolicy.FAIL_CLOSED,
        ),
        provenance=provenance("route:agreement"),
    )
    candidate = control_candidate_from_route_decision(decision)
    assert candidate is not None
    return decision, candidate


def route_conflict() -> RouteDecision:
    return adjudicate_routes(
        plan_selection(wait_score=1, move_score=5),
        habit_selection(),
        RouteCriterion(
            criterion_id="route-fail-closed",
            conflict_policy=RouteConflictPolicy.FAIL_CLOSED,
        ),
        provenance=provenance("route:conflict"),
    )


def identity() -> IdentitySpecification:
    return IdentitySpecification(
        self_id="self-s13",
        directives=("admission never transfers execution authority",),
        provenance=provenance("identity"),
    )


def memory(memory_id: str) -> Memory:
    return Memory(
        memory_id=memory_id,
        content=f"memory:{memory_id}",
        source_provenance=provenance(f"memory-source:{memory_id}"),
        integration_provenance=provenance(f"memory-integration:{memory_id}"),
    )


def full_upstream(
    *,
    wait_score: int = 8,
    move_score: int = 3,
) -> tuple[
    AttentionSelection,
    BeliefAssessment,
    ConceptRepresentation,
    PredictionResult,
    PredictionResult,
    PlanSelection,
    HabitSelection,
    RouteDecision,
    ControlCandidate | None,
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
    selected = require_attention_selection(attention)
    belief = assess_belief(
        tuple(evidence for _ in selected.selected),
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
    route = adjudicate_routes(
        plan,
        habit,
        RouteCriterion(
            criterion_id="route-fail-closed",
            conflict_policy=RouteConflictPolicy.FAIL_CLOSED,
        ),
        provenance=provenance("route:full-upstream"),
    )
    control = control_candidate_from_route_decision(route)
    return (
        attention,
        belief,
        concept,
        wait_prediction,
        move_prediction,
        plan,
        habit,
        route,
        control,
    )


def test_package_exports_s13_admission_surface() -> None:
    assert relay_self.AdmissionDecision is AdmissionDecision
    assert relay_self.AdmissionDecisionStatus is AdmissionDecisionStatus
    assert relay_self.AdmissionPolicy is AdmissionPolicy
    assert relay_self.AdmissionReason is AdmissionReason
    assert relay_self.ExecutionAdmissionCriterion is ExecutionAdmissionCriterion
    assert relay_self.admit_control_candidate is admit_control_candidate
    assert relay_self.AdmissionProfileId is AdmissionProfileId
    assert relay_self.S13_ADMISSION_PROFILES is S13_ADMISSION_PROFILES


def test_admission_descriptor_is_contract_guard_and_stateless_metadata() -> None:
    assert S13_ADMISSION_CAPABILITY_SPEC.capability_id == "ADMISSION"
    assert S13_ADMISSION_CAPABILITY_SPEC.state_scopes == ()
    assert S13_ADMISSION_CAPABILITY_SPEC.dependencies == ()
    assert (
        S13_ADMISSION_OPERATOR_DESCRIPTOR.operator_id
        == "execution.admit_candidate"
    )
    assert S13_ADMISSION_OPERATOR_DESCRIPTOR.effect is OperatorEffect.READ_ONLY
    assert S13_ADMISSION_OPERATOR_DESCRIPTOR.hidden_persistent_state is False
    assert S13_ADMISSION_OPERATOR_DESCRIPTOR.writes == (
        "transient.admission_decision",
    )
    assert (
        S13_ADMISSION_CRITERION_DESCRIPTOR.kind
        is CriterionKind.CONTRACT_GUARD
    )


def test_admission_profiles_are_explicit_integration_metadata() -> None:
    assert [profile.profile_id for profile in S13_ADMISSION_PROFILES] == [
        AdmissionProfileId.ADMISSION,
        AdmissionProfileId.ROUTE_ADMISSION,
        AdmissionProfileId.PLAN_HABIT_ROUTE_ADMISSION,
        AdmissionProfileId.FULL_DETERMINISTIC_ADMISSION,
    ]
    assert s13_admission_profile(
        AdmissionProfileId.ROUTE_ADMISSION
    ).enabled_ids == frozenset({"ROUTE", "ADMISSION"})


def test_valid_control_candidate_is_explicitly_admitted() -> None:
    route, control = route_agreement()
    intent = committed_intent()
    before_events = intent.events
    before_current = intent.current_intent
    decision = admit_control_candidate(
        control,
        route,
        intent,
        admission_criterion("MOVE_AWAY"),
        provenance=provenance("admission:allowed"),
    )
    assert decision.status is AdmissionDecisionStatus.ADMITTED
    assert decision.reason is AdmissionReason.ADMITTED
    assert decision.candidate_ref == "MOVE_AWAY"
    assert decision.route_status is RouteDecisionStatus.AGREED
    assert decision.current_intent_id == "escape-threat"
    assert intent.events == before_events
    assert intent.current_intent == before_current


def test_candidate_disallowed_by_explicit_guard_is_rejected() -> None:
    route, control = route_agreement()
    intent = committed_intent()
    decision = admit_control_candidate(
        control,
        route,
        intent,
        admission_criterion("WAIT"),
        provenance=provenance("admission:disallowed"),
    )
    assert decision.status is AdmissionDecisionStatus.REJECTED
    assert decision.reason is AdmissionReason.CANDIDATE_NOT_ALLOWED
    assert decision.candidate_ref == "MOVE_AWAY"
    assert intent.current_intent is not None
    assert intent.current_intent.intent_id == "escape-threat"


def test_current_intent_mismatch_is_rejected_without_rewrite() -> None:
    route, control = route_agreement()
    intent = committed_intent("hold-position")
    before = (intent.events, intent.current_intent)
    decision = admit_control_candidate(
        control,
        route,
        intent,
        admission_criterion(
            "MOVE_AWAY",
            required_intent_id="escape-threat",
        ),
        provenance=provenance("admission:intent-mismatch"),
    )
    assert decision.status is AdmissionDecisionStatus.REJECTED
    assert decision.reason is AdmissionReason.CURRENT_INTENT_MISMATCH
    assert decision.current_intent_id == "hold-position"
    assert (intent.events, intent.current_intent) == before


@pytest.mark.parametrize("owner", (None, IntentCommitment()))
def test_missing_current_intent_is_undetermined_not_admitted(
    owner: IntentCommitment | None,
) -> None:
    route, control = route_agreement()
    decision = admit_control_candidate(
        control,
        route,
        owner,
        admission_criterion("MOVE_AWAY"),
        provenance=provenance("admission:missing-intent"),
    )
    assert decision.status is AdmissionDecisionStatus.UNDETERMINED
    assert decision.reason is AdmissionReason.MISSING_CURRENT_INTENT
    assert decision.current_intent_id is None


def test_s12_conflict_has_no_candidate_and_cannot_be_overridden_by_admission() -> None:
    conflict = route_conflict()
    assert conflict.status is RouteDecisionStatus.CONFLICT
    assert control_candidate_from_route_decision(conflict) is None

    with pytest.raises(InvalidExecutionAdmissionData, match="ControlCandidate"):
        admit_control_candidate(
            None,  # type: ignore[arg-type]
            conflict,
            committed_intent(),
            admission_criterion("MOVE_AWAY"),
            provenance=provenance("admission:conflict-none"),
        )

    agreement_route, agreement_control = route_agreement()
    fabricated = ControlCandidate(
        candidate_ref=agreement_control.candidate_ref,
        route_status=agreement_control.route_status,
        selected_source=agreement_control.selected_source,
        criterion_id=agreement_control.criterion_id,
        plan_candidate_ref=agreement_control.plan_candidate_ref,
        habit_candidate_ref=agreement_control.habit_candidate_ref,
        provenance=agreement_control.provenance,
    )
    assert agreement_route.status is RouteDecisionStatus.AGREED
    decision = admit_control_candidate(
        fabricated,
        conflict,
        committed_intent(),
        admission_criterion("MOVE_AWAY"),
        provenance=provenance("admission:conflict-fabricated"),
    )
    assert decision.status is AdmissionDecisionStatus.REJECTED
    assert decision.reason is AdmissionReason.ROUTE_NOT_ADMISSIBLE


def test_no_candidate_and_undetermined_route_cannot_be_admitted() -> None:
    no_candidate = adjudicate_routes(
        plan_selection(wait_score=3, move_score=3),
        habit_selection(no_match=True),
        RouteCriterion(
            criterion_id="route-fail-closed",
            conflict_policy=RouteConflictPolicy.FAIL_CLOSED,
        ),
        provenance=provenance("route:no-candidate"),
    )
    assert no_candidate.status is RouteDecisionStatus.NO_CANDIDATE

    selected_plan = plan_selection()
    undetermined = adjudicate_routes(
        selected_plan,
        None,
        RouteCriterion(
            criterion_id="route-require-two",
            conflict_policy=RouteConflictPolicy.FAIL_CLOSED,
            allow_single_source=False,
        ),
        provenance=provenance("route:undetermined"),
    )
    assert undetermined.status is RouteDecisionStatus.UNDETERMINED

    _, valid_control = route_agreement()
    for route in (no_candidate, undetermined):
        decision = admit_control_candidate(
            valid_control,
            route,
            committed_intent(),
            admission_criterion("MOVE_AWAY"),
            provenance=provenance(f"admission:{route.status.value}"),
        )
        assert decision.status is AdmissionDecisionStatus.REJECTED
        assert decision.reason is AdmissionReason.ROUTE_NOT_ADMISSIBLE


def test_control_candidate_source_or_provenance_mismatch_is_rejected() -> None:
    route, control = route_agreement()
    mismatched = ControlCandidate(
        candidate_ref=control.candidate_ref,
        route_status=control.route_status,
        selected_source=control.selected_source,
        criterion_id=control.criterion_id,
        plan_candidate_ref=control.plan_candidate_ref,
        habit_candidate_ref=control.habit_candidate_ref,
        provenance=provenance("fabricated-control-provenance"),
    )
    decision = admit_control_candidate(
        mismatched,
        route,
        committed_intent(),
        admission_criterion("MOVE_AWAY"),
        provenance=provenance("admission:control-mismatch"),
    )
    assert decision.status is AdmissionDecisionStatus.REJECTED
    assert decision.reason is AdmissionReason.CONTROL_ROUTE_MISMATCH


def test_malformed_admission_inputs_fail_closed() -> None:
    with pytest.raises(InvalidExecutionAdmissionData, match="criterion_id"):
        ExecutionAdmissionCriterion(
            criterion_id="",
            policy=AdmissionPolicy.CURRENT_INTENT_ALLOW_LIST,
            required_intent_id="escape-threat",
            allowed_candidate_refs=("MOVE_AWAY",),
        )
    with pytest.raises(InvalidExecutionAdmissionData, match="AdmissionPolicy"):
        ExecutionAdmissionCriterion(
            criterion_id="bad-policy",
            policy="allow_any",  # type: ignore[arg-type]
            required_intent_id="escape-threat",
            allowed_candidate_refs=("MOVE_AWAY",),
        )
    with pytest.raises(
        InvalidExecutionAdmissionData,
        match="must not be empty",
    ):
        ExecutionAdmissionCriterion(
            criterion_id="empty-allow-list",
            policy=AdmissionPolicy.CURRENT_INTENT_ALLOW_LIST,
            required_intent_id="escape-threat",
            allowed_candidate_refs=(),
        )
    with pytest.raises(InvalidRouteData, match="non-empty string"):
        ControlCandidate(
            candidate_ref="",
            route_status=RouteDecisionStatus.SELECTED,
            selected_source=RouteSource.PLAN,
            criterion_id="route",
            plan_candidate_ref="MOVE_AWAY",
            habit_candidate_ref=None,
            provenance=provenance("bad-control"),
        )


def test_provider_text_cannot_grant_admission_or_replace_authority() -> None:
    route, control = route_agreement()
    expression = ProviderExpression(
        text="Yes, do it.",
        provenance=provenance("provider-permission"),
    )
    with pytest.raises(
        InvalidExecutionAdmissionData,
        match="ExecutionAdmissionCriterion",
    ):
        admit_control_candidate(
            control,
            route,
            committed_intent(),
            expression,  # type: ignore[arg-type]
            provenance=provenance("admission:provider-criterion"),
        )
    with pytest.raises(
        InvalidExecutionAdmissionData,
        match="IntentCommitment",
    ):
        admit_control_candidate(
            control,
            route,
            expression,  # type: ignore[arg-type]
            admission_criterion("MOVE_AWAY"),
            provenance=provenance("admission:provider-authority"),
        )


def test_admission_off_suppresses_only_admission_after_route_candidate_exists() -> None:
    box: dict[str, object] = {}
    plan = plan_selection()
    habit = habit_selection()

    def route_work() -> None:
        route = adjudicate_routes(
            plan,
            habit,
            RouteCriterion(
                criterion_id="route-fail-closed",
                conflict_policy=RouteConflictPolicy.FAIL_CLOSED,
            ),
            provenance=provenance("route:epoch"),
        )
        box["route"] = route
        box["control"] = control_candidate_from_route_decision(route)

    binding = EpochBinding("route-1", "route.adjudicate", route_work)
    epoch = compile_epoch_plan(
        s13_capability_plan(enabled_ids=frozenset({"ROUTE"})),
        S13_DESCRIPTOR_SET,
        due_items=(
            EpochWorkItem("route-1", "route.adjudicate", "routes-ready"),
            EpochWorkItem(
                "admission-1",
                "execution.admit_candidate",
                "admission-disabled",
            ),
        ),
        bindings=(binding,),
    )
    result = coordinate_planned_epoch(
        ActionSupervisor(),
        epoch,
        bindings=(binding,),
        at_ns=10,
        provenance=provenance("epoch:admission-off"),
    )
    assert isinstance(box["route"], RouteDecision)
    assert isinstance(box["control"], ControlCandidate)
    assert "admission" not in box
    assert result.executed_work_ids == ("route-1",)
    assert result.suppressed_work_ids == ("admission-1",)
    assert result.cognition_requested is False


def test_enabled_admission_requires_exact_explicit_epoch_binding() -> None:
    with pytest.raises(MissingEpochBinding, match="admission-1"):
        compile_epoch_plan(
            s13_capability_plan(enabled_ids=frozenset({"ADMISSION"})),
            S13_DESCRIPTOR_SET,
            due_items=(
                EpochWorkItem(
                    "admission-1",
                    "execution.admit_candidate",
                    "explicit-admission",
                ),
            ),
            bindings=(),
        )


def test_action_supervision_deadline_is_serviced_before_admission_work() -> None:
    intent = committed_intent()
    skill = SkillExecution.start(
        "skill-supervised",
        skill_id="WAIT",
        intent_commitment=intent,
        at_ns=2,
        provenance=provenance("skill-supervised"),
    )
    action = ActionLifecycle.propose(
        "action-supervised",
        skill_execution=skill,
        intent_commitment=intent,
        at_ns=3,
        provenance=provenance("action-proposed"),
    ).authorize(
        at_ns=4,
        provenance=provenance("action-authorized"),
        authority="explicit-authority",
    )
    supervisor = ActionSupervisor()
    supervisor.issue(
        action,
        at_ns=5,
        deadline_ns=9,
        provenance=provenance("action-issued"),
    )
    route, control = route_agreement()
    box: dict[str, object] = {}

    def admission_work() -> None:
        assert supervisor.get("action-supervised").state is ActionState.TIMEOUT
        box["admission"] = admit_control_candidate(
            control,
            route,
            intent,
            admission_criterion("MOVE_AWAY"),
            provenance=provenance("admission:after-supervision"),
        )

    binding = EpochBinding(
        "admission-1",
        "execution.admit_candidate",
        admission_work,
    )
    epoch = compile_epoch_plan(
        s13_capability_plan(enabled_ids=frozenset({"ADMISSION"})),
        S13_DESCRIPTOR_SET,
        due_items=(
            EpochWorkItem(
                "admission-1",
                "execution.admit_candidate",
                "control-candidate-ready",
            ),
        ),
        bindings=(binding,),
    )
    result = coordinate_planned_epoch(
        supervisor,
        epoch,
        bindings=(binding,),
        at_ns=10,
        provenance=provenance("epoch:supervision-first"),
    )
    assert result.timed_out_actions[0].state is ActionState.TIMEOUT
    assert box["admission"].status is AdmissionDecisionStatus.ADMITTED


def test_full_deterministic_route_to_admission_uses_zero_provider_calls() -> None:
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
        "PROVIDER": 0,
    }
    intent = committed_intent()
    intent_before = (intent.events, intent.current_intent)
    proposition = PropositionKey("entity", "zombie-1", "nearby")
    evidence = BeliefEvidence(
        "E1",
        proposition,
        EvidenceRelation.SUPPORT,
        provenance("evidence:E1"),
    )
    attention_candidates = (
        AttentionCandidate(
            "E1",
            "belief-evidence:E1",
            provenance("attention:E1"),
            focus_keys=("zombie-1",),
        ),
    )

    def attend() -> None:
        invocations["ATT"] += 1
        box["attention"] = select_attention(
            attention_candidates,
            AttentionCriterion("focus-zombie", focus_key="zombie-1"),
        )

    def believe() -> None:
        invocations["BLF"] += 1
        selected = require_attention_selection(box.get("attention"))
        assert selected.candidate_ids == ("E1",)
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
            RouteCriterion(
                criterion_id="route-fail-closed",
                conflict_policy=RouteConflictPolicy.FAIL_CLOSED,
            ),
            provenance=provenance("route:full-chain"),
        )
        box["route"] = route
        box["control"] = control_candidate_from_route_decision(route)

    def admission_work() -> None:
        invocations["ADMISSION"] += 1
        box["admission"] = admit_control_candidate(
            box.get("control"),  # type: ignore[arg-type]
            box.get("route"),  # type: ignore[arg-type]
            intent,
            admission_criterion("MOVE_AWAY"),
            provenance=provenance("admission:full-chain"),
        )

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
    )
    epoch = compile_epoch_plan(
        s13_admission_profile(
            AdmissionProfileId.FULL_DETERMINISTIC_ADMISSION
        ).plan(),
        S13_DESCRIPTOR_SET,
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
        ),
        bindings=bindings,
    )
    result = coordinate_planned_epoch(
        ActionSupervisor(),
        epoch,
        bindings=bindings,
        at_ns=10,
        provenance=provenance("epoch:full-admission"),
    )

    assert box["route"].status is RouteDecisionStatus.AGREED
    assert box["control"].candidate_ref == "MOVE_AWAY"
    assert box["admission"].status is AdmissionDecisionStatus.ADMITTED
    assert invocations == {
        "ATT": 1,
        "BLF": 1,
        "CNC": 1,
        "PRD": 2,
        "PLAN": 1,
        "HABIT": 1,
        "ROUTE": 1,
        "ADMISSION": 1,
        "PROVIDER": 0,
    }
    assert result.cognition_requested is False
    assert result.cognition_result is None
    assert (intent.events, intent.current_intent) == intent_before


def test_admitted_result_does_not_mutate_any_existing_authority_or_cognition() -> None:
    cognition = PersistentCognition(
        identity=identity(),
        memories=(memory("existing"),),
    )
    intent = committed_intent()
    skill = SkillExecution.start(
        "skill-s13",
        skill_id="FLEE",
        intent_commitment=intent,
        at_ns=2,
        provenance=provenance("skill"),
    )
    proposed = ActionLifecycle.propose(
        "action-proposed",
        skill_execution=skill,
        intent_commitment=intent,
        at_ns=3,
        provenance=provenance("action-proposed"),
    )
    authorized = ActionLifecycle.propose(
        "action-authorized",
        skill_execution=skill,
        intent_commitment=intent,
        at_ns=4,
        provenance=provenance("action-authorized-proposed"),
    ).authorize(
        at_ns=5,
        provenance=provenance("action-authorized"),
        authority="explicit-authority",
    )
    issued = ActionLifecycle.propose(
        "action-issued",
        skill_execution=skill,
        intent_commitment=intent,
        at_ns=6,
        provenance=provenance("action-issued-proposed"),
    ).authorize(
        at_ns=7,
        provenance=provenance("action-issued-authorized"),
        authority="explicit-authority",
    ).issue(
        at_ns=8,
        deadline_ns=100,
        provenance=provenance("action-issued"),
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
        route,
        control,
    ) = full_upstream()
    assert control is not None
    before = (
        cognition,
        cognition.memories,
        intent.events,
        intent.current_intent,
        skill.events,
        proposed.events,
        authorized.events,
        issued.events,
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
    )

    decision = admit_control_candidate(
        control,
        route,
        intent,
        admission_criterion("MOVE_AWAY"),
        provenance=provenance("admission:authority-negative"),
    )

    assert decision.status is AdmissionDecisionStatus.ADMITTED
    assert cognition == before[0]
    assert cognition.memories == before[1]
    assert intent.events == before[2]
    assert intent.current_intent == before[3]
    assert skill.events == before[4]
    assert skill.state is SkillState.STARTED
    assert proposed.events == before[5]
    assert proposed.state is ActionState.PROPOSED
    assert authorized.events == before[6]
    assert authorized.state is ActionState.AUTHORIZED
    assert issued.events == before[7]
    assert issued.state is ActionState.ISSUED
    assert attention == before[8]
    assert belief == before[9]
    assert belief.status is BeliefStatus.SUPPORTED
    assert concept == before[10]
    assert concept.status is ConceptStatus.MATCHED
    assert wait_prediction == before[11]
    assert move_prediction == before[12]
    assert plan == before[13]
    assert learned == before[14]
    assert habit.repertoire == before[15]
    assert habit == before[16]
    assert route == before[17]
    assert control == before[18]

    with pytest.raises(InvalidLearningData, match="LearningFeedback"):
        propose_learning_update(
            learned,
            decision,  # type: ignore[arg-type]
            LearningUpdateRule(
                rule_id="bounded-step",
                version=1,
                step=1,
            ),
        )


def test_rejected_result_is_not_negative_learning_feedback() -> None:
    route, control = route_agreement()
    learned = LearningPreferenceState(
        target_id="risk_weight",
        value=3,
        minimum=0,
        maximum=10,
        revision=0,
        origin_provenance=provenance("learning-origin"),
    )
    rejected = admit_control_candidate(
        control,
        route,
        committed_intent(),
        admission_criterion("WAIT"),
        provenance=provenance("admission:rejected-not-feedback"),
    )
    assert rejected.status is AdmissionDecisionStatus.REJECTED
    with pytest.raises(InvalidLearningData, match="LearningFeedback"):
        propose_learning_update(
            learned,
            rejected,  # type: ignore[arg-type]
            LearningUpdateRule(
                rule_id="bounded-step",
                version=1,
                step=1,
            ),
        )
    assert learned.value == 3
    assert learned.revision == 0


def test_admission_decision_is_immutable_and_owns_no_execution_state() -> None:
    route, control = route_agreement()
    decision = admit_control_candidate(
        control,
        route,
        committed_intent(),
        admission_criterion("MOVE_AWAY"),
        provenance=provenance("admission:immutable"),
    )
    with pytest.raises(FrozenInstanceError):
        decision.status = AdmissionDecisionStatus.REJECTED  # type: ignore[misc]

    forbidden = {
        "intent",
        "intent_commitment",
        "skill",
        "skill_execution",
        "action",
        "action_supervisor",
        "authorization",
        "scheduler",
        "memory",
        "belief",
        "learning",
        "arbitration",
        "world",
        "callback",
    }
    assert forbidden.isdisjoint(AdmissionDecision.__dataclass_fields__)
    assert S13_ADMISSION_CAPABILITY_SPEC.state_scopes == ()
    assert S13_ADMISSION_OPERATOR_DESCRIPTOR.hidden_persistent_state is False
