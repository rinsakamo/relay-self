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
    ConceptCandidate,
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
    compile_epoch_plan,
    coordinate_planned_epoch,
)
from relay_self.execution_descriptor import (
    S12_DESCRIPTOR_SET,
    S12_ROUTE_CAPABILITY_SPEC,
    S12_ROUTE_CRITERION_DESCRIPTOR,
    S12_ROUTE_OPERATOR_DESCRIPTOR,
    CriterionKind,
    OperatorEffect,
    s12_capability_plan,
)
from relay_self.habit import (
    CueFeature,
    HabitCue,
    HabitRepertoire,
    HabitRule,
    HabitSelection,
    HabitSelectionStatus,
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
    PlanSelectionStatus,
    plan_candidate_from_prediction,
    select_plan,
)
from relay_self.prediction import (
    PredictionResult,
    PredictionStatus,
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
    RouteCandidate,
    RouteConflictPolicy,
    RouteCriterion,
    RouteDecision,
    RouteDecisionStatus,
    RouteSource,
    adjudicate_routes,
    control_candidate_from_route_decision,
    route_candidate_from_habit,
    route_candidate_from_plan,
)
from relay_self.route_profile import (
    S12_ROUTE_PROFILES,
    RouteProfileId,
    s12_route_profile,
)
from relay_self.skill import SkillExecution, SkillState


def provenance(reference: str) -> Provenance:
    return Provenance(source="s12-route-qualification", reference=reference)


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
    tie: bool = False,
) -> HabitRepertoire:
    rules = [
        HabitRule(
            habit_id="H1",
            cue_requirements=(
                CueFeature("concept", "spatial:nearby_threat"),
            ),
            candidate_ref="MOVE_AWAY",
            priority=10,
            provenance=provenance("habit:H1"),
        )
    ]
    if tie:
        rules.append(
            HabitRule(
                habit_id="H2",
                cue_requirements=(
                    CueFeature("concept", "spatial:nearby_threat"),
                ),
                candidate_ref="LOOK_AT_THREAT",
                priority=10,
                provenance=provenance("habit:H2"),
            )
        )
    return HabitRepertoire(
        repertoire_id="survival-habits",
        revision=7,
        rules=tuple(rules),
        provenance=provenance("habit-repertoire"),
    )


def habit_selection(
    *,
    tie: bool = False,
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
    return select_habit(habit_repertoire(tie=tie), cue)


def fail_closed() -> RouteCriterion:
    return RouteCriterion(
        criterion_id="explicit-fail-closed",
        conflict_policy=RouteConflictPolicy.FAIL_CLOSED,
    )


def identity() -> IdentitySpecification:
    return IdentitySpecification(
        self_id="self-s12",
        directives=("route decisions remain non-authoritative",),
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
        "intent-s12",
        objective="maintain existing objective",
        at_ns=1,
        provenance=provenance("intent"),
    )
    return owner


def integrated_upstream(
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
            AttentionCandidate(
                "E2",
                "belief-evidence:E2",
                provenance("attention:E2"),
                focus_keys=("other",),
            ),
        ),
        AttentionCriterion("focus-zombie", focus_key="zombie-1"),
    )
    selected = require_attention_selection(attention)
    assert selected.candidate_ids == ("E1",)
    belief = assess_belief(
        (evidence,),
        BeliefCriterion("zombie-nearby", proposition),
    )
    concept_source = concept_candidate_from_belief(
        belief,
        candidate_id="belief:zombie-nearby",
        payload_ref="transient:belief:zombie-nearby",
        provenance=provenance("belief-to-concept"),
    )
    concept = classify_concept(
        concept_source,
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
            assignments=(
                StateVariable("comparison_score", wait_score),
            ),
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
            assignments=(
                StateVariable("comparison_score", move_score),
            ),
            provenance=provenance("rule:move-away"),
        ),
    )
    wait = plan_candidate_from_prediction(
        wait_prediction,
        candidate_id="WAIT",
        feature_keys=("comparison_score",),
        provenance=provenance("prediction-to-plan:wait"),
        action_ref="WAIT",
    )
    move = plan_candidate_from_prediction(
        move_prediction,
        candidate_id="MOVE_AWAY",
        feature_keys=("comparison_score",),
        provenance=provenance("prediction-to-plan:move"),
        action_ref="MOVE_BACKWARD",
    )
    plan = select_plan(
        (wait, move),
        PlanningCriterion(
            criterion_id="minimize-comparison-score",
            feature_key="comparison_score",
            direction=PlanningDirection.MINIMIZE,
        ),
    )
    cue = HabitCue(
        cue_id="concept-nearby-threat",
        features=(CueFeature("concept", concept.concept.canonical),),
        provenance=provenance("concept-to-habit-cue"),
    )
    habit = select_habit(habit_repertoire(), cue)
    return (
        attention,
        belief,
        concept,
        wait_prediction,
        move_prediction,
        plan,
        habit,
    )


def test_package_exports_s12_route_surface() -> None:
    assert relay_self.RouteCandidate is RouteCandidate
    assert relay_self.RouteCriterion is RouteCriterion
    assert relay_self.RouteDecision is RouteDecision
    assert relay_self.ControlCandidate is ControlCandidate
    assert relay_self.adjudicate_routes is adjudicate_routes
    assert relay_self.RouteProfileId is RouteProfileId
    assert relay_self.S12_ROUTE_PROFILES is S12_ROUTE_PROFILES


def test_route_descriptor_is_stateless_read_only_integration_metadata() -> None:
    assert S12_ROUTE_CAPABILITY_SPEC.capability_id == "ROUTE"
    assert S12_ROUTE_CAPABILITY_SPEC.state_scopes == ()
    assert S12_ROUTE_CAPABILITY_SPEC.dependencies == ()
    assert S12_ROUTE_OPERATOR_DESCRIPTOR.operator_id == "route.adjudicate"
    assert S12_ROUTE_OPERATOR_DESCRIPTOR.effect is OperatorEffect.READ_ONLY
    assert S12_ROUTE_OPERATOR_DESCRIPTOR.hidden_persistent_state is False
    assert S12_ROUTE_OPERATOR_DESCRIPTOR.writes == (
        "transient.route_decision",
    )
    assert (
        S12_ROUTE_CRITERION_DESCRIPTOR.kind
        is CriterionKind.COGNITIVE_ORIENTATION
    )


def test_route_profiles_are_integration_only_and_explicit() -> None:
    assert [profile.profile_id for profile in S12_ROUTE_PROFILES] == [
        RouteProfileId.ROUTE,
        RouteProfileId.PLAN_ROUTE,
        RouteProfileId.HABIT_ROUTE,
        RouteProfileId.PLAN_HABIT_ROUTE,
        RouteProfileId.FULL_DETERMINISTIC_ROUTE,
    ]
    assert s12_route_profile(
        RouteProfileId.PLAN_HABIT_ROUTE
    ).enabled_ids == frozenset({"PLAN", "HABIT", "ROUTE"})


def test_plan_only_route_is_selected_when_single_source_is_allowed() -> None:
    plan = plan_selection()
    decision = adjudicate_routes(
        plan,
        None,
        fail_closed(),
        provenance=provenance("route:plan-only"),
    )
    assert decision.status is RouteDecisionStatus.SELECTED
    assert decision.selected_candidate_ref == "MOVE_AWAY"
    assert decision.selected_source is RouteSource.PLAN
    assert decision.plan_candidate is not None
    assert decision.habit_candidate is None


def test_habit_only_route_is_selected_when_single_source_is_allowed() -> None:
    habit = habit_selection()
    decision = adjudicate_routes(
        None,
        habit,
        fail_closed(),
        provenance=provenance("route:habit-only"),
    )
    assert decision.status is RouteDecisionStatus.SELECTED
    assert decision.selected_candidate_ref == "MOVE_AWAY"
    assert decision.selected_source is RouteSource.HABIT
    assert decision.plan_candidate is None
    assert decision.habit_candidate is not None


def test_single_source_can_remain_explicitly_undetermined() -> None:
    criterion = RouteCriterion(
        criterion_id="agreement-required",
        conflict_policy=RouteConflictPolicy.FAIL_CLOSED,
        allow_single_source=False,
    )
    decision = adjudicate_routes(
        plan_selection(),
        None,
        criterion,
        provenance=provenance("route:single-disabled"),
    )
    assert decision.status is RouteDecisionStatus.UNDETERMINED
    assert decision.selected_candidate_ref is None
    assert control_candidate_from_route_decision(decision) is None


def test_plan_and_habit_same_candidate_are_agreed_without_extra_authority() -> None:
    decision = adjudicate_routes(
        plan_selection(),
        habit_selection(),
        fail_closed(),
        provenance=provenance("route:agreement"),
    )
    assert decision.status is RouteDecisionStatus.AGREED
    assert decision.selected_candidate_ref == "MOVE_AWAY"
    assert decision.selected_source is None
    control = control_candidate_from_route_decision(decision)
    assert isinstance(control, ControlCandidate)
    assert control.candidate_ref == "MOVE_AWAY"
    assert control.route_status is RouteDecisionStatus.AGREED
    assert control.selected_source is None


def test_conflict_fail_closed_has_no_control_candidate() -> None:
    decision = adjudicate_routes(
        plan_selection(wait_score=1, move_score=5),
        habit_selection(),
        fail_closed(),
        provenance=provenance("route:conflict"),
    )
    assert decision.status is RouteDecisionStatus.CONFLICT
    assert decision.selected_candidate_ref is None
    assert decision.plan_candidate is not None
    assert decision.plan_candidate.candidate_ref == "WAIT"
    assert decision.habit_candidate is not None
    assert decision.habit_candidate.candidate_ref == "MOVE_AWAY"
    assert control_candidate_from_route_decision(decision) is None


@pytest.mark.parametrize(
    ("policy", "expected_ref", "expected_source"),
    (
        (RouteConflictPolicy.PLAN_WINS, "WAIT", RouteSource.PLAN),
        (
            RouteConflictPolicy.HABIT_WINS,
            "MOVE_AWAY",
            RouteSource.HABIT,
        ),
    ),
)
def test_explicit_conflict_override_works_only_when_criterion_says_so(
    policy: RouteConflictPolicy,
    expected_ref: str,
    expected_source: RouteSource,
) -> None:
    decision = adjudicate_routes(
        plan_selection(wait_score=1, move_score=5),
        habit_selection(),
        RouteCriterion(
            criterion_id=f"explicit-{policy.value}",
            conflict_policy=policy,
        ),
        provenance=provenance(f"route:{policy.value}"),
    )
    assert decision.status is RouteDecisionStatus.SELECTED
    assert decision.selected_candidate_ref == expected_ref
    assert decision.selected_source is expected_source
    assert decision.plan_candidate is not None
    assert decision.habit_candidate is not None


def test_plan_tied_and_undetermined_never_fabricate_route_candidate() -> None:
    tied = plan_selection(wait_score=3, move_score=3)
    assert tied.status is PlanSelectionStatus.TIED
    assert route_candidate_from_plan(tied) is None
    decision = adjudicate_routes(
        tied,
        habit_selection(no_match=True),
        fail_closed(),
        provenance=provenance("route:no-candidate-tied"),
    )
    assert decision.status is RouteDecisionStatus.NO_CANDIDATE

    malformed_candidate = PlanCandidate(
        candidate_id="UNRANKABLE",
        outcome_features=(),
        provenance=provenance("plan:unrankable"),
    )
    undetermined = select_plan(
        (malformed_candidate,),
        PlanningCriterion(
            criterion_id="missing-score",
            feature_key="comparison_score",
            direction=PlanningDirection.MINIMIZE,
        ),
    )
    assert undetermined.status is PlanSelectionStatus.UNDETERMINED
    assert route_candidate_from_plan(undetermined) is None
    decision = adjudicate_routes(
        undetermined,
        habit_selection(no_match=True),
        fail_closed(),
        provenance=provenance("route:no-candidate-undetermined"),
    )
    assert decision.status is RouteDecisionStatus.NO_CANDIDATE


def test_habit_tied_and_no_match_never_fabricate_route_candidate() -> None:
    tied = habit_selection(tie=True)
    no_match = habit_selection(no_match=True)
    assert tied.status is HabitSelectionStatus.TIED
    assert no_match.status is HabitSelectionStatus.NO_MATCH
    assert route_candidate_from_habit(tied) is None
    assert route_candidate_from_habit(no_match) is None
    assert adjudicate_routes(
        None,
        no_match,
        fail_closed(),
        provenance=provenance("route:no-habit"),
    ).status is RouteDecisionStatus.NO_CANDIDATE


def test_malformed_route_inputs_and_candidate_mismatch_fail_closed() -> None:
    with pytest.raises(InvalidRouteData, match="criterion_id"):
        RouteCriterion(criterion_id="")
    with pytest.raises(InvalidRouteData, match="RouteConflictPolicy"):
        RouteCriterion(
            criterion_id="bad-policy",
            conflict_policy="habit_wins",  # type: ignore[arg-type]
        )
    with pytest.raises(InvalidRouteData, match="PlanSelection"):
        adjudicate_routes(
            object(),  # type: ignore[arg-type]
            None,
            fail_closed(),
            provenance=provenance("bad-plan-input"),
        )
    with pytest.raises(InvalidRouteData, match="structured identifier"):
        RouteCandidate(
            source=RouteSource.PLAN,
            candidate_ref="MOVE AWAY",
            source_ref="plan:bad",
            provenance=provenance("bad-route-candidate"),
        )

    plan_candidate = route_candidate_from_plan(plan_selection())
    assert plan_candidate is not None
    with pytest.raises(InvalidRouteData, match="does not match"):
        RouteDecision(
            status=RouteDecisionStatus.SELECTED,
            criterion=fail_closed(),
            selected_candidate_ref="WAIT",
            selected_source=RouteSource.PLAN,
            plan_candidate=plan_candidate,
            habit_candidate=None,
            provenance=provenance("mismatched-decision"),
        )


def test_provider_expression_cannot_become_route_policy_or_source_selection() -> None:
    expression = ProviderExpression(
        text="Follow the habit this time.",
        provenance=provenance("provider-policy"),
    )
    with pytest.raises(InvalidRouteData, match="RouteCriterion"):
        adjudicate_routes(
            plan_selection(),
            habit_selection(),
            expression,  # type: ignore[arg-type]
            provenance=provenance("route:provider-policy"),
        )
    with pytest.raises(InvalidRouteData, match="PlanSelection"):
        adjudicate_routes(
            expression,  # type: ignore[arg-type]
            habit_selection(),
            fail_closed(),
            provenance=provenance("route:provider-plan"),
        )


def test_route_off_suppresses_arbitration_while_plan_and_habit_exist() -> None:
    box: dict[str, object] = {}

    def choose_plan() -> None:
        box["plan"] = plan_selection()

    def choose_habit() -> None:
        box["habit"] = habit_selection()

    bindings = (
        EpochBinding("plan-1", "plan.select", choose_plan),
        EpochBinding("habit-1", "habit.select", choose_habit),
    )
    epoch = compile_epoch_plan(
        s12_capability_plan(enabled_ids=frozenset({"PLAN", "HABIT"})),
        S12_DESCRIPTOR_SET,
        due_items=(
            EpochWorkItem("plan-1", "plan.select", "explicit-plan-input"),
            EpochWorkItem("habit-1", "habit.select", "explicit-habit-input"),
            EpochWorkItem("route-1", "route.adjudicate", "route-disabled"),
        ),
        bindings=bindings,
    )
    result = coordinate_planned_epoch(
        ActionSupervisor(),
        epoch,
        bindings=bindings,
        at_ns=10,
        provenance=provenance("epoch-route-off"),
    )
    assert isinstance(box["plan"], PlanSelection)
    assert isinstance(box["habit"], HabitSelection)
    assert "route" not in box
    assert result.executed_work_ids == ("plan-1", "habit-1")
    assert result.suppressed_work_ids == ("route-1",)
    assert result.cognition_requested is False


def test_route_on_executes_as_explicit_zero_cognition_epoch_work() -> None:
    box: dict[str, object] = {}

    def choose_plan() -> None:
        box["plan"] = plan_selection()

    def choose_habit() -> None:
        box["habit"] = habit_selection()

    def route() -> None:
        box["route"] = adjudicate_routes(
            box.get("plan"),  # type: ignore[arg-type]
            box.get("habit"),  # type: ignore[arg-type]
            fail_closed(),
            provenance=provenance("route:epoch"),
        )

    bindings = (
        EpochBinding("plan-1", "plan.select", choose_plan),
        EpochBinding("habit-1", "habit.select", choose_habit),
        EpochBinding("route-1", "route.adjudicate", route),
    )
    epoch = compile_epoch_plan(
        s12_route_profile(RouteProfileId.PLAN_HABIT_ROUTE).plan(),
        S12_DESCRIPTOR_SET,
        due_items=(
            EpochWorkItem("plan-1", "plan.select", "plan-ready"),
            EpochWorkItem("habit-1", "habit.select", "habit-ready"),
            EpochWorkItem("route-1", "route.adjudicate", "both-ready"),
        ),
        bindings=bindings,
    )
    result = coordinate_planned_epoch(
        ActionSupervisor(),
        epoch,
        bindings=bindings,
        at_ns=10,
        provenance=provenance("epoch-route-on"),
    )
    decision = box["route"]
    assert isinstance(decision, RouteDecision)
    assert decision.status is RouteDecisionStatus.AGREED
    assert result.executed_work_ids == ("plan-1", "habit-1", "route-1")
    assert result.cognition_requested is False
    assert result.cognition_result is None


def test_existing_ctl_services_action_supervision_before_route_work() -> None:
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
        provenance=provenance("action-supervised"),
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
    box: dict[str, object] = {}

    def route() -> None:
        assert supervisor.get("action-supervised").state is ActionState.TIMEOUT
        box["route"] = adjudicate_routes(
            plan_selection(),
            habit_selection(),
            fail_closed(),
            provenance=provenance("route:after-supervision"),
        )

    binding = EpochBinding("route-1", "route.adjudicate", route)
    epoch = compile_epoch_plan(
        s12_capability_plan(enabled_ids=frozenset({"ROUTE"})),
        S12_DESCRIPTOR_SET,
        due_items=(
            EpochWorkItem("route-1", "route.adjudicate", "explicit-route"),
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
    assert box["route"].status is RouteDecisionStatus.AGREED


def test_full_deterministic_multi_route_integration_uses_zero_provider_calls() -> None:
    box: dict[str, object] = {}
    invocations = {
        "ATT": 0,
        "BLF": 0,
        "CNC": 0,
        "PRD": 0,
        "PLAN": 0,
        "HABIT": 0,
        "ROUTE": 0,
        "PROVIDER": 0,
    }
    proposition = PropositionKey("entity", "zombie-1", "nearby")
    evidence_by_id = {
        "E1": BeliefEvidence(
            "E1",
            proposition,
            EvidenceRelation.SUPPORT,
            provenance("evidence:E1"),
        )
    }
    source_candidates = (
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
            source_candidates,
            AttentionCriterion("focus-zombie", focus_key="zombie-1"),
        )

    def believe() -> None:
        invocations["BLF"] += 1
        selection = require_attention_selection(box.get("attention"))
        box["belief"] = assess_belief(
            tuple(evidence_by_id[item.candidate_id] for item in selection.selected),
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

    def base_state() -> object:
        return prediction_state_from_concept(
            box.get("concept"),
            state_id="threat:zombie-1",
            extra_variables=(StateVariable("comparison_score", 99),),
            provenance=provenance("concept-to-prediction"),
        )

    def predict_wait() -> None:
        invocations["PRD"] += 1
        box["wait_prediction"] = predict_transition(
            base_state(),  # type: ignore[arg-type]
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
            base_state(),  # type: ignore[arg-type]
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

    def route() -> None:
        invocations["ROUTE"] += 1
        box["route"] = adjudicate_routes(
            box.get("plan"),  # type: ignore[arg-type]
            box.get("habit"),  # type: ignore[arg-type]
            fail_closed(),
            provenance=provenance("route:full-chain"),
        )

    bindings = (
        EpochBinding("att-1", "att.select", attend),
        EpochBinding("blf-1", "blf.assess", believe),
        EpochBinding("cnc-1", "cnc.classify", conceptualize),
        EpochBinding("prd-wait", "prd.predict", predict_wait),
        EpochBinding("prd-move", "prd.predict", predict_move),
        EpochBinding("plan-1", "plan.select", choose_plan),
        EpochBinding("habit-1", "habit.select", choose_habit),
        EpochBinding("route-1", "route.adjudicate", route),
    )
    epoch = compile_epoch_plan(
        s12_route_profile(RouteProfileId.FULL_DETERMINISTIC_ROUTE).plan(),
        S12_DESCRIPTOR_SET,
        due_items=(
            EpochWorkItem("att-1", "att.select", "evidence-ready"),
            EpochWorkItem("blf-1", "blf.assess", "attention-ready"),
            EpochWorkItem("cnc-1", "cnc.classify", "belief-ready"),
            EpochWorkItem("prd-wait", "prd.predict", "concept-ready-wait"),
            EpochWorkItem("prd-move", "prd.predict", "concept-ready-move"),
            EpochWorkItem("plan-1", "plan.select", "predictions-ready"),
            EpochWorkItem("habit-1", "habit.select", "concept-ready-habit"),
            EpochWorkItem("route-1", "route.adjudicate", "routes-ready"),
        ),
        bindings=bindings,
    )
    result = coordinate_planned_epoch(
        ActionSupervisor(),
        epoch,
        bindings=bindings,
        at_ns=10,
        provenance=provenance("epoch:full-route"),
    )
    decision = box["route"]
    assert isinstance(decision, RouteDecision)
    assert decision.status is RouteDecisionStatus.AGREED
    assert decision.selected_candidate_ref == "MOVE_AWAY"
    assert invocations == {
        "ATT": 1,
        "BLF": 1,
        "CNC": 1,
        "PRD": 2,
        "PLAN": 1,
        "HABIT": 1,
        "ROUTE": 1,
        "PROVIDER": 0,
    }
    assert result.cognition_requested is False
    assert result.cognition_result is None


def test_full_route_disagreement_remains_non_executable() -> None:
    (
        attention,
        belief,
        concept,
        wait_prediction,
        move_prediction,
        plan,
        habit,
    ) = integrated_upstream(wait_score=1, move_score=5)
    assert plan.selected is not None
    assert plan.selected.candidate_id == "WAIT"
    assert habit.selected_candidate_ref == "MOVE_AWAY"
    decision = adjudicate_routes(
        plan,
        habit,
        fail_closed(),
        provenance=provenance("route:integrated-conflict"),
    )
    assert decision.status is RouteDecisionStatus.CONFLICT
    assert control_candidate_from_route_decision(decision) is None
    assert attention.candidate_ids == ("E1",)
    assert belief.status is BeliefStatus.SUPPORTED
    assert concept.status is ConceptStatus.MATCHED
    assert wait_prediction.status is PredictionStatus.PREDICTED
    assert move_prediction.status is PredictionStatus.PREDICTED


def test_route_decision_is_immutable_and_sources_remain_unchanged() -> None:
    plan = plan_selection()
    habit = habit_selection()
    before = (plan, habit, habit.repertoire.rules, habit.repertoire.revision)
    decision = adjudicate_routes(
        plan,
        habit,
        fail_closed(),
        provenance=provenance("route:immutable"),
    )
    assert (plan, habit, habit.repertoire.rules, habit.repertoire.revision) == before
    with pytest.raises(FrozenInstanceError):
        decision.status = RouteDecisionStatus.CONFLICT  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        decision.plan_candidate.candidate_ref = "WAIT"  # type: ignore[union-attr,misc]


def test_route_adjudication_does_not_mutate_any_existing_authority_owner() -> None:
    intent_owner = committed_intent()
    skill = SkillExecution.start(
        "skill-s12",
        skill_id="FLEE",
        intent_commitment=intent_owner,
        at_ns=2,
        provenance=provenance("skill"),
    )
    proposed = ActionLifecycle.propose(
        "action-proposed",
        skill_execution=skill,
        intent_commitment=intent_owner,
        at_ns=3,
        provenance=provenance("action-proposed"),
    )
    authorized = ActionLifecycle.propose(
        "action-authorized",
        skill_execution=skill,
        intent_commitment=intent_owner,
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
        intent_commitment=intent_owner,
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
    ) = integrated_upstream()
    before = (
        cognition,
        intent_owner.events,
        intent_owner.current_intent,
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
    )

    decision = adjudicate_routes(
        plan,
        habit,
        fail_closed(),
        provenance=provenance("route:authority-negative"),
    )
    control = control_candidate_from_route_decision(decision)

    assert isinstance(control, ControlCandidate)
    assert cognition == before[0]
    assert intent_owner.events == before[1]
    assert intent_owner.current_intent == before[2]
    assert skill.events == before[3]
    assert skill.state is SkillState.STARTED
    assert proposed.events == before[4]
    assert proposed.state is ActionState.PROPOSED
    assert authorized.events == before[5]
    assert authorized.state is ActionState.AUTHORIZED
    assert issued.events == before[6]
    assert issued.state is ActionState.ISSUED
    assert attention == before[7]
    assert belief == before[8]
    assert concept == before[9]
    assert wait_prediction == before[10]
    assert move_prediction == before[11]
    assert plan == before[12]
    assert learned == before[13]
    assert habit.repertoire == before[14]
    assert habit == before[15]

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


def test_no_central_executive_or_persistent_route_owner_is_declared() -> None:
    assert S12_ROUTE_CAPABILITY_SPEC.state_scopes == ()
    assert S12_ROUTE_OPERATOR_DESCRIPTOR.effect is OperatorEffect.READ_ONLY
    assert S12_ROUTE_OPERATOR_DESCRIPTOR.hidden_persistent_state is False
    assert set(RouteDecision.__dataclass_fields__) == {
        "status",
        "criterion",
        "selected_candidate_ref",
        "selected_source",
        "plan_candidate",
        "habit_candidate",
        "provenance",
    }
    forbidden = {
        "memory",
        "belief",
        "concept",
        "prediction",
        "plan_owner",
        "habit_owner",
        "current_intent",
        "skill",
        "action_supervisor",
        "scheduler",
        "learning_state",
    }
    assert forbidden.isdisjoint(RouteDecision.__dataclass_fields__)
